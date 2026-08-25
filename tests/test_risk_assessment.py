from agent.constructor import TradeConstructor


def portfolio(loss=1000, confidence=.72):
    leg = {'symbol': 'SPY'}
    return {
        'thesis': 'test', 'primary_trade': leg,
        'secondary_trade': {'symbol': 'HYG'}, 'hedge': {'symbol': 'TLT'},
        'confidence': confidence, 'total_max_loss': loss,
    }


def live_state(fallbacks=None):
    return {'data_quality': {'fallback_sources': fallbacks or []}}


def test_valid_portfolio_exposes_each_gate():
    result = TradeConstructor().assess_portfolio(
        portfolio(), {'buying_power': 20_000}, live_state()
    )
    assert result['passed'] is True
    assert len(result['checks']) == 6


def test_fallback_data_fails_closed():
    result = TradeConstructor().assess_portfolio(
        portfolio(), {'buying_power': 20_000}, live_state(['credit'])
    )
    assert result['passed'] is False
    assert any(c['name'] == 'Live-data integrity' and not c['passed'] for c in result['checks'])


def test_loss_and_buying_power_are_enforced():
    result = TradeConstructor().assess_portfolio(
        portfolio(loss=2_000), {'buying_power': 500}, live_state()
    )
    assert result['passed'] is False
    failed = {c['name'] for c in result['checks'] if not c['passed']}
    assert {'Maximum defined loss', 'Buying power'} <= failed
