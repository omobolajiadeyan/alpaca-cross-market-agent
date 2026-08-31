from agent.thesis_scorer import _direction_correct, _direction_multiplier, _extract_metric


def test_equity_bullish_means_price_up():
    assert _direction_correct('BULLISH', 100, 105, 'EQUITY') is True
    assert _direction_correct('BULLISH', 100, 95, 'EQUITY') is False


def test_credit_bullish_means_spreads_tighten():
    assert _direction_correct('BULLISH', 200, 175, 'CREDIT_SPREADS') is True
    assert _direction_correct('BEARISH', 200, 225, 'CREDIT_SPREADS') is True


def test_unknown_direction_is_not_silently_scored():
    assert _direction_correct('SIDEWAYS', 100, 101, 'EQUITY') is None
    for direction in ('UNWIND', 'FLATTER', 'UNRELIABLE'):
        assert _direction_multiplier(direction, 'CREDIT_SPREADS') is None


def test_counterfactual_multiplier_uses_the_same_alias_semantics():
    assert _direction_multiplier('BULLISH', 'CREDIT_SPREADS') == -1
    assert _direction_multiplier('BEARISH', 'CREDIT_SPREADS') == 1
    assert _direction_multiplier('RALLY', 'EQUITY') == 1
    assert _direction_multiplier('SELLOFF', 'EQUITY') == -1


def test_metric_extraction_handles_missing_data():
    assert _extract_metric('EQUITY', {'equity_vol': {'price': 500}}) == 500
    assert _extract_metric('EQUITY_VOL', {}) is None
