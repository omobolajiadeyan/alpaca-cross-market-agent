"""
Central configuration for the trading agent
"""

import os
from dotenv import load_dotenv

load_dotenv()

# Alpaca Configuration
ALPACA_API_KEY = os.getenv("APCA_API_KEY_ID")
ALPACA_SECRET_KEY = os.getenv("APCA_API_SECRET_KEY")
ALPACA_BASE_URL = os.getenv("APCA_API_BASE_URL", "https://paper-api.alpaca.markets")

# Anthropic Configuration
ANTHROPIC_API_KEY = os.getenv("ANTHROPIC_API_KEY")

# Trading Configuration
INITIAL_BALANCE = float(os.getenv("INITIAL_BALANCE", "100000"))
MAX_LOSS_PER_TRADE = float(os.getenv("MAX_LOSS_PER_TRADE", "500"))
MAX_PORTFOLIO_LOSS = float(os.getenv("MAX_PORTFOLIO_LOSS", "1500"))
MIN_SIGNAL_CONFIDENCE = float(os.getenv("MIN_SIGNAL_CONFIDENCE", "0.55"))
MAX_MARGIN_UTILIZATION = float(os.getenv("MAX_MARGIN_UTILIZATION", "0.30"))
REQUIRE_LIVE_DATA = os.getenv("REQUIRE_LIVE_DATA", "true").lower() in ("1", "true", "yes")
ALLOW_PAPER_EXECUTION = os.getenv("ALLOW_PAPER_EXECUTION", "false").lower() in ("1", "true", "yes")
PUBLIC_DEMO_MODE = os.getenv("PUBLIC_DEMO_MODE", "true").lower() in ("1", "true", "yes")

# Healthy-position lifecycle. Entry authorization and exit authorization are
# deliberately separate: a public/replay deployment can prove the policy
# without gaining the ability to mutate a broker account.
ENABLE_AUTOMATED_PAPER_EXITS = os.getenv("ENABLE_AUTOMATED_PAPER_EXITS", "false").lower() in ("1", "true", "yes")
PAUSE_NEW_ENTRIES = os.getenv("PAUSE_NEW_ENTRIES", "false").lower() in ("1", "true", "yes")
TAKE_PROFIT_FRACTION = float(os.getenv("TAKE_PROFIT_FRACTION", "0.50"))
STOP_LOSS_FRACTION = float(os.getenv("STOP_LOSS_FRACTION", "0.50"))
MAX_HOLDING_DAYS = int(os.getenv("MAX_HOLDING_DAYS", "5"))
EXIT_BEFORE_EXPIRY_DAYS = int(os.getenv("EXIT_BEFORE_EXPIRY_DAYS", "2"))
MAX_EXIT_QUOTE_AGE_SECONDS = int(os.getenv("MAX_EXIT_QUOTE_AGE_SECONDS", "300"))
if not 0 < TAKE_PROFIT_FRACTION <= 1:
    raise ValueError("TAKE_PROFIT_FRACTION must be greater than 0 and at most 1")
if not 0 < STOP_LOSS_FRACTION <= 1:
    raise ValueError("STOP_LOSS_FRACTION must be greater than 0 and at most 1")
if MAX_HOLDING_DAYS < 1 or EXIT_BEFORE_EXPIRY_DAYS < 0:
    raise ValueError("Exit timing values must be non-negative and MAX_HOLDING_DAYS at least 1")
if MAX_EXIT_QUOTE_AGE_SECONDS < 1:
    raise ValueError("MAX_EXIT_QUOTE_AGE_SECONDS must be at least 1")

# Minimum age before a thesis is scored against subsequent market data.
# Five trading days gives the stated repricing thesis time to develop; it is
# still preliminary evidence rather than an investment-grade backtest.
EVALUATION_HORIZON_DAYS = float(os.getenv("EVALUATION_HORIZON_DAYS", "5"))
THESIS_EVALUATION_DAYS = EVALUATION_HORIZON_DAYS

# Database
DATABASE_URL = os.getenv("DATABASE_URL", "sqlite:///trading_log.db")

# Logging
LOG_LEVEL = os.getenv("LOG_LEVEL", "INFO")
LOG_FILE = os.getenv("LOG_FILE", "logs/trading.log")

# Risk Configuration
RISK_GATES = {
    'max_delta': 5000,
    'max_vega': 2000,
    'min_theta': -100,
    'max_loss_per_trade': 500,
    'daily_drawdown_limit': -2000,
    'max_drawdown_limit': -5000,
    'margin_utilization_cap': 0.30,
    'bid_ask_spread_limit': 0.25,
    'min_volume': 10
}

# Markets to Monitor
MARKETS = {
    'equity': 'SPY',
    'credit': 'HYG',
    'duration': 'TLT'
}
