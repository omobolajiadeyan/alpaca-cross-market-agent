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

# Minimum age (days) before a thesis's repricing_signals get scored against
# real subsequent market data. A real deployment should use 5-10 (roughly a
# trading week) so markets have time to actually move; kept low by default
# so the accuracy-tracking feature is demonstrable within a short window.
THESIS_EVALUATION_DAYS = float(os.getenv("THESIS_EVALUATION_DAYS", "1"))

# Database
DATABASE_URL = os.getenv("DATABASE_URL", "sqlite:///trading_log.db")

# Logging
LOG_LEVEL = os.getenv("LOG_LEVEL", "INFO")
LOG_FILE = os.getenv("LOG_FILE", "logs/trading.log")

# Risk Configuration
RISK_GATES = {
    'max_delta': 5000,
    'max_vega': 2000,
    'min_theta': 50,
    'max_loss_per_trade': 500,
    'daily_drawdown_limit': -2000,
    'max_drawdown_limit': -5000,
    'margin_utilization_cap': 0.30,
    'bid_ask_spread_limit': 0.05,
    'min_volume': 100000
}

# Markets to Monitor
MARKETS = {
    'equity': 'SPY',
    'credit': 'HYG',
    'duration': 'TLT'
}
