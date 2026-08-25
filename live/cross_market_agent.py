"""
Main trading agent
Cross-market macro synthesis trading loop
"""

import sys
import os
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from src.data_feed.cross_market_feed import CrossMarketDataFeed
from agent.synthesizer import MacroSynthesizer
from agent.constructor import TradeConstructor
from agent.thesis_scorer import ThesisScorer
from agent.signal_protocol import (
    DisagreementEngine, StabilityTester, DecisionContractBuilder, ContractEvaluator,
)
from tools.alpaca_tools import AlpacaTools
from compliance.audit_logger import AuditLogger
from config import THESIS_EVALUATION_DAYS, REQUIRE_LIVE_DATA


class CrossMarketAgent:
    """
    Autonomous trading agent:
    1. Reads 6 market data sources
    2. Claude synthesizes macro thesis
    3. Constructs asymmetric trades
    4. Executes via Alpaca
    5. Logs everything for audit trail
    """

    def __init__(self):
        print("\n" + "="*70)
        print("CROSS-MARKET MACRO SYNTHESIS AI TRADING AGENT")
        print("="*70 + "\n")

        print("[INIT] Starting up components...")
        self.alpaca = AlpacaTools()
        self.logger = AuditLogger()
        self.feed = CrossMarketDataFeed(alpaca=self.alpaca, logger=self.logger)
        self.synthesizer = MacroSynthesizer()
        self.constructor = TradeConstructor()
        self.scorer = ThesisScorer(logger=self.logger, feed=self.feed)
        self.disagreement_engine = DisagreementEngine()
        self.stability_tester = StabilityTester(self.disagreement_engine)
        self.contract_builder = DecisionContractBuilder()
        self.contract_evaluator = ContractEvaluator()

        print("[INIT] ✓ All components ready\n")

    def close(self):
        """Shut down the persistent Alpaca MCP connection"""
        self.alpaca.close()

    def run(self, execute=True):
        """Main trading loop"""
        try:
            # STEP 0: Score any past theses old enough to check against real
            # subsequent data -- this is what turns "prints a thesis" into an
            # agent with an actual, honest track record.
            print(f"[AGENT] STEP 0: Scoring theses older than {THESIS_EVALUATION_DAYS:g} day(s)...")
            results = self.scorer.score_pending_theses(min_age_days=THESIS_EVALUATION_DAYS)
            if results:
                for r in results:
                    hr = f"{r['hit_rate']:.0%}" if r['hit_rate'] is not None else "n/a (no scorable signals)"
                    print(f"  Thesis #{r['thesis_id']} (from {r['thesis_timestamp']}): hit rate {hr}")
            else:
                print("  No theses due for scoring yet")
            track_record = self.logger.get_track_record()
            if track_record['theses_scored']:
                print(f"  Running track record: {track_record['average_hit_rate']:.0%} average hit rate "
                      f"across {track_record['theses_scored']} scored theses "
                      f"({track_record['theses_pending']} pending)\n")
            else:
                print(f"  Running track record: no theses scored yet "
                      f"({track_record['theses_pending']} pending)\n")

            # STEP 1: Read cross-market state
            print("[AGENT] STEP 1: Reading cross-market state...")
            market_state = self.feed.get_full_market_state()
            print("  ✓ Equity vol metrics")
            print("  ✓ Treasury curve")
            print("  ✓ Credit spreads")
            print("  ✓ Realized volatility")
            print("  ✓ Rate expectations")
            print("  ✓ Market positioning\n")
            matured_contracts = self.logger.get_pending_contracts(min_age_days=5)
            for pending_contract in matured_contracts:
                evaluation = self.contract_evaluator.evaluate(pending_contract, market_state)
                self.logger.record_contract_evaluation(pending_contract['contract_id'], evaluation)
            if matured_contracts:
                print(f"  ✓ Issued verdicts for {len(matured_contracts)} matured Decision Contract(s)\n")
            fallbacks = market_state['data_quality']['fallback_sources']
            if fallbacks:
                print(f"  ⚠ Fallback data detected: {', '.join(fallbacks)}")
                if REQUIRE_LIVE_DATA and execute:
                    print("  ✗ Execution disabled: REQUIRE_LIVE_DATA is enabled\n")
                    execute = False

            print("[AGENT] STEP 1B: Quantifying cross-market disagreement...")
            disagreement = self.disagreement_engine.score(market_state)
            stability = self.stability_tester.test(market_state, disagreement)
            print(f"  ✓ Leading case: {disagreement['primary']['title']}")
            print(f"  ✓ Disagreement score: {disagreement['score']:.0f}/100")
            print(f"  ✓ Stability: {stability['score']:.0%} "
                  f"({stability['stable_cases']}/{stability['total_cases']} perturbations)\n")

            # STEP 2: Check account
            print("[AGENT] STEP 2: Checking account...")
            account = self.alpaca.get_account_info()
            if account:
                print(f"  ✓ Balance: ${account['cash']:,.0f}")
                print(f"  ✓ Portfolio value: ${account['portfolio_value']:,.0f}")
                print(f"  ✓ Status: {account.get('status', 'unknown')}\n")

            # STEP 3: Generate macro thesis
            print("[AGENT] STEP 3: Generating macro thesis with Claude...")
            thesis = self.synthesizer.synthesize_macro_view(market_state)

            if thesis:
                print(f"\n  📊 THESIS:")
                print(f"     {thesis['thesis']}\n")
                print(f"  💡 RATIONALE:")
                print(f"     {thesis['rationale']}\n")
                print(f"  🎯 PRIMARY OPPORTUNITY:")
                print(f"     {thesis.get('primary_trade_opportunity', 'N/A')}\n")
                print(f"  📈 CONFIDENCE: {thesis['confidence_overall']:.0%}\n")

                print("[AGENT] STEP 3B: Falsifying the thesis...")
                falsification = self.synthesizer.falsify(thesis, market_state, disagreement)
                adjusted = thesis['confidence_overall'] + falsification.get('confidence_adjustment', 0)
                print(f"  Challenge: {falsification['strongest_counterargument']}")
                print(f"  Invalidation: {falsification['invalidation_condition']}")
                print(f"  Adjusted confidence: {max(0, adjusted):.0%}\n")
                thesis['confidence_pre_falsification'] = thesis['confidence_overall']
                thesis['confidence_overall'] = max(0, adjusted)

                # STEP 4: Construct trades
                print("[AGENT] STEP 4: Constructing asymmetric portfolio...")
                portfolio = self.constructor.build_portfolio(thesis, market_state)

                if portfolio:
                    print(f"  Primary: {portfolio['primary_trade']['strategy']} {portfolio['primary_trade']['symbol']}")
                    print(f"  Secondary: {portfolio['secondary_trade']['strategy']} {portfolio['secondary_trade']['symbol']}")
                    print(f"  Hedge: {portfolio['hedge']['strategy']} {portfolio['hedge']['symbol']}")
                    print(f"  Total max loss: ${portfolio['total_max_loss']:,.0f}\n")

                    # STEP 5: Validate
                    print("[AGENT] STEP 5: Validating portfolio...")
                    assessment = self.constructor.assess_portfolio(portfolio, account, market_state)
                    portfolio['risk_assessment'] = assessment
                    for check in assessment['checks']:
                        mark = '✓' if check['passed'] else '✗'
                        print(f"  {mark} {check['name']}: {check['detail']}")

                    contract = self.contract_builder.build(
                        thesis, market_state, disagreement, stability,
                        falsification, portfolio, assessment,
                    )
                    portfolio['decision_contract'] = contract
                    self.logger.log_decision_contract(contract)
                    print(f"  {'✓' if contract['authorization'] == 'AUTHORIZED' else '✗'} "
                          f"Decision contract {contract['contract_id']}: {contract['authorization']}")
                    print(f"  SHA-256: {contract['decision_hash']}\n")
                    if contract['authorization'] != 'AUTHORIZED':
                        execute = False
                        print("  ABSTAIN — " + '; '.join(contract['authorization_reasons']) + "\n")

                    if assessment['passed']:
                        print("  ✓ Portfolio passed implemented risk gates\n")

                        # Preflight every leg before submitting any order, preventing a
                        # known-invalid leg from creating a partially hedged portfolio.
                        print("[AGENT] STEP 6: Preflighting legs via Alpaca...")
                        preflights = {}
                        for leg_name in ('primary_trade', 'secondary_trade', 'hedge'):
                            leg = portfolio[leg_name]
                            preflights[leg_name] = self.alpaca.execute_spread(
                                underlying_symbol=leg['symbol'],
                                option_type=leg['option_type'],
                                spread_type=leg['spread_type'],
                                max_premium=leg['max_loss'],
                                qty=leg['qty'],
                                submit=False,
                            )
                        preflight_ok = all(result.get('preflight_passed') for result in preflights.values())
                        if not preflight_ok:
                            execute = False
                            print("  ✗ Portfolio preflight failed; no orders will be submitted")

                        for leg_name in ('primary_trade', 'secondary_trade', 'hedge'):
                            leg = portfolio[leg_name]
                            if execute and preflight_ok:
                                result = self.alpaca.execute_spread(
                                    underlying_symbol=leg['symbol'], option_type=leg['option_type'],
                                    spread_type=leg['spread_type'], max_premium=leg['max_loss'],
                                    qty=leg['qty'], submit=True,
                                )
                            else:
                                result = dict(preflights[leg_name])
                                result['reason'] = result.get('reason') or 'preview only; order not submitted'
                            leg['execution'] = result
                            if result.get('submitted'):
                                order_id = result.get('order_id')
                                if order_id:
                                    latest_order = self.alpaca.get_order(order_id)
                                    result['status'] = latest_order.get('status', result.get('status'))
                                    result['filled_qty'] = latest_order.get('filled_qty')
                                    result['filled_avg_price'] = latest_order.get('filled_avg_price')
                                    result['filled_at'] = latest_order.get('filled_at')
                                print(f"  ✓ {leg_name}: {leg['spread_type']} {leg['option_type']} spread "
                                      f"{result['legs'][0]} / {result['legs'][1]} "
                                      f"(max loss ${result['max_loss']:,.0f}, status {result.get('status', 'submitted')})")
                            else:
                                print(f"  ✗ {leg_name}: not submitted — {result.get('reason', 'unknown error')}")
                        print()

                        # STEP 7: Log
                        print("[AGENT] STEP 7: Logging to audit trail...")
                        thesis_id = self.logger.log_thesis(thesis, market_state)
                        trade_id = self.logger.log_trade(thesis_id, portfolio)
                        execution_states = [portfolio[name].get('execution', {}).get('status')
                                            for name in ('primary_trade', 'secondary_trade', 'hedge')]
                        contract_status = ('abstained' if contract['authorization'] != 'AUTHORIZED'
                                           else 'filled' if execution_states and all(s == 'filled' for s in execution_states)
                                           else 'submitted' if any(portfolio[name].get('execution', {}).get('submitted')
                                                                   for name in ('primary_trade', 'secondary_trade', 'hedge'))
                                           else 'preview')
                        self.logger.link_contract_execution(contract['contract_id'], trade_id, contract_status)

                        report = self.logger.get_report()
                        print(f"  ✓ Thesis logged (ID: {thesis_id})")
                        print(f"  ✓ Trade logged")
                        print(f"  ✓ Total theses in audit: {report['total_theses']}")
                        print(f"  ✓ Total trades in audit: {report['total_trades']}\n")
                    else:
                        print("  ✗ Portfolio failed risk validation; no orders submitted\n")
                        thesis_id = self.logger.log_thesis(thesis, market_state)
                        trade_id = self.logger.log_trade(thesis_id, portfolio)
                        self.logger.link_contract_execution(contract['contract_id'], trade_id, 'abstained')

            else:
                print("[AGENT] ✗ Failed to generate thesis\n")

            # Summary
            print("="*70)
            print("CYCLE COMPLETE")
            print("="*70 + "\n")
            return {'market_state': market_state, 'account': account,
                    'thesis': thesis if 'thesis' in locals() else None,
                    'portfolio': portfolio if 'portfolio' in locals() else None,
                    'disagreement': disagreement, 'stability': stability,
                    'falsification': falsification if 'falsification' in locals() else None,
                    'decision_contract': contract if 'contract' in locals() else None}

        except Exception as e:
            print(f"\n[ERROR] {e}")
            import traceback
            traceback.print_exc()


if __name__ == "__main__":
    agent = CrossMarketAgent()
    try:
        agent.run()
    finally:
        agent.close()
