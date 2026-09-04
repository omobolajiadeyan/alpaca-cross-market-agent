"""Run CrossSignal's position monitor. Observe-only unless --execute is explicit."""

import argparse
import os
import sys

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from agent.position_manager import PositionLifecycleManager
from compliance.audit_logger import AuditLogger
from config import (ALLOW_PAPER_EXECUTION, ENABLE_AUTOMATED_PAPER_EXITS,
                    MAX_EXIT_QUOTE_AGE_SECONDS, PUBLIC_DEMO_MODE)
from tools.alpaca_tools import AlpacaTools


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--execute', action='store_true', help='submit eligible atomic exits to Alpaca paper')
    args = parser.parse_args()
    authorized = bool(args.execute and ALLOW_PAPER_EXECUTION and ENABLE_AUTOMATED_PAPER_EXITS
                      and not PUBLIC_DEMO_MODE)
    broker = AlpacaTools(mutation_authorized=authorized)
    try:
        results = PositionLifecycleManager(
            broker, AuditLogger(), automated_exits_enabled=ENABLE_AUTOMATED_PAPER_EXITS,
            max_quote_age_seconds=MAX_EXIT_QUOTE_AGE_SECONDS,
        ).run(execute=authorized)
        for result in results:
            print(result)
        if args.execute and not authorized:
            raise SystemExit('Exit submission blocked by deployment policy.')
    finally:
        broker.close()


if __name__ == '__main__':
    main()
