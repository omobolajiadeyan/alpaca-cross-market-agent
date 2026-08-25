"""
Quick test to verify everything is set up correctly
"""

import sys
import os

sys.path.insert(0, os.path.abspath('.'))

print("\n" + "="*70)
print("TESTING PROJECT SETUP")
print("="*70 + "\n")

# Test 1: Config loads
print("[TEST 1] Loading configuration...")
try:
    from config import ALPACA_API_KEY, ANTHROPIC_API_KEY, RISK_GATES, MARKETS
    api_key_set = bool(ALPACA_API_KEY and ALPACA_API_KEY != 'your_alpaca_key_here')
    claude_key_set = bool(ANTHROPIC_API_KEY and ANTHROPIC_API_KEY != 'your_claude_key_here')

    if api_key_set and claude_key_set:
        print("  ✓ Config loaded with API keys configured\n")
    else:
        print("  ⚠ Config loaded but API keys not set (use real keys in .env)\n")
except Exception as e:
    print(f"  ✗ Config error: {e}\n")

# Test 2: Data feed
print("[TEST 2] Testing data feed...")
try:
    from src.data_feed.cross_market_feed import CrossMarketDataFeed
    feed = CrossMarketDataFeed()
    data = feed.get_full_market_state()

    markets = list(data.keys())
    print(f"  ✓ Data feed working")
    print(f"    Markets: {', '.join(markets)}\n")
except Exception as e:
    print(f"  ✗ Data feed error: {e}\n")

# Test 3: Synthesizer
print("[TEST 3] Testing synthesizer...")
try:
    from agent.synthesizer import MacroSynthesizer
    synth = MacroSynthesizer()
    print("  ✓ Synthesizer initialized\n")
except Exception as e:
    print(f"  ✗ Synthesizer error: {e}\n")

# Test 4: Constructor
print("[TEST 4] Testing trade constructor...")
try:
    from agent.constructor import TradeConstructor
    constructor = TradeConstructor()
    print("  ✓ Constructor initialized\n")
except Exception as e:
    print(f"  ✗ Constructor error: {e}\n")

# Test 5: Alpaca tools
print("[TEST 5] Testing Alpaca tools...")
try:
    from tools.alpaca_tools import AlpacaTools
    alpaca = AlpacaTools()
    account = alpaca.get_account_info()
    if account:
        print(f"  ✓ Alpaca tools working")
        print(f"    Balance: ${account['cash']:,.0f}\n")
except Exception as e:
    print(f"  ✗ Alpaca error: {e}\n")

# Test 6: Audit logger
print("[TEST 6] Testing audit logger...")
try:
    from compliance.audit_logger import AuditLogger
    logger = AuditLogger()
    print("  ✓ Audit logger initialized\n")
except Exception as e:
    print(f"  ✗ Audit logger error: {e}\n")

# Test 7: Full agent
print("[TEST 7] Testing full agent...")
try:
    from live.cross_market_agent import CrossMarketAgent
    print("  ✓ Agent imports successful\n")
except Exception as e:
    print(f"  ✗ Agent error: {e}\n")

print("="*70)
print("SETUP TEST COMPLETE")
print("="*70 + "\n")
