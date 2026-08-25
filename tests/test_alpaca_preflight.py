from tools.alpaca_tools import AlpacaTools


def fake_tools(max_loss_quotes=((2.0, 2.1), (.5, .6))):
    tools = object.__new__(AlpacaTools)
    tools.get_stock_price = lambda symbol: 100
    contracts = [
        {'symbol': 'OPT_NEAR', 'strike_price': '100', 'multiplier': '100'},
        {'symbol': 'OPT_FAR', 'strike_price': '105', 'multiplier': '100'},
    ]
    tools.find_option_contract = lambda *args, **kwargs: contracts[0] if kwargs['target_strike'] == 100 else contracts[1]
    tools.get_option_bid_ask = lambda symbol: max_loss_quotes[0] if symbol == 'OPT_NEAR' else max_loss_quotes[1]
    tools.place_multileg_option_order = lambda *args, **kwargs: (_ for _ in ()).throw(AssertionError('must not submit'))
    return tools


def test_preflight_prices_without_submitting():
    result = fake_tools().execute_spread('SPY', 'call', 'debit', max_premium=500, submit=False)
    assert result['preflight_passed'] is True
    assert result['submitted'] is False
    assert result['max_loss'] == 160


def test_preflight_rejects_excess_loss():
    result = fake_tools(max_loss_quotes=((8, 9), (.1, .2))).execute_spread(
        'SPY', 'call', 'debit', max_premium=500, submit=False
    )
    assert result['submitted'] is False
    assert 'exceeds' in result['reason']
