"""
Thesis accuracy scorer

The agent's actual differentiator: instead of only ever printing a new
thesis, it checks its own past predictions against what the real market
data did afterward, and keeps a running, honest hit-rate track record.
"""

from datetime import datetime

# Which direction words count as the metric having gone "up" vs. "down"
_UP_WORDS = {'UP', 'HIGHER', 'WIDER'}
_DOWN_WORDS = {'DOWN', 'LOWER', 'TIGHTER'}


def _normalize_direction(direction, market_label=None):
    """Map supported aliases to metric direction; return None if unscoreable."""
    normalized = (direction or '').upper()
    label = (market_label or '').upper()
    if normalized in ('BULLISH', 'RALLY'):
        normalized = 'TIGHTER' if label in ('CREDIT', 'CREDIT_SPREADS') else 'UP'
    elif normalized in ('BEARISH', 'SELLOFF'):
        normalized = 'WIDER' if label in ('CREDIT', 'CREDIT_SPREADS') else 'DOWN'
    return normalized if normalized in (_UP_WORDS | _DOWN_WORDS) else None


def _direction_multiplier(direction, market_label=None):
    """Return +1/-1 only for vocabulary the scorer can actually evaluate."""
    normalized = _normalize_direction(direction, market_label)
    if normalized in _UP_WORDS:
        return 1
    if normalized in _DOWN_WORDS:
        return -1
    return None


def _extract_metric(market_label, market_state):
    """Pull the one real number a signal's `market` label is actually about."""
    label = (market_label or '').upper()
    try:
        if label == 'EQUITY_VOL':
            return market_state['equity_vol']['atm_iv']
        if label == 'EQUITY':
            return market_state['equity_vol']['price']
        if label in ('CREDIT', 'CREDIT_SPREADS'):
            return market_state['credit']['hy_spread_proxy_bps']
        if label in ('RATES', 'RATES_EXPECTATIONS', 'DURATION', 'TREASURY'):
            return market_state['rates_curve']['yields']['10yr']
        if label == 'REALIZED':
            return market_state['realized']['realized_vol']
        if label == 'POSITIONING':
            return market_state['positioning']['put_call_ratio']
    except (KeyError, TypeError):
        return None
    return None


def _direction_correct(direction, before, after, market_label=None):
    """Did `after` move the way `direction` predicted, relative to `before`?
    Returns None (unscoreable) rather than guessing when data or vocabulary
    doesn't match -- an unscored signal should never silently count as a miss."""
    if before is None or after is None:
        return None
    direction = _normalize_direction(direction, market_label)
    delta = after - before
    if direction in _UP_WORDS:
        return delta > 0
    if direction in _DOWN_WORDS:
        return delta < 0
    return None


class ThesisScorer:
    """Scores past theses' repricing_signals against real subsequent market data."""

    def __init__(self, logger, feed):
        self.logger = logger
        self.feed = feed

    def score_pending_theses(self, min_age_days=1):
        """
        Find theses old enough to evaluate and not yet scored, fetch current
        real market state once, and score each one's repricing_signals.
        Returns the list of results (empty if nothing was due).
        """
        pending = self.logger.get_pending_theses(min_age_days)
        if not pending:
            return []

        current_state = self.feed.get_full_market_state()
        results = []
        for row in pending:
            result = self._score_one(row, current_state)
            self.logger.record_thesis_evaluation(row['id'], result['hit_rate'], result)
            results.append(result)
        return results

    def _score_one(self, row, current_state):
        before_state = row['market_state']
        signals = row['repricing_signals']

        scored = []
        for signal in signals:
            before = _extract_metric(signal.get('market'), before_state)
            after = _extract_metric(signal.get('market'), current_state)
            correct = _direction_correct(
                signal.get('direction'), before, after, signal.get('market')
            )
            scored.append({
                'market': signal.get('market'),
                'direction': signal.get('direction'),
                'confidence': signal.get('confidence'),
                'before': before,
                'after': after,
                'correct': correct,
            })

        scorable = [s for s in scored if s['correct'] is not None]
        hit_rate = (sum(1 for s in scorable if s['correct']) / len(scorable)) if scorable else None

        return {
            'thesis_id': row['id'],
            'thesis_timestamp': row['timestamp'],
            'hit_rate': hit_rate,
            'signals': scored,
            'evaluated_at': datetime.now().isoformat(),
        }
