"""
Audit trail logging
Every decision is logged with full transparency
"""

import sqlite3
import json
from datetime import datetime, timedelta
import os
from security.controls import redact


class AuditLogger:
    """
    SQLite-based audit trail
    Logs all theses, trades, and decisions
    """

    def __init__(self, db_path="trading_audit.db"):
        self.db_path = db_path
        self._init_db()

    def _init_db(self):
        """Initialize database tables"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()

        # Theses table
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS theses (
                id INTEGER PRIMARY KEY,
                timestamp TEXT,
                thesis TEXT,
                rationale TEXT,
                confidence REAL,
                repricing_signals TEXT
            )
        """)

        # Schema migration: add accuracy-tracking columns to theses created
        # before this feature existed, without losing already-logged rows.
        existing_columns = {row[1] for row in cursor.execute("PRAGMA table_info(theses)")}
        for column, ddl in (
            ('market_state', 'TEXT'),
            ('evaluated', 'INTEGER DEFAULT 0'),
            ('hit_rate', 'REAL'),
            ('evaluated_at', 'TEXT'),
            ('evaluation_detail', 'TEXT'),
        ):
            if column not in existing_columns:
                cursor.execute(f"ALTER TABLE theses ADD COLUMN {column} {ddl}")

        # Trades table
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS trades (
                id INTEGER PRIMARY KEY,
                timestamp TEXT,
                thesis_id INTEGER,
                strategy TEXT,
                portfolio TEXT,
                status TEXT
            )
        """)

        # Implied-vol history, so IV rank can be computed against the agent's
        # own observed history instead of a hardcoded percentile
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS iv_history (
                id INTEGER PRIMARY KEY,
                timestamp TEXT,
                symbol TEXT,
                iv REAL
            )
        """)

        cursor.execute("""
            CREATE TABLE IF NOT EXISTS decision_contracts (
                contract_id TEXT PRIMARY KEY,
                decision_hash TEXT NOT NULL,
                created_at TEXT NOT NULL,
                authorization TEXT NOT NULL,
                contract_json TEXT NOT NULL,
                execution_status TEXT DEFAULT 'not_submitted',
                trade_id INTEGER,
                evaluated INTEGER DEFAULT 0,
                evaluation_json TEXT
            )
        """)

        cursor.execute("""
            CREATE TABLE IF NOT EXISTS managed_positions (
                id INTEGER PRIMARY KEY,
                trade_id INTEGER NOT NULL,
                contract_id TEXT,
                role TEXT NOT NULL,
                underlying_symbol TEXT NOT NULL,
                strategy TEXT,
                spread_type TEXT NOT NULL,
                qty INTEGER NOT NULL,
                multiplier REAL NOT NULL DEFAULT 100,
                opening_legs_json TEXT NOT NULL,
                entry_order_id TEXT,
                entry_price REAL NOT NULL,
                max_profit REAL NOT NULL,
                max_loss REAL NOT NULL,
                take_profit_target REAL NOT NULL,
                stop_loss_limit REAL NOT NULL,
                max_holding_days INTEGER NOT NULL,
                exit_before_expiry_days INTEGER NOT NULL,
                expiration_date TEXT,
                opened_at TEXT,
                status TEXT NOT NULL,
                exit_reason TEXT,
                exit_order_id TEXT,
                exit_client_order_id TEXT,
                exit_attempts INTEGER NOT NULL DEFAULT 0,
                exit_submitted_at TEXT,
                closed_at TEXT,
                last_mark REAL,
                last_pnl REAL,
                last_checked_at TEXT,
                realized_pnl REAL,
                UNIQUE(entry_order_id, role)
            )
        """)
        position_columns = {
            row[1] for row in cursor.execute("PRAGMA table_info(managed_positions)")
        }
        for column, ddl in (
            ('exit_client_order_id', 'TEXT'),
            ('exit_attempts', 'INTEGER NOT NULL DEFAULT 0'),
            ('exit_submitted_at', 'TEXT'),
        ):
            if column not in position_columns:
                cursor.execute(f"ALTER TABLE managed_positions ADD COLUMN {column} {ddl}")
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS position_events (
                id INTEGER PRIMARY KEY,
                position_id INTEGER NOT NULL,
                timestamp TEXT NOT NULL,
                event_type TEXT NOT NULL,
                state_before TEXT,
                state_after TEXT,
                reason TEXT,
                detail_json TEXT,
                FOREIGN KEY(position_id) REFERENCES managed_positions(id)
            )
        """)

        conn.commit()
        conn.close()

    def record_iv(self, symbol, iv):
        """Record one observed implied-vol reading for `symbol`"""
        if iv is None:
            return
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        cursor.execute(
            "INSERT INTO iv_history (timestamp, symbol, iv) VALUES (?, ?, ?)",
            (datetime.now().isoformat(), symbol, iv)
        )
        conn.commit()
        conn.close()

    def get_iv_rank(self, symbol, current_iv):
        """
        Percentile rank (0-100) of `current_iv` against every IV reading this
        agent has recorded for `symbol` so far. Starts at 100 with one data
        point and becomes a genuine IV rank as the agent accumulates history
        -- there's no full-year options history available to compute a
        textbook 252-day IV rank from a cold start.
        """
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        rows = cursor.execute(
            "SELECT iv FROM iv_history WHERE symbol = ?", (symbol,)
        ).fetchall()
        conn.close()

        history = [r[0] for r in rows]
        if not history:
            return None

        below_or_equal = sum(1 for v in history if v <= current_iv)
        return round(100 * below_or_equal / len(history), 1)

    def log_thesis(self, thesis, market_state=None):
        """Log a macro thesis, along with the market snapshot it was based on
        (needed later to score whether its repricing_signals actually happened)"""
        if not thesis:
            return

        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()

        cursor.execute("""
            INSERT INTO theses (timestamp, thesis, rationale, confidence, repricing_signals, market_state, evaluated)
            VALUES (?, ?, ?, ?, ?, ?, 0)
        """, (
            datetime.now().isoformat(),
            thesis.get('thesis', ''),
            thesis.get('rationale', ''),
            thesis.get('confidence_overall', 0),
            json.dumps(thesis.get('repricing_signals', [])),
            json.dumps(redact(market_state)) if market_state is not None else None,
        ))

        conn.commit()
        thesis_id = cursor.lastrowid
        conn.close()

        return thesis_id

    def get_pending_theses(self, min_age_days=1):
        """
        Theses old enough to evaluate, not yet scored, and with a stored
        market snapshot to compare against (older rows logged before this
        feature existed won't have one, and can't be scored).
        """
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        cutoff = (datetime.now() - timedelta(days=min_age_days)).isoformat()
        rows = cursor.execute("""
            SELECT id, timestamp, repricing_signals, market_state
            FROM theses
            WHERE evaluated = 0 AND timestamp <= ? AND market_state IS NOT NULL
        """, (cutoff,)).fetchall()
        conn.close()

        return [
            {
                'id': r[0],
                'timestamp': r[1],
                'repricing_signals': json.loads(r[2]) if r[2] else [],
                'market_state': json.loads(r[3]),
            }
            for r in rows
        ]

    def record_thesis_evaluation(self, thesis_id, hit_rate, detail):
        """Store the result of scoring one thesis's repricing_signals"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        cursor.execute("""
            UPDATE theses
            SET evaluated = 1, hit_rate = ?, evaluated_at = ?, evaluation_detail = ?
            WHERE id = ?
        """, (hit_rate, datetime.now().isoformat(), json.dumps(detail), thesis_id))
        conn.commit()
        conn.close()

    def get_track_record(self):
        """Aggregate accuracy across every thesis this agent has scored so far"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        rows = cursor.execute(
            "SELECT hit_rate FROM theses WHERE evaluated = 1 AND hit_rate IS NOT NULL"
        ).fetchall()
        pending = cursor.execute(
            "SELECT COUNT(*) FROM theses WHERE evaluated = 0"
        ).fetchone()[0]
        conn.close()

        hit_rates = [r[0] for r in rows]
        return {
            'theses_scored': len(hit_rates),
            'theses_pending': pending,
            'average_hit_rate': round(sum(hit_rates) / len(hit_rates), 3) if hit_rates else None,
        }

    def log_trade(self, thesis_id, portfolio):
        """Log a trade execution"""
        if not portfolio:
            return

        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()

        executions = [portfolio.get(name, {}).get('execution', {})
                      for name in ('primary_trade', 'secondary_trade', 'hedge')]
        submitted = sum(1 for execution in executions if execution.get('submitted'))
        if submitted == len(executions) and executions:
            status = 'submitted'
        elif submitted:
            status = 'partial'
        else:
            status = 'rejected'
        cursor.execute("""
            INSERT INTO trades (timestamp, thesis_id, strategy, portfolio, status)
            VALUES (?, ?, ?, ?, ?)
        """, (
            datetime.now().isoformat(),
            thesis_id,
            portfolio.get('primary_trade', {}).get('strategy', ''),
            json.dumps(redact(portfolio)),
            status
        ))

        conn.commit()
        trade_id = cursor.lastrowid
        conn.close()
        return trade_id

    def get_report(self):
        """Get audit report"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()

        theses_count = cursor.execute("SELECT COUNT(*) FROM theses").fetchone()[0]
        trades_count = cursor.execute("SELECT COUNT(*) FROM trades").fetchone()[0]

        conn.close()

        return {
            'total_theses': theses_count,
            'total_trades': trades_count
        }

    def register_managed_position(self, trade_id, contract_id, role, leg, policy):
        """Persist the exit contract for one submitted vertical spread."""
        execution = leg.get('execution', {})
        if not execution.get('submitted') or not execution.get('order_legs'):
            return None
        status = 'OPEN' if str(execution.get('status', '')).lower() == 'filled' else 'PENDING_ENTRY'
        opened_at = execution.get('filled_at') if status == 'OPEN' else None
        values = (
            trade_id, contract_id, role, leg.get('symbol', ''), leg.get('strategy', ''),
            execution.get('spread_type') or leg.get('spread_type', ''), int(execution.get('qty', leg.get('qty', 1))),
            float(execution.get('multiplier', 100)), json.dumps(redact(execution['order_legs'])),
            execution.get('order_id'), float(execution.get('limit_price', 0)),
            float(execution.get('max_profit', 0)), float(execution.get('max_loss', 0)),
            float(execution.get('max_profit', 0)) * float(policy['take_profit_fraction']),
            float(execution.get('max_loss', 0)) * float(policy['stop_loss_fraction']),
            int(policy['max_holding_days']), int(policy['exit_before_expiry_days']),
            execution.get('expiration_date'), opened_at, status,
        )
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        cursor.execute("""
            INSERT OR IGNORE INTO managed_positions
            (trade_id, contract_id, role, underlying_symbol, strategy, spread_type,
             qty, multiplier, opening_legs_json, entry_order_id, entry_price,
             max_profit, max_loss, take_profit_target, stop_loss_limit,
             max_holding_days, exit_before_expiry_days, expiration_date, opened_at, status)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, values)
        inserted = cursor.rowcount == 1
        position_id = cursor.lastrowid if inserted else None
        if position_id is None:
            row = cursor.execute(
                "SELECT id FROM managed_positions WHERE entry_order_id = ? AND role = ?",
                (execution.get('order_id'), role),
            ).fetchone()
            position_id = row[0] if row else None
        if position_id and inserted:
            cursor.execute("""
                INSERT INTO position_events
                (position_id, timestamp, event_type, state_before, state_after, reason, detail_json)
                VALUES (?, ?, ?, ?, ?, ?, ?)
            """, (position_id, datetime.now().isoformat(), 'POSITION_REGISTERED', None, status,
                  'Exit policy sealed when the entry was logged.', json.dumps(redact(policy))))
        conn.commit()
        conn.close()
        return position_id

    def get_managed_positions(self, active_only=False):
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        sql = "SELECT * FROM managed_positions"
        params = ()
        if active_only:
            sql += " WHERE status IN ('PENDING_ENTRY', 'OPEN', 'EXIT_SUBMITTING', 'EXIT_PENDING')"
        sql += " ORDER BY id DESC"
        rows = [dict(row) for row in conn.execute(sql, params).fetchall()]
        conn.close()
        for row in rows:
            row['opening_legs'] = json.loads(row.pop('opening_legs_json'))
        return rows

    def update_managed_position(self, position_id, **changes):
        allowed = {
            'entry_price', 'opened_at', 'status', 'exit_reason', 'exit_order_id',
            'exit_client_order_id',
            'exit_submitted_at', 'closed_at', 'last_mark', 'last_pnl',
            'last_checked_at', 'realized_pnl',
        }
        values = {key: value for key, value in changes.items() if key in allowed}
        if not values:
            return
        conn = sqlite3.connect(self.db_path)
        assignments = ', '.join(f"{key} = ?" for key in values)
        conn.execute(f"UPDATE managed_positions SET {assignments} WHERE id = ?",
                     (*values.values(), position_id))
        conn.commit()
        conn.close()

    def claim_managed_position_exit(self, position_id, reason):
        """Atomically reserve an OPEN row before any broker close call.

        This compare-and-set is the concurrency boundary that prevents two
        scheduled monitors from submitting duplicate exits.
        """
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        cursor.execute("""
            UPDATE managed_positions
            SET status = 'EXIT_SUBMITTING', exit_reason = ?,
                exit_attempts = exit_attempts + 1, last_checked_at = ?
            WHERE id = ? AND status = 'OPEN'
        """, (reason, datetime.now().isoformat(), position_id))
        claimed = cursor.rowcount == 1
        attempt = None
        if claimed:
            attempt = cursor.execute(
                "SELECT exit_attempts FROM managed_positions WHERE id = ?",
                (position_id,),
            ).fetchone()[0]
        conn.commit()
        conn.close()
        return attempt

    def get_position_performance(self):
        """Aggregate realized lifecycle results without projecting returns."""
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        status_rows = conn.execute("""
            SELECT status, COUNT(*) AS count
            FROM managed_positions GROUP BY status
        """).fetchall()
        closed = conn.execute("""
            SELECT realized_pnl, exit_reason
            FROM managed_positions
            WHERE status = 'CLOSED' AND realized_pnl IS NOT NULL
        """).fetchall()
        conn.close()

        pnl = [float(row['realized_pnl']) for row in closed]
        wins = sum(value > 0 for value in pnl)
        losses = sum(value < 0 for value in pnl)
        return {
            'by_status': {row['status']: row['count'] for row in status_rows},
            'closed_positions': len(pnl),
            'wins': wins,
            'losses': losses,
            'win_rate': round(wins / len(pnl), 4) if pnl else None,
            'realized_pnl': round(sum(pnl), 2),
            'average_pnl': round(sum(pnl) / len(pnl), 2) if pnl else None,
            'exit_reasons': {
                reason: sum(1 for row in closed if row['exit_reason'] == reason)
                for reason in sorted({row['exit_reason'] for row in closed if row['exit_reason']})
            },
        }

    def log_position_event(self, position_id, event_type, state_before, state_after,
                           reason='', detail=None):
        conn = sqlite3.connect(self.db_path)
        conn.execute("""
            INSERT INTO position_events
            (position_id, timestamp, event_type, state_before, state_after, reason, detail_json)
            VALUES (?, ?, ?, ?, ?, ?, ?)
        """, (position_id, datetime.now().isoformat(), event_type, state_before,
              state_after, reason, json.dumps(redact(detail or {}))))
        conn.commit()
        conn.close()

    def get_position_events(self, limit=100):
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        rows = [dict(row) for row in conn.execute(
            "SELECT * FROM position_events ORDER BY id DESC LIMIT ?", (limit,)
        ).fetchall()]
        conn.close()
        for row in rows:
            row['detail'] = json.loads(row.pop('detail_json') or '{}')
        return rows

    def get_dashboard_data(self, limit=25):
        """Read-only presentation model used by the browser dashboard."""
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        theses = [dict(row) for row in conn.execute(
            "SELECT * FROM theses ORDER BY id DESC LIMIT ?", (limit,)
        ).fetchall()]
        trades = [dict(row) for row in conn.execute(
            "SELECT * FROM trades ORDER BY id DESC LIMIT ?", (limit,)
        ).fetchall()]
        contracts = [dict(row) for row in conn.execute(
            "SELECT * FROM decision_contracts ORDER BY created_at DESC LIMIT ?", (limit,)
        ).fetchall()]
        positions = [dict(row) for row in conn.execute(
            "SELECT * FROM managed_positions ORDER BY id DESC LIMIT ?", (limit,)
        ).fetchall()]
        position_events = [dict(row) for row in conn.execute(
            "SELECT * FROM position_events ORDER BY id DESC LIMIT ?", (limit * 4,)
        ).fetchall()]
        conn.close()
        for row in theses:
            for key in ('repricing_signals', 'market_state', 'evaluation_detail'):
                if row.get(key):
                    row[key] = json.loads(row[key])
        for row in trades:
            row['portfolio'] = json.loads(row['portfolio'])
        for row in contracts:
            row['contract'] = json.loads(row.pop('contract_json'))
            if row.get('evaluation_json'):
                row['evaluation'] = json.loads(row['evaluation_json'])
        for row in positions:
            row['opening_legs'] = json.loads(row.pop('opening_legs_json'))
        for row in position_events:
            row['detail'] = json.loads(row.pop('detail_json') or '{}')
        return {'theses': theses, 'trades': trades, 'contracts': contracts,
                'positions': positions, 'position_events': position_events,
                'track_record': self.get_track_record(),
                'position_performance': self.get_position_performance()}

    def log_decision_contract(self, contract):
        """Persist a sealed decision before any broker submission."""
        conn = sqlite3.connect(self.db_path)
        conn.execute("""
            INSERT INTO decision_contracts
            (contract_id, decision_hash, created_at, authorization, contract_json)
            VALUES (?, ?, ?, ?, ?)
        """, (contract['contract_id'], contract['decision_hash'], contract['created_at'],
              contract['authorization'], json.dumps(redact(contract))))
        conn.commit()
        conn.close()
        return contract['contract_id']

    def link_contract_execution(self, contract_id, trade_id, status):
        conn = sqlite3.connect(self.db_path)
        conn.execute("""
            UPDATE decision_contracts SET trade_id = ?, execution_status = ?
            WHERE contract_id = ?
        """, (trade_id, status, contract_id))
        conn.commit()
        conn.close()

    def get_pending_contracts(self, min_age_days=5):
        conn = sqlite3.connect(self.db_path)
        cutoff = (datetime.now() - timedelta(days=min_age_days)).isoformat()
        rows = conn.execute("""
            SELECT contract_json FROM decision_contracts
            WHERE evaluated = 0 AND created_at <= ?
        """, (cutoff,)).fetchall()
        conn.close()
        return [json.loads(row[0]) for row in rows]

    def record_contract_evaluation(self, contract_id, evaluation):
        conn = sqlite3.connect(self.db_path)
        conn.execute("""
            UPDATE decision_contracts SET evaluated = 1, evaluation_json = ?
            WHERE contract_id = ?
        """, (json.dumps(evaluation), contract_id))
        conn.commit()
        conn.close()
