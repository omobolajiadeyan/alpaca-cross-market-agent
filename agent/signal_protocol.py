"""Deterministic SIGNAL protocol: quantify, stress, authorize, and seal AI decisions."""

from __future__ import annotations

import hashlib
import json
from copy import deepcopy
from datetime import datetime, timezone

from config import MIN_SIGNAL_CONFIDENCE, EVALUATION_HORIZON_DAYS
from agent.thesis_scorer import _extract_metric, _direction_correct, _direction_multiplier


def _number(value, default=0.0):
    try:
        return float(value)
    except (TypeError, ValueError):
        return default


def _clamp(value, low=0.0, high=100.0):
    return round(max(low, min(high, value)), 1)


class DisagreementEngine:
    """Turn heterogeneous market observations into reproducible anomaly candidates."""

    def score(self, state):
        equity = state.get('equity_vol', {})
        credit = state.get('credit', {})
        realized = state.get('realized', {})
        positioning = state.get('positioning', {})
        rates = state.get('rate_expectations', {})

        iv = _number(equity.get('atm_iv'))
        rv = _number(realized.get('realized_vol'))
        put_call = _number(positioning.get('put_call_ratio'), 1.0)
        credit_bps = _number(credit.get('hy_spread_proxy_bps', credit.get('hy_oas')))

        vol_ratio = iv / rv if rv > 0 else 1.0
        vol_score = _clamp(abs(vol_ratio - 1) * 55)
        positioning_score = _clamp(abs(put_call - 1) * 100)
        # Defensive equity positioning with calm/tight credit is the signature cross-market gap.
        credit_calm = _clamp(55 - credit_bps / 3)
        fear_credit_score = _clamp((positioning_score * .55) + (credit_calm * .45))
        rate_direction = rates.get('rate_change_expected', 'FLAT')
        rate_credit_score = _clamp((60 if rate_direction == 'UP' else 25) + credit_calm * .35)

        candidates = [
            {
                'id': 'equity_fear_vs_credit',
                'title': 'Equity fear vs credit complacency',
                'score': fear_credit_score,
                'repricing_market': 'CREDIT_SPREADS',
                'direction': 'WIDER' if put_call > 1 else 'TIGHTER',
                'evidence': {
                    'put_call_ratio': put_call,
                    'hy_spread_proxy_bps': credit_bps,
                },
                'explanation': 'Options positioning and high-yield credit imply different levels of risk appetite.',
            },
            {
                'id': 'implied_vs_realized_vol',
                'title': 'Implied vs realized volatility',
                'score': vol_score,
                'repricing_market': 'EQUITY_VOL',
                'direction': 'DOWN' if vol_ratio > 1 else 'UP',
                'evidence': {'atm_iv': iv, 'realized_vol': rv, 'iv_rv_ratio': round(vol_ratio, 2)},
                'explanation': 'The volatility price differs materially from recently realized movement.',
            },
            {
                'id': 'rates_vs_credit',
                'title': 'Rate expectations vs credit pricing',
                'score': rate_credit_score,
                'repricing_market': 'CREDIT_SPREADS',
                'direction': 'WIDER' if rate_direction == 'UP' else 'TIGHTER',
                'evidence': {'rate_change_expected': rate_direction, 'hy_spread_proxy_bps': credit_bps},
                'explanation': 'The direction of policy expectations is not fully reflected in credit risk pricing.',
            },
        ]
        candidates.sort(key=lambda item: item['score'], reverse=True)
        top = candidates[0]
        return {
            'score': top['score'],
            'primary': top,
            'candidates': candidates,
            'method': 'deterministic-v1',
            'calculated_at': datetime.now(timezone.utc).isoformat(),
        }


class StabilityTester:
    """Measure whether plausible input noise changes the top quantitative conclusion."""

    PERTURBATIONS = (
        ('atm_iv', -.01), ('atm_iv', .01), ('realized_vol', -.01), ('realized_vol', .01),
        ('put_call_ratio', -.10), ('put_call_ratio', .10),
        ('hy_spread_proxy_bps', -10), ('hy_spread_proxy_bps', 10),
        ('price', -.005), ('price', .005),
    )

    def __init__(self, engine=None):
        self.engine = engine or DisagreementEngine()

    def test(self, state, baseline=None):
        baseline = baseline or self.engine.score(state)
        expected_id = baseline['primary']['id']
        outcomes = []
        for field, delta in self.PERTURBATIONS:
            perturbed = deepcopy(state)
            if field in ('atm_iv', 'price'):
                bucket = perturbed.setdefault('equity_vol', {})
            elif field == 'realized_vol':
                bucket = perturbed.setdefault('realized', {})
            elif field == 'put_call_ratio':
                bucket = perturbed.setdefault('positioning', {})
            else:
                bucket = perturbed.setdefault('credit', {})
            original = _number(bucket.get(field))
            bucket[field] = original * (1 + delta) if abs(delta) < 1 else original + delta
            result = self.engine.score(perturbed)
            outcomes.append({
                'field': field, 'change': delta, 'winner': result['primary']['id'],
                'stable': result['primary']['id'] == expected_id,
            })
        stable_count = sum(item['stable'] for item in outcomes)
        return {
            'score': round(stable_count / len(outcomes), 3),
            'stable_cases': stable_count,
            'total_cases': len(outcomes),
            'outcomes': outcomes,
            'method': 'bounded-perturbation-v1',
        }


