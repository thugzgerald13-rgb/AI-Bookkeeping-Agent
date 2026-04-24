import sqlite3
import logging
import csv
import datetime
from enum import Enum
from typing import List, Optional, Dict, Tuple
from dataclasses import dataclass, field

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')


class TransactionType(Enum):
    INCOME = 'income'
    EXPENSE = 'expense'
    TRANSFER = 'transfer'
    ADJUSTMENT = 'adjustment'


class ExpenseCategory(Enum):
    FOOD = 'Food'
    TRANSPORT = 'Transport'
    UTILITIES = 'Utilities'
    ENTERTAINMENT = 'Entertainment'
    SALARY = 'Salary'
    RENT = 'Rent'
    SUPPLIES = 'Supplies'
    MARKETING = 'Marketing'
    PROFESSIONAL_FEES = 'Professional Fees'
    TAXES = 'Taxes'
    OTHER = 'Other'


@dataclass
class Transaction:
    trans_type: TransactionType
    amount: float
    category: Optional[ExpenseCategory] = None
    description: str = ''
    date: str = field(default_factory=lambda: datetime.datetime.now().strftime('%Y-%m-%d'))
    id: Optional[int] = None
    reference: str = ''
    ai_notes: str = ''

    def to_dict(self) -> Dict:
        return {
            'id': self.id,
            'date': self.date,
            'type': self.trans_type.value,
            'amount': self.amount,
            'category': self.category.value if self.category else 'Uncategorized',
            'description': self.description,
            'reference': self.reference,
            'ai_notes': self.ai_notes,
        }


class Database:
    def __init__(self, db_path: str = "data/bookkeeping.db"):
        import os
        os.makedirs(os.path.dirname(db_path), exist_ok=True)
        self.db_path = db_path
        self._init_db()

    def _init_db(self):
        with sqlite3.connect(self.db_path) as conn:
            conn.execute("""
                CREATE TABLE IF NOT EXISTS transactions (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    date TEXT NOT NULL,
                    type TEXT NOT NULL,
                    amount REAL NOT NULL,
                    category TEXT,
                    description TEXT,
                    reference TEXT,
                    ai_notes TEXT,
                    created_at TEXT DEFAULT (datetime('now'))
                )
            """)
            conn.commit()

    def insert(self, t: Transaction) -> int:
        with sqlite3.connect(self.db_path) as conn:
            cur = conn.execute(
                "INSERT INTO transactions (date, type, amount, category, description, reference, ai_notes) VALUES (?,?,?,?,?,?,?)",
                (t.date, t.trans_type.value, t.amount,
                 t.category.value if t.category else None,
                 t.description, t.reference, t.ai_notes)
            )
            conn.commit()
            return cur.lastrowid

    def fetch_all(self, limit: int = 500) -> List[Dict]:
        with sqlite3.connect(self.db_path) as conn:
            conn.row_factory = sqlite3.Row
            rows = conn.execute(
                "SELECT * FROM transactions ORDER BY date DESC, id DESC LIMIT ?", (limit,)
            ).fetchall()
            return [dict(r) for r in rows]

    def fetch_summary(self) -> Dict:
        with sqlite3.connect(self.db_path) as conn:
            income = conn.execute(
                "SELECT COALESCE(SUM(amount),0) FROM transactions WHERE type='income'"
            ).fetchone()[0]
            expense = conn.execute(
                "SELECT COALESCE(SUM(amount),0) FROM transactions WHERE type='expense'"
            ).fetchone()[0]
            count = conn.execute("SELECT COUNT(*) FROM transactions").fetchone()[0]
        return {
            'total_income': income,
            'total_expense': expense,
            'net': income - expense,
            'transaction_count': count,
        }

    def fetch_by_category(self) -> List[Tuple]:
        with sqlite3.connect(self.db_path) as conn:
            rows = conn.execute(
                """SELECT category, type, SUM(amount) as total, COUNT(*) as count
                   FROM transactions
                   GROUP BY category, type
                   ORDER BY total DESC"""
            ).fetchall()
            return rows

    def fetch_monthly(self) -> List[Tuple]:
        with sqlite3.connect(self.db_path) as conn:
            rows = conn.execute(
                """SELECT strftime('%Y-%m', date) as month, type, SUM(amount) as total
                   FROM transactions
                   GROUP BY month, type
                   ORDER BY month DESC
                   LIMIT 24"""
            ).fetchall()
            return rows

    def delete(self, transaction_id: int) -> bool:
        with sqlite3.connect(self.db_path) as conn:
            conn.execute("DELETE FROM transactions WHERE id=?", (transaction_id,))
            conn.commit()
        return True


