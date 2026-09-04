"""Deterministic, auditable lifecycle management for filled paper spreads."""

from __future__ import annotations

from collections import defaultdict
from datetime import date, datetime, timezone
from enum import Enum


FINAL_ORDER_STATES = frozenset({'canceled', 'expired', 'rejected', 'replaced'})


class PositionState(str, Enum):
    """Persisted lifecycle states shared by the monitor and audit database."""

    PENDING_ENTRY = 'PENDING_ENTRY'
    OPEN = 'OPEN'
    EXIT_SUBMITTING = 'EXIT_SUBMITTING'
    EXIT_PENDING = 'EXIT_PENDING'
    CLOSED = 'CLOSED'
    ENTRY_FAILED = 'ENTRY_FAILED'


class ExitReason(str, Enum):
    """Stable reason codes used in reports and lifecycle events."""

    TAKE_PROFIT = 'TAKE_PROFIT'
    STOP_LOSS = 'STOP_LOSS'
    MAX_HOLDING_PERIOD = 'MAX_HOLDING_PERIOD'
    EXPIRY_WINDOW = 'EXPIRY_WINDOW'
    HOLD = 'HOLD'


def _as_datetime(value):
    if not value:
        return None
    parsed = value if isinstance(value, datetime) else datetime.fromisoformat(
        str(value).replace('Z', '+00:00')
    )
    return parsed if parsed.tzinfo else parsed.replace(tzinfo=timezone.utc)


def business_days_elapsed(start, end):
    """Count completed weekdays after ``start`` through ``end``."""
    current = start.date()
    finish = end.date()
    count = 0
    while current < finish:
        current = current.fromordinal(current.toordinal() + 1)
        if current.weekday() < 5:
            count += 1
    return count


class ExitPolicyEngine:
    """Evaluate sealed dollar thresholds without broker side effects."""

    def evaluate(self, position, unrealized_pnl, now=None):
        now = now or datetime.now(timezone.utc)
        expiration = position.get('expiration_date')
        if expiration:
            dte = (date.fromisoformat(str(expiration)[:10]) - now.date()).days
            if dte <= int(position['exit_before_expiry_days']):
                return {'exit': True, 'reason': ExitReason.EXPIRY_WINDOW.value,
                        'detail': f'{dte} calendar day(s) to expiry'}
        if unrealized_pnl <= -float(position['stop_loss_limit']):
            return {'exit': True, 'reason': ExitReason.STOP_LOSS.value,
                    'detail': f"${unrealized_pnl:,.2f} <= -${float(position['stop_loss_limit']):,.2f}"}
        if unrealized_pnl >= float(position['take_profit_target']):
            return {'exit': True, 'reason': ExitReason.TAKE_PROFIT.value,
                    'detail': f"${unrealized_pnl:,.2f} >= ${float(position['take_profit_target']):,.2f}"}
        opened = _as_datetime(position.get('opened_at'))
        if opened and business_days_elapsed(opened, now) >= int(position['max_holding_days']):
            return {'exit': True, 'reason': ExitReason.MAX_HOLDING_PERIOD.value,
                    'detail': f"{business_days_elapsed(opened, now)} trading day(s) held"}
        return {'exit': False, 'reason': ExitReason.HOLD.value,
                'detail': 'No sealed exit threshold was reached.'}


