You are a Principal AI Engineer, Fintech Architect, Staff Backend Engineer, Product Designer, Quant Systems Designer, and Frontend Architect.

Your task is NOT to create a new project.

Your task is to inspect the existing Vestra repository and evolve it into a production-grade autonomous fintech platform.

FIRST ACTION (MANDATORY)

DO NOT GENERATE CODE IMMEDIATELY.

First:

Analyze the entire repository.
Understand existing architecture.
Identify current implementation status.
Create an architecture report.
Identify completed features.
Identify missing components.
Identify technical debt.
Identify scalability issues.
Identify deployment issues.
Identify security issues.

Current repository contains:

app/
 ├── agent/
 │   ├── graph.py
 │   ├── nodes/
 │   │   ├── signal.py
 │   │   ├── risk.py
 │   │   ├── strategy.py
 │   │   ├── validator.py
 │   │   ├── execution.py
 │   │   ├── audit.py
 │   │   └── notifier.py
 │
 ├── mcp/
 │   └── server.py
 │
 ├── models/
 │
 └── main.py

Do not replace this architecture.

Extend it.

PROJECT VISION

Vestra should become:

Bloomberg Terminal
+
Hedge Fund Risk Desk
+
AI Financial Analyst
+
Portfolio Risk Manager
+
Autonomous Execution Agent
+
Research Assistant
+
Personal Wealth Operating System

focused initially on:

Indian Equity Markets
NSE
BSE
Mutual Funds
ETFs
Retail Investors
CORE PRODUCT PHILOSOPHY

Current Vestra:

Event
↓
AI Decision
↓
Simulated Execution

Target Vestra:

Live Markets
↓
Research
↓
Signal Detection
↓
Risk Assessment
↓
Scenario Simulation
↓
Strategy Planning
↓
Reflection
↓
Validation
↓
Human Approval
↓
Execution
↓
Monitoring
↓
Learning
ARCHITECTURAL REQUIREMENTS

Keep LangGraph as orchestration layer.

Keep MongoDB Atlas as memory layer.

Keep FastAPI as API layer.

Keep current agents.

Extend them.

NEW AGENTS TO BUILD
1. Research Agent

Create:

app/agent/nodes/research.py

Responsibilities:

Fetch:

NSE data
Yahoo Finance
Moneycontrol
Economic Times
Company announcements
Earnings information
Macro news

Produce:

ResearchContext

including:

sentiment
relevant_news
sector_impact
historical_context
market_conditions
2. Reflection Agent

Create:

app/agent/nodes/reflection.py

Purpose:

Self-check AI decisions.

Example:

Strategy says:

SELL 10 RELIANCE

Reflection asks:

Is this logical?
What assumptions were made?
What data may be missing?
Would a different strategy be better?

Must return:

ReflectionResult
3. Scenario Simulation Agent

Create:

app/agent/nodes/simulation.py

Generate:

Best case
Base case
Worst case

Calculate:

Portfolio impact
Expected drawdown
Risk score
Potential upside
4. Portfolio Rebalancer Agent

Create:

app/agent/nodes/rebalancer.py

Responsibilities:

Periodic portfolio review.

Detect:

Sector concentration
Allocation drift
Overexposure
Underexposure

Generate rebalance plans.

5. Memory Intelligence Agent

Create:

app/agent/nodes/memory.py

Store:

Past decisions
Past outcomes
Win rate
Execution history
Portfolio evolution

Allow future agents to learn from previous actions.

6. Confidence Agent

Create:

app/agent/nodes/confidence.py

Generate:

Decision confidence score
Risk confidence score
Data completeness score

Used before execution.

HUMAN APPROVAL SYSTEM

Complete notifier.py.

Implement:

Telegram Bot

Capabilities:

trade approvals
trade rejection
portfolio summaries
daily reports
emergency alerts

Flow:

