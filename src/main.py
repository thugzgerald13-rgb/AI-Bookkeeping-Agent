import sys, os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import streamlit as st
import pandas as pd
import io, csv
from datetime import datetime, timedelta, date

from config.config import config
from src.database import DB
from src.agent import BookkeepingAgent

st.set_page_config(page_title="AI Books", page_icon="📗", layout="wide", initial_sidebar_state="expanded")

# ── QBO-like CSS ───────────────────────────────────────────────────────────────
st.markdown("""
<style>
@import url('https://fonts.googleapis.com/css2?family=Source+Sans+3:wght@400;500;600;700&display=swap');
html, body, [class*="css"] { font-family: 'Source Sans 3', 'Segoe UI', sans-serif !important; }
#MainMenu, footer, header,
[data-testid="manage-app-button"],
[data-testid="stToolbarActions"],
[data-testid="stStatusWidget"] { display: none !important; }
.stApp { background: #f4f5f7 !important; }
[data-testid="stSidebar"] { background: #2c3e50 !important; border-right: none !important; }
[data-testid="stSidebar"] * { color: #ecf0f1 !important; }
[data-testid="stSidebar"] .stRadio label { color: #bdc3c7 !important; font-size: 14px !important; padding: 6px 8px !important; border-radius: 6px !important; display: block !important; }
[data-testid="stSidebar"] .stRadio label:hover { background: rgba(255,255,255,0.1) !important; color: #fff !important; }
[data-testid="stSidebar"] hr { border-color: rgba(255,255,255,0.15) !important; }
.main .block-container { padding: 1.5rem 2rem 2rem 2rem !important; max-width: 100% !important; }
.page-header { font-size: 22px; font-weight: 700; color: #1a1a2e; margin-bottom: 20px; padding-bottom: 12px; border-bottom: 2px solid #e8e9eb; }
.kpi-card { background: white; border-radius: 8px; padding: 18px 20px; box-shadow: 0 1px 4px rgba(0,0,0,0.08); border-left: 4px solid #2ecc71; margin-bottom: 4px; }
.kpi-card.red { border-left-color: #e74c3c; }
.kpi-card.blue { border-left-color: #3498db; }
.kpi-card.orange { border-left-color: #e67e22; }
.kpi-card.teal { border-left-color: #1abc9c; }
.kpi-label { font-size: 12px; color: #7f8c8d; font-weight: 600; text-transform: uppercase; letter-spacing: 0.5px; margin-bottom: 6px; }
.kpi-value { font-size: 24px; font-weight: 700; color: #2c3e50; }
.kpi-sub { font-size: 12px; color: #95a5a6; margin-top: 4px; }
.section-card { background: white; border-radius: 8px; padding: 20px 24px; box-shadow: 0 1px 4px rgba(0,0,0,0.08); margin-bottom: 16px; }
.alert-box { padding: 12px 16px; border-radius: 8px; margin-bottom: 12px; font-size: 14px; }
.alert-info { background: #eaf4fb; border-left: 4px solid #3498db; color: #1a5276; }
.alert-warning { background: #fef9e7; border-left: 4px solid #f39c12; color: #784212; }
.alert-success { background: #eafaf1; border-left: 4px solid #27ae60; color: #145a32; }
.alert-danger { background: #fdedec; border-left: 4px solid #e74c3c; color: #78281f; }
.stButton > button { border-radius: 6px !important; font-weight: 600 !important; font-size: 14px !important; }
.stButton > button[kind="primary"] { background: #27ae60 !important; border-color: #27ae60 !important; color: white !important; }
.stButton > button[kind="primary"]:hover { background: #1e8449 !important; }
</style>
""", unsafe_allow_html=True)

# ── Session state ─────────────────────────────────────────────────────────────
if "db" not in st.session_state:
    st.session_state.db = DB("data/bookkeeping.db")
if "agent" not in st.session_state:
    api_key = config.api.anthropic_api_key or os.getenv("ANTHROPIC_API_KEY", "")
    st.session_state.agent = BookkeepingAgent(api_key=api_key or None)
if "chat_messages" not in st.session_state:
    st.session_state.chat_messages = []

db: DB = st.session_state.db
agent: BookkeepingAgent = st.session_state.agent

# ── Helpers ───────────────────────────────────────────────────────────────────
def peso(v): return f"₱{float(v or 0):,.2f}"
def kpi(label, value, sub="", color=""):
    st.markdown(f'<div class="kpi-card {color}"><div class="kpi-label">{label}</div><div class="kpi-value">{value}</div>{"<div class=kpi-sub>"+sub+"</div>" if sub else ""}</div>', unsafe_allow_html=True)
