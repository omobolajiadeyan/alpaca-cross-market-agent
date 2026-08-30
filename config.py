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
