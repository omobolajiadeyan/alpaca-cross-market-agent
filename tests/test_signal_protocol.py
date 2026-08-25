import hashlib
import json

from agent.signal_protocol import (
    DisagreementEngine, StabilityTester, DecisionContractBuilder, ContractEvaluator,
)


def market_state(all_live=True):
    return {
        'equity_vol': {'price': 500, 'atm_iv': .20},
        'realized': {'realized_vol': .10},
        'positioning': {'put_call_ratio': 1.7},
        'credit': {'hy_spread_proxy_bps': -10},
        'rate_expectations': {'rate_change_expected': 'UP'},
        'timestamp': '2026-08-25T12:00:00Z',
        'data_quality': {'all_live': all_live, 'fallback_sources': [] if all_live else ['credit'], 'sources': {}},
    }


def portfolio():
    return {
        'primary_trade': {'symbol': 'HYG', 'max_loss': 300},
        'secondary_trade': {'symbol': 'SPY', 'max_loss': 500},
        'hedge': {'symbol': 'TLT', 'max_loss': 200},
    }


def thesis(confidence=.72):
    return {'thesis': 'Credit should reprice wider', 'confidence_overall': confidence}


def challenge(adjustment=-.05):
    return {
        'strongest_counterargument': 'Hedging flow may be temporary',
        'missing_evidence': 'event controls',
        'alternative_explanation': 'temporary hedge demand',
        'invalidation_condition': 'score below 55',
        'confidence_adjustment': adjustment,
    }


def test_disagreement_is_quantified_and_ranked():
    result = DisagreementEngine().score(market_state())
    assert 0 <= result['score'] <= 100
    assert result['candidates'][0]['score'] >= result['candidates'][1]['score']
    assert result['primary']['id'] in {item['id'] for item in result['candidates']}


def test_stability_reports_every_bounded_perturbation():
    result = StabilityTester().test(market_state())
    assert result['total_cases'] == 10
    assert 0 <= result['score'] <= 1


def test_authorized_contract_hash_matches_sealed_payload():
    state = market_state()
    disagreement = DisagreementEngine().score(state)
    stability = StabilityTester().test(state, disagreement)
    risk = {'passed': True, 'checks': []}
    contract = DecisionContractBuilder().build(
        thesis(), state, disagreement, stability, challenge(), portfolio(), risk
    )
    assert contract['authorization'] == 'AUTHORIZED'
    expected_hash = contract.pop('decision_hash')
    contract.pop('contract_id')
    canonical = json.dumps(contract, sort_keys=True, separators=(',', ':'), default=str)
    assert hashlib.sha256(canonical.encode()).hexdigest() == expected_hash


def test_contract_abstains_on_bad_data_and_low_confidence():
    state = market_state(all_live=False)
    disagreement = DisagreementEngine().score(state)
    stability = StabilityTester().test(state, disagreement)
    contract = DecisionContractBuilder().build(
        thesis(.50), state, disagreement, stability, challenge(-.10), portfolio(),
        {'passed': True, 'checks': []},
    )
    assert contract['authorization'] == 'ABSTAIN'
    assert len(contract['authorization_reasons']) >= 2


def test_contract_evaluator_compares_inverse_and_cash():
    state = market_state()
    disagreement = DisagreementEngine().score(state)
    stability = StabilityTester().test(state, disagreement)
    contract = DecisionContractBuilder().build(
        thesis(), state, disagreement, stability, challenge(), portfolio(),
        {'passed': True, 'checks': []},
    )
    later = market_state()
    later['credit']['hy_spread_proxy_bps'] = 20
    result = ContractEvaluator().evaluate(contract, later)
    assert result['counterfactuals']['cash_proxy'] == 0
    assert result['counterfactuals']['agent_direction_proxy'] == -result['counterfactuals']['inverse_direction_proxy']
