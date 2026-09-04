from datetime import datetime, timedelta, timezone

from agent.position_manager import ExitPolicyEngine, PositionLifecycleManager
from compliance.audit_logger import AuditLogger


NOW = datetime(2026, 9, 3, 15, 0, tzinfo=timezone.utc)


def position(**changes):
    base = {
        'id': 1, 'status': 'OPEN', 'spread_type': 'debit', 'qty': 1,
        'multiplier': 100, 'entry_price': 1.0, 'take_profit_target': 200,
        'stop_loss_limit': 100, 'max_holding_days': 5,
        'exit_before_expiry_days': 2, 'expiration_date': '2026-09-25',
        'opened_at': '2026-09-02T15:00:00+00:00',
        'opening_legs': [{'symbol': 'NEAR', 'side': 'buy'}, {'symbol': 'FAR', 'side': 'sell'}],
    }
    base.update(changes)
    return base


def test_exit_policy_covers_profit_loss_time_and_expiry():
    engine = ExitPolicyEngine()
    assert engine.evaluate(position(), 200, NOW)['reason'] == 'TAKE_PROFIT'
    assert engine.evaluate(position(), -100, NOW)['reason'] == 'STOP_LOSS'
    old = position(opened_at=(NOW - timedelta(days=9)).isoformat())
    assert engine.evaluate(old, 0, NOW)['reason'] == 'MAX_HOLDING_PERIOD'
    expiring = position(expiration_date='2026-09-04')
    assert engine.evaluate(expiring, -500, NOW)['reason'] == 'EXPIRY_WINDOW'


class Broker:
    def __init__(self, cashflow=3.0, market_open=True):
        self.cashflow = cashflow
        self.market_open = market_open
        self.closed = []
        self.orders = {}

    def quote_spread_exit(self, legs):
        return {'cashflow_per_share': self.cashflow, 'limit_price': -self.cashflow,
                'closing_legs': [],
                'quotes': {leg['symbol']: {'timestamp': NOW.isoformat()} for leg in legs}}

    def get_positions(self, raise_on_error=False):
        return [{'symbol': 'NEAR', 'qty': '1'}, {'symbol': 'FAR', 'qty': '-1'}]

    def get_market_clock(self):
        return {'is_open': self.market_open}

    def close_option_spread(self, legs, qty, limit_price, client_order_id=None):
        self.closed.append((legs, qty, limit_price, client_order_id))
        self.orders['exit-1'] = {'id': 'exit-1', 'status': 'accepted'}
        return {'submitted': True, 'order_id': 'exit-1', 'status': 'accepted'}

    def get_order(self, order_id):
        return self.orders.get(order_id, {'id': order_id, 'status': 'accepted'})


def registered_logger(tmp_path, status='filled'):
    logger = AuditLogger(str(tmp_path / 'positions.db'))
    leg = {
        'symbol': 'SPY', 'strategy': 'call_debit_spread', 'qty': 1,
        'execution': {
            'submitted': True, 'status': status, 'filled_at': NOW.isoformat(),
            'order_id': 'entry-1', 'order_legs': position()['opening_legs'],
            'spread_type': 'debit', 'qty': 1, 'multiplier': 100,
            'limit_price': 1.0, 'max_profit': 400, 'max_loss': 100,
            'expiration_date': '2026-09-25',
        },
    }
    logger.register_managed_position(7, 'CS-TEST', 'primary_trade', leg, {
        'take_profit_fraction': .5, 'stop_loss_fraction': .5,
        'max_holding_days': 5, 'exit_before_expiry_days': 2,
    })
    return logger


def test_observe_mode_records_recommendation_without_order(tmp_path):
    logger = registered_logger(tmp_path)
    broker = Broker(cashflow=3.0)
    result = PositionLifecycleManager(broker, logger, True, now_fn=lambda: NOW).run(execute=False)[0]
    assert result['action'] == 'EXIT_RECOMMENDED'
    assert broker.closed == []
    assert logger.get_managed_positions(True)[0]['status'] == 'OPEN'


def test_execute_submits_one_atomic_exit_and_is_idempotent(tmp_path):
    logger = registered_logger(tmp_path)
    broker = Broker(cashflow=3.0)
    manager = PositionLifecycleManager(broker, logger, True, now_fn=lambda: NOW)
    assert manager.run(execute=True)[0]['action'] == 'EXIT_SUBMITTED'
    assert manager.run(execute=True)[0]['action'] == 'WAIT_EXIT'
    assert len(broker.closed) == 1
    assert logger.get_managed_positions(True)[0]['status'] == 'EXIT_PENDING'


