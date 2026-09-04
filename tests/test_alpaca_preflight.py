from tools.alpaca_tools import AlpacaTools
from datetime import date, timedelta


def fake_tools(max_loss_quotes=((2.0, 2.1), (.5, .6))):
    tools = object.__new__(AlpacaTools)
    tools.get_stock_price = lambda symbol: 100
    contracts = [
        {'symbol': 'OPT_NEAR', 'strike_price': '100', 'multiplier': '100'},
        {'symbol': 'OPT_FAR', 'strike_price': '105', 'multiplier': '100'},
    ]
    snapshots = {
        'OPT_NEAR': {
            'dailyBar': {'v': 100},
            'latestQuote': {'bp': max_loss_quotes[0][0], 'ap': max_loss_quotes[0][1]},
            'greeks': {'delta': .5},
        },
        'OPT_FAR': {
            'dailyBar': {'v': 100},
            'latestQuote': {'bp': max_loss_quotes[1][0], 'ap': max_loss_quotes[1][1]},
            'greeks': {'delta': .3},
        },
    }
    tools.find_option_spread_contracts = lambda *args, **kwargs: (contracts[0], contracts[1], snapshots)
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


def test_submission_uses_a_defined_limit_price():
    tools = fake_tools()
    captured = {}
    tools.place_multileg_option_order = lambda legs, qty, limit_price: captured.update(
        {'legs': legs, 'qty': qty, 'limit_price': limit_price}
    ) or {'id': 'paper-order', 'status': 'accepted'}
    result = tools.execute_spread('SPY', 'call', 'debit', max_premium=500, submit=True)
    assert result['submitted'] is True
    assert captured['limit_price'] == 1.6
    assert result['order_legs'][0]['position_intent'] == 'buy_to_open'


def test_atomic_spread_exit_reverses_both_legs_at_executable_limit():
    tools = object.__new__(AlpacaTools)
    tools.get_option_quote = lambda symbol: {
        'bid': 2.0 if symbol == 'NEAR' else .5,
        'ask': 2.1 if symbol == 'NEAR' else .6,
        'timestamp': '2026-09-03T15:00:00+00:00',
    }
    captured = {}
    tools.place_multileg_option_order = lambda legs, qty, limit_price, client_order_id=None: captured.update(
        {'legs': legs, 'qty': qty, 'limit_price': limit_price,
         'client_order_id': client_order_id}
    ) or {'id': 'exit-paper', 'status': 'accepted'}
    result = tools.close_option_spread([
        {'symbol': 'NEAR', 'side': 'buy', 'position_intent': 'buy_to_open'},
        {'symbol': 'FAR', 'side': 'sell', 'position_intent': 'sell_to_open'},
    ])
    assert result['order_id'] == 'exit-paper'
    assert captured['limit_price'] == -1.4
    assert [leg['position_intent'] for leg in captured['legs']] == ['sell_to_close', 'buy_to_close']


def test_multileg_order_uses_day_tif_and_client_order_id():
    tools = object.__new__(AlpacaTools)
    tools._mutation_authorized = True
    captured = {}
    tools.call = lambda name, arguments: captured.update(
        {'name': name, 'arguments': arguments}
    ) or {'id': 'paper-order'}
    tools.place_multileg_option_order([
        {'symbol': 'NEAR', 'side': 'sell', 'position_intent': 'sell_to_close'},
        {'symbol': 'FAR', 'side': 'buy', 'position_intent': 'buy_to_close'},
    ], qty=1, limit_price=-1.4, client_order_id='cs-exit-7-1')
    assert captured['arguments']['time_in_force'] == 'day'
    assert captured['arguments']['client_order_id'] == 'cs-exit-7-1'


def test_contract_selection_uses_target_dte_to_break_same_strike_ties():
    tools = object.__new__(AlpacaTools)
    target = date.today() + timedelta(days=25)
    deferred = date.today() + timedelta(days=44)
    active = date.today() + timedelta(days=34)
    tools.call = lambda name, arguments: {
        'option_contracts': [
            {
                'symbol': 'SPY_DEFERRED',
                'strike_price': '100',
                'expiration_date': deferred.isoformat(),
            },
            {
                'symbol': 'SPY_ACTIVE',
                'strike_price': '100',
                'expiration_date': active.isoformat(),
            },
        ]
    }

    selected = tools.find_option_contract(
        'SPY', 'call', target_strike=100, days_out_min=25, days_out_max=45
    )

    assert abs((active - target).days) < abs((deferred - target).days)
    assert selected['symbol'] == 'SPY_ACTIVE'


def test_contract_search_uses_narrow_strike_window_to_avoid_page_truncation():
    tools = object.__new__(AlpacaTools)
    captured = {}

    def fake_call(name, arguments):
        captured.update(arguments)
        return {
            'option_contracts': [
                {
                    'symbol': 'SPY_ATM',
                    'strike_price': '765',
                    'expiration_date': (date.today() + timedelta(days=28)).isoformat(),
                }
            ]
        }

    tools.call = fake_call
    selected = tools.find_option_contract('SPY', 'call', target_strike=765)

    assert captured['strike_price_gte'] == round(765 * 0.97, 2)
    assert captured['strike_price_lte'] == round(765 * 1.03, 2)
    assert selected['symbol'] == 'SPY_ATM'


def test_spread_selection_prefers_liquid_same_expiry_pair():
    tools = object.__new__(AlpacaTools)
    expiry = (date.today() + timedelta(days=30)).isoformat()
    contracts = [
        {'symbol': 'NEAR_THIN', 'strike_price': '79', 'expiration_date': expiry},
        {'symbol': 'NEAR_LIQUID', 'strike_price': '80', 'expiration_date': expiry},
        {'symbol': 'FAR_LIQUID', 'strike_price': '78', 'expiration_date': expiry},
    ]
    tools.call = lambda name, arguments: {'option_contracts': contracts}

    def fake_snapshot(symbol):
        volume = {'NEAR_THIN': 9, 'NEAR_LIQUID': 10, 'FAR_LIQUID': 1000}[symbol]
        return {
            'dailyBar': {'v': volume},
            'latestQuote': {'bp': 1.0, 'ap': 1.1},
            'greeks': {'delta': -.4},
        }

    tools.get_option_snapshot = fake_snapshot
    near, far, snapshots = tools.find_option_spread_contracts(
        'HYG', 'put', near_target=79.1, far_target=78.3
    )

    assert near['symbol'] == 'NEAR_LIQUID'
    assert far['symbol'] == 'FAR_LIQUID'
    assert set(snapshots) == {'NEAR_LIQUID', 'FAR_LIQUID'}
    assert near['expiration_date'] == far['expiration_date']
