"""
Agent performance report
Summarizes the audit trail: thesis accuracy track record and trade/risk stats.
Run this any time to see the agent's actual track record, not just its latest cycle.
"""

import json
import sqlite3
import sys
import os

sys.path.insert(0, os.path.abspath(os.path.dirname(__file__)))

from compliance.audit_logger import AuditLogger


def main():
    logger = AuditLogger()

    print("\n" + "=" * 70)
    print("AGENT PERFORMANCE REPORT")
    print("=" * 70 + "\n")

    report = logger.get_report()
    track_record = logger.get_track_record()
    dashboard = logger.get_dashboard_data()

    print(f"Total theses generated: {report['total_theses']}")
    print(f"Total trade cycles logged: {report['total_trades']}\n")

    print("Thesis accuracy track record:")
    if track_record['theses_scored']:
        print(f"  Average hit rate: {track_record['average_hit_rate']:.0%} "
              f"across {track_record['theses_scored']} scored theses")
    else:
        print("  No theses scored yet (signals need to age past THESIS_EVALUATION_DAYS first)")
    print(f"  Theses pending evaluation: {track_record['theses_pending']}\n")

    contracts = dashboard.get('contracts', [])
    authorized = sum(row['authorization'] == 'AUTHORIZED' for row in contracts)
    abstained = sum(row['authorization'] == 'ABSTAIN' for row in contracts)
    filled_contracts = sum(row['execution_status'] == 'filled' for row in contracts)
    print("SIGNAL decision contracts:")
    print(f"  Contracts sealed: {len(contracts)}")
    print(f"  Authorized: {authorized}")
    print(f"  Abstained: {abstained}")
    print(f"  Filled contract portfolios: {filled_contracts}\n")

    conn = sqlite3.connect(logger.db_path)
    cursor = conn.cursor()
    rows = cursor.execute("SELECT portfolio FROM trades").fetchall()
    conn.close()

    total_legs = 0
    submitted_legs = 0
    total_max_loss_submitted = 0.0
    total_max_loss_attempted = 0.0

    for (portfolio_json,) in rows:
        portfolio = json.loads(portfolio_json)
        for leg_name in ('primary_trade', 'secondary_trade', 'hedge'):
            leg = portfolio.get(leg_name, {})
            execution = leg.get('execution')
            if not execution:
                continue
            total_legs += 1
            max_loss = execution.get('max_loss') or execution.get('premium') or leg.get('max_loss', 0) or 0
            total_max_loss_attempted += max_loss
            if execution.get('submitted'):
                submitted_legs += 1
                total_max_loss_submitted += max_loss

    print("Trade execution stats:")
    print(f"  Legs attempted: {total_legs}")
    print(f"  Legs actually submitted to Alpaca: {submitted_legs}")
    print(f"  Total max loss at risk on submitted legs: ${total_max_loss_submitted:,.0f}")
    print(f"  Total max loss across all attempted legs: ${total_max_loss_attempted:,.0f}\n")

    print("=" * 70)


if __name__ == "__main__":
    main()
