"""
Alpaca trading tools

Routes account, position, market-data, and options-order operations through
Alpaca's official MCP server (the `alpaca-mcp-server` package), per the
hackathon requirement to use Alpaca's Trading API via its MCP server (or CLI)
and to trade options in the paper environment.

Uses one persistent MCP connection (a background thread running its own
asyncio event loop) for the lifetime of an AlpacaTools instance, instead of
spawning a fresh subprocess per call -- the agent now makes many calls per
cycle (spot prices, option chains, snapshots, bars, orders) and re-spawning
`alpaca-mcp-server` for each one added seconds of pure startup overhead.
"""

import asyncio
import json
import os
import shutil
import statistics
import sys
import threading
from datetime import date, timedelta

from mcp import ClientSession, StdioServerParameters
from mcp.client.stdio import stdio_client

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))
from config import ALPACA_API_KEY, ALPACA_SECRET_KEY, ALPACA_BASE_URL, MAX_LOSS_PER_TRADE


def _server_params():
    command = shutil.which("alpaca-mcp-server") or os.path.join(
        os.path.dirname(sys.executable), "alpaca-mcp-server"
    )
    env = os.environ.copy()
    env["ALPACA_API_KEY"] = ALPACA_API_KEY or ""
    env["ALPACA_SECRET_KEY"] = ALPACA_SECRET_KEY or ""
    env["ALPACA_PAPER_TRADE"] = "true" if "paper" in ALPACA_BASE_URL else "false"
    return StdioServerParameters(command=command, args=[], env=env)


class AlpacaMCPError(Exception):
    """Raised when the Alpaca MCP server returns an {"error": ...} payload
    without the underlying transport itself raising (e.g. a rejected order)."""


def _innermost(exc):
    """anyio's TaskGroups (used by stdio_client) can nest ExceptionGroups
    multiple levels deep around a single real exception -- unwrap to it."""
    while isinstance(exc, ExceptionGroup) and len(exc.exceptions) == 1:
        exc = exc.exceptions[0]
    return exc


class _AlpacaMCPSession:
    """
    One persistent stdio connection to alpaca-mcp-server, run on a dedicated
    background event loop thread so the rest of this (synchronous) codebase
    can call it without paying subprocess-startup cost on every tool call.
    """

    def __init__(self):
        self._loop = asyncio.new_event_loop()
        self._thread = threading.Thread(target=self._loop.run_forever, daemon=True)
        self._thread.start()
        self._stdio_cm = None
        self._session_cm = None
        self._session = None
        self._run(self._connect(), timeout=30)

    def _run(self, coro, timeout=60):
        future = asyncio.run_coroutine_threadsafe(coro, self._loop)
        try:
            return future.result(timeout=timeout)
        except ExceptionGroup as eg:
            raise _innermost(eg) from None

    async def _connect(self):
        self._stdio_cm = stdio_client(_server_params())
        read, write = await self._stdio_cm.__aenter__()
        self._session_cm = ClientSession(read, write)
        self._session = await self._session_cm.__aenter__()
        await self._session.initialize()

    async def _call_async(self, tool_name, arguments):
        result = await self._session.call_tool(tool_name, arguments or {})
        text = "".join(block.text for block in result.content if block.type == "text")
        parsed = json.loads(text)
        payload = parsed.get("data", parsed) if isinstance(parsed, dict) else parsed
        if isinstance(payload, dict) and "error" in payload:
            err = payload["error"]
            raise AlpacaMCPError(err.get("detail", {}).get("message") or err.get("message", str(err)))
        return payload

    def call(self, tool_name, arguments=None):
        return self._run(self._call_async(tool_name, arguments))

    def close(self):
        async def _close():
            if self._session_cm:
                await self._session_cm.__aexit__(None, None, None)
            if self._stdio_cm:
                await self._stdio_cm.__aexit__(None, None, None)
        try:
            self._run(_close(), timeout=10)
        except Exception:
            pass
        self._loop.call_soon_threadsafe(self._loop.stop)
        self._thread.join(timeout=5)