def page_header(icon, title):
    st.markdown(f'<div class="page-header">{icon} {title}</div>', unsafe_allow_html=True)
def overdue_check(d):
    try: return date.today() > datetime.strptime(d, "%Y-%m-%d").date()
    except: return False

# ── Sidebar ───────────────────────────────────────────────────────────────────
with st.sidebar:
    st.markdown('<div style="padding:8px 0 16px;border-bottom:1px solid rgba(255,255,255,0.15);margin-bottom:16px"><div style="font-size:20px;font-weight:800;color:#2ecc71">📗 AI Books</div><div style="font-size:12px;color:#95a5a6;margin-top:2px">Powered by Claude</div></div>', unsafe_allow_html=True)
    page = st.radio("", ["🏠  Dashboard","📄  Invoices","💸  Expenses","🏦  Banking","👤  Customers","🏪  Vendors","📊  Reports","🗂️  Chart of Accounts","💬  AI Advisor"], label_visibility="collapsed")
    st.divider()
    try:
        summary = db.get_summary()
        inv_sum = db.get_invoice_summary()
        net = summary["net"]
        nc = "#2ecc71" if net >= 0 else "#e74c3c"
        st.markdown(f'<div style="font-size:12px;color:#95a5a6;margin-bottom:8px;font-weight:600;text-transform:uppercase;letter-spacing:.5px">Quick Snapshot</div><div style="display:flex;justify-content:space-between;margin-bottom:6px"><span style="color:#bdc3c7;font-size:13px">Net Profit</span><span style="color:{nc};font-weight:700;font-size:13px">{peso(net)}</span></div><div style="display:flex;justify-content:space-between;margin-bottom:6px"><span style="color:#bdc3c7;font-size:13px">A/R Open</span><span style="color:#3498db;font-weight:600;font-size:13px">{peso(inv_sum["open"])}</span></div><div style="display:flex;justify-content:space-between"><span style="color:#bdc3c7;font-size:13px">Overdue</span><span style="color:#e74c3c;font-weight:600;font-size:13px">{peso(inv_sum["overdue"])}</span></div>', unsafe_allow_html=True)
    except: pass
    st.divider()
    st.markdown(f'<div style="font-size:11px;color:#636e72;text-align:center">{config.app.company_name} · v{config.app.version}</div>', unsafe_allow_html=True)

# ══════════════════════════════════════════════════════════════════════════════
# DASHBOARD
# ══════════════════════════════════════════════════════════════════════════════
if page == "🏠  Dashboard":
    page_header("🏠", "Business Overview")
    summary = db.get_summary()
    inv_sum = db.get_invoice_summary()
    banks = db.get_bank_accounts()
    bank_total = sum(b["balance"] for b in banks)
    net = summary["net"]

    c1,c2,c3 = st.columns(3)
    with c1: kpi("💰 Total Income", peso(summary["total_income"]), f"{summary['count']} transactions")
    with c2: kpi("💸 Total Expenses", peso(summary["total_expense"]), "All time", "red")
    with c3: kpi("📈 Net Profit / Loss", peso(net), "", "" if net >= 0 else "red")
    st.markdown("<div style='margin-top:12px'></div>", unsafe_allow_html=True)
    c1,c2,c3 = st.columns(3)
    with c1: kpi("📄 A/R Open", peso(inv_sum["open"]), f"{inv_sum['count_open']} open invoices", "blue")
    with c2: kpi("⚠️ Overdue", peso(inv_sum["overdue"]), "Past due date", "orange")
    with c3: kpi("🏦 Bank Balance", peso(bank_total), f"{len(banks)} account(s)", "teal")
    st.markdown("<div style='margin-top:20px'></div>", unsafe_allow_html=True)

    col1, col2 = st.columns([3,2])
    with col1:
        st.markdown('<div class="section-card">', unsafe_allow_html=True)
        st.markdown("**📅 Income vs Expenses — Monthly**")
        monthly = db.get_monthly()
        if monthly:
            df_m = pd.DataFrame(monthly)
            pivot = df_m.pivot_table(index="month", columns="type", values="total", aggfunc="sum").fillna(0)
            st.bar_chart(pivot)
        else:
            st.info("Add transactions to see the trend.")
        st.markdown('</div>', unsafe_allow_html=True)
    with col2:
        st.markdown('<div class="section-card">', unsafe_allow_html=True)
        st.markdown("**📋 Recent Transactions**")
        txns = db.get_transactions(limit=8)
        if txns:
            for t in txns:
                color = "#e74c3c" if t["type"] == "expense" else "#27ae60"
                sign = "-" if t["type"] == "expense" else "+"
                st.markdown(f'<div style="display:flex;justify-content:space-between;align-items:center;padding:6px 0;border-bottom:1px solid #f4f5f7"><div><div style="font-size:13px;font-weight:600;color:#2c3e50">{t["description"] or "—"}</div><div style="font-size:11px;color:#95a5a6">{t["date"]} · {t.get("category","")}</div></div><div style="font-size:14px;font-weight:700;color:{color}">{sign}{peso(t["amount"])}</div></div>', unsafe_allow_html=True)
        else:
            st.info("No transactions yet.")
        st.markdown('</div>', unsafe_allow_html=True)

    st.markdown('<div class="section-card">', unsafe_allow_html=True)
    st.markdown("**🗂️ Spending by Category**")
    cats = db.get_by_category()
    expenses = [c for c in cats if c["type"] == "expense"]
    if expenses:
        df_e = pd.DataFrame(expenses)[["category","total","cnt"]]
        df_e.columns = ["Category","Amount (₱)","Transactions"]
        df_e["Amount (₱)"] = df_e["Amount (₱)"].apply(lambda x: round(x,2))
        st.dataframe(df_e, use_container_width=True, hide_index=True)
    else:
        st.info("No category data yet.")
    st.markdown('</div>', unsafe_allow_html=True)


