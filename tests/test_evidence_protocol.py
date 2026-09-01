import json

from agent.evidence_protocol import (
    CatalystClassifier, EvidenceReceiptBuilder, ExecutionRecoveryPlanner, ExecutionRiskGate,
    PaperRecoveryExecutor, PortfolioStressEngine,
)


def preflights(complete=True):
    snapshot = {'greeks': {'delta': .50, 'gamma': .02, 'theta': -.03, 'vega': .11},
                'dailyBar': {'v': 100}}
    far = {'greeks': {'delta': .30, 'gamma': .01, 'theta': -.02, 'vega': .07},
           'dailyBar': {'v': 100}}
    if not complete:
        far = {}
    return {'primary_trade': {
        'max_loss': 300, 'qty': 1, 'underlyings': ['HYG'], 'underlying_price': 80,
        'order_legs': [
            {'symbol': 'HYG_CALL_NEAR', 'side': 'buy'},
            {'symbol': 'HYG_CALL_FAR', 'side': 'sell'},
        ],
        'snapshots': {'HYG_CALL_NEAR': snapshot, 'HYG_CALL_FAR': far},
        'quotes': {'HYG_CALL_NEAR': {'bid': 1.0, 'ask': 1.1},
                   'HYG_CALL_FAR': {'bid': .5, 'ask': .55}},
    }}


def test_stress_aggregates_sponsor_native_greeks_and_scenarios():
    result = PortfolioStressEngine().analyze(preflights())
    assert result['snapshot_coverage']['complete'] is True
    assert result['greeks']['delta'] == 20
    assert len(result['scenarios']) == 9
    assert result['passed'] is True


def test_stress_fails_closed_when_a_greek_snapshot_is_missing():
    result = PortfolioStressEngine().analyze(preflights(complete=False))
    assert result['snapshot_coverage']['complete'] is False
    assert result['passed'] is False


def test_recovery_requires_human_approval_for_partial_exposure():
    result = ExecutionRecoveryPlanner().assess({
        'primary_trade': {'status': 'filled'},
        'secondary_trade': {'status': 'rejected'},
        'hedge': {'status': 'accepted'},
    })
    assert result['state'] == 'RECOVERY_REQUIRED'
    assert result['automatic_orders'] is False


def test_recovery_is_preflighted_not_stopped_when_nothing_was_submitted():
    """A normal preview/abstain cycle -- nothing sent to the broker -- must
    not be reported as a stopped/failed recovery state."""
    result = ExecutionRecoveryPlanner().assess({
        'primary_trade': {'status': 'not_submitted'},
        'secondary_trade': {'status': 'not_submitted'},
        'hedge': {'status': 'not_submitted'},
    })
    assert result['state'] == 'PREFLIGHTED'


def test_recovery_is_stopped_when_broker_actually_rejects():
    result = ExecutionRecoveryPlanner().assess({
        'primary_trade': {'status': 'rejected'},
        'secondary_trade': {'status': 'not_submitted'},
        'hedge': {'status': 'not_submitted'},
    })
    assert result['state'] == 'STOPPED'


def test_catalyst_classifier_only_keeps_portfolio_symbols():
    result = CatalystClassifier().classify([
        {'headline': 'Rates move', 'symbols': ['TLT'], 'source': 'wire'},
        {'headline': 'Unrelated', 'symbols': ['AAPL'], 'source': 'wire'},
    ])
    assert result['classification'] == 'SUPPORTED_CATALYST'
    assert result['relevant_count'] == 1


def test_receipt_is_portable_and_excludes_credentials():
    import hashlib
    sealed = {'prediction': {}}
    canonical = json.dumps(sealed, sort_keys=True, separators=(',', ':'))
    decision_hash = hashlib.sha256(canonical.encode()).hexdigest()
    contract = {**sealed, 'contract_id': 'CS-1', 'decision_hash': decision_hash}
    payload = EvidenceReceiptBuilder().dumps(contract, 'preview')
    decoded = json.loads(payload)
    assert decoded['contract_id'] == 'CS-1'
    assert 'api_key' not in payload.lower()
    assert EvidenceReceiptBuilder().verify(payload)['valid'] is True


def test_execution_risk_gate_enforces_greeks_liquidity_margin_and_drawdown():
    prepared = preflights()
    stress = PortfolioStressEngine().analyze(prepared)
    result = ExecutionRiskGate().assess(
        stress, prepared, {'portfolio_value': 100000}, [100000, 99500],
    )
    assert result['passed'] is True
    assert {item['name'] for item in result['checks']} >= {
        'Net delta', 'Net vega', 'Net theta', 'Margin utilization',
        'Option liquidity', 'Bid-ask quality', 'Daily drawdown', 'Maximum drawdown',
    }


class FakeBroker:
    def __init__(self):
        self.canceled = []
        self.closed = []

    def cancel_order(self, order_id):
        self.canceled.append(order_id)

    def close_position(self, symbol, qty=None):
        self.closed.append((symbol, qty))


def test_recovery_executor_requires_approval_and_paper_mode():
    plan = {'state': 'RECOVERY_REQUIRED'}
    executions = {'hedge': {'status': 'accepted', 'order_id': 'order-1'}}
    broker = FakeBroker()
    executor = PaperRecoveryExecutor()
    assert executor.execute(plan, executions, broker)['state'] == 'AWAITING_APPROVAL'
    assert executor.execute(plan, executions, broker, approved=True,
                            paper_mode=False)['state'] == 'BLOCKED_LIVE_ACCOUNT'
    result = executor.execute(plan, executions, broker, approved=True, paper_mode=True,
                              positions_to_close=[{'symbol': 'SPYOPT', 'qty': 1}])
    assert result['state'] == 'RECOVERY_SUBMITTED'
    assert broker.canceled == ['order-1']
    assert broker.closed == [('SPYOPT', 1)]
