<div align="center">

<img src="./assets/vestra-banner.png" alt="Vestra Banner" width="100%">

# 🚀 VESTRA
### AI Wealth Operating System & Digital Chief Investment Officer

[![FastAPI](https://img.shields.io/badge/FastAPI-009688?style=for-the-badge&logo=fastapi&logoColor=white)](https://fastapi.tiangolo.com/)
[![Next.js](https://img.shields.io/badge/Next.js_15-000000?style=for-the-badge&logo=next.js&logoColor=white)](https://nextjs.org/)
[![MongoDB Atlas](https://img.shields.io/badge/MongoDB-4EA94B?style=for-the-badge&logo=mongodb&logoColor=white)](https://www.mongodb.com/)
[![LangGraph](https://img.shields.io/badge/LangGraph-000000?style=for-the-badge&logo=langchain&logoColor=white)](https://langchain-ai.github.io/langgraph/)
[![Docker](https://img.shields.io/badge/Docker-2496ED?style=for-the-badge&logo=docker&logoColor=white)](https://www.docker.com/)
[![Groq](https://img.shields.io/badge/Groq_LLM-F55036?style=for-the-badge&logo=groq&logoColor=white)](https://groq.com/)

**Research · Risk Analysis · Simulation · AI Reasoning · Human Approval · Autonomous Execution · Continuous Learning**

</div>

---

## 📖 Overview

**Vestra** is a production-grade, multi-agent fintech platform that acts as a **Digital Chief Investment Officer (CIO)** for retail investors in the Indian market.

Most AI finance tools deliver isolated stock picks. Vestra replaces reactive, emotion-driven trading with a structured, end-to-end AI pipeline — from signal detection to trade execution — with human approval at every critical decision point.

| Traditional Flow | Vestra Flow |
|---|---|
| News → Panic → Random Trade → Regret | Market Event → Research → Risk Analysis → Simulation → AI Reasoning → Human Approval → Execution → Learning |

---

## ✨ Key Features

### 🧠 15-Agent Strategy Council
Vestra replaces the monolithic prompt with a council of specialized agents, each owning a discrete phase of the investment lifecycle — from Signal Detection through Audit and Continuous Learning.

### 📊 Portfolio Health Engine
Dynamically computes a **Portfolio Health Score (0–100)** across:
- Diversification & Liquidity
- Sector Concentration Risk
- Volatility Metrics
- Base-case and Worst-case Scenario Simulations
- Goal Alignment Scoring

### 🧑‍💼 Digital Twin Investor Profiling
Vestra models *you*, not just the market:
- Income, Expenses, and Active SIPs
- Outstanding Loans and Emergency Fund Status
- Risk Tolerance Levels
- Goal-Based Investing (Retirement, Real Estate, Wealth Creation)

### 🛡️ Human-in-the-Loop Governance
No rogue AI trading. Every recommendation requires explicit human consent:
- **Telegram Approvals** — detailed AI summaries delivered to your phone
- **Audit Trails** — full decision traceability logged per workflow run
- **Paper Trading Only** — real-money execution is intentionally disabled for safety

### ⚡ OpenClaw Execution Layer
Browser automation to interface with Indian broker platforms (Zerodha, Groww, Upstox, Angel One) — operating strictly in demo/paper mode.

### 🖥️ Agent Reasoning Dashboard
A transparent interface exposing *why* the AI made each decision — Strategy Debate logs, Simulation Results, and Confidence Scores all visible in real time.

---

## 🏗️ System Architecture

```mermaid
graph TD
    A[Market Event Detected] --> B[Signal Agent]
    B --> C[Research Agent]
    C --> D[Market Regime Agent]
    D --> E[Risk Agent]
    E --> F[Simulation Agent]
    F --> G[Strategy Council]
    G --> H[CIO Agent]
    H --> I[Reflection Agent]
    I --> J[Confidence Agent]
    J --> K[Validator Agent]
    K --> L[Approval Agent]
    L --> M{Human Decision}
    M -->|Approved| N[Execution Agent]
    M -->|Rejected| O[Audit Agent]
    N --> O
    O --> P[Memory Agent]
    P --> Q[Learning Agent]
```

---

## 💻 Technology Stack

| Category | Technologies |
|---|---|
| **Frontend** | Next.js 15, React, TypeScript, Tailwind CSS, shadcn/ui |
| **Backend** | FastAPI, Python 3.12, Pydantic, JWT Authentication |
| **Database** | MongoDB Atlas |
| **AI Orchestration** | LangGraph (Multi-Agent DAG), Groq LLM API |
| **Execution Layer** | OpenClaw (Browser Automation) |
| **Infrastructure** | Docker, Docker Compose, Railway |

---

## 📂 Repository Structure

```
VESTRA/
├── assets/                    # Platform imagery and screenshots
│   ├── vestra-banner.png
│   ├── dashboard.png
│   └── telegram-approval.png
├── backend/                   # FastAPI Core Server
│   ├── agents/                # LangGraph specialized agents (15 agents)
│   ├── api/                   # RESTful Endpoints
│   ├── core/                  # Security, config, middleware
│   ├── models/                # MongoDB schemas & Pydantic models
│   ├── services/              # External integrations (Telegram, OpenClaw)
│   └── tests/                 # Pytest suite
├── frontend/                  # Next.js 15 Application
│   ├── app/                   # App Router pages
│   ├── components/            # UI Components (shadcn/ui)
│   └── lib/                   # Utilities and API clients
├── docker-compose.yml
└── Dockerfile
```

---

## 🚀 Getting Started

### Prerequisites

- Docker and Docker Compose
- MongoDB Atlas cluster URI
- Groq API Key
- Telegram Bot Token (via [@BotFather](https://t.me/BotFather))

### 1. Clone the Repository

```bash
git clone https://github.com/vidorc/VESTRA.git
cd VESTRA
```

### 2. Configure Environment Variables

**Backend** — `backend/.env`
```env
GROQ_API_KEY=gsk_your_groq_api_key
MONGODB_URI=mongodb+srv://user:password@cluster.mongodb.net/vestra
TELEGRAM_BOT_TOKEN=your_telegram_bot_token
JWT_SECRET=your_super_secret_jwt_key
```

**Frontend** — `frontend/.env.local`
```env
NEXT_PUBLIC_API_URL=http://localhost:8000
```

### 3. Start with Docker

```bash
docker compose up --build
```

| Service | URL |
|---|---|
| Frontend | http://localhost:3000 |
| Backend API | http://localhost:8000 |
| Swagger Docs | http://localhost:8000/docs |

---

## 🎬 Demo Walkthrough

1. Open the Vestra Dashboard at `http://localhost:3000`
2. Trigger a Market Event simulation — e.g. *"RBI increases repo rate by 50bps"*
3. Watch the 15-agent pipeline execute in real time:

| Stage | Agent(s) | Output |
|---|---|---|
| 1 | Signal + Research | Macroeconomic impact parsed |
| 2 | Market Regime + Risk | Portfolio concentration evaluated |
| 3 | Simulation | Base-case and worst-case scenarios modeled |
| 4 | Strategy Council + CIO | Rebalancing recommendation issued |
| 5 | Reflection + Confidence | Recommendation challenged and scored |
| 6 | Validator + Approval | Policy check → Telegram notification sent |
| 7 | Execution | Paper-trade simulation run on approval |
| 8 | Audit + Memory | Full workflow log recorded |

---

## 🧪 Testing

```bash
cd backend
pytest
```

**Coverage includes:**
- Multi-Agent LangGraph orchestration
- Portfolio Health Engine calculations
- Telegram webhook integration
- Scenario simulation logic

---

## 📸 Screenshots

<details>
<summary><b>Click to expand platform screenshots</b></summary>
<br>

**Agent Reasoning Dashboard**
<img src="./assets/dashboard.png" alt="Agent Reasoning Dashboard" width="100%">

**Telegram Approval Workflow**
<img src="./assets/telegram-approval.png" alt="Telegram Approval" width="100%">

**Portfolio Health Monitoring**
<img src="./assets/portfolio-health.png" alt="Portfolio Health" width="100%">

</details>

---

## 🛣️ Roadmap

### ✅ Completed
- [x] 15-Agent LangGraph architecture
- [x] Portfolio Health Engine with scenario simulation
- [x] Digital Twin investor profiling
- [x] Goal-based investing framework
- [x] Telegram human-in-the-loop approval workflows
- [x] Agent Reasoning Dashboard
- [x] Reflection + Confidence + Validator agents
- [x] MongoDB Atlas integration
- [x] JWT Authentication
- [x] Docker containerization

### 🚧 In Progress
- [ ] OpenClaw execution automation enhancements
- [ ] Advanced portfolio analytics & visualizations
- [ ] NSE real-time market intelligence feed

### 🔮 Planned
- [ ] Real-time NSE/BSE data integration
- [ ] Institutional portfolio features
- [ ] Global market support
- [ ] Deep Memory & Continuous Learning System
- [ ] Voice interface

---

## 📈 What This Demonstrates

| Competency | Implementation |
|---|---|
| **AI System Design** | Production multi-agent LangGraph pipelines with DAG orchestration |
| **Full-Stack Fintech** | Secure React dashboards backed by FastAPI with JWT auth |
| **Human-in-the-Loop** | Telegram approval workflows with full audit traceability |
| **Risk Modeling** | Quantitative portfolio health scoring with scenario simulation |
| **Platform Engineering** | Dockerized, Railway-deployable architecture |

---

## 👨‍💻 Author

**Mayank Sharma**
- GitHub: [@vidorc](https://github.com/vidorc)
- LinkedIn: [Mayank Sharma](https://linkedin.com/in/mayank-sharma)

---

## 📄 License & Disclaimer

This project is licensed under the **MIT License**.

> ⚠️ **Disclaimer:** Vestra is an educational and experimental project. It does not constitute financial advice. Real-money trading functionality is intentionally disabled. The platform operates strictly in **Paper Trading / Demo mode** to ensure safety and regulatory compliance.