# ══════════════════════════════════════════════════════════════════════════════
# INVOICES
# ══════════════════════════════════════════════════════════════════════════════
elif page == "📄  Invoices":
    page_header("📄", "Invoices")
    tab1, tab2 = st.tabs(["📋 Invoice List", "➕ New Invoice"])
    with tab1:
        inv_sum = db.get_invoice_summary()
        c1,c2,c3 = st.columns(3)
        with c1: kpi("Open", peso(inv_sum["open"]), f"{inv_sum['count_open']} invoices", "blue")
        with c2: kpi("Overdue", peso(inv_sum["overdue"]), "Needs follow-up", "orange")
        with c3: kpi("Collected", peso(inv_sum["paid"]), "Paid invoices")
        st.markdown("<div style='margin-top:16px'></div>", unsafe_allow_html=True)
        invoices = db.get_invoices()
        if invoices:
            for inv in invoices:
                if inv["status"] == "open" and overdue_check(inv["due_date"]):
                    db.execute("UPDATE invoices SET status='overdue' WHERE id=?", (inv["id"],))
            invoices = db.get_invoices()
            df = pd.DataFrame(invoices)
            show = ["invoice_number","customer_name","issue_date","due_date","total","amount_paid","balance_due","status"]
            df_show = df[[c for c in show if c in df.columns]].copy()
            df_show.columns = ["Invoice #","Customer","Issue Date","Due Date","Total","Paid","Balance Due","Status"]
            for col in ["Total","Paid","Balance Due"]: df_show[col] = df_show[col].apply(lambda x: f"₱{x:,.2f}")
            st.dataframe(df_show, use_container_width=True, hide_index=True)
            st.markdown("**Record Payment**")
            col1,col2,col3 = st.columns([2,1,1])
            open_inv = {f"{i['invoice_number']} — {i['customer_name']} (₱{i['balance_due']:,.2f})": i["id"] for i in invoices if i["status"] in ("open","overdue","partial")}
            if open_inv:
                with col1: sel = st.selectbox("Select Invoice", list(open_inv.keys()), key="pay_inv")
                with col2: pay_amt = st.number_input("Amount (₱)", min_value=0.01, step=100.0, key="pay_amt")
                with col3:
                    st.markdown("<div style='margin-top:28px'></div>", unsafe_allow_html=True)
                    if st.button("✅ Record Payment", type="primary"):
                        db.mark_invoice_paid(open_inv[sel], pay_amt)
                        db.insert_transaction(date=date.today().strftime("%Y-%m-%d"), type_="income", amount=pay_amt, category="Service Revenue", description=f"Payment — {sel.split('—')[0].strip()}")
                        st.success("Payment recorded!")
                        st.rerun()
            else:
                st.markdown('<div class="alert-box alert-success">🎉 All invoices are paid!</div>', unsafe_allow_html=True)
        else:
            st.markdown('<div class="alert-box alert-info">📄 No invoices yet. Create one in the New Invoice tab.</div>', unsafe_allow_html=True)

    with tab2:
        customers = db.get_customers()
        if not customers:
            st.markdown('<div class="alert-box alert-warning">⚠️ No customers found. Add one in Customers first.</div>', unsafe_allow_html=True)
        else:
            with st.form("new_invoice", clear_on_submit=True):
                c1,c2,c3 = st.columns(3)
                with c1:
                    cust_map = {c["name"]: c["id"] for c in customers}
                    cust = st.selectbox("Customer *", list(cust_map.keys()))
                with c2: issue_date = st.date_input("Issue Date", value=date.today())
                with c3: due_date = st.date_input("Due Date", value=date.today()+timedelta(days=30))
                st.markdown("**Line Items**")
                items = []
                for i in range(1,6):
                    c1,c2,c3 = st.columns([4,1,1])
                    with c1: desc = st.text_input(f"Description {i}", key=f"desc_{i}", placeholder="Service or product")
                    with c2: qty = st.number_input("Qty", value=1.0, min_value=0.0, key=f"qty_{i}")
                    with c3: price = st.number_input("Price (₱)", value=0.0, min_value=0.0, key=f"price_{i}")
                    if desc and price > 0: items.append({"description":desc,"quantity":qty,"unit_price":price})
                c1,c2 = st.columns(2)
                with c1: tax_rate = st.number_input("VAT / Tax Rate (%)", value=0.0, min_value=0.0, max_value=100.0)
                with c2: notes = st.text_area("Notes", height=80)
                subtotal = sum(i["quantity"]*i["unit_price"] for i in items)
                tax = subtotal*(tax_rate/100)
                st.markdown(f'<div style="background:#f8f9fa;border-radius:8px;padding:12px 16px;margin-top:8px"><div style="display:flex;justify-content:space-between"><span>Subtotal</span><strong>{peso(subtotal)}</strong></div><div style="display:flex;justify-content:space-between;color:#7f8c8d"><span>VAT ({tax_rate}%)</span><strong>{peso(tax)}</strong></div><hr style="border-color:#dee2e6;margin:8px 0"><div style="display:flex;justify-content:space-between;font-size:16px"><span><strong>Total</strong></span><strong style="color:#27ae60">{peso(subtotal+tax)}</strong></div></div>', unsafe_allow_html=True)
                if st.form_submit_button("💾 Create Invoice", type="primary", use_container_width=True):
                    if not items: st.error("Add at least one line item.")
                    else:
                        inv_id = db.create_invoice(customer_id=cust_map[cust], issue_date=issue_date.strftime("%Y-%m-%d"), due_date=due_date.strftime("%Y-%m-%d"), items=items, tax_rate=tax_rate, notes=notes)
                        st.success(f"✅ Invoice created! (#{inv_id})")
                        st.rerun()


