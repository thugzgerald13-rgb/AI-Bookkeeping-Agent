import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import streamlit as st
import pandas as pd
import io
from datetime import datetime

from config.config import config
from src.agent import BookkeepingAgent
from src.bookkeeper import TransactionType, ExpenseCategory

# ── Page config ──────────────────────────────────────────────────────────────
st.set_page_config(
    page_title="AI Bookkeeping Agent",
    page_icon="📒",
    layout="wide",
    initial_sidebar_state="expanded",
)

# ── Hide Streamlit UI chrome (Manage App, footer, menu) ──────────────────────
st.markdown("""
<style>
#MainMenu {visibility: hidden !important;}
footer {visibility: hidden !important;}
header {visibility: hidden !important;}
[data-testid="manage-app-button"] {display: none !important;}
[data-testid="stToolbar"] {display: none !important;}
[data-testid="stDecoration"] {display: none !important;}
[data-testid="stStatusWidget"] {display: none !important;}
.stDeployButton {display: none !important;}
</style>
""", unsafe_allow_html=True)

# ── Password Lock ─────────────────────────────────────────────────────────────
APP_PASSWORD = os.getenv("APP_PASSWORD", "capo2024")

def check_password():
    if st.session_state.get("authenticated"):
        return True
    st.markdown("""
    <div style="max-width:380px;margin:80px auto;text-align:center;">
        <div style="font-size:48px;margin-bottom:8px;">📒</div>
        <h2 style="margin-bottom:4px;">AI Bookkeeping Agent</h2>
        <p style="color:#64748b;margin-bottom:24px;">Enter your password to continue</p>
    </div>
    """, unsafe_allow_html=True)
    col = st.columns([1, 2, 1])[1]
    with col:
        pwd = st.text_input("Password", type="password", label_visibility="collapsed",
                            placeholder="Enter password...")
        if st.button("Unlock →", use_container_width=True, type="primary"):
            if pwd == APP_PASSWORD:
                st.session_state.authenticated = True
                st.rerun()
            else:
                st.error("Incorrect password.")
    return False

if not check_password():
    st.stop()

# ── Inject minimal CSS ────────────────────────────────────────────────────────
st.markdown("""
<style>
.metric-card {
    background: #f8fafc;
    border: 1px solid #e2e8f0;
    border-radius: 10px;
    padding: 16px 20px;
    text-align: center;
}
.metric-label { font-size: 13px; color: #64748b; margin-bottom: 4px; }
.metric-value { font-size: 26px; font-weight: 700; }
.income { color: #16a34a; }
.expense { color: #dc2626; }
.net-pos { color: #2563eb; }
.net-neg { color: #dc2626; }
</style>
""", unsafe_allow_html=True)

# ── Session state ─────────────────────────────────────────────────────────────
if "agent" not in st.session_state:
    api_key = config.api.anthropic_api_key or os.getenv("ANTHROPIC_API_KEY", "")
    st.session_state.agent = BookkeepingAgent(api_key=api_key if api_key else None)

if "chat_messages" not in st.session_state:
    st.session_state.chat_messages = []

agent: BookkeepingAgent = st.session_state.agent

# ── Sidebar ───────────────────────────────────────────────────────────────────
with st.sidebar:
    st.image("https://img.icons8.com/fluency/96/ledger.png", width=60)
    st.title("AI Bookkeeping")
    st.caption(f"v{config.app.version} · {config.app.company_name}")
    st.divider()

    page = st.radio(
        "Navigation",
        ["📊 Dashboard", "➕ Add Transaction", "📋 Transactions", "💬 AI Assistant", "📈 Insights"],
        label_visibility="collapsed",
    )
    st.divider()
    st.caption("Powered by Claude · SQLite")

# ── Helper ────────────────────────────────────────────────────────────────────
def fmt(amount: float) -> str:
    return f"₱{amount:,.2f}"

# ══════════════════════════════════════════════════════════════════════════════
# DASHBOARD
# ══════════════════════════════════════════════════════════════════════════════
if page == "📊 Dashboard":
    st.header("📊 Dashboard")
    summary = agent.bookkeeper.get_summary()
    net = summary["net"]

    c1, c2, c3, c4 = st.columns(4)
    with c1:
        st.metric("💰 Total Income", fmt(summary["total_income"]), delta=None)
    with c2:
        st.metric("💸 Total Expense", fmt(summary["total_expense"]), delta=None)
    with c3:
        color = "normal" if net >= 0 else "inverse"
        st.metric("📈 Net Balance", fmt(net))
    with c4:
        st.metric("🔢 Transactions", summary["transaction_count"])

    st.divider()

    col1, col2 = st.columns(2)

    with col1:
        st.subheader("By Category")
        cats = agent.bookkeeper.get_category_breakdown()
        if cats:
            df_cat = pd.DataFrame(cats, columns=["Category", "Type", "Total", "Count"])
            df_cat["Total"] = df_cat["Total"].apply(lambda x: round(x, 2))
            st.dataframe(df_cat, use_container_width=True, hide_index=True)
        else:
            st.info("No transactions yet.")

    with col2:
        st.subheader("Monthly Trend")
        monthly = agent.bookkeeper.get_monthly_trend()
        if monthly:
            df_m = pd.DataFrame(monthly, columns=["Month", "Type", "Amount"])
            pivot = df_m.pivot_table(index="Month", columns="Type", values="Amount", aggfunc="sum").fillna(0)
            st.bar_chart(pivot)
        else:
            st.info("No data yet.")

