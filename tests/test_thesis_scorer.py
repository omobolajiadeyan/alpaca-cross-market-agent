from agent.thesis_scorer import _direction_correct, _extract_metric


def test_equity_bullish_means_price_up():
    assert _direction_correct('BULLISH', 100, 105, 'EQUITY') is True
    assert _direction_correct('BULLISH', 100, 95, 'EQUITY') is False


def test_credit_bullish_means_spreads_tighten():
    assert _direction_correct('BULLISH', 200, 175, 'CREDIT_SPREADS') is True
    assert _direction_correct('BEARISH', 200, 225, 'CREDIT_SPREADS') is True


def test_unknown_direction_is_not_silently_scored():
    assert _direction_correct('SIDEWAYS', 100, 101, 'EQUITY') is None


def test_metric_extraction_handles_missing_data():
    assert _extract_metric('EQUITY', {'equity_vol': {'price': 500}}) == 500
    assert _extract_metric('EQUITY_VOL', {}) is None
