"""
Cross-market data feed
Pulls real data from multiple markets to feed to Claude.

All 6 markets are computed from live sources rather than fixed placeholder
numbers:
  - equity_vol: real SPY spot (Alpaca), real ATM implied vol + a same-strike
    call/put volume ratio (Alpaca options data), and a self-bootstrapping IV
    rank against this agent's own recorded IV history (see AuditLogger).
  - rates_curve / rate_expectations: the U.S. Treasury's public daily par
    yield curve (home.treasury.gov) -- not available from Alpaca, which
    trades equities/options/crypto, not government bond yields directly.
  - credit: a returns-based proxy (HYG vs. LQD vs. IEF 20-day returns), not
    the official ICE BofA OAS index -- that index isn't available without a
    separate paid/licensed data source, so this is labeled as a proxy rather
    than misrepresented as the real thing.
  - realized: computed here from real daily SPY bars (annualized stdev of
    daily returns, and average true range %), not a fixed number.
"""

import csv
import io
import os
import sys
from datetime import date, datetime

import httpx

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '../..')))
from config import MARKETS
from tools.alpaca_tools import AlpacaTools

TREASURY_CSV_URL = (
    "https://home.treasury.gov/resource-center/data-chart-center/interest-rates/"
    "daily-treasury-rates.csv/{year}/all?type=daily_treasury_yield_curve"
    "&field_tdr_date_value={year}&page&_format=csv"
)


