# CrownAuto Insurance AI — Multi-Agent Car Insurance Assistant

A chat assistant for a Canadian auto insurer. It runs locally: Python with FastAPI and LangGraph on the back end, and a browser chat UI on the front end.

## Business case study

> CrownAuto Insurance is a fictional company. The operating figures below are illustrative assumptions for a mid-sized Canadian insurer, not real data.

### Situation

CrownAuto insures about **200,000 policyholders** across Canada. Its service team handles thousands of interactions a day, almost all of them one of three types:

| Type | Examples | Today |
|---|---|---|
| **Quote requests** | "How much to insure my Honda Civic?" | A long form, then a callback. **24–48 hours**, and many prospects go to a competitor. |
| **Claims** | "I hit a guardrail on the highway." | Body shop visit, appraiser, paperwork. **7–14 days.** |
| **Policy questions** | "Is flood damage covered?" | Every call needs a trained agent. **22-minute average queue.** |

Agents spend **6–8 hours a day** on this work, most of which follows predictable steps. Each interaction costs about **$8**.

### Task

Build a working prototype of an AI assistant that:

1. **Handles routine quotes, claims and policy questions in one chat conversation**, around the clock.
2. **Gets the money right every time**, using CrownAuto's own rating and claim rules rather than figures made up by an AI model.
3. **Answers from CrownAuto's policy documents** and says when they don't cover a question.
4. **Hands complex cases to people**: large repairs, total losses and fraud concerns.
5. **Shows its work**, so staff can audit and trust each answer.

### Action

- **One supervisor, three specialists.** A supervisor agent (built with LangGraph) routes each message to a **Quote**, **Claims** or **Policy Q&A** agent. Each one has a focused prompt and only the tools for its own job.
- **Calculations live in code, not in the AI model.** Premiums, Actual Cash Value (ACV), deductibles, total-loss rules and payouts are tested Python functions. The model decides *when* to call them; the code produces the numbers.
- **Instant quotes.** The Quote agent asks for three or four details and returns three plans side by side. It explains when an option isn't available.
- **Photo-based claims.** A vision model estimates the damage and repair cost from the customer's photo. The Claims agent then verifies the policy and calculates the payout and the customer's out-of-pocket cost.
- **Answers from the documents.** Policy wording, provincial guidelines and FAQs are indexed in a vector database (ChromaDB). The Policy Q&A agent answers from what it finds and cites the source.
- **Built-in escalation.** Repairs over $5,000 trigger an appraiser inspection, and likely total losses are flagged.
- **Transparent and extensible.** The chat UI streams each step and labels every answer with the agent and tools used. The code is split into layers and tested, so the mock policy database and vehicle catalogue can be replaced with real systems without changing the agents.

### Result

**What the prototype delivers today**

- A quote, a first notice of loss (FNOL) with a damage estimate, or an answer from the policy documents, **in one chat conversation**.
- **Repeatable pricing.** For example, a 2-year-old Honda Civic with one claim-free year is always quoted at **$998 / $1,497 / $1,587** for the three plans.
- **50 automated tests** covering the business rules, the multi-turn agent flow and the API, all running without an API key.

**Projected business impact (targets to confirm in a pilot)**

| Metric | Today | Target |
|---|---|---|
| Routine interactions handled without an agent | 0% | **70–80%** |
| Quote turnaround | 24–48 hours | **Under 1 minute** |
| Claim intake to payout estimate | 7–14 days | **Minutes** (complex cases still go to an adjuster) |
| Policy question wait | 22 minutes | **Seconds** |
| Cost per routine interaction | ~$8 | **Under $0.10** in model costs |

This frees the service team to focus on complex claims, fraud investigation and key customer relationships.

### Lessons learned and next steps