def test_market_closed_defers_exit(tmp_path):
    logger = registered_logger(tmp_path)
    broker = Broker(cashflow=3.0, market_open=False)
    result = PositionLifecycleManager(broker, logger, True, now_fn=lambda: NOW).run(execute=True)[0]
    assert result['action'] == 'EXIT_DEFERRED'
    assert broker.closed == []


def test_pending_entry_reconciles_to_open(tmp_path):
    logger = registered_logger(tmp_path, status='accepted')
    broker = Broker()
    broker.orders['entry-1'] = {'status': 'filled', 'filled_avg_price': '1.25',
                                'filled_at': NOW.isoformat()}
    result = PositionLifecycleManager(broker, logger, False, now_fn=lambda: NOW).run()[0]
    assert result['action'] == 'ENTRY_FILLED'
    row = logger.get_managed_positions(True)[0]
    assert row['status'] == 'OPEN'
    assert row['entry_price'] == 1.25


def test_dashboard_exposes_position_policy_and_events(tmp_path):
    logger = registered_logger(tmp_path)
    dashboard = logger.get_dashboard_data()
    assert dashboard['positions'][0]['take_profit_target'] == 200
    assert dashboard['positions'][0]['stop_loss_limit'] == 50
    assert dashboard['position_events'][0]['event_type'] == 'POSITION_REGISTERED'


def test_exit_claim_is_atomic(tmp_path):
    logger = registered_logger(tmp_path)
    position_id = logger.get_managed_positions(True)[0]['id']
    assert logger.claim_managed_position_exit(position_id, 'TAKE_PROFIT') == 1
    assert logger.claim_managed_position_exit(position_id, 'TAKE_PROFIT') is None


def test_stale_quote_blocks_automated_exit(tmp_path):
    logger = registered_logger(tmp_path)
    broker = Broker(cashflow=3.0)
    stale = (NOW - timedelta(minutes=10)).isoformat()
    broker.quote_spread_exit = lambda legs: {
        'cashflow_per_share': 3.0, 'limit_price': -3.0,
        'quotes': {leg['symbol']: {'timestamp': stale} for leg in legs},
    }
    result = PositionLifecycleManager(
        broker, logger, True, now_fn=lambda: NOW, max_quote_age_seconds=300,
    ).run(execute=True)[0]
    assert result['reason'] == 'STALE_EXIT_QUOTE'
    assert broker.closed == []


def test_broker_position_mismatch_blocks_monitoring(tmp_path):
    logger = registered_logger(tmp_path)
    broker = Broker(cashflow=3.0)
    broker.get_positions = lambda raise_on_error=False: []
    result = PositionLifecycleManager(
        broker, logger, True, now_fn=lambda: NOW,
    ).run(execute=True)[0]
    assert result['action'] == 'BROKER_RECONCILIATION_FAILED'
    assert broker.closed == []


def test_position_performance_reports_realized_results(tmp_path):
    logger = registered_logger(tmp_path)
    position_id = logger.get_managed_positions(True)[0]['id']
    logger.update_managed_position(
        position_id, status='CLOSED', realized_pnl=125.0,
        exit_reason='TAKE_PROFIT', closed_at=NOW.isoformat(),
    )
    report = logger.get_position_performance()
    assert report['closed_positions'] == 1
    assert report['realized_pnl'] == 125.0
    assert report['win_rate'] == 1.0


def test_uncertain_exit_submission_stays_locked_for_reconciliation(tmp_path):
    logger = registered_logger(tmp_path)
    broker = Broker(cashflow=3.0)
    broker.close_option_spread = lambda *args, **kwargs: (_ for _ in ()).throw(
        TimeoutError('response timed out')
    )
    result = PositionLifecycleManager(
        broker, logger, True, now_fn=lambda: NOW,
    ).run(execute=True)[0]
    row = logger.get_managed_positions(True)[0]
    assert result['action'] == 'EXIT_SUBMISSION_UNCERTAIN'
    assert result['client_order_id'] == 'cs-exit-1-1'
    assert row['status'] == 'EXIT_SUBMITTING'
    assert row['exit_client_order_id'] == 'cs-exit-1-1'
