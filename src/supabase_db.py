"""
Supabase database layer — replaces SQLite for multi-user SaaS.
All queries are scoped to auth.uid() via Row Level Security.
"""
import os
from typing import Any, Dict, List, Optional
from supabase import create_client, Client
from datetime import date


def get_client() -> Client:
    url = os.environ["SUPABASE_URL"]
    key = os.environ["SUPABASE_ANON_KEY"]
    return create_client(url, key)


class SupabaseDB:
    """Drop-in replacement for SQLite DB class — same public API."""

    def __init__(self, access_token: str):
        self._client = get_client()
        # Set user JWT so RLS applies correctly
        self._client.postgrest.auth(access_token)
        self._client.auth.set_session(access_token, "")

    def _q(self, table: str):
        return self._client.table(table)

    # ── Summary ──────────────────────────────────────────────────────────────
    def get_summary(self) -> Dict:
        rows = self._q("transactions").select("type, amount").execute().data
        income  = sum(r["amount"] for r in rows if r["type"] == "income")
        expense = sum(r["amount"] for r in rows if r["type"] == "expense")
        return {
            "total_income": income,
            "total_expense": expense,
            "net": income - expense,
            "count": len(rows),
            "transaction_count": len(rows),
        }

    # ── Transactions ─────────────────────────────────────────────────────────
    def get_transactions(self, limit: int = 200) -> List[Dict]:
        return (self._q("transactions")
                .select("*")
                .order("date", desc=True)
                .order("id", desc=True)
                .limit(limit)
                .execute().data)

    def insert_transaction(self, date, type_, amount, category="",
                           description="", reference="", payee="",
                           ai_notes="", invoice_id=None) -> int:
        row = {
            "date": str(date), "type": type_, "amount": float(amount),
            "category": category, "description": description,
            "reference": reference, "payee": payee, "ai_notes": ai_notes,
        }
        if invoice_id:
            row["invoice_id"] = invoice_id
        res = self._q("transactions").insert(row).execute()
        return res.data[0]["id"]

    def get_monthly(self) -> List[Dict]:
        rows = (self._q("transactions")
                .select("date, type, amount")
                .execute().data)
        # Aggregate in Python (no raw SQL via anon key)
        agg: Dict[str, Dict[str, float]] = {}
        for r in rows:
            month = r["date"][:7]
            key = (month, r["type"])
            agg[key] = agg.get(key, 0) + float(r["amount"])
        result = [{"month": k[0], "type": k[1], "total": v}
                  for k, v in sorted(agg.items(), reverse=True)]
        return result[:24]

    def get_by_category(self) -> List[Dict]:
        rows = self._q("transactions").select("type, category, amount").execute().data
        agg: Dict = {}
        for r in rows:
            key = (r.get("category") or "Uncategorized", r["type"])
            if key not in agg:
                agg[key] = {"total": 0, "cnt": 0}
            agg[key]["total"] += float(r["amount"])
            agg[key]["cnt"]   += 1
        return [{"category": k[0], "type": k[1], "total": v["total"], "cnt": v["cnt"]}
                for k, v in sorted(agg.items(), key=lambda x: -x[1]["total"])]

    def fetch_by_type(self, type_: str, limit: int = 200) -> List[Dict]:
        return (self._q("transactions")
                .select("*")
                .eq("type", type_)
                .order("date", desc=True)
                .limit(limit)
                .execute().data)

    def delete_transaction(self, txn_id: int):
        self._q("transactions").delete().eq("id", txn_id).execute()

    # ── Invoices ─────────────────────────────────────────────────────────────
    def get_invoices(self) -> List[Dict]:
        rows = (self._q("invoices")
                .select("*, customers(name, company)")
                .order("created_at", desc=True)
                .execute().data)
        for r in rows:
            cust = r.pop("customers", None) or {}
            r["customer_name"]    = cust.get("name", "")
            r["customer_company"] = cust.get("company", "")
        return rows

    def get_invoice_summary(self) -> Dict:
        rows = self._q("invoices").select("status, balance_due, amount_paid, total").execute().data
        open_    = sum(float(r["balance_due"]) for r in rows if r["status"] in ("open","partial"))
        overdue  = sum(float(r["balance_due"]) for r in rows if r["status"] == "overdue")
        paid     = sum(float(r["amount_paid"]) for r in rows if r["status"] == "paid")
        count_op = sum(1 for r in rows if r["status"] in ("open","partial","overdue"))
        return {"open": open_, "overdue": overdue, "paid": paid, "count_open": count_op}

    def create_invoice(self, customer_id, issue_date, due_date,
                       items, tax_rate=0.0, notes="") -> int:
        # Get next invoice number
        existing = self._q("invoices").select("id").execute().data
        inv_num  = f"INV-{date.today().year}-{(len(existing)+1):04d}"
        subtotal = sum(i["quantity"] * i["unit_price"] for i in items)
        tax_amt  = subtotal * (tax_rate / 100)
        total    = subtotal + tax_amt

        inv = self._q("invoices").insert({
            "invoice_number": inv_num,
            "customer_id":    customer_id,
            "issue_date":     str(issue_date),
            "due_date":       str(due_date),
            "status":         "open",
            "subtotal":       subtotal,
            "tax_rate":       tax_rate,
            "tax_amount":     tax_amt,
            "total":          total,
            "balance_due":    total,
            "amount_paid":    0,
            "notes":          notes,
        }).execute().data[0]

        for item in items:
            self._q("invoice_items").insert({
                "invoice_id":  inv["id"],
                "description": item["description"],
                "quantity":    item["quantity"],
                "unit_price":  item["unit_price"],
                "amount":      item["quantity"] * item["unit_price"],
            }).execute()

        return inv["id"]

    def mark_invoice_paid(self, invoice_id: int, amount: float):
        inv = self._q("invoices").select("*").eq("id", invoice_id).single().execute().data
        new_paid = float(inv["amount_paid"]) + amount
        new_bal  = max(0, float(inv["total"]) - new_paid)
        status   = "paid" if new_bal <= 0 else "partial"
        self._q("invoices").update({
            "amount_paid": new_paid,
            "balance_due": new_bal,
            "status": status,
        }).eq("id", invoice_id).execute()

    # ── Customers ────────────────────────────────────────────────────────────
    def get_customers(self) -> List[Dict]:
        return self._q("customers").select("*").eq("is_active", True).order("name").execute().data

    def create_customer(self, name, email="", phone="", address="", company="") -> int:
        res = self._q("customers").insert({
            "name": name, "email": email, "phone": phone,
            "address": address, "company": company,
        }).execute()
        return res.data[0]["id"]

    # ── Vendors ───────────────────────────────────────────────────────────────
    def get_vendors(self) -> List[Dict]:
        return self._q("vendors").select("*").eq("is_active", True).order("name").execute().data

    def create_vendor(self, name, email="", phone="", address="", company="") -> int:
        res = self._q("vendors").insert({
            "name": name, "email": email, "phone": phone,
            "address": address, "company": company,
        }).execute()
        return res.data[0]["id"]

    # ── Chart of Accounts ────────────────────────────────────────────────────
    def get_accounts(self) -> List[Dict]:
        return (self._q("accounts")
                .select("*")
                .eq("is_active", True)
                .order("code")
                .execute().data)

    # ── Bank Accounts ────────────────────────────────────────────────────────
    def get_bank_accounts(self) -> List[Dict]:
        return (self._q("bank_accounts")
                .select("*")
                .eq("is_active", True)
                .execute().data)

    def update_bank_balance(self, bank_id: int, delta: float):
        bank = self._q("bank_accounts").select("balance").eq("id", bank_id).single().execute().data
        new_balance = float(bank["balance"]) + delta
        self._q("bank_accounts").update({"balance": new_balance}).eq("id", bank_id).execute()

    # ── Profile ───────────────────────────────────────────────────────────────
    def get_profile(self) -> Optional[Dict]:
        res = self._q("profiles").select("*").execute()
        return res.data[0] if res.data else None

    def update_profile(self, company_name: str, currency: str = "PHP"):
        profile = self.get_profile()
        if profile:
            self._q("profiles").update({
                "company_name": company_name,
                "currency": currency,
            }).eq("id", profile["id"]).execute()

    # ── Generic helpers ───────────────────────────────────────────────────────
    def scalar(self, table: str, column: str, filters: Dict = None) -> Any:
        q = self._q(table).select(column)
        if filters:
            for k, v in filters.items():
                q = q.eq(k, v)
        res = q.execute()
        return res.data[0][column] if res.data else None

    def get_pl_data(self, from_date: str, to_date: str):
        rows = (self._q("transactions")
                .select("type, category, amount")
                .gte("date", from_date)
                .lte("date", to_date)
                .execute().data)
        income_cats: Dict[str, float] = {}
        expense_cats: Dict[str, float] = {}
        for r in rows:
            cat = r.get("category") or "Uncategorized"
            amt = float(r["amount"])
            if r["type"] == "income":
                income_cats[cat] = income_cats.get(cat, 0) + amt
            elif r["type"] == "expense":
                expense_cats[cat] = expense_cats.get(cat, 0) + amt
        return income_cats, expense_cats