class AlpacaTools:
    """
    Wrapper around Alpaca's MCP server for paper trading: account/position
    lookups, market data (spot prices, bars, option chains/snapshots), and
    options order execution -- all over one persistent MCP connection.
    """

    def __init__(self):
        print("[ALPACA] Connecting to Alpaca MCP server (alpaca-mcp-server)...")
        self._session = _AlpacaMCPSession()
        print("[ALPACA] ✓ Connected")

    def close(self):
        self._session.close()

    def call(self, tool_name, arguments=None):
        return self._session.call(tool_name, arguments)

    def get_account_info(self):
        """Get account balance and state"""
        try:
            data = self.call("get_account_info")
            return {
                'cash': float(data['cash']),
                'portfolio_value': float(data['portfolio_value']),
                'buying_power': float(data['buying_power']),
                'status': 'connected'
            }
        except Exception as e:
            print(f"[ERROR] Account info: {e}")
            # Clearly marked mock state: callers must never mistake this for a live account.
            return {
                'cash': 100000.0,
                'portfolio_value': 100000.0,
                'buying_power': 400000.0,
                'status': 'mock'
            }

    def get_order(self, order_id):
        """Fetch the latest lifecycle state for a submitted order."""
        try:
            return self.call("get_order_by_id", {'order_id': order_id})
        except Exception as e:
            return {'id': order_id, 'status': 'unknown', 'error': str(e)}

    def get_positions(self):
        """Get open positions"""
        try:
            data = self.call("get_all_positions")
            positions = data if isinstance(data, list) else data.get('positions', [])
            return [
                {
                    'symbol': p['symbol'],
                    'qty': p['qty'],
                    'current_price': float(p.get('current_price', 0) or 0),
                    'pnl': float(p.get('unrealized_pl', 0) or 0)
                }
                for p in positions
            ]
        except Exception as e:
            print(f"[ERROR] Get positions: {e}")
            return []

    def get_stock_price(self, symbol):
        """Latest trade price for an underlying (used to find at-the-money strikes)"""
        try:
            data = self.call("get_stock_latest_trade", {'symbols': symbol})
            return float(data['trades'][symbol]['p'])
        except Exception as e:
            print(f"[ERROR] Get stock price for {symbol}: {e}")
            return None

    def get_daily_bars(self, symbol, days=30):
        """Recent daily OHLCV bars for one symbol"""
        return self.get_daily_bars_multi([symbol], days=days).get(symbol, [])

    def get_daily_bars_multi(self, symbols, days=30):
        """Recent daily OHLCV bars for several symbols in a single call"""
        try:
            data = self.call("get_stock_bars", {
                'symbols': ",".join(symbols), 'timeframe': '1Day', 'days': days
            })
            return data.get('bars', {})
        except Exception as e:
            print(f"[ERROR] Get daily bars for {symbols}: {e}")
            return {}

    def get_realized_vol_metrics(self, symbol=None, days=21, bars=None):
        """
        Annualized realized volatility and average true range % from real
        daily closing prices -- computed here, not fetched pre-computed.
        Pass `bars` directly to reuse an already-fetched multi-symbol batch.
        """
        if bars is None:
            bars = self.get_daily_bars(symbol, days=days + 1)
        if len(bars) < 2:
            return None

        closes = [b['c'] for b in bars]
        daily_returns = [
            (closes[i] / closes[i - 1]) - 1
            for i in range(1, len(closes))
        ]
        realized_vol = statistics.pstdev(daily_returns) * (252 ** 0.5)

        atr_pcts = [
            (b['h'] - b['l']) / b['c'] for b in bars if b.get('c')
        ]
        atr_pct = statistics.mean(atr_pcts) * 100 if atr_pcts else None

        return {'realized_vol': realized_vol, 'atr_pct': atr_pct}

    def find_option_contract(self, underlying_symbol, option_type, target_strike,
                              days_out_min=25, days_out_max=45, strike_band=0.2):
        """Find the real, tradable option contract closest to a target strike."""
        try:
            today = date.today()
            data = self.call("get_option_contracts", {
                'underlying_symbols': underlying_symbol,
                'type': option_type,
                'expiration_date_gte': (today + timedelta(days=days_out_min)).isoformat(),
                'expiration_date_lte': (today + timedelta(days=days_out_max)).isoformat(),
                # Without a strike bound, `limit` can silently truncate before reaching
                # the target strike on instruments with hundreds of strikes (e.g. SPY).
                'strike_price_gte': round(target_strike * (1 - strike_band), 2),
                'strike_price_lte': round(target_strike * (1 + strike_band), 2),
                'limit': 100,
            })
            contracts = data.get('option_contracts', [])
            if not contracts:
                return None
            return min(contracts, key=lambda c: abs(float(c['strike_price']) - target_strike))
        except Exception as e:
            print(f"[ERROR] Find option contract for {underlying_symbol}: {e}")
            return None

    def get_option_snapshot(self, contract_symbol):
        """Full snapshot (implied vol, greeks, latest quote/trade/bar) for one contract"""
        try:
            data = self.call("get_option_snapshot", {'symbols': contract_symbol})
            return data.get('snapshots', {}).get(contract_symbol)
        except Exception as e:
            print(f"[ERROR] Get option snapshot for {contract_symbol}: {e}")
            return None

    def get_atm_iv_and_volume(self, underlying_symbol, spot):
        """
        Real ATM implied volatility (from the nearest-strike call) and a
        same-strike call/put daily-volume ratio, as a lightweight, genuinely
        live positioning proxy (not a market-wide put/call ratio).
        """
        call_contract = self.find_option_contract(underlying_symbol, 'call', target_strike=spot,
                                                    days_out_min=25, days_out_max=45)
        if not call_contract:
            return None

        call_snap = self.get_option_snapshot(call_contract['symbol'])
        if not call_snap:
            return None

        put_contract = self.find_option_contract(underlying_symbol, 'put', target_strike=spot,
                                                   days_out_min=25, days_out_max=45)
        put_snap = self.get_option_snapshot(put_contract['symbol']) if put_contract else None

        call_volume = (call_snap.get('dailyBar') or {}).get('v', 0)
        put_volume = (put_snap.get('dailyBar') or {}).get('v', 0) if put_snap else 0

        # Below this, one side's volume is thin enough that the ratio is
        # dominated by noise (e.g. call_volume=1 makes any put_volume look
        # like an extreme, meaningless ratio) rather than real positioning.
        min_reliable_volume = 10
        reliable = call_volume >= min_reliable_volume and put_volume >= min_reliable_volume

        return {
            'atm_iv': call_snap.get('impliedVolatility'),
            'call_volume': call_volume,
            'put_volume': put_volume,
            'put_call_vol_ratio': (put_volume / call_volume) if reliable else None,
        }

    def get_option_ask_price(self, contract_symbol):
        """Latest ask price for one option contract"""
        bid_ask = self.get_option_bid_ask(contract_symbol)
        return bid_ask[1] if bid_ask else None

    def get_option_bid_ask(self, contract_symbol):
        """Latest (bid, ask) for one option contract"""
        try:
            data = self.call("get_option_latest_quote", {'symbols': contract_symbol})
            quote = data['quotes'][contract_symbol]
            return float(quote['bp']), float(quote['ap'])
        except Exception as e:
            print(f"[ERROR] Get option quote for {contract_symbol}: {e}")
            return None

    def place_option_order(self, symbol, side, qty=1, position_intent=None):
        """Submit a single-leg market options order via Alpaca's MCP server.
        Raises AlpacaMCPError (or another exception) on rejection -- callers
        that want a soft failure should catch it, e.g. execute_leg below."""
        args = {'symbol': symbol, 'side': side, 'qty': str(qty), 'type': 'market'}
        if position_intent:
            args['position_intent'] = position_intent
        return self.call("place_option_order", args)

    def place_multileg_option_order(self, legs, qty=1):
        """Submit a multi-leg (e.g. vertical spread) market options order.
        `legs` is a list of {'symbol', 'side', 'position_intent'} dicts (max 4).
        Raises AlpacaMCPError (or another exception) on rejection."""
        args = {
            'qty': str(qty),
            'type': 'market',
            'order_class': 'mleg',
            'legs': [
                {'symbol': leg['symbol'], 'ratio_qty': '1', 'side': leg['side'],
                 'position_intent': leg['position_intent']}
                for leg in legs
            ],
        }
        return self.call("place_option_order", args)

    def execute_spread(self, underlying_symbol, option_type, spread_type,
                        max_premium=None, qty=1, width_pct=0.01, submit=True):
        """
        Build and submit a real 2-leg vertical spread (the actual "asymmetric,
        defined-risk" structure the project's thesis narrative describes,
        rather than a naive single-leg call/put):

        - 'near' leg: contract closest to the current spot price (ATM-ish)
        - 'far' leg: contract `width_pct` further out of the money
        - spread_type='debit': buy near, sell far (bull call spread / bear put spread)
        - spread_type='credit': sell near, buy far (bear call spread / bull put spread)

        Max loss is computed properly for each type (a debit spread can't lose
        more than its cost; a credit spread's max loss is the strike width
        minus the credit received) and checked against `max_premium` before
        submitting. Returns a dict describing what happened either way.
        """
        max_premium = MAX_LOSS_PER_TRADE if max_premium is None else max_premium

        spot = self.get_stock_price(underlying_symbol)
        if spot is None:
            return {'submitted': False, 'reason': 'could not fetch underlying price'}

        far_target = spot * (1 + width_pct) if option_type == 'call' else spot * (1 - width_pct)

        near = self.find_option_contract(underlying_symbol, option_type, target_strike=spot)
        far = self.find_option_contract(underlying_symbol, option_type, target_strike=far_target)
        if not near or not far or near['symbol'] == far['symbol']:
            return {'submitted': False, 'reason': 'could not find two distinct strikes for a spread'}

        near_quote = self.get_option_bid_ask(near['symbol'])
        far_quote = self.get_option_bid_ask(far['symbol'])
        if not near_quote or not far_quote:
            return {'submitted': False, 'reason': 'no quote available for one or both legs'}

        near_bid, near_ask = near_quote
        far_bid, far_ask = far_quote
        multiplier = float(near.get('multiplier', 100))
        strike_width = abs(float(far['strike_price']) - float(near['strike_price']))

        if spread_type == 'debit':
            net_price = near_ask - far_bid  # buy near at ask, sell far at bid
            max_loss = max(net_price, 0) * multiplier * qty
            legs = [
                {'symbol': near['symbol'], 'side': 'buy', 'position_intent': 'buy_to_open'},
                {'symbol': far['symbol'], 'side': 'sell', 'position_intent': 'sell_to_open'},
            ]
        elif spread_type == 'credit':
            net_credit = near_bid - far_ask  # sell near at bid, buy far at ask
            max_loss = max(strike_width - max(net_credit, 0), 0) * multiplier * qty
            legs = [
                {'symbol': near['symbol'], 'side': 'sell', 'position_intent': 'sell_to_open'},
                {'symbol': far['symbol'], 'side': 'buy', 'position_intent': 'buy_to_open'},
            ]
        else:
            return {'submitted': False, 'reason': f"unknown spread_type '{spread_type}'"}

        if max_loss > max_premium:
            return {
                'submitted': False,
                'legs': [near['symbol'], far['symbol']],
                'max_loss': max_loss,
                'reason': f'max loss ${max_loss:,.0f} exceeds max_loss_per_trade cap ${max_premium:,.0f}'
            }

        prepared = {
            'submitted': False,
            'preflight_passed': True,
            'legs': [near['symbol'], far['symbol']],
            'max_loss': max_loss,
            'order_legs': legs,
            'qty': qty,
        }
        if not submit:
            return prepared

        try:
            order = self.place_multileg_option_order(legs, qty=qty)
        except Exception as e:
            print(f"[ERROR] Place multi-leg order for {underlying_symbol}: {e}")
            return {
                'submitted': False,
                'legs': [near['symbol'], far['symbol']],
                'max_loss': max_loss,
                'reason': str(e),
            }

        order_id = order.get('id') if isinstance(order, dict) else None
        return {
            'submitted': True,
            'preflight_passed': True,
            'legs': [near['symbol'], far['symbol']],
            'max_loss': max_loss,
            'order': order,
            'order_id': order_id,
            'status': order.get('status', 'submitted') if isinstance(order, dict) else 'submitted',
        }

    def execute_leg(self, underlying_symbol, option_type, max_premium=None, qty=1):
        """
        Find a real ATM-ish contract for `underlying_symbol`, check its premium
        against a risk cap, and submit a buy order (long call or long put) if
        it fits. Returns a dict describing what happened, for the audit trail.
        """
        max_premium = MAX_LOSS_PER_TRADE if max_premium is None else max_premium

        spot = self.get_stock_price(underlying_symbol)
        if spot is None:
            return {'submitted': False, 'reason': 'could not fetch underlying price'}

        contract = self.find_option_contract(underlying_symbol, option_type, target_strike=spot)
        if not contract:
            return {'submitted': False, 'reason': 'no matching option contract found'}

        contract_symbol = contract['symbol']
        multiplier = float(contract.get('multiplier', 100))

        ask = self.get_option_ask_price(contract_symbol)
        if ask is None:
            return {'submitted': False, 'contract': contract_symbol, 'reason': 'no quote available'}

        premium = ask * multiplier * qty
        if premium > max_premium:
            return {
                'submitted': False,
                'contract': contract_symbol,
                'premium': premium,
                'reason': f'premium ${premium:,.0f} exceeds max_loss_per_trade cap ${max_premium:,.0f}'
            }

        try:
            order = self.place_option_order(contract_symbol, side='buy', qty=qty, position_intent='buy_to_open')
        except Exception as e:
            print(f"[ERROR] Place option order for {contract_symbol}: {e}")
            return {
                'submitted': False,
                'contract': contract_symbol,
                'premium': premium,
                'reason': str(e),
            }

        return {
            'submitted': True,
            'contract': contract_symbol,
            'premium': premium,
            'order': order,
        }
