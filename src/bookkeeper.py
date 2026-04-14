from enum import Enum
import logging
from typing import List, Union

# Configure logging
logging.basicConfig(level=logging.DEBUG, format='%(asctime)s - %(levelname)s - %(message)s')


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
    OTHER = 'Other'


class Transaction:
    def __init__(self, trans_type: TransactionType, amount: float, category: Union[ExpenseCategory, None] = None, description: str = ''):
        self.trans_type = trans_type
        self.amount = amount
        self.category = category
        self.description = description
        self.timestamp = logging.Formatter().formatTime(logging.LogRecord('', 0, '', 0, '', '', [], None))


class Ledger:
    def __init__(self):
        self.transactions = []
        self.accounts = {'main': 0.0}

    def add_transaction(self, transaction: Transaction):
        self.transactions.append(transaction)
        logging.info(f'Transaction added: {transaction.__dict__}')

    def get_account_balance(self, account_name: str = 'main') -> float:
        balance = self.accounts.get(account_name, 0.0)
        logging.debug(f'Balance for account {account_name}: {balance}')
        return balance

    def get_ledger_summary(self) -> str:
        summary = f'Transaction Summary:\n'
        for t in self.transactions:
            summary += f'- {t.trans_type.value}: {t.amount} {t.category.name if t.category else ''} - {t.description}\n'
        logging.debug(summary)
        return summary


class Bookkeeper:
    def __init__(self):
        self.ledger = Ledger()

    def process_transaction(self, trans_type: TransactionType, amount: float, category: Union[ExpenseCategory, None] = None, description: str = ''):
        if amount <= 0:
            logging.error('Transaction amount must be positive. Transaction not processed.')
            return
        transaction = Transaction(trans_type, amount, category, description)
        self.ledger.add_transaction(transaction)
        self.update_account_balance(trans_type, amount)

    def update_account_balance(self, trans_type: TransactionType, amount: float):
        if trans_type == TransactionType.INCOME:
            self.ledger.accounts['main'] += amount
            logging.info('Income processed.')
        elif trans_type == TransactionType.EXPENSE:
            self.ledger.accounts['main'] -= amount
            logging.info('Expense processed.')
        elif trans_type == TransactionType.TRANSFER:
            # Implement transfer logic if needed
            logging.info('Transfer processed (not implemented).')
        elif trans_type == TransactionType.ADJUSTMENT:
            # Implement adjustment logic if needed
            logging.info('Adjustment processed (not implemented).')

    def categorize_expense(self, amount: float, description: str) -> ExpenseCategory:
        category = ExpenseCategory.OTHER  # Default category
        if 'food' in description.lower():
            category = ExpenseCategory.FOOD
        elif 'transport' in description.lower():
            category = ExpenseCategory.TRANSPORT
        elif 'utilities' in description.lower():
            category = ExpenseCategory.UTILITIES
        elif 'entertainment' in description.lower():
            category = ExpenseCategory.ENTERTAINMENT
        logging.info(f'Expense categorized: {category}')
        return category

    def generate_report(self):
        report = self.ledger.get_ledger_summary()
        logging.info('Report generated.')
        return report

    def export_transactions(self, file_name: str):
        with open(file_name, 'w') as file:
            for transaction in self.ledger.transactions:
                file.write(f'{transaction.__dict__}\n')
        logging.info(f'Transactions exported to {file_name}')


# Example usage:
# bookkeeper = Bookkeeper()
# bookkeeper.process_transaction(TransactionType.INCOME, 100, description='Salary')
# bookkeeper.process_transaction(TransactionType.EXPENSE, 20, category=ExpenseCategory.FOOD, description='Groceries')
# report = bookkeeper.generate_report()  
# print(report)