AI recommends
↓
Telegram message
↓
Approve / Reject
↓
Execution
OPENCLAW INTEGRATION

Create:

app/agent/nodes/browser_executor.py

Purpose:

Turn decisions into actions.

Responsibilities:

browser automation
login flows
workflow execution
screenshot capture
audit proof generation

Support:

Demo Mode
Paper Trading Mode

Architecture:

Decision
↓
Approval
↓
OpenClaw
↓
Execution
↓
Screenshot
↓
Audit Log
AGENT ORCHESTRATION UPGRADE

Current:

Signal
↓
Risk
↓
Strategy
↓
Validator
↓
Execution

Upgrade to:

Signal
↓
Research
↓
Risk
↓
Simulation
↓
Strategy
↓
Reflection
↓
Confidence
↓
Validator
↓
Approval
↓
Execution
↓
Audit
↓
Memory

Implement fully in LangGraph.

DATABASE REDESIGN

Create collections:

investor_profiles
market_events
research_context
trade_decisions
trade_executions
audit_logs
portfolio_snapshots
agent_memories
approval_requests
simulation_results

Design schemas.

Add indexes.

Support future scale.

FRONTEND REQUIREMENTS

Build a world-class frontend.

Framework:

Next.js 15
TypeScript
Tailwind CSS
shadcn/ui
Framer Motion
TanStack Query

Design quality target:

Linear
Stripe Dashboard
Vercel
Bloomberg

NOT:

Student project
UI SYSTEM

Use design system from repository/global instructions if available.

Create:

Dashboard

Show:

Portfolio value
PnL
Risk score
Cash balance
AI confidence
Market Intelligence Screen

Show:

Live events
AI analysis
Research summaries
Sector heatmaps
Agent Reasoning Screen

Visualize:

Signal
Research
Risk
Strategy
Reflection
Validator

Users should see AI thinking process.

Execution Screen

Show:

Pending approvals
Executed trades
Rejected trades
Execution screenshots
Audit Screen

Show:

Every agent action
Timeline
Logs
Decision traces
Portfolio Screen

Show:

Holdings
Allocation
Sector distribution
Risk concentration
VISUAL DESIGN

Requirements:

Dark mode first
Bloomberg-inspired
Financial terminal aesthetic
Glassmorphism where useful
Professional typography
Smooth micro-interactions
High information density
Beautiful charts

Use:

Recharts
TradingView widgets
Tremor
API DESIGN

Build production-grade APIs.

Include:

Auth
RBAC
Portfolio APIs
Research APIs
Execution APIs
Audit APIs
Agent APIs

Document all endpoints.

DEPLOYMENT

Support:

Railway
Docker
Docker Compose
Vercel
Mongo Atlas

Provide:

README
Architecture docs
Deployment docs
SECURITY

Implement:

JWT authentication
Environment validation
Rate limiting
Input validation
Secret management
TESTING

Create:

Unit tests
Integration tests
Agent tests
API tests
Workflow tests

Target:
 The prompt I gave is strong from an engineering perspective, but if your goal is:

Win hackathons
Build something personally useful
Turn it into a startup later
Stand out from generic AI agents

then I'd add the following sections.

1. ADD A FINANCIAL DIGITAL TWIN

This is probably the biggest upgrade.

Most fintech agents react to events.

Instead, create:

Investor Digital Twin

Store:

age
salary
expenses
risk tolerance
goals
loans
SIPs
emergency fund
tax bracket

Then Vestra doesn't just say:

SELL RELIANCE

It says:

You need liquidity in 8 months.
Preserve cash.
Avoid increasing volatility.

This makes decisions personalized.

2. ADD A CHIEF INVESTMENT OFFICER AGENT

Right now:

Signal
Risk
Strategy

Still tactical.

Add:

CIO Agent

Responsibilities:

overall portfolio vision
long-term asset allocation
strategy arbitration

Example:

Strategy agent:

SELL INFY

CIO:

Reject.
Long-term thesis still intact.

Very hedge-fund style.

3. ADD MULTIPLE STRATEGY AGENTS

Instead of one strategy agent.

Create:

Value Investor Agent
Momentum Agent
Risk-Off Agent
Income Agent
Growth Agent

Then:

Planner Agent

collects opinions.

Example:

Value Agent → BUY
Momentum → SELL
Risk-Off → HOLD

Then CIO chooses.

This looks insanely impressive.

4. ADD MARKET REGIME DETECTION

Before strategy.

Agent determines:

Bull Market
Bear Market
Sideways Market
High Volatility
Crisis

Different strategies activate.

Very realistic.

5. ADD LEARNING LOOP

Current:

Decision
Done

Upgrade:

Decision
↓
Outcome
↓
Performance Review
↓
Memory Update

Now Vestra learns.

Store:

successful trades
failed trades
reasoning quality
6. ADD PORTFOLIO HEALTH SCORE

Like a credit score.

Generate:

Portfolio Health = 78/100

Factors:

diversification
concentration
liquidity
drawdown risk
volatility

Users understand this immediately.

7. ADD INDIAN MARKET SPECIALIZATION

Very important.

Most people build generic US-stock demos.

Build:

NSE
BSE
NIFTY50
BANKNIFTY
SENSEX
Indian Mutual Funds
Indian ETFs

Add agents for:

RBI policy
Union Budget
SEBI regulations
Election impacts

This gives differentiation.

8. ADD GOAL-BASED INVESTING

Instead of:

maximize returns

Use:

buy house
retirement
higher education
car
emergency fund

AI aligns portfolio to goals.

Much more useful.

9. ADD VOICE MODE

Future enhancement.

User says:

What should I do with my portfolio?

Vestra responds.

Would look amazing in demos.

10. ADD AN AGENT MARKETPLACE

Far future.

Allow:

Custom Risk Agents
Custom Strategy Agents
Community Agents

Like GPTs for investing.

11. ADD EXECUTIVE DASHBOARD

Not just charts.

Show:

Portfolio Health
Risk Score
AI Confidence
Market Regime
Recent Decisions
Upcoming Risks

This feels premium.

12. ADD A REAL PRODUCT VISION

Tell Claude:

Do NOT build a hackathon project.

Build:

AI Wealth Operating System

Think:

Bloomberg Terminal
+
Personal CFO
+
Portfolio Manager
+
Risk Officer
+
Execution Assistant
MOST IMPORTANT ADDITION TO YOUR PROMPT

Add this paragraph near the top:

Do not treat Vestra as a stock-trading bot.

Treat Vestra as an AI Wealth Operating System.

The system should reason about investor goals, portfolio construction, risk management, market conditions, liquidity needs, long-term planning, and autonomous execution.

Every new component should move Vestra closer to functioning as a digital Chief Investment Officer for an individual investor.

That single paragraph changes the direction of the whole project.

If I were optimizing Vestra for maximum long-term value, I'd prioritize:

1. Research Agent
2. Reflection Agent
3. Market Regime Agent
4. CIO Agent
5. Telegram Approval
6. OpenClaw
7. Digital Twin
8. Portfolio Health Score
9. Goal-Based Investing
10. Frontend

At that point, Vestra stops being "an AI that reacts to stock events" and becomes an AI wealth operating system for Indian retail investors, which is a much bigger and more interesting vision.
80%+ coverage1. Build for Humans, Not Just AI

Tell Claude:

Every AI recommendation must be explainable in plain English.

The user should never need to understand finance jargon, agent architecture, or LLM reasoning to use the system.

Every decision must include:
- Why this recommendation was made
- What risks exist
- Alternative actions
- Confidence score
- Potential upside/downside

Most AI finance projects fail here.

2. Human Override Everywhere

Add:

No autonomous financial action should occur without configurable approval policies.

Users must be able to choose:

- Fully manual
- Approval required
- Auto-execute below risk threshold
- Fully autonomous sandbox mode

This makes it realistic.

3. Portfolio Health Engine

Not just trades.

Create:

Portfolio Health Score (0-100)

Based on:
- diversification
- concentration
- liquidity
- volatility
- drawdown risk
- goal alignment

This becomes a sticky feature.

4. Goal-Based Wealth Planning

Huge addition.

Instead of:

Buy stock
Sell stock

Add:

Goals:
- retirement
- house purchase
- emergency fund
- higher education
- wealth growth

Then every agent reasons against goals.

5. Personal CFO Mode

This is where Vestra becomes much bigger.

Future prompt addition:

Support:
- salary tracking
- SIP tracking
- EMI tracking
- recurring investments
- savings targets
- tax planning

Now it becomes a wealth OS, not a stock bot.

6. Decision Review Agent

Very underrated.

Every week:

Review all decisions made.

Which worked?
Which failed?
Why?

Generate a report.

This creates learning and trust.

7. Risk Stress Testing

Before execution:

What if:
- market drops 5%
- market drops 15%
- RBI surprises markets
- sector crashes

Generate outcome projections.

This is very fintech.

8. Multi-Modal Inputs

Future-proof it.

Allow:

PDF annual reports
Screenshots
News articles
Portfolio exports
Broker statements

Research agent should ingest them.

9. Build an Internal Event Bus

This is a serious architecture upgrade.

Tell Claude:

All agents communicate through events.

Example:

MarketEventDetected
ResearchCompleted
RiskAssessmentGenerated
TradeApproved
TradeExecuted

Makes scaling much easier.

10. Build Agent Observability

Almost nobody does this.

Create:

Agent Monitoring Dashboard

Track:
- execution time
- token usage
- confidence
- failures
- retries

Very impressive technically.

11. Support Multiple Users From Day One

Right now you have:

user_001

Tell Claude:

Design everything as multi-tenant.

No hardcoded users.

Every entity must be scoped by user_id.

Future startup-proofing.

12. Agent Memory Timeline

Not just MongoDB storage.

Create:

Investor Timeline

Jan 10:
Bought RELIANCE

Feb 02:
Portfolio risk increased

Mar 12:
RBI shock handled

Users love this.

13. Build a Trust Layer

Every recommendation should expose:

Confidence: 87%

Evidence:
- News source A
- Market data B
- Portfolio exposure C

This dramatically improves perceived quality.

14. Add "Why Not?" Explanations

Example:

Recommended:
SELL 5 INFY

Why not HOLD?
...
Why not BUY?
...

This feels very advanced.

15. Long-Term Vision Section

Add this at the very top of the prompt:

Vestra is not a stock trading bot.

Vestra is an AI Wealth Operating System.

Its purpose is to function as a digital Chief Investment Officer, Risk Manager, Research Analyst, Financial Planner, and Execution Assistant for retail investors.

Every architectural decision should move the platform toward becoming the operating system through which an individual manages their financial life.

If I were building Vestra for the next 6–12 months, the highest-value roadmap would be:

Phase 1:
Research Agent
Reflection Agent
Telegram Approval

Phase 2:
OpenClaw
Portfolio Health Score
Market Regime Detection

Phase 3:
CIO Agent
Goal-Based Investing
Stress Testing

Phase 4:
Digital Twin
Personal CFO
Learning System

Phase 5:
Frontend
Multi-user SaaS
Broker Integrations

Those additions make Vestra feel less like a hackathon project and more like the foundation of a real fintech product.
The only thing I would still add to the Claude prompt is this hard requirement:

Do not rewrite working code.

First inspect the repository.

Reuse existing architecture.

Extend existing files whenever reasonable.

Preserve current functionality.

Every feature must be production-ready, testable, and documented.

Do not generate placeholder implementations.

This single instruction will save you hours of debugging.