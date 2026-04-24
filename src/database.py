import os
import sqlite3
from datetime import date
from typing import Any, Dict, List, Optional, Sequence


class DB:
    """SQLite database layer used by the Streamlit app.

    This file restores the missing src.database module expected by src/main.py.
    It creates all tables needed by the Dashboard, Invoices, Banking,
    Customers, Vendors, Reports, and Chart of Accounts pages.
    """

    def __init__(self, db_path: str = "data/bookkeeping.db"):
        directory = os.path.dirname(db_path)
        if directory:
            os.makedirs(directory, exist_ok=True)
        self.db_path = db_path
        self._init_db()
        self._seed_defaults()

    def _connect(self) -> sqlite3.Connection:
        conn = sqlite3.connect(self.db_path, check_same_thread=False)
        conn.row_factory = sqlite3.Row
        return conn

    def execute(self, sql: str, params: Sequence[Any] = ()) -> int:
        with self._connect() as conn:
            cur = conn.execute(sql, tuple(params))
            conn.commit()
            return cur.lastrowid

    def fetch(self, sql: str, params: Sequence[Any] = ()) -> List[Dict[str, Any]]:
        with self._connect() as conn:
            rows = conn.execute(sql, tuple(params)).fetchall()
            return [dict(r) for r in rows]

    def scalar(self, sql: str, params: Sequence[Any] = ()) -> Any:
        with self._connect() as conn:
            row = conn.execute(sql, tuple(params)).fetchone()
            return row[0] if row else None

    def _init_db(self) -> None:
        with self._connect() as conn:
            conn.executescript(
                """
                CREATE TABLE IF NOT EXISTS transactions (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    date TEXT NOT NULL,
                    type TEXT NOT NULL,
                    amount REAL NOT NULL DEFAULT 0,
                    category TEXT,
                    description TEXT,
                    reference TEXT,
                    payee TEXT,
                    ai_notes TEXT,
                    created_at TEXT DEFAULT (datetime('now'))
                );

                CREATE TABLE IF NOT EXISTS customers (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    name TEXT NOT NULL,
                    email TEXT,
                    phone TEXT,
                    address TEXT,
                    company TEXT,
                    balance REAL NOT NULL DEFAULT 0,
                    created_at TEXT DEFAULT (datetime('now'))
                );

                CREATE TABLE IF NOT EXISTS vendors (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    name TEXT NOT NULL,
                    email TEXT,
                    phone TEXT,
                    address TEXT,
                    company TEXT,
                    balance REAL NOT NULL DEFAULT 0,
                    created_at TEXT DEFAULT (datetime('now'))
                );

                CREATE TABLE IF NOT EXISTS invoices (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    invoice_number TEXT UNIQUE,
                    customer_id INTEGER NOT NULL,
                    issue_date TEXT NOT NULL,
                    due_date TEXT NOT NULL,
                    subtotal REAL NOT NULL DEFAULT 0,
                    tax_rate REAL NOT NULL DEFAULT 0,
                    tax_amount REAL NOT NULL DEFAULT 0,
                    total REAL NOT NULL DEFAULT 0,
                    amount_paid REAL NOT NULL DEFAULT 0,
                    balance_due REAL NOT NULL DEFAULT 0,
                    status TEXT NOT NULL DEFAULT 'open',
                    notes TEXT,
                    created_at TEXT DEFAULT (datetime('now')),
                    FOREIGN KEY(customer_id) REFERENCES customers(id)
                );

                CREATE TABLE IF NOT EXISTS invoice_items (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    invoice_id INTEGER NOT NULL,
                    description TEXT NOT NULL,
                    quantity REAL NOT NULL DEFAULT 1,
                    unit_price REAL NOT NULL DEFAULT 0,
                    amount REAL NOT NULL DEFAULT 0,
                    FOREIGN KEY(invoice_id) REFERENCES invoices(id)
                );

                CREATE TABLE IF NOT EXISTS bank_accounts (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    name TEXT NOT NULL,
                    type TEXT NOT NULL DEFAULT 'checking',
                    bank_name TEXT,
                    account_number TEXT,
                    balance REAL NOT NULL DEFAULT 0,
                    currency TEXT NOT NULL DEFAULT 'PHP',
                    created_at TEXT DEFAULT (datetime('now'))
                );

                CREATE TABLE IF NOT EXISTS accounts (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    code TEXT,
                    name TEXT NOT NULL,
                    type TEXT NOT NULL,
                    subtype TEXT,
                    balance REAL NOT NULL DEFAULT 0,
                    created_at TEXT DEFAULT (datetime('now'))
                );
                """
            )
            conn.commit()

    def _seed_defaults(self) -> None:
        if (self.scalar("SELECT COUNT(*) FROM accounts") or 0) == 0:
            defaults = [
                ("1000", "Cash on Hand", "Asset", "Cash"),
                ("1010", "Bank Account", "Asset", "Bank"),
                ("1100", "Accounts Receivable", "Asset", "Receivable"),
                ("2000", "Accounts Payable", "Liability", "Payable"),
                ("3000", "Owner's Equity", "Equity", "Capital"),
                ("4000", "Service Revenue", "Income", "Operating Income"),
                ("5000", "Cost of Services", "Expense", "Direct Cost"),
                ("6000", "Salaries Expense", "Expense", "Operating Expense"),
                ("6100", "Rent Expense", "Expense", "Operating Expense"),
                ("6200", "Utilities Expense", "Expense", "Operating Expense"),
                ("6300", "Office Supplies", "Expense", "Operating Expense"),
                ("6400", "Professional Fees", "Expense", "Operating Expense"),
                ("6500", "Transportation", "Expense", "Operating Expense"),
                ("6600", "Taxes & Licenses", "Expense", "Operating Expense"),
                ("6999", "Miscellaneous Expense", "Expense", "Operating Expense"),
            ]
            with self._connect() as conn:
                conn.executemany(
                    "INSERT INTO accounts (code, name, type, subtype) VALUES (?,?,?,?)",
                    defaults,
                )
                conn.commit()

        if (self.scalar("SELECT COUNT(*) FROM bank_accounts") or 0) == 0:
            self.execute(
                "INSERT INTO bank_accounts (name, type, bank_name, balance, currency) VALUES (?,?,?,?,?)",
                ("Main Cash / Bank", "checking", "Default", 0, "PHP"),
            )

    # Dashboard and reports
    def get_summary(self) -> Dict[str, Any]:
        income = float(self.scalar("SELECT COALESCE(SUM(amount),0) FROM transactions WHERE type='income'") or 0)
        expense = float(self.scalar("SELECT COALESCE(SUM(amount),0) FROM transactions WHERE type='expense'") or 0)
        count = int(self.scalar("SELECT COUNT(*) FROM transactions") or 0)
        return {
            "total_income": income,
            "total_expense": expense,
            "net": income - expense,
            "count": count,
            "transaction_count": count,
        }

    def get_transactions(self, limit: int = 200) -> List[Dict[str, Any]]:
        return self.fetch("SELECT * FROM transactions ORDER BY date DESC, id DESC LIMIT ?", (limit,))

    def get_monthly(self) -> List[Dict[str, Any]]:
        return self.fetch(
            """
            SELECT strftime('%Y-%m', date) AS month, type, SUM(amount) AS total
            FROM transactions
            GROUP BY month, type
            ORDER BY month DESC
            LIMIT 24
            """
        )

    def get_by_category(self) -> List[Dict[str, Any]]:
        return self.fetch(
            """
            SELECT COALESCE(category, 'Uncategorized') AS category,
                   type,
                   SUM(amount) AS total,
                   COUNT(*) AS cnt
            FROM transactions
            GROUP BY category, type
            ORDER BY total DESC
            """
        )

    # Transactions
    def insert_transaction(
        self,
        date: str,
        type_: str,
        amount: float,
        category: str = "",
        description: str = "",
        reference: str = "",
        payee: str = "",
        ai_notes: str = "",
    ) -> int:
        return self.execute(
            """
            INSERT INTO transactions (date, type, amount, category, description, reference, payee, ai_notes)
            VALUES (?,?,?,?,?,?,?,?)
            """,
            (date, type_, float(amount), category, description, reference, payee, ai_notes),
        )

    # Customers and vendors
    def create_customer(self, name: str, email: str = "", phone: str = "", address: str = "", company: str = "") -> int:
        return self.execute(
            "INSERT INTO customers (name, email, phone, address, company) VALUES (?,?,?,?,?)",
            (name, email, phone, address, company),
        )

    def get_customers(self) -> List[Dict[str, Any]]:
        return self.fetch("SELECT * FROM customers ORDER BY name")

    def create_vendor(self, name: str, email: str = "", phone: str = "", address: str = "", company: str = "") -> int:
        return self.execute(
            "INSERT INTO vendors (name, email, phone, address, company) VALUES (?,?,?,?,?)",
            (name, email, phone, address, company),
        )

    def get_vendors(self) -> List[Dict[str, Any]]:
        return self.fetch("SELECT * FROM vendors ORDER BY name")

    # Invoices
    def _next_invoice_number(self) -> str:
        next_id = int(self.scalar("SELECT COALESCE(MAX(id),0)+1 FROM invoices") or 1)
        return f"INV-{date.today().year}-{next_id:04d}"

    def create_invoice(
        self,
        customer_id: int,
        issue_date: str,
        due_date: str,
        items: List[Dict[str, Any]],
        tax_rate: float = 0,
        notes: str = "",
    ) -> int:
        subtotal = sum(float(i.get("quantity", 1)) * float(i.get("unit_price", 0)) for i in items)
        tax_amount = subtotal * (float(tax_rate or 0) / 100)
        total = subtotal + tax_amount
        invoice_number = self._next_invoice_number()
        invoice_id = self.execute(
            """
            INSERT INTO invoices
            (invoice_number, customer_id, issue_date, due_date, subtotal, tax_rate, tax_amount, total, balance_due, status, notes)
            VALUES (?,?,?,?,?,?,?,?,?,?,?)
            """,
            (invoice_number, customer_id, issue_date, due_date, subtotal, tax_rate, tax_amount, total, total, "open", notes),
        )
        for item in items:
            qty = float(item.get("quantity", 1))
            price = float(item.get("unit_price", 0))
            amount = qty * price
            self.execute(
                "INSERT INTO invoice_items (invoice_id, description, quantity, unit_price, amount) VALUES (?,?,?,?,?)",
                (invoice_id, item.get("description", ""), qty, price, amount),
            )
        self.execute("UPDATE customers SET balance = balance + ? WHERE id=?", (total, customer_id))
        return invoice_id

    def get_invoices(self) -> List[Dict[str, Any]]:
        return self.fetch(
            """
            SELECT i.*, c.name AS customer_name, c.company AS customer_company
            FROM invoices i
            LEFT JOIN customers c ON c.id = i.customer_id
            ORDER BY i.issue_date DESC, i.id DESC
            """
        )

    def get_invoice_summary(self) -> Dict[str, Any]:
        open_amount = float(self.scalar("SELECT COALESCE(SUM(balance_due),0) FROM invoices WHERE status IN ('open','partial')") or 0)
        overdue_amount = float(self.scalar("SELECT COALESCE(SUM(balance_due),0) FROM invoices WHERE status='overdue'") or 0)
        paid_amount = float(self.scalar("SELECT COALESCE(SUM(amount_paid),0) FROM invoices") or 0)
        count_open = int(self.scalar("SELECT COUNT(*) FROM invoices WHERE status IN ('open','partial','overdue')") or 0)
        return {"open": open_amount, "overdue": overdue_amount, "paid": paid_amount, "count_open": count_open}

    def mark_invoice_paid(self, invoice_id: int, amount: float) -> None:
        invoice = self.fetch("SELECT * FROM invoices WHERE id=?", (invoice_id,))
        if not invoice:
            return
        inv = invoice[0]
        amount = float(amount or 0)
        new_paid = float(inv["amount_paid"] or 0) + amount
        balance = max(float(inv["total"] or 0) - new_paid, 0)
        status = "paid" if balance <= 0 else "partial"
        self.execute(
            "UPDATE invoices SET amount_paid=?, balance_due=?, status=? WHERE id=?",
            (new_paid, balance, status, invoice_id),
        )
        self.execute("UPDATE customers SET balance = MAX(balance - ?, 0) WHERE id=?", (amount, inv["customer_id"]))

    # Banking and chart of accounts
    def get_bank_accounts(self) -> List[Dict[str, Any]]:
        return self.fetch("SELECT * FROM bank_accounts ORDER BY id")

    def update_bank_balance(self, bank_id: int, delta: float) -> None:
        self.execute("UPDATE bank_accounts SET balance = balance + ? WHERE id=?", (float(delta or 0), bank_id))

    def get_accounts(self) -> List[Dict[str, Any]]:
        return self.fetch("SELECT * FROM accounts ORDER BY code, name")