# ══════════════════════════════════════════════════════════════════════════════
# EXPENSES
# ══════════════════════════════════════════════════════════════════════════════
elif page == "💸  Expenses":
    page_header("💸", "Expenses")
    tab1, tab2 = st.tabs(["📋 Expense List", "➕ New Expense"])
    with tab1:
        txns = db.fetch("SELECT id,date,description,category,amount,reference,payee,ai_notes FROM transactions WHERE type='expense' ORDER BY date DESC LIMIT 200")
        if txns:
            df = pd.DataFrame(txns)
            df["amount"] = df["amount"].apply(lambda x: f"₱{x:,.2f}")
            st.dataframe(df, use_container_width=True, hide_index=True)
            total_exp = db.scalar("SELECT COALESCE(SUM(amount),0) FROM transactions WHERE type='expense'")
            st.markdown(f'<div class="alert-box alert-info">Total Expenses: <strong>{peso(total_exp)}</strong></div>', unsafe_allow_html=True)
            raw = db.fetch("SELECT * FROM transactions WHERE type='expense'")
            if raw:
                buf = io.StringIO()
                w = csv.DictWriter(buf, fieldnames=raw[0].keys()); w.writeheader(); w.writerows(raw)
                st.download_button("⬇️ Export CSV", buf.getvalue(), file_name=f"expenses_{date.today()}.csv", mime="text/csv")
        else:
            st.markdown('<div class="alert-box alert-info">No expenses recorded yet.</div>', unsafe_allow_html=True)
    with tab2:
        accounts = db.get_accounts()
        expense_accounts = [a for a in accounts if a["type"] == "Expense"]
        vendors = db.get_vendors()
        cat_opts = [a["name"] for a in expense_accounts] or ["Salaries Expense","Rent Expense","Utilities Expense","Office Supplies","Marketing & Advertising","Professional Fees","Transportation","Meals & Entertainment","Taxes & Licenses","Miscellaneous Expense"]
        with st.form("new_expense", clear_on_submit=True):
            c1,c2,c3 = st.columns(3)
            with c1: exp_date = st.date_input("Date", value=date.today())
            with c2: amount = st.number_input("Amount (₱) *", min_value=0.01, step=1.0, format="%.2f")
            with c3: payee = st.selectbox("Vendor / Payee", ["— None —"]+[v["name"] for v in vendors])
            c1,c2 = st.columns(2)
            with c1: description = st.text_input("Description *", placeholder="e.g. Office supplies")
            with c2: category = st.selectbox("Category *", cat_opts)
            c1,c2 = st.columns(2)
            with c1: reference = st.text_input("Reference / OR #")
            with c2: use_ai = st.checkbox("🤖 AI Auto-Categorize", value=True)
            if st.form_submit_button("💾 Save Expense", type="primary", use_container_width=True):
                if not description: st.error("Description required.")
                else:
                    ai_notes = ""; final_cat = category
                    if use_ai:
                        with st.spinner("AI categorizing..."):
                            result = agent.categorize_transaction(description, amount, "expense")
                            ai_notes = result.get("notes",""); final_cat = result.get("category", category)
                    db.insert_transaction(date=exp_date.strftime("%Y-%m-%d"), type_="expense", amount=amount, category=final_cat, description=description, reference=reference, payee=payee if payee != "— None —" else "", ai_notes=ai_notes)
                    st.success(f"✅ Expense saved! Category: **{final_cat}**")
                    if ai_notes: st.info(f"🤖 {ai_notes}")
                    st.rerun()