class DecisionContractBuilder:
    """Create a canonical, tamper-evident precommitment before broker access."""

    def build(self, thesis, market_state, disagreement, stability, falsification, portfolio, risk):
        confidence_before = _number(thesis.get('confidence_pre_falsification', thesis.get('confidence_overall')))
        confidence_adjustment = _number(falsification.get('confidence_adjustment'))
        confidence_after = _clamp((confidence_before + confidence_adjustment) * 100, 0, 100) / 100
        data_quality = market_state.get('data_quality', {})
        reasons = []
        if not data_quality.get('all_live', False):
            reasons.append('required market data is not fully live')
        if disagreement.get('score', 0) < 55:
            reasons.append('disagreement score below 55')
        if stability.get('score', 0) < .60:
            reasons.append('decision stability below 60%')
        if confidence_after < MIN_SIGNAL_CONFIDENCE:
            reasons.append(f'adjusted confidence below {MIN_SIGNAL_CONFIDENCE:.0%}')
        if not risk.get('passed'):
            reasons.append('deterministic risk assessment failed')

        primary = disagreement['primary']
        payload = {
            'protocol_version': 'SIGNAL-1.0',
            'created_at': datetime.now(timezone.utc).isoformat(),
            'creator': 'Omobolaji E Adeyan',
            'prediction': {
                'market': primary['repricing_market'],
                'direction': primary['direction'],
                'minimum_move': 'measurable directional move from sealed baseline',
                'horizon_trading_days': EVALUATION_HORIZON_DAYS,
                'invalidation': falsification.get('invalidation_condition'),
            },
            'thesis': thesis.get('thesis'),
            'confidence_before_challenge': confidence_before,
            'confidence_after_challenge': confidence_after,
            'disagreement': disagreement,
            'stability': stability,
            'falsification': falsification,
            'risk_assessment': risk,
            'portfolio_stress': portfolio.get('portfolio_stress'),
            'catalyst_context': portfolio.get('catalyst_context'),
            'portfolio': {
                name: {key: value for key, value in portfolio.get(name, {}).items() if key != 'execution'}
                for name in ('primary_trade', 'secondary_trade', 'hedge')
            },
            'market_timestamp': market_state.get('timestamp'),
            'sealed_baseline_value': _extract_metric(primary['repricing_market'], market_state),
            'data_quality': data_quality,
            'authorization': 'ABSTAIN' if reasons else 'AUTHORIZED',
            'authorization_reasons': reasons,
        }
        canonical = json.dumps(payload, sort_keys=True, separators=(',', ':'), default=str)
        payload['decision_hash'] = hashlib.sha256(canonical.encode()).hexdigest()
        payload['contract_id'] = f"CS-{datetime.now(timezone.utc):%Y%m%d}-{payload['decision_hash'][:8].upper()}"
        return payload


class ContractEvaluator:
    """Issue a predetermined verdict and normalized counterfactual comparison."""

    def evaluate(self, contract, current_state):
        prediction = contract['prediction']
        before = contract.get('sealed_baseline_value')
        after = _extract_metric(prediction['market'], current_state)
        correct = _direction_correct(prediction['direction'], before, after, prediction['market'])
        if before in (None, 0) or after is None:
            normalized_move = None
        else:
            normalized_move = round((after - before) / abs(before), 4)
        direction_multiplier = _direction_multiplier(
            prediction.get('direction'), prediction.get('market')
        )
        agent_score = (
            round(normalized_move * direction_multiplier, 4)
            if normalized_move is not None and direction_multiplier is not None else None
        )
        return {
            'contract_id': contract['contract_id'],
            'evaluated_at': datetime.now(timezone.utc).isoformat(),
            'before': before,
            'after': after,
            'direction_correct': correct,
            'normalized_market_move': normalized_move,
            'counterfactuals': {
                'agent_direction_proxy': agent_score,
                'inverse_direction_proxy': -agent_score if agent_score is not None else None,
                'cash_proxy': 0.0,
            },
            'note': 'Directional proxies isolate forecast value; broker P&L remains the execution-performance measure.',
        }
