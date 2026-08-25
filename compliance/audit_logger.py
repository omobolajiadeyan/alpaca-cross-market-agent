"""
Audit trail logging
Every decision is logged with full transparency
"""

import sqlite3
import json
from datetime import datetime, timedelta
import os


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
            json.dumps(market_state) if market_state is not None else None,
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
            json.dumps(portfolio),
            status
        ))

        conn.commit()
        conn.close()

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
        conn.close()
        for row in theses:
            for key in ('repricing_signals', 'market_state', 'evaluation_detail'):
                if row.get(key):
                    row[key] = json.loads(row[key])
        for row in trades:
            row['portfolio'] = json.loads(row['portfolio'])
        return {'theses': theses, 'trades': trades, 'track_record': self.get_track_record()}
