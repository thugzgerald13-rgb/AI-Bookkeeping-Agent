import json
import logging
import os
from typing import Optional, Dict, List
import anthropic

logger = logging.getLogger(__name__)

SYSTEM_PROMPT = """You are an expert AI Bookkeeping Assistant for a small business in the Philippines.
Your role is to:
1. Accurately categorize transactions
2. Answer bookkeeping and accounting questions
3. Provide financial insights from transaction data
4. Assist with BIR tax compliance questions
5. Generate financial summaries and recommendations

When categorizing transactions, respond ONLY with valid JSON:
{"category": "Service Revenue|Product Sales|Salaries Expense|Rent Expense|Utilities Expense|Office Supplies|Marketing & Advertising|Professional Fees|Transportation|Meals & Entertainment|Taxes & Licenses|Miscellaneous Expense|Other",
 "confidence": 0.0-1.0,
 "notes": "brief explanation"}

For general Q&A, respond in clear professional English. Be concise and practical.
Always consider Philippine business context (BIR, VAT, withholding tax) where relevant."""


class BookkeepingAgent:
    """AI-powered bookkeeping agent using Anthropic Claude — unified with DB class."""

    def __init__(self, api_key: Optional[str] = None, db=None):
        key = api_key or os.getenv("ANTHROPIC_API_KEY", "")
        self.client = anthropic.Anthropic(api_key=key) if key else None
        self.model = "claude-sonnet-4-20250514"
        self.db = db  # injected from main.py session state
        self.chat_history: List[Dict] = []
        logger.info("BookkeepingAgent initialized.")

    def _ai_available(self) -> bool:
        return self.client is not None

    def categorize_transaction(self, description: str, amount: float, trans_type: str) -> Dict:
        """Use Claude to categorize a transaction. Falls back gracefully if no API key."""
        if not self._ai_available():
            return {"category": "Miscellaneous Expense", "confidence": 0.0,
                    "notes": "AI unavailable — set ANTHROPIC_API_KEY in Streamlit secrets"}

        prompt = f"""Categorize this {trans_type} transaction:
Description: {description}
Amount: ₱{amount:,.2f}
Respond with JSON only."""

        try:
            response = self.client.messages.create(
                model=self.model, max_tokens=200,
                system=SYSTEM_PROMPT,
                messages=[{"role": "user", "content": prompt}]
            )
            text = response.content[0].text.strip()
            if text.startswith("```"):
                text = text.split("```")[1]
                if text.startswith("json"):
                    text = text[4:]
            return json.loads(text.strip())
        except Exception as e:
            logger.error(f"AI categorization failed: {e}")
            return {"category": "Miscellaneous Expense", "confidence": 0.0, "notes": "AI categorization failed"}

    def chat(self, user_message: str) -> str:
        """Conversational assistant with financial context."""
        if not self._ai_available():
            return "⚠️ AI Advisor is unavailable. Please add your `ANTHROPIC_API_KEY` in Streamlit Cloud → Settings → Secrets."

        summary = {"total_income": 0, "total_expense": 0, "net": 0, "count": 0}
        if self.db:
            try:
                summary = self.db.get_summary()
            except Exception:
                pass

        context = f"""Current business snapshot:
- Total Income: ₱{summary['total_income']:,.2f}
- Total Expense: ₱{summary['total_expense']:,.2f}
- Net Balance: ₱{summary['net']:,.2f}
- Transactions: {summary['count']}

User: {user_message}"""

        self.chat_history.append({"role": "user", "content": context})

        try:
            response = self.client.messages.create(
                model=self.model, max_tokens=1000,
                system=SYSTEM_PROMPT,
                messages=self.chat_history[-10:]
            )
            reply = response.content[0].text
            self.chat_history.append({"role": "assistant", "content": reply})
            return reply
        except Exception as e:
            logger.error(f"Chat error: {e}")
            return f"Sorry, I encountered an error: {e}"

    def generate_insights(self) -> str:
        """AI-powered financial insights from current data."""
        if not self._ai_available():
            return "⚠️ AI Advisor is unavailable. Please add your `ANTHROPIC_API_KEY` in Streamlit Cloud → Settings → Secrets."

        summary = {"total_income": 0, "total_expense": 0, "net": 0, "count": 0}
        cats, monthly = [], []
        if self.db:
            try:
                summary = self.db.get_summary()
                cats = self.db.get_by_category()
                monthly = self.db.get_monthly()
            except Exception:
                pass

        cat_text = "\n".join([f"  {r['category']} ({r['type']}): ₱{r['total']:,.2f} ({r['cnt']} txns)"
                               for r in cats[:10]])
        monthly_text = "\n".join([f"  {r['month']} — {r['type']}: ₱{r['total']:,.2f}"
                                   for r in monthly[:6]])

        prompt = f"""Analyze this Philippine business financial data and give 3-5 actionable insights:

Summary: Income ₱{summary['total_income']:,.2f} | Expense ₱{summary['total_expense']:,.2f} | Net ₱{summary['net']:,.2f} | {summary['count']} transactions

Categories:
{cat_text or 'No data yet'}

Monthly:
{monthly_text or 'No data yet'}

Be specific and practical. Include BIR/VAT context where relevant."""

        try:
            response = self.client.messages.create(
                model=self.model, max_tokens=800,
                messages=[{"role": "user", "content": prompt}]
            )
            return response.content[0].text
        except Exception as e:
            return f"Unable to generate insights: {e}"

    def clear_chat(self):
        self.chat_history = []