- **Narrow agents beat one big agent.** Giving each specialist only its own tools made its behaviour easier to predict and debug.
- **Keep money out of the model.** Rules in tested code give consistent quotes and payouts that compliance staff can review.
- **Follow-ups need context.** A reply like "POL-2026-12345" only makes sense with the previous turn, so the supervisor considers which agent handled it.
- **Before production:** connect the real rating engine and policy database, store conversations durably, add identity checks, track each answer and its cost, and run a pilot to measure the targets above.

---

## Overview

A LangGraph **supervisor** sends each message to one of three specialist agents:

| Agent | Tools | Does |
|---|---|---|
| **Quote** | `vehicle_lookup`, `calculate_premium`, `postal_code_risk` | Gives an instant 3-plan quote (Canadian rating model) |
| **Claims** | `verify_policy`, `analyze_damage_image` (vision), `estimate_payout` | Takes the first notice of loss (FNOL): checks the policy, reads the photo, estimates the payout |
| **Policy Q&A** | `policy_kb_search` (RAG over ChromaDB) | Answers from the policy and provincial-rule documents, citing the source |

The browser UI streams each step live (routing, then each tool call, then the reply). It also shows which agent answered and which tools ran, lets you attach a damage photo, and has starter prompts.

## Quick start (Windows / macOS / Linux)