class PositionLifecycleManager:
    """Reconcile entries, value spreads, and submit idempotent paper exits."""

    def __init__(self, broker, logger, automated_exits_enabled=False, now_fn=None,
                 max_quote_age_seconds=300):
        self.broker = broker
        self.logger = logger
        self.automated_exits_enabled = bool(automated_exits_enabled)
        self.now_fn = now_fn or (lambda: datetime.now(timezone.utc))
        self.max_quote_age_seconds = int(max_quote_age_seconds)
        self.policy = ExitPolicyEngine()

    @staticmethod
    def unrealized_pnl(position, exit_cashflow_per_share):
        opening_cashflow = -float(position['entry_price'])
        return round(
            (opening_cashflow + float(exit_cashflow_per_share))
            * float(position.get('multiplier', 100)) * int(position['qty']), 2,
        )

    def _event(self, position, event, after, reason, detail=None):
        self.logger.log_position_event(
            position['id'], event, position['status'], after, reason, detail,
        )

    def _reconcile_entry(self, position):
        order = self.broker.get_order(position['entry_order_id'])
        status = str(order.get('status', 'unknown')).lower()
        if status == 'filled':
            raw_price = order.get('filled_avg_price')
            entry_price = float(position['entry_price'])
            if raw_price not in (None, ''):
                magnitude = abs(float(raw_price))
                entry_price = magnitude if position['spread_type'] == 'debit' else -magnitude
            opened_at = order.get('filled_at') or self.now_fn().isoformat()
            self.logger.update_managed_position(
                position['id'], status=PositionState.OPEN.value, opened_at=opened_at,
                entry_price=entry_price, last_checked_at=self.now_fn().isoformat(),
            )
            self._event(position, 'ENTRY_FILLED', PositionState.OPEN.value,
                        'Broker confirmed every spread leg filled.', order)
            return {'position_id': position['id'], 'action': 'ENTRY_FILLED',
                    'status': PositionState.OPEN.value}
        if status in FINAL_ORDER_STATES:
            self.logger.update_managed_position(
                position['id'], status=PositionState.ENTRY_FAILED.value,
                last_checked_at=self.now_fn().isoformat(),
            )
            self._event(position, 'ENTRY_FAILED', PositionState.ENTRY_FAILED.value,
                        f'Broker entry state: {status}', order)
            return {'position_id': position['id'], 'action': 'ENTRY_FAILED',
                    'status': PositionState.ENTRY_FAILED.value}
        self.logger.update_managed_position(
            position['id'], last_checked_at=self.now_fn().isoformat(),
        )
        return {'position_id': position['id'], 'action': 'WAIT_ENTRY', 'status': status}

    def _reconcile_exit(self, position):
        order = self.broker.get_order(position['exit_order_id'])
        status = str(order.get('status', 'unknown')).lower()
        if status == 'filled':
            raw_price = order.get('filled_avg_price')
            # Alpaca MLeg prices are signed: positive is debit, negative is
            # credit. Cash flow is therefore the inverse of the broker price.
            close_cashflow = -float(raw_price) if raw_price not in (None, '') else 0.0
            realized = self.unrealized_pnl(position, close_cashflow)
            closed_at = order.get('filled_at') or self.now_fn().isoformat()
            self.logger.update_managed_position(
                position['id'], status=PositionState.CLOSED.value,
                closed_at=closed_at, realized_pnl=realized,
                last_checked_at=self.now_fn().isoformat(),
            )
            self._event(position, 'EXIT_FILLED', PositionState.CLOSED.value,
                        position.get('exit_reason') or 'EXIT', order)
            return {'position_id': position['id'], 'action': 'EXIT_FILLED',
                    'status': PositionState.CLOSED.value, 'realized_pnl': realized}
        if status in FINAL_ORDER_STATES:
            self.logger.update_managed_position(
                position['id'], status=PositionState.OPEN.value,
                exit_order_id=None, exit_client_order_id=None,
                exit_submitted_at=None,
                last_checked_at=self.now_fn().isoformat(),
            )
            self._event(position, 'EXIT_NOT_FILLED', PositionState.OPEN.value,
                        f'Broker exit state: {status}', order)
            return {'position_id': position['id'], 'action': 'EXIT_NOT_FILLED',
                    'status': PositionState.OPEN.value}
        return {'position_id': position['id'], 'action': 'WAIT_EXIT', 'status': status}

    def _quote_is_fresh(self, quote, now):
        timestamps = [
            _as_datetime(item.get('timestamp'))
            for item in quote.get('quotes', {}).values()
        ]
        if not timestamps or any(value is None for value in timestamps):
            return False, None
        oldest_age = max((now - value).total_seconds() for value in timestamps)
        return 0 <= oldest_age <= self.max_quote_age_seconds, round(oldest_age, 3)

    def _monitor_open(self, position, execute):
        now = self.now_fn()
        try:
            quote = self.broker.quote_spread_exit(position['opening_legs'])
            pnl = self.unrealized_pnl(position, quote['cashflow_per_share'])
        except Exception as exc:
            self.logger.update_managed_position(
                position['id'], last_checked_at=now.isoformat(),
            )
            self._event(position, 'VALUATION_FAILED', PositionState.OPEN.value, str(exc))
            return {'position_id': position['id'], 'action': 'VALUATION_FAILED',
                    'reason': str(exc)}

        quote_fresh, quote_age = self._quote_is_fresh(quote, now)
        self.logger.update_managed_position(
            position['id'], last_mark=quote['cashflow_per_share'], last_pnl=pnl,
            last_checked_at=now.isoformat(),
        )
        decision = self.policy.evaluate(position, pnl, now)
        if not decision['exit']:
            return {'position_id': position['id'], 'action': 'HOLD', 'pnl': pnl,
                    'quote_fresh': quote_fresh, 'quote_age_seconds': quote_age,
                    **decision}

        self._event(position, 'EXIT_RECOMMENDED', PositionState.OPEN.value,
                    decision['reason'], {'policy': decision, 'pnl': pnl, 'quote': quote})
        if not execute or not self.automated_exits_enabled:
            return {'position_id': position['id'], 'action': 'EXIT_RECOMMENDED',
                    'pnl': pnl, 'quote_fresh': quote_fresh,
                    'quote_age_seconds': quote_age, **decision}

        if not quote_fresh:
            detail = ('Exit quote has no broker timestamp.' if quote_age is None else
                      f'Oldest exit quote is {quote_age:.1f}s old; limit is '
                      f'{self.max_quote_age_seconds}s.')
            self._event(position, 'EXIT_DEFERRED', PositionState.OPEN.value,
                        'STALE_EXIT_QUOTE', {'detail': detail, 'quote': quote})
            return {'position_id': position['id'], 'action': 'EXIT_DEFERRED',
                    'reason': 'STALE_EXIT_QUOTE', 'detail': detail, 'pnl': pnl}

        clock = self.broker.get_market_clock()
        market_is_open = clock.get('is_open') is True or str(clock.get('is_open')).lower() == 'true'
        if not market_is_open:
            self._event(position, 'EXIT_DEFERRED', PositionState.OPEN.value,
                        'Alpaca market clock is closed.', clock)
            return {'position_id': position['id'], 'action': 'EXIT_DEFERRED',
                    'reason': 'MARKET_CLOSED', 'pnl': pnl}

        attempt = self.logger.claim_managed_position_exit(position['id'], decision['reason'])
        if attempt is None:
            return {'position_id': position['id'], 'action': 'EXIT_ALREADY_CLAIMED',
                    'reason': decision['reason'], 'pnl': pnl}

        client_order_id = f"cs-exit-{position['id']}-{attempt}"
        self.logger.update_managed_position(
            position['id'], exit_client_order_id=client_order_id,
        )
        try:
            response = self.broker.close_option_spread(
                position['opening_legs'], qty=position['qty'],
                limit_price=quote['limit_price'], client_order_id=client_order_id,
            )
            if not response.get('order_id'):
                raise ValueError('broker did not return an exit order id')
        except Exception as exc:
            # A transport error can occur after Alpaca accepted an order. Keep
            # the claim locked until the client ID is reconciled; reopening the
            # row here could submit a duplicate close on the next cycle.
            self._event(position, 'EXIT_SUBMISSION_UNCERTAIN',
                        PositionState.EXIT_SUBMITTING.value, str(exc),
                        {'policy': decision, 'client_order_id': client_order_id})
            return {'position_id': position['id'],
                    'action': 'EXIT_SUBMISSION_UNCERTAIN', 'reason': str(exc),
                    'client_order_id': client_order_id, 'pnl': pnl}

        self.logger.update_managed_position(
            position['id'], status=PositionState.EXIT_PENDING.value,
            exit_reason=decision['reason'], exit_order_id=response['order_id'],
            exit_submitted_at=now.isoformat(), last_checked_at=now.isoformat(),
        )
        self._event(position, 'EXIT_SUBMITTED', PositionState.EXIT_PENDING.value,
                    decision['reason'], {**response, 'client_order_id': client_order_id})
        return {'position_id': position['id'], 'action': 'EXIT_SUBMITTED',
                'order_id': response['order_id'], 'client_order_id': client_order_id,
                'reason': decision['reason'], 'pnl': pnl}

    @staticmethod
    def _broker_mismatches(open_positions, broker_positions):
        """Compare registered option-leg exposure with the broker inventory."""
        expected = defaultdict(float)
        for position in open_positions:
            for leg in position['opening_legs']:
                direction = 1 if leg['side'].lower() == 'buy' else -1
                ratio = float(leg.get('ratio_qty', 1))
                expected[leg['symbol']] += direction * ratio * int(position['qty'])

        actual = {item['symbol']: float(item['qty']) for item in broker_positions}
        mismatches = {}
        for symbol, expected_qty in expected.items():
            actual_qty = actual.get(symbol, 0.0)
            if expected_qty and (actual_qty * expected_qty <= 0
                                 or abs(actual_qty) < abs(expected_qty)):
                mismatches[symbol] = {'expected_at_least': expected_qty,
                                      'actual': actual_qty}
        return mismatches

    def run(self, execute=False):
        positions = self.logger.get_managed_positions(active_only=True)
        open_positions = [
            item for item in positions if item['status'] == PositionState.OPEN.value
        ]
        broker_mismatches = {}
        reconciliation_error = None
        if open_positions:
            try:
                broker_positions = self.broker.get_positions(raise_on_error=True)
                broker_mismatches = self._broker_mismatches(open_positions, broker_positions)
            except Exception as exc:
                reconciliation_error = str(exc)

        results = []
        for position in positions:
            status = position['status']
            if status == PositionState.PENDING_ENTRY.value:
                results.append(self._reconcile_entry(position))
            elif status == PositionState.EXIT_PENDING.value:
                results.append(self._reconcile_exit(position))
            elif status == PositionState.EXIT_SUBMITTING.value:
                results.append({
                    'position_id': position['id'],
                    'action': 'EXIT_SUBMISSION_UNCERTAIN',
                    'reason': ('A prior process claimed this exit but did not persist '
                               'an order id; reconcile by client order id before retrying.'),
                    'client_order_id': position.get('exit_client_order_id'),
                })
            elif status == PositionState.OPEN.value:
                relevant = {
                    leg['symbol']: broker_mismatches[leg['symbol']]
                    for leg in position['opening_legs']
                    if leg['symbol'] in broker_mismatches
                }
                if reconciliation_error or relevant:
                    detail = {'error': reconciliation_error, 'mismatches': relevant}
                    self.logger.update_managed_position(
                        position['id'], last_checked_at=self.now_fn().isoformat(),
                    )
                    self._event(position, 'BROKER_RECONCILIATION_FAILED',
                                PositionState.OPEN.value,
                                'Registered legs do not match confirmed broker inventory.',
                                detail)
                    results.append({
                        'position_id': position['id'],
                        'action': 'BROKER_RECONCILIATION_FAILED',
                        'reason': reconciliation_error or 'POSITION_MISMATCH',
                        'detail': relevant,
                    })
                else:
                    results.append(self._monitor_open(position, execute=execute))
        return results
