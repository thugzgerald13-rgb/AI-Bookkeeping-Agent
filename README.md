# 📒 AI Bookkeeping Agent v2.0

An AI-powered bookkeeping web app for small businesses — built with **Claude (Anthropic)**, **Streamlit**, and **SQLite**.

## ✨ Features

- 🤖 **AI Transaction Categorization** — Claude auto-categorizes every entry
- 💬 **AI Chat Assistant** — Ask bookkeeping & BIR tax questions in plain English
- 📈 **Financial Insights** — AI-generated recommendations from your data
- 📊 **Dashboard** — Income, expense, net balance, monthly trends
- 💾 **SQLite Persistence** — All data saved locally
- ⬇️ **CSV Export** — Download your transactions any time

## 🚀 Quick Start

```bash
# 1. Clone
git clone https://github.com/thugzgerald13-rgb/AI-Bookkeeping-Agent.git
cd AI-Bookkeeping-Agent

# 2. Install
pip install -r requirements.txt

# 3. Configure
cp .env.example .env
# Edit .env and add your ANTHROPIC_API_KEY

# 4. Run
streamlit run src/main.py
```

Open http://localhost:8501

## 🌐 Deploy to Render (Free)

1. Push this repo to GitHub
2. Go to [render.com](https://render.com) → **New Web Service**
3. Connect your GitHub repo
4. Render auto-detects `render.yaml`
5. Set `ANTHROPIC_API_KEY` in **Environment Variables**
6. Click **Deploy**

## 🐳 Deploy with Docker

```bash
docker build -t ai-bookkeeping .
docker run -p 8501:8501 -e ANTHROPIC_API_KEY=sk-ant-... ai-bookkeeping
```

## 🗂️ Project Structure

```
├── config/
│   └── config.py          # App configuration (env-based)
├── src/
│   ├── agent.py           # Claude AI agent (fixed from broken langchain)
│   ├── bookkeeper.py      # Core bookkeeping + SQLite
│   ├── main.py            # Streamlit web app
│   └── utils.py           # Utility functions (fixed escape bug)
├── data/                  # SQLite DB (auto-created)
├── .env.example           # Environment variables template
├── Dockerfile             # Docker deployment
├── render.yaml            # Render.com deployment config
└── requirements.txt
```

## 🔑 Environment Variables

| Variable | Required | Default | Description |
|---|---|---|---|
| `ANTHROPIC_API_KEY` | ✅ | — | Your Claude API key |
| `COMPANY_NAME` | ❌ | My Business | Your business name |
| `CURRENCY` | ❌ | PHP | Currency code |
| `DB_PATH` | ❌ | data/bookkeeping.db | SQLite path |

## 📋 What Was Fixed (v1 → v2)

| File | Issue | Fix |
|---|---|---|
| `agent.py` | `from langchain import LLMFactory, BookkeepingTools` — **doesn't exist** | Replaced with real Anthropic SDK |
| `utils.py` | Stored with literal `\n` escape chars — **completely broken** | Rewrote with proper newlines |
| `main.py` | Just `print()` — **nothing wired** | Full Streamlit multi-page app |
| `bookkeeper.py` | In-memory only, bad timestamp hack | SQLite persistence, proper dataclasses |
| *(missing)* | No `requirements.txt` | Added |
| *(missing)* | No deployment config | Docker + Render |

## License

MIT