# ══════════════════════════════════════════════════════════════════════════════
# BANKING
# ══════════════════════════════════════════════════════════════════════════════
elif page == "🏦  Banking":
    page_header("🏦", "Banking")
    banks = db.get_bank_accounts()
    if banks:
        cols = st.columns(min(len(banks),3))
        for i,bank in enumerate(banks):
            with cols[i%3]:
                color = "#27ae60" if bank["balance"] >= 0 else "#e74c3c"
                st.markdown(f'<div class="section-card" style="border-left:4px solid {color}"><div style="font-size:13px;color:#7f8c8d;font-weight:600">{bank.get("bank_name","Bank")} · {bank["type"].upper()}</div><div style="font-size:18px;font-weight:800;color:#2c3e50;margin:4px 0">{bank["name"]}</div><div style="font-size:22px;font-weight:700;color:{color}">{peso(bank["balance"])}</div><div style="font-size:11px;color:#95a5a6;margin-top:4px">{bank["currency"]}</div></div>', unsafe_allow_html=True)
    st.markdown("<div style='margin-top:8px'></div>", unsafe_allow_html=True)
    tab1,tab2,tab3 = st.tabs(["📋 All Transactions","➕ Add Transaction","🏦 Add Bank Account"])
    with tab1:
        c1,c2,c3 = st.columns(3)
        with c1: type_filter = st.multiselect("Type", ["income","expense","transfer","adjustment"])
        with c2: search = st.text_input("Search", placeholder="e.g. rent, salary...")
        with c3: limit = st.selectbox("Show", [50,100,200,500], index=0)
        sql = "SELECT * FROM transactions WHERE 1=1"; params = []
        if type_filter:
            sql += f" AND type IN ({','.join('?'*len(type_filter))})"; params.extend(type_filter)
        if search:
            sql += " AND description LIKE ?"; params.append(f"%{search}%")
        sql += f" ORDER BY date DESC, id DESC LIMIT {limit}"
        txns = db.fetch(sql, tuple(params))
        if txns:
            df = pd.DataFrame(txns)
            show_c = ["id","date","type","amount","category","description","reference","payee"]
            df_show = df[[c for c in show_c if c in df.columns]].copy()
            df_show["amount"] = df_show["amount"].apply(lambda x: f"₱{x:,.2f}")
            st.dataframe(df_show, use_container_width=True, hide_index=True)
            buf = io.StringIO(); w = csv.DictWriter(buf, fieldnames=txns[0].keys()); w.writeheader(); w.writerows(txns)
            st.download_button("⬇️ Export CSV", buf.getvalue(), file_name=f"transactions_{date.today()}.csv", mime="text/csv")
        else:
            st.info("No transactions found.")
    with tab2:
        with st.form("add_txn", clear_on_submit=True):
            c1,c2,c3,c4 = st.columns(4)
            with c1: txn_type = st.selectbox("Type", ["income","expense","transfer","adjustment"])
            with c2: txn_amt = st.number_input("Amount (₱)", min_value=0.01, step=1.0, format="%.2f")
            with c3: txn_date = st.date_input("Date", value=date.today())
            with c4: txn_ref = st.text_input("Reference #")
            c1,c2 = st.columns(2)
            with c1: txn_desc = st.text_input("Description *")
            with c2: txn_payee = st.text_input("Payee / Payer")
            txn_cat = st.text_input("Category")
            if st.form_submit_button("💾 Save Transaction", type="primary", use_container_width=True):
                if not txn_desc: st.error("Description required.")
                else:
                    db.insert_transaction(date=txn_date.strftime("%Y-%m-%d"), type_=txn_type, amount=txn_amt, category=txn_cat, description=txn_desc, reference=txn_ref, payee=txn_payee)
                    if banks:
                        delta = txn_amt if txn_type=="income" else -txn_amt if txn_type=="expense" else 0
                        if delta: db.update_bank_balance(banks[0]["id"], delta)
                    st.success("✅ Transaction saved!"); st.rerun()
    with tab3:
        with st.form("add_bank", clear_on_submit=True):
            c1,c2 = st.columns(2)
            with c1: bname = st.text_input("Account Name *")
            with c2: bbank = st.text_input("Bank Name", placeholder="e.g. BDO, BPI")
            c1,c2,c3 = st.columns(3)
            with c1: btype = st.selectbox("Type", ["checking","savings","cash","credit card"])
            with c2: bacct = st.text_input("Account # (last 4)")
            with c3: bbal = st.number_input("Opening Balance (₱)", value=0.0, step=100.0)
            if st.form_submit_button("Add Bank Account", type="primary"):
                if not bname: st.error("Name required.")
                else:
                    db.execute("INSERT INTO bank_accounts (name, type, bank_name, account_number, balance) VALUES (?,?,?,?,?)", (bname,btype,bbank,bacct,bbal))
                    st.success("✅ Added!"); st.rerun()