Requires [uv](https://docs.astral.sh/uv/). It runs on Python 3.12 (3.14 is not supported yet by chromadb's dependencies).

```bash
uv sync                       # creates .venv with Python 3.12 + deps
cp .env.example .env          # then put your OPENAI_API_KEY in .env
uv run uvicorn app.main:app --reload
```

Open http://127.0.0.1:8000.

The first policy question embeds the knowledge base into `data/chroma/`. This takes about a second and costs a fraction of a cent. After that the index is reused, and it is rebuilt automatically if `app/knowledge/documents.py` changes.

### Using a different model

The model names come from `.env`. With a non-reasoning model such as `gpt-4o-mini`, set the three `*_REASONING_EFFORT` values to empty:

```ini
CHAT_MODEL=gpt-4o-mini
VISION_MODEL=gpt-4o-mini
ROUTER_REASONING_EFFORT=
VISION_REASONING_EFFORT=
AGENT_REASONING_EFFORT=
```

## Tests

```bash
uv run pytest
```

All tests run offline with no API key, and they never call OpenAI even if your `.env` has a key. A scripted `FakeChatModel` in `tests/conftest.py` stands in for the LLM.

| Folder | What it tests |
|---|---|
| `tests/unit/` | Business rules (the reference $998 / $1,497 / $1,587 Civic quote, payouts, ACV), the tool executor, routing, chunking |
| `tests/integration/` | Full multi-turn conversations through the real graph: quote, then photo claim, then policy question |
| `tests/api/` | HTTP endpoints through FastAPI's `TestClient`: validation, JSON reply, SSE stream |

## Architecture

The code is split into **layers**. Each layer only imports from the layers *below* it, never above. So business rules don't know about LLMs, and agents don't know about HTTP.

```
 ┌───────────────────────────────────────────────────────────────┐
 │ api/        HTTP: routes, request/response schemas, uploads   │  ← FastAPI lives only here
 ├───────────────────────────────────────────────────────────────┤
 │ services/   Use cases: "run one chat turn", "reset a chat"    │
 ├───────────────────────────────────────────────────────────────┤
 │ workflow/   LangGraph: wires agents + tools into a graph      │
 ├───────────────────────────────────────────────────────────────┤
 │ agents/     Supervisor + 3 specialists, their prompts, state  │
 ├───────────────────────────────────────────────────────────────┤
 │ tools/      Functions the LLM may call (@tool wrappers)       │
 ├──────────────────────────────┬────────────────────────────────┤
 │ knowledge/  KB docs + Chroma │ llm/  model factory, JSON parse│
 ├──────────────────────────────┴────────────────────────────────┤
 │ domain/     Pure business rules — no frameworks, no I/O       │  ← easiest to test
 ├───────────────────────────────────────────────────────────────┤
 │ core/       Settings (.env)                                   │
 └───────────────────────────────────────────────────────────────┘
```

### Project layout

```
app/
├── main.py                  create_app(): builds ChatService at startup, adds routers, serves UI
├── core/config.py           Settings class (pydantic-settings) + get_settings()
├── domain/                  Pure Python business rules
│   ├── pricing.py           ACV, mandatory premium, calculate_premium, get_three_quotes
│   ├── vehicles.py          Vehicle catalogue + fuzzy lookup
│   ├── territory.py         Postal-code risk tiers
│   └── claims.py            verify_policy, estimate_payout
├── llm/
│   ├── factory.py           get_chat_model("router" | "agent" | "vision"), get_embeddings()
│   └── parsing.py           parse_json_response() — strips ```json fences
├── knowledge/
│   ├── documents.py         The 3 policy documents
│   └── vector_store.py      PolicyVectorStore: chunk → embed → store → search
├── tools/
│   ├── quote_tools.py       vehicle_lookup, calculate_premium, postal_code_risk
│   ├── claims_tools.py      verify_policy, analyze_damage_image (vision), estimate_payout
│   ├── policy_tools.py      policy_kb_search (RAG)
│   └── __init__.py          Tool lists per agent + TOOL_REGISTRY
├── agents/
│   ├── state.py             AgentState (the shared conversation state)
│   ├── prompts.py           Every system prompt in one place
│   ├── supervisor.py        Intent router
│   └── specialists.py       Quote / Claims / Policy Q&A agent nodes
├── workflow/
│   ├── tool_executor.py     Runs requested tools (injects the uploaded photo)
│   └── graph.py             build_graph(): nodes + edges + checkpointer
├── services/
│   └── chat_service.py      ChatService.stream() / send() / reset()
└── api/
    ├── routes/chat.py       POST /api/chat, POST /api/chat/stream, DELETE /api/session/{id}
    ├── routes/health.py     GET /api/health
    ├── forms.py             Validates the chat form + photo upload
    ├── schemas.py           Request/response models
    └── dependencies.py      get_chat_service() for Depends(...)
static/                      Chat UI: index.html, styles.css, app.js (no build step)
tests/                       unit/, integration/, api/ + conftest.py (FakeChatModel)
```

### How one message flows through the code

1. **`static/app.js`** posts the form (text + optional photo) to `POST /api/chat/stream`.
2. **`api/forms.py`** validates the input: message not empty, image type and size OK. It turns the photo into a data URL.
3. **`api/routes/chat.py`** gets the `ChatService` through `Depends(get_chat_service)` and calls `service.stream(...)`.
4. **`services/chat_service.py`** runs the graph for that `session_id` and converts each finished node into a small event (`route`, `tool_call`, `tool_result`, `final`).
5. **`workflow/graph.py`** runs the nodes in order:
   ```
   START → supervisor ─┬─▶ quote ─────┐
                       ├─▶ claims ────┼─▶ tools ─▶ back to the same agent
                       └─▶ policy_qa ─┘
                         (no tool calls) ─▶ END
   ```
6. **`agents/supervisor.py`** picks the specialist. The **agent** in `agents/specialists.py` calls the LLM, which either replies or asks for tools.
7. **`workflow/tool_executor.py`** runs the requested tools from `tools/`. These call `domain/` for the maths, or `knowledge/` for RAG. The agent then sees the results.
8. The events stream back to the browser over SSE, and the UI draws the badges and the reply.

### Where do I change…?

| I want to… | Edit |
|---|---|
| Change premium rates, discounts or payout rules | `app/domain/pricing.py`, `app/domain/claims.py` |
| Add a vehicle | `VEHICLE_CATALOG` in `app/domain/vehicles.py` |
| Change how an agent behaves or talks | `app/agents/prompts.py` |
| Add or edit policy documents for RAG | `app/knowledge/documents.py` (the index rebuilds automatically) |
| Add a new tool | Write it in the matching `app/tools/*_tools.py` and add it to that file's tool list |
| Add a new specialist agent | Prompt in `prompts.py`, node in `specialists.py`, an intent in `state.py` (`INTENT_TO_AGENT`), register it in `AGENT_NODES` in `workflow/graph.py`, and describe it in `SUPERVISOR_PROMPT` |
| Switch models or reasoning effort | `.env` (see `app/core/config.py` for all settings) |
| Save chats across restarts | Pass a SQLite or Postgres checkpointer to `build_graph()` in `app/main.py` |
| Add an endpoint | A new router in `app/api/routes/`, included in `create_app()` |

### Design choices

- **Business rules have no dependencies.** `domain/` is plain Python, so the money maths is unit-tested without LLMs or a server.
- **Dependency injection.** `ChatService` receives its graph as a parameter instead of creating one, and routes receive the service through `Depends`. Tests can swap either one easily.
- **One place for each concern.** Model clients are only created in `llm/factory.py`, prompts only live in `agents/prompts.py`, and settings only come from `core/config.py`.
- **Thin routes.** Routes validate, call a service and return. The logic lives in services and below.

## API

| Method | Path | Body | Returns |
|---|---|---|---|
| `GET` | `/api/health` | — | Server status, whether a key is set, model names |
| `POST` | `/api/chat/stream` | form: `message`, `session_id`, optional `image` | Server-Sent Events: `route`, `tool_call`, `tool_result`, `final` / `error` |
| `POST` | `/api/chat` | same | JSON `{reply, intent, agent, tools_used}` |
| `DELETE` | `/api/session/{id}` | — | Deletes that conversation's saved state |

Example:

```bash
curl -N -X POST localhost:8000/api/chat/stream -F session_id=demo -F message="Is flood damage covered?"
curl -X POST localhost:8000/api/chat -F session_id=demo2 -F message="I had an accident, policy POL-2026-12345" -F image=@damage.jpg
```

## Rating model

All figures are in CAD. The model is defined in `app/domain/pricing.py` and `app/domain/claims.py`.

```
ACV                = MSRP × (1 − depreciation by age: 10% … 53%, 60% after 5 years)
Mandatory premium  = $1,050 car / $1,150 SUV / $1,300 pickup
Physical damage    = ACV × 2.5%            (Collision & Comprehensive plans)
Claims-free disc.  = (Mandatory + Physical damage) × 5% per claim-free year, max 25%
Waiver of Dep.     = flat $90 / year       (cars up to 2 years old)
Total              = Mandatory + Physical damage − discount + Waiver   (no GST/HST)
```

Every quote shows three plans: **Mandatory Coverage Only**, **+ Collision & Comprehensive**, and **+ Waiver of Depreciation**.

For claims, a repair pays the repair cost minus the deductible. If the repair costs more than 75% of ACV, the car is a total loss and is paid at ACV minus the deductible (or the purchase price, with Waiver of Depreciation). Repairs over $5,000 need an appraiser inspection.

## Behaviour

- **Photo routing:** a photo uploaded with a message always goes to the Claims agent. The photo stays in the conversation, so Claims can analyse it on a later turn, but later messages are routed normally.
- **Follow-ups stay with the same agent:** the supervisor sees which agent handled the last turn and its last reply. Short answers like a policy number or "which plan is best?" stay with that agent.
- **Safety limits:** each turn has a step limit (`GRAPH_RECURSION_LIMIT`). The message history is cleaned before each LLM call, so a failed tool call can't break the rest of the conversation.
- **Images stay out of the prompt:** the Claims agent passes a placeholder, and the tool executor swaps in the uploaded photo. Image bytes never enter the chat history or the UI events.

## Notes

- Conversations are held in memory (`MemorySaver`) and are lost when the server restarts. For durable sessions, swap in `langgraph-checkpoint-sqlite` or `PostgresSaver` and pass it to `build_graph()` in `app/main.py`.
- Premiums and payouts are **illustrative**. This is not a real rating engine.
- Policy verification is mocked: any `POL-YYYY-NNNNN` number returns an active policy with ACV $28,000 and a $500 deductible.
