import json
import logging
from typing import Optional, Dict, List
import anthropic

from src.bookkeeper import Bookkeeper, TransactionType, ExpenseCategory, Transaction

logger = logging.getLogger(__name__)


SYSTEM_PROMPT = """You are an expert AI Bookkeeping Assistant for a small business in the Philippines.
Your role is to:
1. Help categorize transactions accurately
2. Answer bookkeeping and accounting questions
3. Provide financial insights from transaction data
4. Assist with BIR tax compliance questions
5. Generate financial summaries and recommendations

When categorizing transactions, respond ONLY with valid JSON in this format:
{"category": "Food|Transport|Utilities|Salary|Rent|Supplies|Marketing|Professional Fees|Taxes|Entertainment|Other",
 "confidence": 0.0-1.0,
 "notes": "brief explanation"}

For general Q&A, respond in clear, professional English. Be concise and practical.
Always consider Philippine business context (BIR, VAT, withholding tax) where relevant."""


class BookkeepingAgent:
    """
    AI-powered bookkeeping agent using Anthropic Claude.
    Fixes the original broken langchain-based implementation.
    """

    def __init__(self, api_key: Optional[str] = None):
        self.client = anthropic.Anthropic(api_key=api_key) if api_key else anthropic.Anthropic()
        self.model = "claude-sonnet-4-20250514"
        self.bookkeeper = Bookkeeper()
        self.chat_history: List[Dict] = []
        logger.info("BookkeepingAgent initialized with Claude.")

    def categorize_transaction(self, description: str, amount: float, trans_type: str) -> Dict:
        """Use Claude to intelligently categorize a transaction."""
        prompt = f"""Categorize this {trans_type} transaction:
Description: {description}
Amount: ₱{amount:,.2f}

Respond with JSON only."""

        try:
            response = self.client.messages.create(
                model=self.model,
                max_tokens=200,
                system=SYSTEM_PROMPT,
                messages=[{"role": "user", "content": prompt}]
            )
            text = response.content[0].text.strip()
            # Strip markdown code fences if present
            if text.startswith("```"):
                text = text.split("```")[1]
                if text.startswith("json"):
                    text = text[4:]
            return json.loads(text)
        except Exception as e:
            logger.error(f"AI categorization failed: {e}")
            return {"category": "Other", "confidence": 0.0, "notes": "Manual review needed"}

    def process_transaction(
        self,
        trans_type: TransactionType,
        amount: float,
        description: str,
        date: Optional[str] = None,
        reference: str = '',
        use_ai_categorization: bool = True,
    ) -> Optional[Transaction]:
        """Process a transaction with optional AI categorization."""
        category = None
        ai_notes = ''

        if use_ai_categorization and description:
            result = self.categorize_transaction(description, amount, trans_type.value)
            cat_name = result.get("category", "Other")
            ai_notes = result.get("notes", "")
            # Map string to enum
            category_map = {e.value: e for e in ExpenseCategory}
            category = category_map.get(cat_name, ExpenseCategory.OTHER)
        else:
            category = self.bookkeeper.categorize_expense(description)

        return self.bookkeeper.process_transaction(
            trans_type=trans_type,
            amount=amount,
            category=category,
            description=description,
            date=date,
            reference=reference,
            ai_notes=ai_notes,
        )

    def chat(self, user_message: str) -> str:
        """
        Conversational bookkeeping assistant.
        Maintains chat history and has access to financial summary context.
        """
        summary = self.bookkeeper.get_summary()
        context = f"""Current business financial summary:
- Total Income: ₱{summary['total_income']:,.2f}
- Total Expense: ₱{summary['total_expense']:,.2f}
- Net Balance: ₱{summary['net']:,.2f}
- Total Transactions: {summary['transaction_count']}

User question: {user_message}"""

        self.chat_history.append({"role": "user", "content": context})

        try:
            response = self.client.messages.create(
                model=self.model,
                max_tokens=1000,
                system=SYSTEM_PROMPT,
                messages=self.chat_history[-10:]  # Keep last 10 turns
            )
            reply = response.content[0].text
            self.chat_history.append({"role": "assistant", "content": reply})
            return reply
        except Exception as e:
            logger.error(f"Chat error: {e}")
            return f"Sorry, I encountered an error: {e}"

    def generate_insights(self) -> str:
        """Generate AI-powered financial insights from current data."""
        summary = self.bookkeeper.get_summary()
        categories = self.bookkeeper.get_category_breakdown()
        monthly = self.bookkeeper.get_monthly_trend()

        cat_text = "\n".join([f"  {r[0]} ({r[1]}): ₱{r[2]:,.2f} ({r[3]} txns)" for r in categories[:10]])
        monthly_text = "\n".join([f"  {r[0]} — {r[1]}: ₱{r[2]:,.2f}" for r in monthly[:6]])

        prompt = f"""Analyze this business financial data and provide 3-5 actionable insights:

Summary:
- Income: ₱{summary['total_income']:,.2f}
- Expense: ₱{summary['total_expense']:,.2f}  
- Net: ₱{summary['net']:,.2f}
- Transactions: {summary['transaction_count']}

Category Breakdown:
{cat_text or 'No data yet'}

Monthly Trend (recent):
{monthly_text or 'No data yet'}

Provide practical insights for a Philippine small business owner. Be specific and actionable."""

        try:
            response = self.client.messages.create(
                model=self.model,
                max_tokens=800,
                messages=[{"role": "user", "content": prompt}]
            )
            return response.content[0].text
        except Exception as e:
            return f"Unable to generate insights: {e}"

    def clear_chat(self):
        self.chat_history = []