# ══════════════════════════════════════════════════════════════════════════════
# CUSTOMERS
# ══════════════════════════════════════════════════════════════════════════════
elif page == "👤  Customers":
    page_header("👤", "Customers")
    tab1,tab2 = st.tabs(["👥 Customer List","➕ New Customer"])
    with tab1:
        customers = db.get_customers()
        if customers:
            df = pd.DataFrame(customers)
            df["balance"] = df["balance"].apply(lambda x: f"₱{x:,.2f}")
            st.dataframe(df[["id","name","company","email","phone","balance"]], use_container_width=True, hide_index=True)
            st.markdown(f'<div class="alert-box alert-info">{len(customers)} active customers</div>', unsafe_allow_html=True)
        else:
            st.markdown('<div class="alert-box alert-info">No customers yet.</div>', unsafe_allow_html=True)
    with tab2:
        with st.form("new_cust", clear_on_submit=True):
            c1,c2 = st.columns(2)
            with c1: cname = st.text_input("Full Name *")
            with c2: ccomp = st.text_input("Company")
            c1,c2 = st.columns(2)
            with c1: cemail = st.text_input("Email")
            with c2: cphone = st.text_input("Phone")
            caddr = st.text_area("Address", height=80)
            if st.form_submit_button("💾 Save Customer", type="primary", use_container_width=True):
                if not cname: st.error("Name required.")
                else:
                    db.create_customer(cname, cemail, cphone, caddr, ccomp)
                    st.success(f"✅ '{cname}' added!"); st.rerun()

# ══════════════════════════════════════════════════════════════════════════════
# VENDORS
# ══════════════════════════════════════════════════════════════════════════════
elif page == "🏪  Vendors":
    page_header("🏪", "Vendors")
    tab1,tab2 = st.tabs(["🏪 Vendor List","➕ New Vendor"])
    with tab1:
        vendors = db.get_vendors()
        if vendors:
            df = pd.DataFrame(vendors)
            df["balance"] = df["balance"].apply(lambda x: f"₱{x:,.2f}")
            st.dataframe(df[["id","name","company","email","phone","balance"]], use_container_width=True, hide_index=True)
        else:
            st.markdown('<div class="alert-box alert-info">No vendors yet.</div>', unsafe_allow_html=True)
    with tab2:
        with st.form("new_vend", clear_on_submit=True):
            c1,c2 = st.columns(2)
            with c1: vname = st.text_input("Vendor Name *")
            with c2: vcomp = st.text_input("Company")
            c1,c2 = st.columns(2)
            with c1: vemail = st.text_input("Email")
            with c2: vphone = st.text_input("Phone")
            vaddr = st.text_area("Address", height=80)
            if st.form_submit_button("💾 Save Vendor", type="primary", use_container_width=True):
                if not vname: st.error("Name required.")
                else:
                    db.create_vendor(vname, vemail, vphone, vaddr, vcomp)
                    st.success(f"✅ '{vname}' added!"); st.rerun()