class CrossMarketDataFeed:
    """
    Synthesizes data across 6 asset classes:
    1. Equity vol (real spot, real ATM IV, real ATM put/call volume ratio)
    2. Treasury curve (real 2yr/5yr/10yr par yields)
    3. Credit spreads (real HYG/LQD/IEF return-based proxy)
    4. Rate expectations (derived from the real curve's front end)
    5. Realized volatility (computed from real SPY daily bars)
    6. Positioning (same-strike put/call volume ratio, from real option data)
    """

    def __init__(self, alpaca=None, logger=None):
        print("[FEED] Initializing Alpaca MCP client...")
        self.alpaca = alpaca or AlpacaTools()
        self.logger = logger
        self._treasury_cache = None
        self._iv_data_cache = None

    def _fetch_treasury_curve(self):
        """Real daily par yield curve rates from the U.S. Treasury (public, no API key)."""
        if self._treasury_cache is not None:
            return self._treasury_cache
        try:
            url = TREASURY_CSV_URL.format(year=date.today().year)
            response = httpx.get(url, timeout=30)
            response.raise_for_status()
            reader = csv.DictReader(io.StringIO(response.text))
            latest = next(reader)
            self._treasury_cache = latest
            return latest
        except Exception as e:
            print(f"[ERROR] Treasury curve fetch: {e}")
            return None

    def _get_iv_data(self):
        """ATM IV + same-strike put/call volume, cached per get_full_market_state() call
        since both get_equity_vol_metrics and get_positioning need the same data."""
        if self._iv_data_cache is not None:
            return self._iv_data_cache
        symbol = MARKETS['equity']
        price = self.alpaca.get_stock_price(symbol)
        self._iv_data_cache = self.alpaca.get_atm_iv_and_volume(symbol, price) if price else {}
        return self._iv_data_cache

    def get_equity_vol_metrics(self):
        """Real equity volatility metrics: spot, ATM IV, IV rank, put/call volume ratio"""
        try:
            symbol = MARKETS['equity']
            price = self.alpaca.get_stock_price(symbol)
            if price is None:
                raise ValueError("no spot price available")

            iv_data = self._get_iv_data() or {}
            atm_iv = iv_data.get('atm_iv')

            iv_rank = None
            if self.logger and atm_iv is not None:
                self.logger.record_iv(symbol, atm_iv)
                iv_rank = self.logger.get_iv_rank(symbol, atm_iv)

            return {
                'price': price,
                'atm_iv': atm_iv,
                'iv_rank': iv_rank,
                'iv_rank_note': 'percentile vs this agent\'s own recorded IV history, not a 252-day rank',
                'put_call_vol_ratio': iv_data.get('put_call_vol_ratio'),
                'market': 'EQUITY',
                'timestamp': datetime.now().isoformat()
            }
        except Exception as e:
            print(f"[ERROR] Equity vol: {e}")
            return {
                'price': 450.0,
                'atm_iv': None,
                'iv_rank': None,
                'put_call_vol_ratio': None,
                'market': 'EQUITY',
                'note': 'fallback placeholder -- live data unavailable',
                'timestamp': datetime.now().isoformat()
            }

    def get_treasury_curve(self):
        """Real Treasury yields (U.S. Treasury daily par yield curve)"""
        latest = self._fetch_treasury_curve()
        if not latest:
            return {
                'yields': {'2yr': 4.50, '5yr': 4.30, '10yr': 4.10},
                'curve_slope': -0.40,
                'curve_status': 'INVERTED',
                'market': 'RATES',
                'note': 'fallback placeholder -- live Treasury data unavailable',
                'timestamp': datetime.now().isoformat()
            }

        two_yr = float(latest['2 Yr'])
        five_yr = float(latest['5 Yr'])
        ten_yr = float(latest['10 Yr'])
        slope = ten_yr - two_yr

        return {
            'yields': {'2yr': two_yr, '5yr': five_yr, '10yr': ten_yr},
            'curve_slope': round(slope, 2),
            'curve_status': 'INVERTED' if slope < 0 else 'NORMAL',
            'as_of': latest.get('Date'),
            'market': 'RATES',
            'timestamp': datetime.now().isoformat()
        }

    def get_rate_expectations(self):
        """Rate expectations derived from the real curve's front end (1yr vs. 3mo).

        NOTE: this is a curve-shape proxy, not a genuine fed-funds-futures-implied
        rate. `short_end_yield_3mo` is literally the 3-month T-bill yield -- it is
        reported (not a market-implied policy path) so that Claude's synthesis and
        falsification prompts don't misread it as something it isn't (a mislabeled
        earlier version of this field caused exactly that confusion).
        """
        latest = self._fetch_treasury_curve()
        if not latest:
            return {
                'short_end_yield_3mo': 5.25,
                'rate_change_expected': 'DOWN',
                'market': 'RATES_EXPECTATIONS',
                'note': 'fallback placeholder -- live Treasury data unavailable',
                'timestamp': datetime.now().isoformat()
            }

        three_mo = float(latest['3 Mo'])
        one_yr = float(latest['1 Yr'])
        # 3-month yield closely tracks the current effective policy rate;
        # 1yr vs. 3mo direction is a real, live proxy for what the market expects.
        if one_yr < three_mo - 0.05:
            direction = 'DOWN'
        elif one_yr > three_mo + 0.05:
            direction = 'UP'
        else:
            direction = 'FLAT'

        return {
            'short_end_yield_3mo': three_mo,
            'one_year_yield': one_yr,
            'rate_change_expected': direction,
            'note': (
                "short_end_yield_3mo is the reported 3-month Treasury bill yield, "
                "a near-term-policy-rate proxy -- not a fed-funds-futures-implied "
                "rate. rate_change_expected direction comes from comparing it to "
                "the 1-year yield, not from any other point on the curve."
            ),
            'as_of': latest.get('Date'),
            'market': 'RATES_EXPECTATIONS',
            'timestamp': datetime.now().isoformat()
        }

    def get_credit_spreads(self):
        """
        Real, returns-based credit-stress proxy: how much HY (HYG) and IG (LQD)
        have under/outperformed Treasuries (IEF) over the last 20 sessions.
        This is NOT the official ICE BofA OAS index (that requires a licensed
        data source) -- it's a live-data proxy, labeled as such.
        """
        try:
            bars = self.alpaca.get_daily_bars_multi(['HYG', 'LQD', 'IEF'], days=25)

            def total_return(symbol_bars):
                closes = [b['c'] for b in symbol_bars]
                if len(closes) < 2:
                    return None
                return (closes[-1] / closes[0]) - 1

            hy_return = total_return(bars.get('HYG', []))
            ig_return = total_return(bars.get('LQD', []))
            tsy_return = total_return(bars.get('IEF', []))

            if None in (hy_return, ig_return, tsy_return):
                raise ValueError("insufficient bar history")

            # Treasuries outperforming credit -> credit is under stress (spreads widening)
            hy_spread_proxy_bps = round((tsy_return - hy_return) * 10000, 1)
            ig_spread_proxy_bps = round((tsy_return - ig_return) * 10000, 1)
            spread_ratio = (hy_spread_proxy_bps / ig_spread_proxy_bps) if ig_spread_proxy_bps else None

            return {
                'hy_spread_proxy_bps': hy_spread_proxy_bps,
                'ig_spread_proxy_bps': ig_spread_proxy_bps,
                'spread_ratio': round(spread_ratio, 2) if spread_ratio is not None else None,
                'proxy_note': '20-day HYG/LQD return vs. IEF (Treasuries) -- a live proxy, not the official OAS index',
                'market': 'CREDIT',
                'timestamp': datetime.now().isoformat()
            }
        except Exception as e:
            print(f"[ERROR] Credit spreads: {e}")
            return {
                'hy_oas': 375,
                'ig_oas': 150,
                'spread_ratio': 2.5,
                'market': 'CREDIT',
                'note': 'fallback placeholder -- live data unavailable',
                'timestamp': datetime.now().isoformat()
            }

    def get_realized_volatility(self):
        """Real realized volatility, computed from actual SPY daily bars"""
        try:
            metrics = self.alpaca.get_realized_vol_metrics(MARKETS['equity'], days=21)
            if not metrics:
                raise ValueError("insufficient bar history")
            return {
                'realized_vol': round(metrics['realized_vol'], 4),
                'atr_pct': round(metrics['atr_pct'], 2) if metrics['atr_pct'] is not None else None,
                'market': 'REALIZED',
                'timestamp': datetime.now().isoformat()
            }
        except Exception as e:
            print(f"[ERROR] Realized volatility: {e}")
            return {
                'realized_vol': 0.12,
                'atr_pct': 1.2,
                'market': 'REALIZED',
                'note': 'fallback placeholder -- live data unavailable',
                'timestamp': datetime.now().isoformat()
            }

    def get_positioning(self):
        """Same-strike ATM put/call volume ratio, from real option data"""
        try:
            iv_data = self._get_iv_data()
            ratio = iv_data.get('put_call_vol_ratio') if iv_data else None
            if ratio is None:
                raise ValueError("no option volume available")
            return {
                'put_call_ratio': round(ratio, 2),
                'positioning': 'BEARISH' if ratio > 1 else 'BULLISH',
                'proxy_note': 'ATM same-strike put/call volume ratio, not a market-wide put/call ratio',
                'market': 'POSITIONING',
                'timestamp': datetime.now().isoformat()
            }
        except Exception as e:
            print(f"[ERROR] Positioning: {e}")
            return {
                'put_call_ratio': 0.95,
                'positioning': 'BULLISH',
                'market': 'POSITIONING',
                'note': 'fallback placeholder -- live data unavailable',
                'timestamp': datetime.now().isoformat()
            }

    def get_full_market_state(self):
        """Get all market data at once"""
        state = {
            'equity_vol': self.get_equity_vol_metrics(),
            'rates_curve': self.get_treasury_curve(),
            'credit': self.get_credit_spreads(),
            'realized': self.get_realized_volatility(),
            'rate_expectations': self.get_rate_expectations(),
            'positioning': self.get_positioning(),
            'timestamp': datetime.now().isoformat()
        }
        sources = {}
        for name, payload in state.items():
            if not isinstance(payload, dict):
                continue
            sources[name] = {
                'status': 'fallback' if payload.get('note', '').startswith('fallback') else 'live',
                'note': payload.get('proxy_note') or payload.get('note') or 'Direct or computed live market data',
                'timestamp': payload.get('timestamp'),
            }
        state['data_quality'] = {
            'all_live': all(source['status'] == 'live' for source in sources.values()),
            'fallback_sources': [name for name, source in sources.items() if source['status'] == 'fallback'],
            'sources': sources,
        }
        self._iv_data_cache = None
        return state
