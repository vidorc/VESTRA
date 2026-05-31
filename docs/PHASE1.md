# Phase 1 — Intelligence & Human Approval

Phase 1 adds the research/reflection/confidence intelligence layer and a
human-in-the-loop approval workflow (Telegram + REST) on top of the Phase 0
foundation, **extending** the existing LangGraph pipeline rather than replacing it.

## Workflow

```
signal → research → risk → strategy → reflection → confidence → validate
    validate --(approved)--> approval --(approved | auto)--> execute → END
             \--(rejected)-> reject  --(human reject)------> reject  → END
```

New nodes:

| Node | File | LLM? | Output |
|---|---|---|---|
| research | `app/agent/nodes/research.py` | yes | `ResearchContext` (sentiment, news, sector impact, history, conditions, `data_completeness`) |
| reflection | `app/agent/nodes/reflection.py` | yes | `ReflectionResult` (is_logical, assumptions, missing_data, better_alternative, verdict) |
| confidence | `app/agent/nodes/confidence.py` | **no (rule-based)** | `ConfidenceScore` (decision/risk/data + overall) |
| approval | `app/agent/nodes/approval.py` | no | gate: auto-execute or `interrupt()` for human sign-off |

`confidence` is deliberately deterministic — cheap, reproducible, and auditable,
which matters for the `auto_below_threshold` policy and for fintech traceability.

## Approval policies

Set per investor (`investor_profiles.approval_policy`) or globally via
`APPROVAL_POLICY_DEFAULT`:

| Policy | Behavior |
|---|---|
| `manual` | Always require human approval for non-HOLD trades. |
| `approval_required` | Require approval for any non-HOLD trade (default). |
| `auto_below_threshold` | Auto-execute only when `confidence.overall ≥ CONFIDENCE_THRESHOLD` **and** concentration risk is below `RISK_THRESHOLD`; otherwise require approval. |
| `autonomous_sandbox` | Never interrupt (intended for paper/demo execution). |

A `HOLD` decision never requires approval (nothing executes).

## Interrupt / resume mechanics

Human approval uses LangGraph `interrupt()` + a checkpointer
(`app/agent/checkpoint.py`, in-process `MemorySaver` by default).

1. `run_vestra_workflow(user_id, event, event_id=None)` generates a
   `thread_id = "{user_id}:{event_id}"` and runs the graph under a checkpointed
   config.
2. If the approval node interrupts, the call returns the **additive** shape
   `{"status": "pending_approval", "thread_id", "approval_request_id"}`. A
   durable `approval_requests` document (status `pending`) is written to MongoDB.
3. A human decides via the API or Telegram; `resume_workflow(thread_id, approved)`
   continues the run into execute/reject and returns the **legacy** contract.

**Backward compatibility:** runs that do not interrupt return the exact legacy
shape (`success` / `failed` / `rejected`). The webhook fan-out already switches
on `status`, so `pending_approval` is purely additive.

**Re-execution safety:** `interrupt()` re-runs the node body on resume. The
approval-request write is an idempotent upsert keyed by `thread_id`, and the
Telegram notification is gated on first-creation, so the human is pinged exactly
once.

> Known forward-compat note: the checkpointer serializes Pydantic state models.
> On the pinned `langgraph 1.2.1` this works (with a deprecation warning); a
> future langgraph will require registering those types via
> `allowed_msgpack_modules` / `LANGGRAPH_STRICT_MSGPACK`. Tracked for a later bump.

## Telegram approval

Optional — when `TELEGRAM_BOT_TOKEN` is unset the notifier no-ops and approvals
remain fully actionable via the REST API.

Setup:
1. Create a bot with [@BotFather](https://t.me/BotFather); set `TELEGRAM_BOT_TOKEN`.
2. Set a per-user `telegram_chat_id` on the investor profile, or a global
   `TELEGRAM_DEFAULT_CHAT_ID`.
3. Register the webhook so Telegram calls back:
   `https://api.telegram.org/bot<TOKEN>/setWebhook?url=<PUBLIC_URL>/telegram/webhook&secret_token=<TELEGRAM_WEBHOOK_SECRET>`
4. Set the same `TELEGRAM_WEBHOOK_SECRET` in the app env (the webhook enforces it).

Approval messages carry **Approve / Reject** inline buttons; pressing one hits
`POST /telegram/webhook`, which resumes the workflow.

## API

| Method | Path | Auth | Purpose |
|---|---|---|---|
| `GET` | `/approvals?status=pending` | JWT | List the caller's approval requests. |
| `POST` | `/approvals/{id}/decision` | JWT | Approve/reject (ownership-checked); resumes the workflow. Already-decided → 409. |
| `POST` | `/telegram/webhook` | secret header | Telegram inline-button callback → resume. |

## Environment

```
APPROVAL_POLICY_DEFAULT=approval_required
CONFIDENCE_THRESHOLD=0.7
RISK_THRESHOLD=high
TELEGRAM_BOT_TOKEN=
TELEGRAM_DEFAULT_CHAT_ID=
TELEGRAM_WEBHOOK_SECRET=
```

## Tests

- `tests/test_research.py`, `tests/test_reflection.py`, `tests/test_confidence.py`
  — node logic + graceful degradation (LLM mocked via `app.agent.llm.set_llm`).
- `tests/test_approval_workflow.py` — interrupt per policy, resume→execute/reject,
  legacy-shape preservation, research persistence (real graph + `MemorySaver`).
- `tests/test_approvals_api.py` — list/decide, ownership (403), double-decision (409).
- `tests/test_telegram.py` — callback parsing + webhook resume (bot API mocked).