class Bookkeeper:
    def __init__(self, db_path: str = "data/bookkeeping.db"):
        self.db = Database(db_path)
        logging.info("Bookkeeper initialized with SQLite persistence.")

    def process_transaction(
        self,
        trans_type: TransactionType,
        amount: float,
        category: Optional[ExpenseCategory] = None,
        description: str = '',
        date: Optional[str] = None,
        reference: str = '',
        ai_notes: str = '',
    ) -> Optional[Transaction]:
        if amount <= 0:
            logging.error("Transaction amount must be positive.")
            return None

        transaction = Transaction(
            trans_type=trans_type,
            amount=amount,
            category=category,
            description=description,
            date=date or datetime.datetime.now().strftime('%Y-%m-%d'),
            reference=reference,
            ai_notes=ai_notes,
        )
        transaction.id = self.db.insert(transaction)
        logging.info(f"Transaction #{transaction.id} saved: {trans_type.value} {amount}")
        return transaction

    def categorize_expense(self, description: str) -> ExpenseCategory:
        """Rule-based categorization (AI categorization done in agent.py)."""
        desc = description.lower()
        if any(w in desc for w in ['food', 'meal', 'lunch', 'dinner', 'grocery', 'restaurant']):
            return ExpenseCategory.FOOD
        elif any(w in desc for w in ['transport', 'taxi', 'uber', 'grab', 'fuel', 'gas', 'parking']):
            return ExpenseCategory.TRANSPORT
        elif any(w in desc for w in ['electric', 'water', 'internet', 'phone', 'utilities']):
            return ExpenseCategory.UTILITIES
        elif any(w in desc for w in ['salary', 'payroll', 'wage']):
            return ExpenseCategory.SALARY
        elif any(w in desc for w in ['rent', 'lease']):
            return ExpenseCategory.RENT
        elif any(w in desc for w in ['office', 'supplies', 'stationery']):
            return ExpenseCategory.SUPPLIES
        elif any(w in desc for w in ['ads', 'marketing', 'promo', 'advertising']):
            return ExpenseCategory.MARKETING
        elif any(w in desc for w in ['consultant', 'lawyer', 'accountant', 'professional']):
            return ExpenseCategory.PROFESSIONAL_FEES
        elif any(w in desc for w in ['tax', 'bir', 'vat', 'withholding']):
            return ExpenseCategory.TAXES
        elif any(w in desc for w in ['entertainment', 'event', 'party']):
            return ExpenseCategory.ENTERTAINMENT
        return ExpenseCategory.OTHER

    def get_summary(self) -> Dict:
        return self.db.fetch_summary()

    def get_transactions(self, limit: int = 200) -> List[Dict]:
        return self.db.fetch_all(limit)

    def get_category_breakdown(self) -> List[Tuple]:
        return self.db.fetch_by_category()

    def get_monthly_trend(self) -> List[Tuple]:
        return self.db.fetch_monthly()

    def generate_report(self) -> str:
        summary = self.get_summary()
        lines = [
            "=" * 50,
            "       AI BOOKKEEPING AGENT — REPORT",
            "=" * 50,
            f"Total Income:  ₱{summary['total_income']:>12,.2f}",
            f"Total Expense: ₱{summary['total_expense']:>12,.2f}",
            f"Net Balance:   ₱{summary['net']:>12,.2f}",
            f"Transactions:  {summary['transaction_count']:>12}",
            "=" * 50,
        ]
        return "\n".join(lines)

    def export_csv(self, file_path: str = "data/export.csv") -> str:
        transactions = self.get_transactions(limit=10000)
        if not transactions:
            return ""
        with open(file_path, 'w', newline='') as f:
            writer = csv.DictWriter(f, fieldnames=transactions[0].keys())
            writer.writeheader()
            writer.writerows(transactions)
        logging.info(f"Exported {len(transactions)} transactions to {file_path}")
        return file_path

    def delete_transaction(self, transaction_id: int) -> bool:
        return self.db.delete(transaction_id)