# ══════════════════════════════════════════════════════════════════════════════
# ADD TRANSACTION
# ══════════════════════════════════════════════════════════════════════════════
elif page == "➕ Add Transaction":
    st.header("➕ Add Transaction")

    with st.form("add_transaction", clear_on_submit=True):
        col1, col2 = st.columns(2)
        with col1:
            trans_type = st.selectbox("Type", ["expense", "income", "transfer", "adjustment"])
            amount = st.number_input("Amount (₱)", min_value=0.01, step=0.01, format="%.2f")
            date = st.date_input("Date", value=datetime.today())
        with col2:
            description = st.text_input("Description", placeholder="e.g. Office supplies from National Bookstore")
            reference = st.text_input("Reference #", placeholder="e.g. OR-2024-001")
            use_ai = st.checkbox("🤖 AI Auto-Categorize", value=True, help="Use Claude to categorize automatically")

        manual_category = None
        if not use_ai:
            cat_choice = st.selectbox("Category", [e.value for e in ExpenseCategory])
            cat_map = {e.value: e for e in ExpenseCategory}
            manual_category = cat_map[cat_choice]

        submitted = st.form_submit_button("💾 Save Transaction", type="primary", use_container_width=True)

        if submitted:
            if amount <= 0:
                st.error("Amount must be greater than zero.")
            elif not description:
                st.error("Please enter a description.")
            else:
                type_map = {
                    "expense": TransactionType.EXPENSE,
                    "income": TransactionType.INCOME,
                    "transfer": TransactionType.TRANSFER,
                    "adjustment": TransactionType.ADJUSTMENT,
                }
                with st.spinner("🤖 AI is categorizing..." if use_ai else "Saving..."):
                    if use_ai:
                        txn = agent.process_transaction(
                            trans_type=type_map[trans_type],
                            amount=amount,
                            description=description,
                            date=date.strftime("%Y-%m-%d"),
                            reference=reference,
                            use_ai_categorization=True,
                        )
                    else:
                        txn = agent.bookkeeper.process_transaction(
                            trans_type=type_map[trans_type],
                            amount=amount,
                            category=manual_category,
                            description=description,
                            date=date.strftime("%Y-%m-%d"),
                            reference=reference,
                        )

                if txn:
                    cat_val = txn.category.value if txn.category else "Uncategorized"
                    st.success(f"✅ Transaction #{txn.id} saved! Category: **{cat_val}**")
                    if txn.ai_notes:
                        st.info(f"🤖 AI Note: {txn.ai_notes}")
                else:
                    st.error("Failed to save transaction.")

# ══════════════════════════════════════════════════════════════════════════════
# TRANSACTIONS LIST
# ══════════════════════════════════════════════════════════════════════════════
elif page == "📋 Transactions":
    st.header("📋 Transactions")

    transactions = agent.bookkeeper.get_transactions(limit=500)

    if not transactions:
        st.info("No transactions recorded yet.")
    else:
        df = pd.DataFrame(transactions)
        df["amount"] = df["amount"].apply(lambda x: f"₱{x:,.2f}")

        # Filters
        col1, col2 = st.columns(2)
        with col1:
            type_filter = st.multiselect("Filter by Type", ["income", "expense", "transfer", "adjustment"])
        with col2:
            cat_filter = st.multiselect("Filter by Category", df["category"].dropna().unique().tolist())

        if type_filter:
            df = df[df["type"].isin(type_filter)]
        if cat_filter:
            df = df[df["category"].isin(cat_filter)]

        st.dataframe(
            df[["id", "date", "type", "amount", "category", "description", "reference", "ai_notes"]],
            use_container_width=True,
            hide_index=True,
        )

        # Export
        col1, col2 = st.columns([1, 4])
        with col1:
            raw = agent.bookkeeper.get_transactions(limit=10000)
            if raw:
                csv_buf = io.StringIO()
                import csv as csv_mod
                writer = csv_mod.DictWriter(csv_buf, fieldnames=raw[0].keys())
                writer.writeheader()
                writer.writerows(raw)
                st.download_button(
                    "⬇️ Export CSV",
                    csv_buf.getvalue(),
                    file_name=f"transactions_{datetime.today().strftime('%Y%m%d')}.csv",
                    mime="text/csv",
                )

# ══════════════════════════════════════════════════════════════════════════════
# AI CHAT ASSISTANT
# ══════════════════════════════════════════════════════════════════════════════
elif page == "💬 AI Assistant":
    st.header("💬 AI Bookkeeping Assistant")
    st.caption("Ask anything about your finances, BIR compliance, accounting best practices...")

    # Display history
    for msg in st.session_state.chat_messages:
        with st.chat_message(msg["role"]):
            st.markdown(msg["content"])

    if prompt := st.chat_input("Ask your bookkeeping question..."):
        st.session_state.chat_messages.append({"role": "user", "content": prompt})
        with st.chat_message("user"):
            st.markdown(prompt)

        with st.chat_message("assistant"):
            with st.spinner("Thinking..."):
                reply = agent.chat(prompt)
            st.markdown(reply)
            st.session_state.chat_messages.append({"role": "assistant", "content": reply})

    if st.button("🗑️ Clear Chat"):
        st.session_state.chat_messages = []
        agent.clear_chat()
        st.rerun()

# ══════════════════════════════════════════════════════════════════════════════
# INSIGHTS
# ══════════════════════════════════════════════════════════════════════════════
elif page == "📈 Insights":
    st.header("📈 AI Financial Insights")
    st.caption("Claude will analyze your transactions and provide actionable recommendations.")

    if st.button("🔍 Generate Insights", type="primary"):
        with st.spinner("Analyzing your finances with Claude..."):
            insights = agent.generate_insights()
        st.markdown(insights)
    else:
        st.info("Click **Generate Insights** to get AI-powered recommendations based on your transaction data.")