# ══════════════════════════════════════════════════════════════════════════════
# REPORTS
# ══════════════════════════════════════════════════════════════════════════════
elif page == "📊  Reports":
    page_header("📊", "Reports")
    tab1,tab2,tab3,tab4 = st.tabs(["📈 P&L","📋 A/R Aging","📋 Expense Summary","🗓️ Monthly Trend"])
    with tab1:
        c1,c2 = st.columns(2)
        with c1: pl_from = st.date_input("From", value=date.today().replace(month=1,day=1))
        with c2: pl_to = st.date_input("To", value=date.today())
        inc_rows = db.fetch("SELECT category, SUM(amount) as total FROM transactions WHERE type='income' AND date BETWEEN ? AND ? GROUP BY category ORDER BY total DESC", (pl_from.strftime("%Y-%m-%d"), pl_to.strftime("%Y-%m-%d")))
        exp_rows = db.fetch("SELECT category, SUM(amount) as total FROM transactions WHERE type='expense' AND date BETWEEN ? AND ? GROUP BY category ORDER BY total DESC", (pl_from.strftime("%Y-%m-%d"), pl_to.strftime("%Y-%m-%d")))
        total_inc = sum(r["total"] for r in inc_rows)
        total_exp = sum(r["total"] for r in exp_rows)
        net_pl = total_inc - total_exp
        c1,c2 = st.columns(2)
        with c1:
            st.markdown("**INCOME**")
            for r in inc_rows: st.markdown(f'<div style="display:flex;justify-content:space-between;padding:5px 0;border-bottom:1px solid #f4f5f7"><span>{r["category"] or "Uncategorized"}</span><strong style="color:#27ae60">{peso(r["total"])}</strong></div>', unsafe_allow_html=True)
            st.markdown(f'<div style="display:flex;justify-content:space-between;padding:8px 0;margin-top:6px;border-top:2px solid #2c3e50"><strong>Total Income</strong><strong style="color:#27ae60">{peso(total_inc)}</strong></div>', unsafe_allow_html=True)
        with c2:
            st.markdown("**EXPENSES**")
            for r in exp_rows: st.markdown(f'<div style="display:flex;justify-content:space-between;padding:5px 0;border-bottom:1px solid #f4f5f7"><span>{r["category"] or "Uncategorized"}</span><strong style="color:#e74c3c">{peso(r["total"])}</strong></div>', unsafe_allow_html=True)
            st.markdown(f'<div style="display:flex;justify-content:space-between;padding:8px 0;margin-top:6px;border-top:2px solid #2c3e50"><strong>Total Expenses</strong><strong style="color:#e74c3c">{peso(total_exp)}</strong></div>', unsafe_allow_html=True)
        nc = "#27ae60" if net_pl >= 0 else "#e74c3c"
        label = "NET PROFIT" if net_pl >= 0 else "NET LOSS"
        st.markdown(f'<div style="background:#f8f9fa;border-radius:8px;padding:16px;margin-top:16px;border:2px solid {nc}"><div style="display:flex;justify-content:space-between;align-items:center"><span style="font-size:16px;font-weight:700;color:#2c3e50">{label}</span><span style="font-size:24px;font-weight:800;color:{nc}">{peso(net_pl)}</span></div></div>', unsafe_allow_html=True)
    with tab2:
        invoices = db.get_invoices()
        open_inv = [i for i in invoices if i["status"] in ("open","overdue","partial")]
        if open_inv:
            today = date.today()
            for inv in open_inv:
                try:
                    due = datetime.strptime(inv["due_date"],"%Y-%m-%d").date()
                    days = (today-due).days
                    bucket = "Current" if days<=0 else "1-30" if days<=30 else "31-60" if days<=60 else "61-90" if days<=90 else "90+"
                    inv["days_past"]=days; inv["bucket"]=bucket
                except: inv["days_past"]=0; inv["bucket"]="Current"
            df_ar = pd.DataFrame(open_inv)[["invoice_number","customer_name","due_date","balance_due","days_past","bucket"]]
            df_ar.columns = ["Invoice #","Customer","Due Date","Balance Due","Days Past Due","Bucket"]
            df_ar["Balance Due"] = df_ar["Balance Due"].apply(lambda x: f"₱{x:,.2f}")
            st.dataframe(df_ar, use_container_width=True, hide_index=True)
        else:
            st.markdown('<div class="alert-box alert-success">🎉 No open receivables!</div>', unsafe_allow_html=True)
    with tab3:
        cats = db.get_by_category()
        expenses = [c for c in cats if c["type"]=="expense"]
        if expenses:
            df_exp = pd.DataFrame(expenses)
            df_exp["total"] = df_exp["total"].apply(lambda x: round(x,2))
            df_exp.columns = ["Category","Type","Total (₱)","Count"]
            st.dataframe(df_exp[["Category","Total (₱)","Count"]], use_container_width=True, hide_index=True)
            st.markdown(f'<div class="alert-box alert-info">Total: <strong>{peso(sum(c["total"] for c in expenses))}</strong></div>', unsafe_allow_html=True)
        else:
            st.info("No expense data.")
    with tab4:
        monthly = db.get_monthly()
        if monthly:
            df_m = pd.DataFrame(monthly)
            pivot = df_m.pivot_table(index="month", columns="type", values="total", aggfunc="sum").fillna(0).reset_index()
            if "income" in pivot.columns and "expense" in pivot.columns: pivot["profit"] = pivot["income"] - pivot["expense"]
            st.dataframe(pivot, use_container_width=True, hide_index=True)
            chart_cols = [c for c in ["income","expense"] if c in pivot.columns]
            if chart_cols: st.bar_chart(pivot.set_index("month")[chart_cols])
        else:
            st.info("No monthly data yet.")

