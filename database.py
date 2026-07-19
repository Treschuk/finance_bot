import sqlite3
from datetime import datetime, timedelta


class Database:
    def __init__(self, db_path: str):
        self.db_path = db_path
        self._init_db()

    def _get_conn(self):
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        return conn

    def _init_db(self):
        with self._get_conn() as conn:
            conn.executescript("""
                CREATE TABLE IF NOT EXISTS users (
                    user_id INTEGER PRIMARY KEY,
                    name TEXT,
                    currency TEXT DEFAULT NULL,
                    lang TEXT DEFAULT NULL,
                    created_at TEXT DEFAULT (datetime('now'))
                );
                CREATE TABLE IF NOT EXISTS transactions (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    user_id INTEGER NOT NULL,
                    type TEXT NOT NULL CHECK(type IN ('income', 'expense')),
                    amount REAL NOT NULL,
                    category TEXT NOT NULL,
                    description TEXT DEFAULT '',
                    destination TEXT DEFAULT 'wallet',
                    date TEXT DEFAULT (datetime('now', 'localtime')),
                    FOREIGN KEY (user_id) REFERENCES users(user_id)
                );
                CREATE TABLE IF NOT EXISTS piggy_goals (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    user_id INTEGER NOT NULL,
                    name TEXT NOT NULL,
                    target REAL NOT NULL,
                    created_at TEXT DEFAULT (datetime('now', 'localtime')),
                    FOREIGN KEY (user_id) REFERENCES users(user_id)
                );
            """)
            for col, default in [("currency", "NULL"), ("lang", "NULL"), ("destination", "'wallet'")]:
                try:
                    if col == "destination":
                        conn.execute(f"ALTER TABLE transactions ADD COLUMN {col} TEXT DEFAULT {default}")
                    else:
                        conn.execute(f"ALTER TABLE users ADD COLUMN {col} TEXT DEFAULT {default}")
                except Exception:
                    pass

    def add_user(self, user_id: int, name: str):
        with self._get_conn() as conn:
            conn.execute("INSERT OR IGNORE INTO users (user_id, name) VALUES (?, ?)", (user_id, name))

    def get_user_lang(self, user_id: int):
        with self._get_conn() as conn:
            row = conn.execute("SELECT lang FROM users WHERE user_id = ?", (user_id,)).fetchone()
        return row['lang'] if row else None

    def set_user_lang(self, user_id: int, lang: str):
        with self._get_conn() as conn:
            conn.execute("UPDATE users SET lang = ? WHERE user_id = ?", (lang, user_id))

    def get_user_currency(self, user_id: int):
        with self._get_conn() as conn:
            row = conn.execute("SELECT currency FROM users WHERE user_id = ?", (user_id,)).fetchone()
        return row['currency'] if row else None

    def set_user_currency(self, user_id: int, code: str):
        with self._get_conn() as conn:
            conn.execute("UPDATE users SET currency = ? WHERE user_id = ?", (code, user_id))

    def reset_user(self, user_id: int):
        with self._get_conn() as conn:
            conn.execute("UPDATE users SET lang = NULL, currency = NULL WHERE user_id = ?", (user_id,))

    def get_wallet_balance(self, user_id: int) -> float:
        """Кошелёк = доходы в wallet - все расходы"""
        with self._get_conn() as conn:
            income = conn.execute(
                "SELECT COALESCE(SUM(amount), 0) as total FROM transactions WHERE user_id = ? AND type = 'income' AND destination = 'wallet'",
                (user_id,)
            ).fetchone()['total']
            expense = conn.execute(
                "SELECT COALESCE(SUM(amount), 0) as total FROM transactions WHERE user_id = ? AND type = 'expense'",
                (user_id,)
            ).fetchone()['total']
        return income - expense

    def add_transaction(self, user_id: int, t_type: str, amount: float, category: str, description: str = "", destination: str = "wallet"):
        with self._get_conn() as conn:
            conn.execute(
                "INSERT INTO transactions (user_id, type, amount, category, description, destination) VALUES (?, ?, ?, ?, ?, ?)",
                (user_id, t_type, amount, category, description, destination)
            )

    def get_history(self, user_id: int, limit: int = 10) -> list:
        with self._get_conn() as conn:
            rows = conn.execute(
                "SELECT * FROM transactions WHERE user_id = ? ORDER BY date DESC LIMIT ?",
                (user_id, limit)
            ).fetchall()
        return [dict(row) for row in rows]

    def get_stats(self, user_id: int, period: str) -> dict:
        now = datetime.now()
        if period == 'today':
            date_from = now.strftime('%Y-%m-%d 00:00:00')
        elif period == 'week':
            date_from = (now - timedelta(days=7)).strftime('%Y-%m-%d %H:%M:%S')
        elif period == 'month':
            date_from = (now - timedelta(days=30)).strftime('%Y-%m-%d %H:%M:%S')
        else:
            date_from = '2000-01-01 00:00:00'

        with self._get_conn() as conn:
            rows = conn.execute(
                "SELECT type, amount, category, destination FROM transactions WHERE user_id = ? AND date >= ?",
                (user_id, date_from)
            ).fetchall()

        total_income, total_expense, expense_by_cat = 0.0, 0.0, {}
        for row in rows:
            if row['type'] == 'income':
                total_income += row['amount']
            else:
                total_expense += row['amount']
                expense_by_cat[row['category']] = expense_by_cat.get(row['category'], 0) + row['amount']

        return {'total_income': total_income, 'total_expense': total_expense, 'expense_by_category': expense_by_cat}

    def get_piggy_total(self, user_id: int) -> float:
        with self._get_conn() as conn:
            row = conn.execute(
                "SELECT COALESCE(SUM(amount), 0) as total FROM transactions WHERE user_id = ? AND destination = 'piggy'",
                (user_id,)
            ).fetchone()
        return row['total'] if row else 0.0

    def add_piggy_goal(self, user_id: int, name: str, target: float):
        with self._get_conn() as conn:
            conn.execute(
                "INSERT INTO piggy_goals (user_id, name, target) VALUES (?, ?, ?)",
                (user_id, name, target)
            )

    def get_piggy_goals(self, user_id: int) -> list:
        with self._get_conn() as conn:
            rows = conn.execute(
                "SELECT * FROM piggy_goals WHERE user_id = ? ORDER BY created_at DESC",
                (user_id,)
            ).fetchall()
        return [dict(row) for row in rows]

    def delete_piggy_goal(self, goal_id: int):
        with self._get_conn() as conn:
            conn.execute("DELETE FROM piggy_goals WHERE id = ?", (goal_id,))
