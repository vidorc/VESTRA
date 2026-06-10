<p align="center">
  <a href="https://github.com/vidorc/VESTRA">
    <img src="assets/vestra-banner.png" alt="VESTRA Banner" width="100%">
  </a>
</p>

<h1 align="center">🚀 VESTRA — AI Wealth Operating System</h1>

<p align="center">
  Multi-Agent AI Wealth Platform for Research, Risk Analysis, Portfolio Intelligence, and Autonomous Financial Decision Support.
</p>

<p align="center">
  <img src="https://img.shields.io/badge/Python-3.12-blue" alt="Python">
  <img src="https://img.shields.io/badge/FastAPI-Backend-green" alt="FastAPI">
  <img src="https://img.shields.io/badge/LangGraph-MultiAgent-purple" alt="LangGraph">
  <img src="https://img.shields.io/badge/MongoDB-Database-green" alt="MongoDB">
  <img src="https://img.shields.io/badge/Next.js-Frontend-black" alt="Next.js">
  <img src="https://img.shields.io/badge/License-MIT-yellow" alt="License">
</p>

---

## 📖 Project Description

> A multi-agent AI platform that acts as a digital Chief Investment Officer by researching market events, analyzing portfolio risk, running simulations, validating decisions, obtaining approval, executing actions, and continuously learning from outcomes.

Most AI finance tools provide simple, isolated stock recommendations. Vestra replaces emotional, reactive trading with a structured, intelligent pipeline. It combines market intelligence, digital twin investor profiling, strategy generation, and execution automation into a single, production-ready operating system designed initially for the Indian retail market.

---

## ✨ Key Features

* **Multi-Agent Architecture:** 15 specialized AI agents handle distinct aspects of the investment lifecycle (Signal, Research, Risk, CIO, etc.).
* **Research & Market Intelligence:** Automatically contextualizes market events across NSE, BSE, and global macroeconomics.
* **Portfolio Health Engine:** Scores portfolios (0-100) based on diversification, liquidity, and risk exposure.
* **Risk Management & Simulations:** Runs base and worst-case scenarios before making recommendations.
* **Strategy Council & CIO Agent:** Debates momentum, contrarian, and macro strategies before the CIO Agent makes a final call.
* **Reflection & Confidence Scoring:** AI challenges its own logic and assigns a reliability score to every decision.
* **Telegram Approval Workflow:** Human-in-the-loop validation. No actions are executed without explicit user consent.
* **OpenClaw Automation:** Executes approved actions via browser automation (currently restricted to Paper/Demo trading for safety).
* **Digital Twin Investor Profiles:** Understands your income, expenses, loans, and risk tolerance.
* **Goal-Based Investing:** Optimizes for life goals (Retirement, House Purchase) rather than just chasing yield.
* **Modern Next.js Dashboard:** Provides complete transparency into the AI's reasoning, research, and audit logs.

---

## 🏗️ Architecture Diagram

Vestra's core intelligence lies in its LangGraph-powered pipeline. Specialized agents collaborate to form a digital Strategy Council.

```mermaid
graph TD
    Event[Market Event Detected] --> Signal[Signal Agent]
    Signal -->|Determines Event Severity| Research[Research Agent]
    Research -->|Gathers Market Context| Regime[Market Regime Agent]
    Regime -->|Identifies Bull/Bear State| Risk[Risk Agent]
    Risk -->|Analyzes Portfolio Concentration| Sim[Simulation Agent]
    Sim -->|Runs Scenarios| Council[Strategy Council]
    Council -->|Provides Diverse Perspectives| CIO[CIO Agent]
    CIO -->|Makes Final Recommendation| Reflection[Reflection Agent]
    Reflection -->|Challenges Logic| Conf[Confidence Agent]
    Conf -->|Scores Reliability| Valid[Validator Agent]
    Valid -->|Policy Safety Check| Approv[Approval Agent]
    Approv -->|Telegram Notification| Human{Human Approval}
    Human -->|Approved| Exec[Execution Agent]
    Human -->|Rejected| Audit
    Exec -->|OpenClaw Automation| Audit[Audit Agent]
    Audit -->|Records Traceability| Memory[Memory Agent]
    Memory -->|Stores Outcomes| Learn[Learning Agent]
💻 Tech Stack
Component	Technologies
Frontend	Next.js 15, TypeScript, Tailwind CSS, shadcn/ui
Backend	FastAPI, Python, Pydantic, JWT Auth
AI Layer	Groq LLM, LangGraph (Multi-Agent System)
Database	MongoDB Atlas
Execution	OpenClaw (Browser Automation)
Infrastructure	Docker, Railway, GitHub Actions
📸 Screenshots
(Place your screenshots in the assets/ folder to render them here)

Agent Reasoning Dashboard

Telegram Approval Workflow

Portfolio Health Monitoring

🚀 Getting Started
Prerequisites
Node.js 18+ & Python 3.10+

MongoDB Atlas Cluster URI

Groq API Key

Telegram Bot Token

1. Clone the Repository
Bash
git clone [https://github.com/vidorc/VESTRA.git](https://github.com/vidorc/VESTRA.git)
cd VESTRA
2. Backend Setup
Bash
cd backend
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate
pip install -r requirements.txt
Create a .env file in the backend/ directory:

Code snippet
MONGODB_URI=your_mongodb_connection_string
GROQ_API_KEY=your_groq_api_key
TELEGRAM_BOT_TOKEN=your_telegram_bot_token
JWT_SECRET=your_jwt_secret
Run the FastAPI server:

Bash
uvicorn app.main:app --reload --port 8000
3. Frontend Setup
Bash
cd ../frontend
npm install
Create a .env.local file in the frontend/ directory:

Code snippet
NEXT_PUBLIC_API_URL=http://localhost:8000
Run the Next.js development server:

Bash
npm run dev
Navigate to http://localhost:3000 to view the Vestra Dashboard.

📂 Project Structure
Plaintext
VESTRA/
├── assets/                 # Banner and screenshots
│   └── vestra-banner.png
├── backend/                # FastAPI Application
│   ├── agents/             # LangGraph specialized agents
│   ├── api/                # API routes and endpoints
│   ├── core/               # Security and configuration
│   ├── models/             # MongoDB schemas & Pydantic models
│   └── services/           # External integrations (Telegram, OpenClaw)
├── frontend/               # Next.js Application
│   ├── app/                # App router pages
│   ├── components/         # UI components (shadcn)
│   └── lib/                # Utilities and API clients
└── README.md
🛣️ Roadmap
[x] Multi-Agent LangGraph architecture implementation

[x] Portfolio intelligence & Digital Twin modeling

[x] Telegram Human-in-the-Loop approval workflows

[x] End-to-end auditability and Agent Reasoning Dashboard

[ ] OpenClaw Browser Automation integration

[ ] Real-Time NSE Intelligence integration

[ ] Deep Memory & Continuous Learning System

[ ] Advanced Analytics & Institutional Portfolio Features

🤝 Contributing
Contributions make the open-source community an amazing place to learn, inspire, and create. Any contributions you make are greatly appreciated.

Fork the Project

Create your Feature Branch (git checkout -b feature/AmazingFeature)

Commit your Changes (git commit -m 'Add some AmazingFeature')

Push to the Branch (git push origin feature/AmazingFeature)

Open a Pull Request

👨‍💻 Author
Mayank Sharma

GitHub: vidorc

LinkedIn: Mayank Sharma