# ══════════════════════════════════════════════════════════════════════════════
# CHART OF ACCOUNTS
# ══════════════════════════════════════════════════════════════════════════════
elif page == "🗂️  Chart of Accounts":
    page_header("🗂️", "Chart of Accounts")
    accounts = db.get_accounts()
    if accounts:
        df = pd.DataFrame(accounts)
        df["balance"] = df["balance"].apply(lambda x: f"₱{x:,.2f}")
        st.dataframe(df[["code","name","type","subtype","balance"]], use_container_width=True, hide_index=True)
        st.markdown("<div style='margin-top:8px'></div>", unsafe_allow_html=True)
        for acc_type in ["Asset","Liability","Equity","Income","Expense"]:
            group = [a for a in accounts if a["type"]==acc_type]
            if group:
                total = sum(a["balance"] for a in group)
                st.markdown(f'<div style="display:flex;justify-content:space-between;padding:6px 12px;background:#f8f9fa;border-radius:6px;margin-bottom:4px"><strong>{acc_type}</strong><strong>{peso(total)}</strong></div>', unsafe_allow_html=True)
    st.divider()
    st.markdown("**Add New Account**")
    with st.form("add_acct", clear_on_submit=True):
        c1,c2,c3,c4 = st.columns(4)
        with c1: acode = st.text_input("Code", placeholder="e.g. 6999")
        with c2: aname = st.text_input("Name *")
        with c3: atype = st.selectbox("Type", ["Asset","Liability","Equity","Income","Expense"])
        with c4: asub = st.text_input("Subtype")
        if st.form_submit_button("Add Account", type="primary"):
            if not aname: st.error("Name required.")
            else:
                db.execute("INSERT INTO accounts (code, name, type, subtype) VALUES (?,?,?,?)", (acode,aname,atype,asub))
                st.success(f"✅ '{aname}' added!"); st.rerun()

# ══════════════════════════════════════════════════════════════════════════════
# AI ADVISOR
# ══════════════════════════════════════════════════════════════════════════════
elif page == "💬  AI Advisor":
    page_header("💬", "AI Financial Advisor")
    col1,col2 = st.columns([3,1])
    with col2:
        if st.button("🔍 Generate Insights", type="primary", use_container_width=True):
            with st.spinner("Analyzing finances..."):
                insights = agent.generate_insights()
            st.session_state.chat_messages.append({"role":"assistant","content":insights})
        if st.button("🗑️ Clear Chat", use_container_width=True):
            st.session_state.chat_messages = []; agent.clear_chat(); st.rerun()
    with col1:
        st.markdown('<div class="alert-box alert-info">💡 <strong>Try:</strong> "What are my top expenses?" · "Am I profitable?" · "How to handle BIR VAT?" · "Which customers owe me?"</div>', unsafe_allow_html=True)
    st.divider()
    for msg in st.session_state.chat_messages:
        with st.chat_message(msg["role"]): st.markdown(msg["content"])
    if prompt := st.chat_input("Ask your bookkeeping or tax question..."):
        st.session_state.chat_messages.append({"role":"user","content":prompt})
        with st.chat_message("user"): st.markdown(prompt)
        with st.chat_message("assistant"):
            with st.spinner("Thinking..."): reply = agent.chat(prompt)
            st.markdown(reply)
            st.session_state.chat_messages.append({"role":"assistant","content":reply})
