# Repository Full Overview

## 1. Project Overview

Purpose: multi-tenant clinic chat assistant that answers service questions, exposes tenant-specific configuration, guides users toward consultation-first booking, and collects contact details for follow-up.

Technology stack: FastAPI backend, OpenAI Responses API (`gpt-4.1-mini`) for fallback inference, SQLite persistence for lead checkpoints, static HTML/CSS/JS frontend, JSON tenant profiles, and dotenv-based environment loading.

Runtime architecture: the frontend loads a tenant?s public config, opens a session-scoped chat against `/chat`, and the backend resolves tenant configuration, runs deterministic shortcut logic first, falls back to the model when needed, persists booking/contact checkpoints, and returns plain text that the frontend may render as structured lists.

Main services: `/chat` for conversation, `/config/{tenant}` for safe public tenant config, `/agent/{tenant}` for serving the tenant chat UI, `/health` for liveness, `ai_agent.py` for orchestration, `config_loader.py` for tenant validation/exposure, `lead_store.py` for persistence, and `session_trace_logger.py` for optional tracing.

Current implementation focus after Day 4.4

The current implementation focus after Day 4.4 is strict configuration separation: conversation wording, trigger phrases, booking-confirm words, clarification patterns, and cautious fallback behavior now live in tenant JSON, while `backend/app/services/ai_agent.py` stays responsible for orchestration, state transitions, deterministic shortcut routing, repetition awareness, and OpenAI fallback.

## 2. Full Repository Tree

```text
.
|-- README.md
|-- .gitignore
`-- clinic-ai-assistant-src/
    |-- AI_sync/
    |   `-- REPO_FULL_OVERVIEW.md (reference only; excluded from embedded source section)
    |-- backend/
    |   |-- app/
    |   |   |-- main.py
    |   |   |-- config/
    |   |   |   `-- profiles/
    |   |   |       |-- generic.json
    |   |   |       |-- milena_dental.json
    |   |   |       `-- risto.json
    |   |   |-- routes/
    |   |   |   `-- chat.py
    |   |   `-- services/
    |   |       |-- ai_agent.py
    |   |       |-- config_loader.py
    |   |       |-- lead_store.py
    |   |       `-- session_trace_logger.py
    |   `-- tests/
    |       |-- test_chat_flow.py
    |       `-- test_config_loader.py
    |-- configs/
    |   `-- settings.env
    `-- frontend/
        `-- index.html
```

## 3. File Purpose Index

- `README.md` ? Root project status document and Day 4.4 architecture rule reference.
- `.gitignore` ? Repository ignore rules for virtualenvs, database files, traces, and local artifacts.
- `clinic-ai-assistant-src/configs/settings.env` ? Runtime trace toggles used by the session trace logger.
- `clinic-ai-assistant-src/frontend/index.html` ? Single-page chat client that loads tenant config, persists session_id, and renders structured bot lists.
- `clinic-ai-assistant-src/backend/app/main.py` ? FastAPI application bootstrap, CORS setup, static frontend serving, and public config endpoints.
- `clinic-ai-assistant-src/backend/app/routes/chat.py` ? HTTP chat endpoint schema validation and response envelope assembly.
- `clinic-ai-assistant-src/backend/app/services/ai_agent.py` ? Core backend orchestration engine for deterministic routing, OpenAI fallback, sessions, booking, repetition handling, and profile-driven rules.
- `clinic-ai-assistant-src/backend/app/services/config_loader.py` ? Tenant profile loader, validation, and public-profile projection logic.
- `clinic-ai-assistant-src/backend/app/services/lead_store.py` ? SQLite checkpoint persistence for booking/contact collection state.
- `clinic-ai-assistant-src/backend/app/services/session_trace_logger.py` ? Optional per-session trace writer controlled by configs/settings.env.
- `clinic-ai-assistant-src/backend/app/config/profiles/generic.json` ? Base/sample tenant profile with profile-driven reply and conversation rule schema.
- `clinic-ai-assistant-src/backend/app/config/profiles/milena_dental.json` ? Primary Macedonian dental tenant profile with clinical catalog, conversation_rules, and reply_texts.
- `clinic-ai-assistant-src/backend/app/config/profiles/risto.json` ? Secondary sample tenant profile mirroring the profile-driven schema.
- `clinic-ai-assistant-src/backend/tests/test_chat_flow.py` ? Integration-style tests for chat validation, booking transition, and contact collection.
- `clinic-ai-assistant-src/backend/tests/test_config_loader.py` ? Tests for tenant loading and public-config exposure boundaries.
- `clinic-ai-assistant-src/AI_sync/` ? Synchronization-artifact folder; the current overview file is referenced in the tree but intentionally excluded from self-embedding.

## 4. Core Architecture Flow

1. Frontend entry: the browser loads `frontend/index.html` through `/agent/{tenant}`, derives the tenant from the URL, fetches `/config/{tenant}`, shows the tenant greeting, and restores `session_id` from localStorage per tenant.
2. Config loading: `/config/{tenant}` and `/chat` both call `load_profile_config()`; tenant JSON is read from `backend/app/config/profiles`, validated, and then either exposed publicly or used internally.
3. Chat request path: the frontend POSTs `{message, session_id}` to `/chat?tenant=...`; `ChatRequest` trims and validates input, then `generate_reply()` returns `(reply, session_id)` plus `get_session_status()` determines the response status.
4. Backend orchestration: `generate_reply()` loads the profile, builds a model-facing system prompt from business metadata, conversation rules, clinical categories, and flattened services, then processes deterministic logic in order before any model call.
5. Deterministic backend routing: active booking states are handled first, then consultation confirmation prediction, greeting, service clarification, service list requests, explicit price requests, service descriptions, casual social replies, and unknown-detail safety fallback. All relevant trigger/wording inputs are now read from profile JSON.
6. AI call: only when no deterministic path applies, the backend sends the system prompt and user message to `client.responses.create(...)`; the result must parse into the configured JSON output contract.
7. Booking/session flow: bookable service suggestions or predicted consultation confirmations transition through `awaiting_booking_confirmation`, then `_start_collecting_contact()` moves to `collecting_contact`, prompting for `name`, `phone`, and `email` using profile-driven field prompts.
8. Persistence: `lead_store.py` saves checkpoints into SQLite under a unique `(tenant, session_id)` row, and `load_lead_checkpoint()` restores state on subsequent requests; session traces can also be written when enabled by `configs/settings.env`.
9. Response return: `_finalize_reply()` applies repetition-aware reformulation when needed, records recent interaction history in memory, emits session traces, and returns plain text; the frontend converts bullet-formatted bot text into DOM list structures instead of showing one long paragraph.

## 5. Configuration System

Tenant profile locations: tenant JSON files live in `backend/app/config/profiles/` and currently include `generic.json`, `risto.json`, and the primary Macedonian clinic profile `milena_dental.json`.

`configs/settings.env` role: this file does not provide OpenAI credentials; it is read by `session_trace_logger.py` to enable or disable per-session runtime trace files through `USERLOGGING` and `DEBUG_SESSION_TRACE`.

Configuration loading and validation: `config_loader.py` loads raw JSON, validates required sections such as `business`, `prompt_template`, `conversation`, `services`, `actions`, and `output_contract`, and rejects malformed or duplicate service definitions before runtime use.

Public vs internal config exposure: `/config/{tenant}` returns `load_public_profile_config()`, which exposes only safe business/assistant/greeting/service metadata and omits internal prompt rules, output contract details, and full orchestration configuration.

Day 4.4 architecture rule: business wording and trigger configuration were extracted from `ai_agent.py` into tenant JSON under `reply_texts`, `repetition_responses`, and `conversation_rules`; Python now stays focused on engine logic, and onboarding a new business is intended to require only a new profile JSON file following the same schema.

## 6. Session and Booking System

`session_id` lifecycle: if the frontend has no stored session, the backend generates a UUID; the frontend then persists it in localStorage per tenant. If a session is already marked `completed`, the next request rolls to a fresh session ID and clears in-memory repetition history for the old session.

Booking state machine: the backend uses `awaiting_booking_confirmation`, `collecting_contact`, and `completed`. A model-suggested bookable service or a predicted consultation confirmation can start the booking path, after which the backend owns the prompts until contact collection finishes.

Contact field collection: `collect_contact_fields` come from the tenant profile. During `collecting_contact`, the next field is prompted from `reply_texts.field_prompts`. Clarification-like messages are now guarded and do not overwrite collected data; instead the backend returns a profile-driven clarification reply and keeps the same field pending.

Lead persistence and checkpoint recovery: every checkpoint is saved to SQLite with collected contact values and the full serialized state. On later requests, `load_lead_checkpoint()` hydrates state back into memory if needed.

Repetition-aware reply handling: `INTERACTION_HISTORY` stores recent normalized user messages and final replies per session. Similar repeated inputs trigger profile-defined reformulations for broad pricing, service-list repeats, and consultation-explanation repeats.

Consultation prediction / confirmation path: if there is no active booking state but the recent conversation indicates that consultation was just recommended, a confirmation word from profile `conversation_rules.booking_confirm_words` starts consultation booking immediately and moves into contact collection before greeting logic runs.

## 7. Day 4.4 Change Summary

- Backend deterministic behavior was expanded across multiple commits: structured service-list replies, explicit price retrieval from config, casual social-message handling, better greetings, service clarification prompts, explicit-only price disclosure, repetition-aware reformulation, consultation booking prediction, and guarded contact collection.
- `backend/app/services/ai_agent.py` was cleaned up so business wording no longer lives in Python; profile JSON now supplies `reply_texts`, `repetition_responses`, and `conversation_rules`.
- `conversation_rules` was introduced to centralize booking confirmation words, trigger lists, clarification phrases, service-detail safety triggers, casual pattern mappings, and other conversation-level configuration.
- `reply_texts` now drives greeting shortcuts, clarification prompts, field prompts, booking completion wording, contact-clarification replies, service-description templates, and price phrasing.
- Repetition logic remains in Python as engine behavior, but its human wording now comes from JSON per tenant.
- The frontend still renders backend text only, but Day 4.4 preserved the earlier improvement where bullet-formatted service responses are transformed into visible structured HTML lists in the chat UI.
- `README.md` now documents the architecture rule that Python must not contain business configuration and that new tenant onboarding should be done by adding a JSON profile.
- Today?s changes were delivered through a sequence of commits that progressively introduced price rendering, casual handling, trigger coverage, wording polish, repetition awareness, profile-driven reply extraction, safety/booking guards, and final configuration extraction/documentation cleanup.

## 8. Known Risks / Open Follow-ups

- `config_loader.py` validates the core tenant profile structure, but it does not yet deeply validate the newer `conversation_rules`, `reply_texts`, or `repetition_responses` sub-keys; malformed values may fail only at runtime.
- Deterministic safety handling for unsupported treatment details relies on configured trigger heuristics, so unsupported detail questions outside those trigger sets may still reach the model.
- Automated tests currently cover booking/contact flow and config exposure, but they do not yet comprehensively cover the newer profile-driven conversation rules, repetition reformulation variants, or the frontend structured-rendering path.
- Session trace writes are optional and guarded, but local environments without writable trace directories can still produce warnings when tracing is enabled.

## 9. Embedded Source Code

--------------------------------
File: README.md
--------------------------------

```markdown
# Clinic AI Assistant

## Implemented

- FastAPI backend with `/chat`, `/config/{tenant}`, `/agent/{tenant}`, and `/health`
- OpenAI-powered response generation through `client.responses.create(...)`
- JSON tenant profiles loaded from `clinic-ai-assistant-src/backend/app/config/profiles/`
- Lightweight HTML/JS frontend served by the backend
- SQLite-based lead checkpoint persistence
- Booking state machine with these backend states:
  - `awaiting_booking_confirmation`
  - `collecting_contact`
  - `completed`
- Session-based booking continuity with completed-session rollover

## Prototype / In Progress

- Booking flow hardening through canonical intent normalization
- Multi-tenant support beyond the sample tenants
- Frontend session-status awareness
- Localized Macedonian shell text for the default frontend

## Planned

- Broader tenant-specific service catalogs and richer profile validation
- Additional observability and debug tooling
- More complete automated regression coverage
- Stronger deployment and environment hardening

## Architecture Rule

### ARCHITECTURE RULE - CONFIGURATION SEPARATION

1. Python files must never contain:
   - trigger phrases
   - language patterns
   - business wording
   - booking confirmation words
   - fallback texts
2. All such content must exist only inside tenant profile JSON.
3. Onboarding a new business must require only creating a new JSON configuration file.

The backend Python layer is reserved for:
- logic
- routing
- state machine behavior
- orchestration

The tenant profile layer is reserved for:
- reply wording
- trigger lists
- conversation rules
- catalog content
- booking/contact prompts

## Day 4.4

### DAY 4.4 ARCHITECTURE RULE CONFIRMATION

- Configuration has been extracted from `ai_agent.py` into tenant profile JSON.
- Python now loads conversation rules dynamically from profile JSON.
- The rule `NO CONFIGURATION IN PYTHON` is active and should be reviewed before any future backend change.

```

--------------------------------
File: .gitignore
--------------------------------

```gitignore
.venv/
__pycache__/
*.pyc
.env
.vscode/
*.db
clinic-ai-assistant-src/backend/clinic_ai_assistant.db
.pytest_cache/
**/runtime_traces/
FollowUpWithAris.txt
```

--------------------------------
File: clinic-ai-assistant-src/configs/settings.env
--------------------------------

```env
USERLOGGING=on
DEBUG_SESSION_TRACE=true
```

--------------------------------
File: clinic-ai-assistant-src/frontend/index.html
--------------------------------

```html
<!DOCTYPE html>
<html lang="mk">
<head>
  <meta charset="UTF-8" />
  <meta name="viewport" content="width=device-width, initial-scale=1.0" />
  <link rel="icon" href="/frontend/favicon.ico">
  <title id="pageTitle">Се вчитува...</title>
  <style>
    * {
      box-sizing: border-box;
    }

    body {
      margin: 0;
      font-family: Arial, sans-serif;
      background: #f4f4f4;
      display: flex;
      justify-content: center;
      align-items: center;
      min-height: 100vh;
      padding: 20px;
    }

    .chat-app {
      width: 100%;
      max-width: 720px;
      height: 80vh;
      background: #ffffff;
      border: 1px solid #dcdcdc;
      border-radius: 12px;
      display: flex;
      flex-direction: column;
      overflow: hidden;
      box-shadow: 0 8px 24px rgba(0, 0, 0, 0.08);
    }

    .chat-header {
      padding: 16px 20px;
      border-bottom: 1px solid #e5e5e5;
      font-size: 18px;
      font-weight: 700;
      background: #fafafa;
    }

    .chat-messages {
      flex: 1;
      overflow-y: auto;
      padding: 16px;
      display: flex;
      flex-direction: column;
      gap: 12px;
    }

    .message {
      max-width: 80%;
      padding: 12px 14px;
      border-radius: 12px;
      line-height: 1.4;
      word-break: break-word;
    }

    .message-text {
      white-space: pre-wrap;
    }

    .message.user {
      align-self: flex-end;
      background: #dbeafe;
    }

    .message.bot {
      align-self: flex-start;
      background: #f1f5f9;
    }

    .message-structured {
      display: flex;
      flex-direction: column;
      gap: 8px;
    }

    .structured-group {
      display: flex;
      flex-direction: column;
      gap: 4px;
    }

    .structured-title {
      font-weight: 700;
    }

    .structured-list {
      margin: 0;
      padding-left: 18px;
    }

    .structured-list li {
      margin: 0;
    }

    .chat-input-area {
      display: flex;
      gap: 10px;
      padding: 16px;
      border-top: 1px solid #e5e5e5;
      background: #ffffff;
    }

    .chat-input {
      flex: 1;
      padding: 12px;
      border: 1px solid #cfcfcf;
      border-radius: 10px;
      font-size: 16px;
      outline: none;
    }

    .chat-input:focus {
      border-color: #888;
    }

    .send-button {
      padding: 12px 18px;
      border: none;
      border-radius: 10px;
      background: #111827;
      color: #ffffff;
      font-size: 15px;
      cursor: pointer;
    }

    .send-button:disabled {
      opacity: 0.6;
      cursor: not-allowed;
    }

    .status {
      padding: 0 16px 12px 16px;
      font-size: 13px;
      color: #666666;
    }
  </style>
</head>
<body>
  <div class="chat-app">
    <div class="chat-header" id="chatHeader">Се вчитува...</div>

    <div class="chat-messages" id="chatMessages"></div>

    <div class="chat-input-area">
      <input
        type="text"
        id="messageInput"
        class="chat-input"
        placeholder="Напишете порака..."
      />
      <button id="sendButton" class="send-button">Испрати</button>
    </div>

    <div class="status" id="statusText">Подготвено</div>
  </div>

  <script>
    const chatMessages = document.getElementById("chatMessages");
    const messageInput = document.getElementById("messageInput");
    const sendButton = document.getElementById("sendButton");
    const statusText = document.getElementById("statusText");
    const chatHeader = document.getElementById("chatHeader");

    const pathParts = window.location.pathname.split("/").filter(Boolean);
    const tenant = pathParts[0] === "agent" && pathParts[1] ? pathParts[1] : "generic";
    const sessionStorageKey = `clinic-ai-session:${tenant}`;
    let sessionId = window.localStorage.getItem(sessionStorageKey) || null;
    let isSending = false;

    const API_URL = `/chat?tenant=${encodeURIComponent(tenant)}`;
    const CONFIG_URL = `/config/${encodeURIComponent(tenant)}`;

    function renderMessageContent(text) {
      const value = String(text || "");
      const lines = value.split(/\r?\n/);
      const hasStructuredLines = lines.some((line) => {
        const trimmed = line.trim();
        return trimmed.startsWith("• ") || trimmed.startsWith("– ");
      });

      if (!hasStructuredLines) {
        const textEl = document.createElement("div");
        textEl.className = "message-text";
        textEl.textContent = value;
        return textEl;
      }

      const wrapper = document.createElement("div");
      wrapper.className = "message-structured";

      let currentGroup = null;
      let currentList = null;

      for (const rawLine of lines) {
        const trimmed = rawLine.trim();

        if (!trimmed) {
          currentList = null;
          continue;
        }

        if (trimmed.startsWith("• ")) {
          currentGroup = document.createElement("div");
          currentGroup.className = "structured-group";

          const titleEl = document.createElement("div");
          titleEl.className = "structured-title";
          titleEl.textContent = trimmed.slice(2).trim();

          currentGroup.appendChild(titleEl);
          wrapper.appendChild(currentGroup);
          currentList = null;
          continue;
        }

        if (trimmed.startsWith("– ")) {
          if (!currentGroup) {
            currentGroup = document.createElement("div");
            currentGroup.className = "structured-group";
            wrapper.appendChild(currentGroup);
          }

          if (!currentList) {
            currentList = document.createElement("ul");
            currentList.className = "structured-list";
            currentGroup.appendChild(currentList);
          }

          const itemEl = document.createElement("li");
          itemEl.textContent = trimmed.slice(2).trim();
          currentList.appendChild(itemEl);
          continue;
        }

        const textEl = document.createElement("div");
        textEl.className = "message-text";
        textEl.textContent = trimmed;
        wrapper.appendChild(textEl);
        currentGroup = null;
        currentList = null;
      }

      return wrapper;
    }

    function addMessage(text, sender) {
      const messageEl = document.createElement("div");
      messageEl.classList.add("message", sender);
      messageEl.appendChild(renderMessageContent(text));
      chatMessages.appendChild(messageEl);
      chatMessages.scrollTop = chatMessages.scrollHeight;
    }

    async function loadTenantConfig() {
      try {
        const response = await fetch(CONFIG_URL);

        if (!response.ok) {
          throw new Error(`HTTP error: ${response.status}`);
        }

        const config = await response.json();
        const businessName = config.business?.name || config.assistant?.name || "Асистент";
        const greeting = config.conversation?.greeting || "Здраво! Како можам да ви помогнам денес?";

        chatHeader.textContent = businessName;
        document.title = businessName;

        chatMessages.innerHTML = "";
        addMessage(greeting, "bot");
      } catch (error) {
        chatHeader.textContent = "Асистент";
        document.title = "Асистент";
        chatMessages.innerHTML = "";
        addMessage("Здраво! Како можам да ви помогнам денес?", "bot");
        console.error("Failed to load tenant config:", error);
      }
    }

    async function sendMessage() {
      if (isSending) {
        return;
      }

      const userMessage = messageInput.value.trim();

      if (!userMessage) {
        return;
      }

      isSending = true;
      addMessage(userMessage, "user");
      messageInput.value = "";
      sendButton.disabled = true;
      messageInput.disabled = true;
      statusText.textContent = "Се испраќа...";

      try {
        const response = await fetch(API_URL, {
          method: "POST",
          headers: {
            "Content-Type": "application/json"
          },
          body: JSON.stringify({
            message: userMessage,
            session_id: sessionId
          })
        });

        if (!response.ok) {
          throw new Error(`HTTP error: ${response.status}`);
        }

        const data = await response.json();
        if (data.session_id) {
          sessionId = data.session_id;
          window.localStorage.setItem(sessionStorageKey, sessionId);
        }
        addMessage(data.reply || "Нема одговор од серверот.", "bot");
        statusText.textContent = data.session_status === "completed"
          ? "Барањето е завршено."
          : data.session_status === "collecting_contact"
            ? "Се собираат контакт податоци."
            : "Подготвено";
      } catch (error) {
        addMessage("Настана грешка при поврзување со системот.", "bot");
        statusText.textContent = `Грешка: ${error.message}`;
      } finally {
        isSending = false;
        sendButton.disabled = false;
        messageInput.disabled = false;
        messageInput.focus();
      }
    }

    sendButton.addEventListener("click", sendMessage);

    messageInput.addEventListener("keydown", function (event) {
      if (event.key === "Enter") {
        sendMessage();
      }
    });

    loadTenantConfig();
  </script>
</body>
</html>

```

--------------------------------
File: clinic-ai-assistant-src/backend/app/main.py
--------------------------------

```python
import os
from pathlib import Path

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles
from dotenv import load_dotenv

from app.routes.chat import router as chat_router
from app.services.config_loader import (
    TenantConfigError,
    TenantNotFoundError,
    load_profile_config,
    load_public_profile_config,
)
from app.services.lead_store import init_leads_db

load_dotenv()

if not os.getenv("OPENAI_API_KEY"):
    raise RuntimeError("OPENAI_API_KEY is required at startup")

init_leads_db()

app = FastAPI()

BASE_DIR = Path(__file__).resolve().parent.parent.parent
FRONTEND_DIR = BASE_DIR / "frontend"
INDEX_FILE = FRONTEND_DIR / "index.html"
DEFAULT_ALLOWED_ORIGINS = [
    "http://localhost",
    "http://127.0.0.1",
    "http://localhost:3000",
    "http://127.0.0.1:3000",
    "http://localhost:8000",
    "http://127.0.0.1:8000",
]

allowed_origins_env = os.getenv("ALLOWED_ORIGINS", "")
allowed_origins = [
    origin.strip()
    for origin in allowed_origins_env.split(",")
    if origin.strip()
]
if not allowed_origins:
    allowed_origins = DEFAULT_ALLOWED_ORIGINS

app.add_middleware(
    CORSMiddleware,
    allow_origins=allowed_origins,
    allow_credentials=False,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(chat_router)

app.mount("/frontend", StaticFiles(directory=str(FRONTEND_DIR)), name="frontend")


@app.get("/health")
def health():
    return {"status": "Clinic AI Assistant running"}


@app.get("/config/{tenant}")
def get_config(tenant: str):
    try:
        load_profile_config(tenant)
        return load_public_profile_config(tenant)
    except TenantNotFoundError:
        raise HTTPException(status_code=404, detail=f"Tenant '{tenant}' not found")
    except TenantConfigError:
        raise HTTPException(status_code=500, detail=f"Tenant '{tenant}' configuration is invalid")


@app.get("/agent/{tenant}")
def serve_agent(tenant: str):
    try:
        load_profile_config(tenant)
        return FileResponse(str(INDEX_FILE))
    except TenantNotFoundError:
        raise HTTPException(status_code=404, detail=f"Tenant '{tenant}' not found")
    except TenantConfigError:
        raise HTTPException(status_code=500, detail=f"Tenant '{tenant}' configuration is invalid")

```

--------------------------------
File: clinic-ai-assistant-src/backend/app/routes/chat.py
--------------------------------

```python
from fastapi import APIRouter, HTTPException, Query
from pydantic import BaseModel, Field, field_validator

from app.services.ai_agent import AIInferenceError, generate_reply, get_session_status
from app.services.config_loader import TenantConfigError, TenantNotFoundError

router = APIRouter()


class ChatRequest(BaseModel):
    message: str = Field(..., max_length=2000)
    session_id: str | None = Field(default=None, max_length=128)

    @field_validator("message")
    @classmethod
    def validate_message(cls, value: str) -> str:
        trimmed = value.strip()
        if not trimmed:
            raise ValueError("message must not be empty")
        return trimmed

    @field_validator("session_id")
    @classmethod
    def validate_session_id(cls, value: str | None) -> str | None:
        if value is None:
            return None

        trimmed = value.strip()
        return trimmed or None


@router.post("/chat")
def chat(payload: ChatRequest, tenant: str = Query(...)):
    try:
        reply, session_id = generate_reply(tenant, payload.message, payload.session_id)
        session_status = get_session_status(tenant, session_id)
    except TenantNotFoundError:
        raise HTTPException(status_code=404, detail=f"Tenant '{tenant}' not found")
    except TenantConfigError:
        raise HTTPException(status_code=500, detail=f"Tenant '{tenant}' configuration is invalid")
    except AIInferenceError as exc:
        raise HTTPException(status_code=503, detail=str(exc))

    return {
        "received_message": payload.message,
        "tenant": tenant,
        "session_id": session_id,
        "session_status": session_status,
        "reply": reply
    }

```

--------------------------------
File: clinic-ai-assistant-src/backend/app/services/ai_agent.py
--------------------------------

```python
import json
import logging
import os
import re
import uuid

from openai import OpenAI, OpenAIError, RateLimitError

from app.services.config_loader import load_profile_config
from app.services.lead_store import load_lead_checkpoint, save_lead_checkpoint
from app.services.session_trace_logger import trace_event


logger = logging.getLogger(__name__)
DEBUG_AI = os.getenv("DEBUG_AI", "").strip().lower() == "true"
SESSION_STATE = {}
INTERACTION_HISTORY = {}
MAX_INTERACTION_HISTORY = 6
CANONICAL_INTENTS = {"greeting", "suggest_service", "confirm_booking", "collect_contact", "fallback"}
INTENT_ALIASES = {
    "greeting": "greeting",
    "hello": "greeting",
    "welcome": "greeting",
    "suggest_service": "suggest_service",
    "book_service": "suggest_service",
    "booking_inquiry": "suggest_service",
    "booking_request": "suggest_service",
    "list_services": "fallback",
    "confirm_booking": "confirm_booking",
    "booking_initiated": "confirm_booking",
    "booking_initiate": "confirm_booking",
    "booking_start": "confirm_booking",
    "collect_contact": "collect_contact",
    "clarify": "fallback",
    "clarification": "fallback",
    "out_of_scope": "fallback",
    "ask_services": "fallback",
    "fallback": "fallback",
}


class AIInferenceError(Exception):
    pass


def _fallback_reply(profile: dict) -> str:
    conversation = profile.get("conversation", {})
    fallback_message = conversation.get("fallback_message")

    if isinstance(fallback_message, str) and fallback_message.strip():
        return fallback_message

    return ""


def _session_key(tenant: str, session_id: str) -> str:
    return f"{tenant}:{session_id}"


def _normalize_session_id(session_id: str | None) -> str:
    if isinstance(session_id, str) and session_id.strip():
        return session_id.strip()

    return str(uuid.uuid4())


def _load_session_state(tenant: str, session_id: str) -> dict | None:
    session_key = _session_key(tenant, session_id)
    state = SESSION_STATE.get(session_key)

    if state is None:
        state = load_lead_checkpoint(tenant, session_id)
        if state:
            SESSION_STATE[session_key] = state

    return state


def _stage_name(state: dict | None) -> str | None:
    if not isinstance(state, dict):
        return None

    return state.get("stage")


def _log_chat_state(
    *,
    message: str,
    session_id: str,
    intent: str | None,
    stage_before: str | None,
    stage_after: str | None,
) -> None:
    logger.info(
        "chat_state message=%r session_id=%s intent=%s stage_before=%s stage_after=%s",
        message,
        session_id,
        intent,
        stage_before,
        stage_after,
    )


def _trace_stage_transition(
    tenant: str,
    session_id: str,
    from_stage: str | None,
    to_stage: str | None,
    *,
    reason: str,
):
    trace_event(
        tenant,
        session_id,
        "STAGE_TRANSITION",
        from_stage=from_stage,
        to_stage=to_stage,
        reason=reason,
    )


def _profile_text(profile: dict, *path: str) -> str | None:
    value = profile
    for key in path:
        if not isinstance(value, dict):
            return None
        value = value.get(key)

    if isinstance(value, str) and value.strip():
        return value.strip()

    return None


def _profile_text_map(profile: dict, *path: str) -> dict:
    value = profile
    for key in path:
        if not isinstance(value, dict):
            return {}
        value = value.get(key)

    return value if isinstance(value, dict) else {}


def _profile_list(profile: dict, *path: str) -> list[str]:
    value = profile
    for key in path:
        if not isinstance(value, dict):
            return []
        value = value.get(key)

    if not isinstance(value, list):
        return []

    return [item.strip() for item in value if isinstance(item, str) and item.strip()]


def _render_profile_text(profile: dict, path: tuple[str, ...], **values) -> str | None:
    template = _profile_text(profile, *path)
    if not template:
        return None

    return template.format(**values)


def _field_prompt(profile: dict, field_name: str) -> str:
    field_prompts = _profile_text_map(profile, "reply_texts", "field_prompts")
    value = field_prompts.get(field_name)
    if isinstance(value, str) and value.strip():
        return value.strip()
    return field_name


def _conversation_rule_list(profile: dict, rule_name: str) -> list[str]:
    return _profile_list(profile, "conversation_rules", rule_name)


def _conversation_rule_patterns(profile: dict) -> list[tuple[list[str], str]]:
    patterns = profile.get("conversation_rules", {}).get("casual_reply_patterns", [])
    if not isinstance(patterns, list):
        return []

    normalized_patterns: list[tuple[list[str], str]] = []
    for item in patterns:
        if not isinstance(item, dict):
            continue

        triggers = item.get("triggers")
        reply_key = item.get("reply_key")
        if not isinstance(triggers, list) or not isinstance(reply_key, str) or not reply_key.strip():
            continue

        clean_triggers = [trigger.strip() for trigger in triggers if isinstance(trigger, str) and trigger.strip()]
        if clean_triggers:
            normalized_patterns.append((clean_triggers, reply_key.strip()))

    return normalized_patterns


def _status_for_stage(stage: str | None) -> str:
    if stage == "collecting_contact":
        return "collecting_contact"
    if stage == "completed":
        return "completed"
    return "active"


def _message_tokens(value: str) -> set[str]:
    normalized = _normalize_lookup_text(value)
    return {
        token
        for token in re.split(r"[^a-zA-Z0-9\u0400-\u04FF]+", normalized)
        if token
    }


def _messages_are_similar(left: str, right: str) -> bool:
    left_normalized = _normalize_lookup_text(left)
    right_normalized = _normalize_lookup_text(right)

    if not left_normalized or not right_normalized:
        return False

    if left_normalized == right_normalized:
        return True

    if left_normalized in right_normalized or right_normalized in left_normalized:
        return True

    left_tokens = _message_tokens(left_normalized)
    right_tokens = _message_tokens(right_normalized)
    if not left_tokens or not right_tokens:
        return False

    overlap = len(left_tokens & right_tokens)
    smallest = min(len(left_tokens), len(right_tokens))
    return smallest > 0 and (overlap / smallest) >= 0.75


def _recent_interactions(session_key: str) -> list[dict]:
    return INTERACTION_HISTORY.get(session_key, [])


def _last_interaction(session_key: str) -> dict | None:
    history = _recent_interactions(session_key)
    if not history:
        return None

    return history[-1]


def _record_interaction(session_key: str, message: str, reply: str, response_type: str | None) -> None:
    history = INTERACTION_HISTORY.setdefault(session_key, [])
    history.append(
        {
            "message": _normalize_lookup_text(message),
            "reply": reply,
            "response_type": response_type,
        }
    )
    if len(history) > MAX_INTERACTION_HISTORY:
        del history[:-MAX_INTERACTION_HISTORY]


def _is_broad_pricing_request(message: str, profile: dict) -> bool:
    normalized_message = _normalize_lookup_text(message)
    price_terms = _conversation_rule_list(profile, "broad_pricing_price_terms")
    has_price_language = any(
        token in normalized_message
        for token in price_terms
    )
    service_terms = _conversation_rule_list(profile, "broad_pricing_service_terms")
    has_service_language = any(
        token in normalized_message
        for token in service_terms
    )
    return has_price_language and has_service_language and not _is_price_request(message, profile)


def _is_consultation_explanation_request(message: str, services: list[dict], profile: dict) -> bool:
    normalized_message = _normalize_lookup_text(message)
    consultation_service = _match_service_for_message(message, services)
    if not consultation_service or consultation_service.get("id") != "consultation":
        return False

    return any(
        trigger in normalized_message
        for trigger in _conversation_rule_list(profile, "consultation_explanation_triggers")
    )


def _consultation_service(services: list[dict]) -> dict | None:
    for service in services:
        if service.get("id") == "consultation":
            return service
    return None


def _should_start_consultation_booking(message: str, session_key: str, services: list[dict], profile: dict) -> bool:
    if not _is_booking_confirmation(message, profile):
        return False

    last_item = _last_interaction(session_key)
    if not last_item:
        return False

    if last_item.get("response_type") == "service_list":
        return False

    consultation_service = _consultation_service(services)
    if not consultation_service:
        return False

    last_reply = last_item.get("reply", "")
    matched_service = _match_service_for_message(last_reply, services) if isinstance(last_reply, str) else None
    return bool(matched_service and matched_service.get("id") == consultation_service.get("id"))


def _is_contact_clarification(message: str, profile: dict) -> bool:
    normalized_message = _normalize_lookup_text(message)
    if not normalized_message:
        return False

    if "?" in message:
        return True

    prefixes = _conversation_rule_list(profile, "contact_clarification_prefixes")
    if any(normalized_message.startswith(prefix) for prefix in prefixes):
        return True

    phrases = _conversation_rule_list(profile, "contact_clarification_phrases")
    return any(phrase in normalized_message for phrase in phrases)


def _contact_clarification_reply(profile: dict, field_name: str) -> str:
    field_label = _field_prompt(profile, field_name)
    contact_replies = _profile_text_map(profile, "reply_texts", "contact_clarification_replies")
    template = contact_replies.get(field_name) or contact_replies.get("default")
    if isinstance(template, str) and template.strip():
        return template.strip().format(field_prompt=field_label)
    return field_label


def _unknown_service_detail_reply(message: str, services: list[dict], profile: dict) -> str | None:
    normalized_message = _normalize_lookup_text(message)
    detail_triggers = _conversation_rule_list(profile, "service_detail_triggers")
    if not any(trigger in normalized_message for trigger in detail_triggers):
        return None

    service = _match_service_for_message(message, services)
    if not service:
        return None

    known_text_parts: list[str] = []
    for field_name in ("name", "име", "description", "опис", "article_name", "category"):
        value = service.get(field_name)
        if isinstance(value, str) and value.strip():
            known_text_parts.append(_normalize_lookup_text(value))

    for field_name in ("aliases", "keywords", "symptoms", "препорачано_за"):
        values = service.get(field_name) or []
        if isinstance(values, list):
            for item in values:
                if isinstance(item, str) and item.strip():
                    known_text_parts.append(_normalize_lookup_text(item))

    if any(trigger in " ".join(known_text_parts) for trigger in detail_triggers):
        return None

    return _profile_text(profile, "conversation_rules", "safe_detail_fallback")


def _repetition_reformulation(
    *,
    message: str,
    session_key: str,
    services: list[dict],
    profile: dict,
) -> str | None:
    history = _recent_interactions(session_key)
    if not history:
        return None

    repeated = any(_messages_are_similar(message, item.get("message", "")) for item in reversed(history))
    if not repeated:
        return None

    if _is_broad_pricing_request(message, profile):
        return _profile_text(profile, "repetition_responses", "broad_pricing")

    if _is_service_list_request(message, profile):
        return _profile_text(profile, "repetition_responses", "service_list")

    if _is_consultation_explanation_request(message, services, profile):
        return _profile_text(profile, "repetition_responses", "consultation_explanation")

    return None


def _finalize_reply(
    *,
    tenant: str,
    session_id: str,
    session_key: str,
    message: str,
    reply: str,
    response_type: str | None,
    services: list[dict],
    profile: dict,
    stage_after: str | None,
) -> str:
    final_reply = reply
    reformulated = _repetition_reformulation(
        message=message,
        session_key=session_key,
        services=services,
        profile=profile,
    )
    if reformulated:
        final_reply = reformulated

    _record_interaction(session_key, message, final_reply, response_type)
    _trace_response(tenant, session_id, final_reply, stage_after)
    return final_reply


def _trace_response(
    tenant: str,
    session_id: str,
    reply: str,
    stage_after: str | None,
):
    trace_event(
        tenant,
        session_id,
        "RESPONSE_RETURNED",
        reply=reply,
        session_status=_status_for_stage(stage_after),
        stage_after=stage_after,
    )


def _start_collecting_contact(
    tenant: str,
    session_id: str,
    session_key: str,
    service_id: str | None,
    collect_fields: list[str],
    profile: dict,
) -> tuple[str, str]:
    SESSION_STATE[session_key] = {
        "stage": "collecting_contact",
        "service_id": service_id,
        "next_field": collect_fields[0],
        "data": {}
    }
    save_lead_checkpoint(tenant, session_id, SESSION_STATE[session_key])
    return _field_prompt(profile, collect_fields[0]), session_id


def _is_booking_confirmation(message: str, profile: dict) -> bool:
    return message.strip().casefold() in {
        word.casefold()
        for word in _conversation_rule_list(profile, "booking_confirm_words")
    }


def _normalize_intent(intent: str | None) -> str:
    if not isinstance(intent, str):
        return "fallback"

    normalized_key = intent.strip().casefold()
    canonical_intent = INTENT_ALIASES.get(normalized_key, "fallback")

    if canonical_intent not in CANONICAL_INTENTS:
        return "fallback"

    return canonical_intent


def _normalize_lookup_text(value: str) -> str:
    lowered = value.casefold()
    normalized = re.sub(r"\s+", " ", lowered)
    return normalized.strip()


def _service_variants(service: dict) -> set[str]:
    variants = set()
    for field_name in ("name", "\u0438\u043c\u0435", "description", "\u043e\u043f\u0438\u0441"):
        value = service.get(field_name)
        if isinstance(value, str) and value.strip():
            variants.add(_normalize_lookup_text(value))

    for field_name in ("aliases", "keywords", "symptoms", "\u043f\u0440\u0435\u043f\u043e\u0440\u0430\u0447\u0430\u043d\u043e_\u0437\u0430"):
        values = service.get(field_name) or []
        if isinstance(values, list):
            for item in values:
                if isinstance(item, str) and item.strip():
                    variants.add(_normalize_lookup_text(item))

    return variants


def _match_service_for_message(message: str, services: list[dict]) -> dict | None:
    normalized_message = _normalize_lookup_text(message)
    best_match = None
    best_score = 0

    for service in services:
        for variant in _service_variants(service):
            if not variant:
                continue
            if variant in normalized_message:
                score = len(variant)
                if score > best_score:
                    best_score = score
                    best_match = service

    return best_match


def _is_service_list_request(message: str, profile: dict) -> bool:
    normalized_message = _normalize_lookup_text(message)
    return any(
        trigger in normalized_message
        for trigger in _conversation_rule_list(profile, "service_list_triggers")
    )


def _is_price_request(message: str, profile: dict) -> bool:
    normalized_message = _normalize_lookup_text(message)
    return any(
        trigger in normalized_message
        for trigger in _conversation_rule_list(profile, "price_triggers")
    )


def _greeting_reply(message: str, profile: dict) -> str | None:
    normalized_message = _normalize_lookup_text(message)
    if normalized_message not in {
        trigger.casefold()
        for trigger in _conversation_rule_list(profile, "greeting_triggers")
    }:
        return None

    return _profile_text(profile, "reply_texts", "greeting_short")


def _service_clarification_reply(message: str, profile: dict) -> str | None:
    normalized_message = _normalize_lookup_text(message)

    if normalized_message in {
        trigger.casefold()
        for trigger in _conversation_rule_list(profile, "service_clarification_specific_triggers")
    }:
        return _profile_text(profile, "reply_texts", "service_clarification_specific", "koja_usluga_mi_treba")

    if any(
        trigger in normalized_message
        for trigger in _conversation_rule_list(profile, "service_clarification_triggers")
    ):
        return _profile_text(profile, "reply_texts", "service_clarification")

    return None


def _casual_reply(message: str, profile: dict) -> str | None:
    normalized_message = _normalize_lookup_text(message)
    casual_replies = _profile_text_map(profile, "reply_texts", "casual_replies")

    for triggers, reply_key in _conversation_rule_patterns(profile):
        if any(trigger in normalized_message for trigger in triggers):
            reply = casual_replies.get(reply_key)
            if isinstance(reply, str) and reply.strip():
                return reply.strip()

    return None


def _catalog_categories(profile: dict, services: list[dict]) -> list[dict]:
    categories = profile.get("\u043a\u0430\u0442\u0435\u0433\u043e\u0440\u0438\u0438")
    if isinstance(categories, list) and categories:
        return categories

    grouped: dict[str, list[dict]] = {}
    for service in services:
        category_name = service.get("category") or "\u0423\u0441\u043b\u0443\u0433\u0438"
        grouped.setdefault(category_name, []).append(service)

    return [
        {
            "\u0438\u043c\u0435": category_name,
            "\u0443\u0441\u043b\u0443\u0433\u0438": category_services,
        }
        for category_name, category_services in grouped.items()
    ]


def _ordered_categories(profile: dict, services: list[dict]) -> list[dict]:
    categories = list(_catalog_categories(profile, services))
    consultation_name = _normalize_lookup_text("\u041a\u043e\u043d\u0441\u0443\u043b\u0442\u0430\u0446\u0438\u0458\u0430")

    consultation_categories = []
    other_categories = []
    for category in categories:
        category_name = category.get("\u0438\u043c\u0435") or category.get("name") or ""
        if _normalize_lookup_text(category_name) == consultation_name:
            consultation_categories.append(category)
        else:
            other_categories.append(category)

    return consultation_categories + other_categories


def _service_display_name(service: dict) -> str:
    return service.get("\u0438\u043c\u0435") or service.get("name") or service.get("id", "")


def _service_display_description(service: dict) -> str | None:
    description = service.get("\u043e\u043f\u0438\u0441") or service.get("description")
    if isinstance(description, str) and description.strip():
        return description.strip()
    return None


def _service_list_reply(profile: dict, services: list[dict]) -> str:
    lines: list[str] = []

    for category in _ordered_categories(profile, services):
        category_name = category.get("\u0438\u043c\u0435") or category.get("name")
        if not isinstance(category_name, str) or not category_name.strip():
            continue

        lines.append(f"\u2022 {category_name.strip()}")
        category_services = category.get("\u0443\u0441\u043b\u0443\u0433\u0438") or category.get("services") or []

        for service in category_services:
            if not isinstance(service, dict):
                continue

            service_name = _service_display_name(service)
            if not service_name:
                continue

            description = _service_display_description(service)
            if description and category_name == "\u041a\u043e\u043d\u0441\u0443\u043b\u0442\u0430\u0446\u0438\u0458\u0430":
                lines.append(f"  \u2013 {service_name} \u2014 {description}")
            else:
                lines.append(f"  \u2013 {service_name}")

        lines.append("")

    return "\n".join(lines).strip()


def _orientation_price_text(service: dict, profile: dict) -> str | None:
    service_name = _service_display_name(service)
    price = service.get("price", service.get("\u0446\u0435\u043d\u0430"))
    currency = service.get("\u0432\u0430\u043b\u0443\u0442\u0430")
    price_range = service.get("price_range", service.get("\u0446\u0435\u043d\u043e\u0432\u0435\u043d_\u043e\u043f\u0441\u0435\u0433"))
    description = _service_display_description(service)

    if isinstance(price, (int, float)):
        currency_text = f" {currency}" if isinstance(currency, str) and currency.strip() else ""
        first_line = _render_profile_text(
            profile,
            ("reply_texts", "price_templates", "numeric"),
            service_name=service_name,
            price=f"{price:g}",
            currency=currency_text,
        )
    elif isinstance(price, str) and price.strip():
        if price.strip().casefold() == "\u0431\u0435\u0441\u043f\u043b\u0430\u0442\u043d\u043e":
            first_line = _render_profile_text(
                profile,
                ("reply_texts", "price_templates", "free"),
                service_name=service_name,
            )
        else:
            first_line = _render_profile_text(
                profile,
                ("reply_texts", "price_templates", "text"),
                service_name=service_name,
                price=price.strip(),
            )
    elif isinstance(price_range, str) and price_range.strip():
        first_line = _render_profile_text(
            profile,
            ("reply_texts", "price_templates", "range"),
            service_name=service_name,
            service_name_lower=service_name.lower(),
            price_range=price_range.strip(),
        )
    else:
        return None

    if not first_line:
        return None

    lines = [first_line]
    if description:
        lines.append(description)
    lines.append("")
    followup = _profile_text(profile, "reply_texts", "price_followup")
    if followup:
        lines.append(followup)
    return "\n".join(lines)


def _service_description_reply(message: str, services: list[dict], profile: dict) -> str | None:
    normalized_message = _normalize_lookup_text(message)
    if not any(
        trigger in normalized_message
        for trigger in _conversation_rule_list(profile, "service_description_triggers")
    ):
        return None

    service = _match_service_for_message(message, services)
    if not service:
        return None

    service_name = _service_display_name(service)
    description = _service_display_description(service)
    if not description:
        return None

    article_name = service.get("article_name") or service_name
    sentence_description = description[0].lower() + description[1:] if description else description
    followup = _profile_text(profile, "reply_texts", "service_description_followup")
    return _render_profile_text(
        profile,
        ("reply_texts", "service_description_template"),
        article_name=article_name,
        service_name=service_name,
        description=sentence_description,
        followup=followup or "",
    )


def get_session_status(tenant: str, session_id: str | None) -> str:
    if not session_id:
        return "active"

    state = _load_session_state(tenant, session_id)
    stage = _stage_name(state)

    if stage == "collecting_contact":
        return "collecting_contact"
    if stage == "completed":
        return "completed"
    return "active"


def generate_reply(tenant: str, message: str, session_id: str | None = None) -> tuple[str, str]:
    original_session_id = session_id
    profile = load_profile_config(tenant)
    api_key = os.getenv("OPENAI_API_KEY")
    session_id = _normalize_session_id(session_id)

    if not original_session_id:
        trace_event(
            tenant,
            session_id,
            "SESSION_CREATED",
            reason="request_without_session_id",
        )

    trace_event(
        tenant,
        session_id,
        "REQUEST_RECEIVED",
        incoming_session_id=original_session_id,
        message=message,
    )

    business = profile.get("business", {})
    conversation = profile.get("conversation", {})
    prompt_template = profile.get("prompt_template", {})
    services = profile.get("services", [])
    actions = profile.get("actions", {})
    output_contract = profile.get("output_contract", {})

    business_name = business.get("name", "Assistant")
    language = business.get("language", "en")
    goal = conversation.get("goal", "")
    rules = conversation.get("rules", [])

    allow_booking = actions.get("allow_booking", False)
    collect_fields = actions.get("collect_contact_fields", [])
    communication_rules = profile.get("\u043a\u043e\u043c\u0443\u043d\u0438\u043a\u0430\u0446\u0438\u0441\u043a\u0438_\u043f\u0440\u0430\u0432\u0438\u043b\u0430", [])
    categories = _catalog_categories(profile, services)

    template = prompt_template.get(
        "system",
        "You are an AI assistant for {{business_name}}. Your goal: {{goal}}."
    )

    service_catalog = [
        {
            "id": service.get("id"),
            "name": service.get("name"),
            "description": service.get("description"),
            "keywords": service.get("keywords", []),
            "symptoms": service.get("symptoms", []),
            "aliases": service.get("aliases", []),
            "category": service.get("category"),
            "bookable": service.get("bookable", False)
        }
        for service in services
    ]

    services_json = json.dumps(service_catalog, ensure_ascii=False, indent=2)
    rules_text = "\n".join(f"- {rule}" for rule in rules)
    communication_rules_text = "\n".join(f"- {rule}" for rule in communication_rules if isinstance(rule, str))
    categories_json = json.dumps(categories, ensure_ascii=False, indent=2)

    system_prompt = (
        template.replace("{{business_name}}", business_name)
        .replace("{{goal}}", goal)
    )

    if rules_text:
        system_prompt += f"\n\nRules:\n{rules_text}"

    system_prompt += f"\n\nAlways respond in this language: {language}"
    system_prompt += f"\n\nAllowed services catalog:\n{services_json}"
    system_prompt += f"\n\nClinical category catalog:\n{categories_json}"

    if communication_rules_text:
        system_prompt += f"\n\nCommunication rules:\n{communication_rules_text}"

    if allow_booking:
        system_prompt += (
            "\n\nBooking capability: enabled."
            "\nCanonical intents: greeting, suggest_service, confirm_booking, fallback."
            "\nIf the user confirms booking, return confirm_booking."
            "\nIf the user asks what services are available, present them grouped by category."
            "\nDo not volunteer prices in general descriptive answers."
            f"\nCollect these fields in order: {collect_fields}"
        )

    if output_contract:
        system_prompt += (
            "\n\nReturn ONLY a JSON object with this structure:\n"
            + json.dumps(output_contract.get("response_format", {}), ensure_ascii=False, indent=2)
        )

    session_key = _session_key(tenant, session_id)
    state = _load_session_state(tenant, session_id)
    stage_before = _stage_name(state)

    trace_event(
        tenant,
        session_id,
        "SESSION_LOADED",
        stage_before=stage_before,
        state=state,
    )

    if state and state.get("stage") == "completed":
        old_session_id = session_id
        SESSION_STATE.pop(session_key, None)
        INTERACTION_HISTORY.pop(session_key, None)
        session_id = _normalize_session_id(None)
        session_key = _session_key(tenant, session_id)
        state = None
        stage_before = None
        trace_event(
            tenant,
            old_session_id,
            "SESSION_RESET_AFTER_COMPLETION",
            old_session_id=old_session_id,
            new_session_id=session_id,
        )
        trace_event(
            tenant,
            session_id,
            "SESSION_CREATED",
            reason="post_completion_rollover",
            previous_session_id=old_session_id,
        )

    # Booking state 1: waiting for the user to confirm a suggested service.
    if (
        state
        and state.get("stage") == "awaiting_booking_confirmation"
        and allow_booking
        and _is_booking_confirmation(message, profile)
    ):
        reply, session_id = _start_collecting_contact(
            tenant,
            session_id,
            session_key,
            state.get("service_id"),
            collect_fields,
            profile,
        )
        _trace_stage_transition(
            tenant,
            session_id,
            stage_before,
            "collecting_contact",
            reason="backend_confirmation_word",
        )
        _log_chat_state(
            message=message,
            session_id=session_id,
            intent="confirm_booking",
            stage_before=stage_before,
            stage_after="collecting_contact",
        )
        final_reply = _finalize_reply(
            tenant=tenant,
            session_id=session_id,
            session_key=session_key,
            message=message,
            reply=reply,
            response_type="confirm_booking",
            services=services,
            profile=profile,
            stage_after="collecting_contact",
        )
        return final_reply, session_id

    # Booking state 2: backend owns the contact collection prompts until completion.
    if state and state.get("stage") == "collecting_contact":
        next_field = state.get("next_field")

        if _is_contact_clarification(message, profile):
            reply = _contact_clarification_reply(profile, next_field)
            final_reply = _finalize_reply(
                tenant=tenant,
                session_id=session_id,
                session_key=session_key,
                message=message,
                reply=reply,
                response_type="collect_contact",
                services=services,
                profile=profile,
                stage_after="collecting_contact",
            )
            return final_reply, session_id

        state["data"][next_field] = message

        remaining = [field for field in collect_fields if field not in state["data"]]

        if remaining:
            state["next_field"] = remaining[0]
            save_lead_checkpoint(tenant, session_id, state)
            _trace_stage_transition(
                tenant,
                session_id,
                stage_before,
                "collecting_contact",
                reason=f"collected_{next_field}",
            )
            _log_chat_state(
                message=message,
                session_id=session_id,
                intent="collect_contact",
                stage_before=stage_before,
                stage_after="collecting_contact",
            )
            reply = _field_prompt(profile, remaining[0])
            final_reply = _finalize_reply(
                tenant=tenant,
                session_id=session_id,
                session_key=session_key,
                message=message,
                reply=reply,
                response_type="collect_contact",
                services=services,
                profile=profile,
                stage_after="collecting_contact",
            )
            return final_reply, session_id

        SESSION_STATE.pop(session_key, None)
        state["stage"] = "completed"
        save_lead_checkpoint(tenant, session_id, state)
        _trace_stage_transition(
            tenant,
            session_id,
            stage_before,
            "completed",
            reason=f"collected_{next_field}",
        )
        _log_chat_state(
            message=message,
            session_id=session_id,
            intent="collect_contact",
            stage_before=stage_before,
            stage_after="completed",
        )
        reply = _profile_text(profile, "reply_texts", "booking_completed")
        final_reply = _finalize_reply(
            tenant=tenant,
            session_id=session_id,
            session_key=session_key,
            message=message,
            reply=reply,
            response_type="collect_contact",
            services=services,
            profile=profile,
            stage_after="completed",
        )
        return final_reply, session_id

    if not state and allow_booking and _should_start_consultation_booking(message, session_key, services, profile):
        SESSION_STATE[session_key] = {
            "stage": "awaiting_booking_confirmation",
            "service_id": "consultation",
        }
        _trace_stage_transition(
            tenant,
            session_id,
            stage_before,
            "awaiting_booking_confirmation",
            reason="predicted_consultation_confirmation",
        )
        reply, session_id = _start_collecting_contact(
            tenant,
            session_id,
            session_key,
            "consultation",
            collect_fields,
            profile,
        )
        _trace_stage_transition(
            tenant,
            session_id,
            "awaiting_booking_confirmation",
            "collecting_contact",
            reason="predicted_consultation_confirmation",
        )
        _log_chat_state(
            message=message,
            session_id=session_id,
            intent="confirm_booking",
            stage_before=stage_before,
            stage_after="collecting_contact",
        )
        final_reply = _finalize_reply(
            tenant=tenant,
            session_id=session_id,
            session_key=session_key,
            message=message,
            reply=reply,
            response_type="confirm_booking",
            services=services,
            profile=profile,
            stage_after="collecting_contact",
        )
        return final_reply, session_id

    greeting_reply = _greeting_reply(message, profile)
    if greeting_reply:
        _log_chat_state(
            message=message,
            session_id=session_id,
            intent="greeting",
            stage_before=stage_before,
            stage_after=_stage_name(SESSION_STATE.get(session_key)),
        )
        final_reply = _finalize_reply(
            tenant=tenant,
            session_id=session_id,
            session_key=session_key,
            message=message,
            reply=greeting_reply,
            response_type="greeting",
            services=services,
            profile=profile,
            stage_after=_stage_name(SESSION_STATE.get(session_key)),
        )
        return final_reply, session_id

    clarification_reply = _service_clarification_reply(message, profile)
    if clarification_reply:
        _log_chat_state(
            message=message,
            session_id=session_id,
            intent="fallback",
            stage_before=stage_before,
            stage_after=_stage_name(SESSION_STATE.get(session_key)),
        )
        final_reply = _finalize_reply(
            tenant=tenant,
            session_id=session_id,
            session_key=session_key,
            message=message,
            reply=clarification_reply,
            response_type="service_clarification",
            services=services,
            profile=profile,
            stage_after=_stage_name(SESSION_STATE.get(session_key)),
        )
        return final_reply, session_id

    if _is_service_list_request(message, profile):
        reply = _service_list_reply(profile, services)
        _log_chat_state(
            message=message,
            session_id=session_id,
            intent="fallback",
            stage_before=stage_before,
            stage_after=_stage_name(SESSION_STATE.get(session_key)),
        )
        final_reply = _finalize_reply(
            tenant=tenant,
            session_id=session_id,
            session_key=session_key,
            message=message,
            reply=reply,
            response_type="service_list",
            services=services,
            profile=profile,
            stage_after=_stage_name(SESSION_STATE.get(session_key)),
        )
        return final_reply, session_id

    if _is_price_request(message, profile):
        matched_service = _match_service_for_message(message, services)
        price_reply = _orientation_price_text(matched_service, profile) if matched_service else None
        if price_reply:
            _log_chat_state(
                message=message,
                session_id=session_id,
                intent="suggest_service",
                stage_before=stage_before,
                stage_after=_stage_name(SESSION_STATE.get(session_key)),
            )
            final_reply = _finalize_reply(
                tenant=tenant,
                session_id=session_id,
                session_key=session_key,
                message=message,
                reply=price_reply,
                response_type="explicit_price",
                services=services,
                profile=profile,
                stage_after=_stage_name(SESSION_STATE.get(session_key)),
            )
            return final_reply, session_id

    description_reply = _service_description_reply(message, services, profile)
    if description_reply:
        _log_chat_state(
            message=message,
            session_id=session_id,
            intent="suggest_service",
            stage_before=stage_before,
            stage_after=_stage_name(SESSION_STATE.get(session_key)),
        )
        final_reply = _finalize_reply(
            tenant=tenant,
            session_id=session_id,
            session_key=session_key,
            message=message,
            reply=description_reply,
            response_type="service_description",
            services=services,
            profile=profile,
            stage_after=_stage_name(SESSION_STATE.get(session_key)),
        )
        return final_reply, session_id

    casual_reply = _casual_reply(message, profile)
    if casual_reply:
        _log_chat_state(
            message=message,
            session_id=session_id,
            intent="fallback",
            stage_before=stage_before,
            stage_after=_stage_name(SESSION_STATE.get(session_key)),
        )
        final_reply = _finalize_reply(
            tenant=tenant,
            session_id=session_id,
            session_key=session_key,
            message=message,
            reply=casual_reply,
            response_type="casual",
            services=services,
            profile=profile,
            stage_after=_stage_name(SESSION_STATE.get(session_key)),
        )
        return final_reply, session_id

    cautious_detail_reply = _unknown_service_detail_reply(message, services, profile)
    if cautious_detail_reply:
        _log_chat_state(
            message=message,
            session_id=session_id,
            intent="fallback",
            stage_before=stage_before,
            stage_after=_stage_name(SESSION_STATE.get(session_key)),
        )
        final_reply = _finalize_reply(
            tenant=tenant,
            session_id=session_id,
            session_key=session_key,
            message=message,
            reply=cautious_detail_reply,
            response_type="fallback",
            services=services,
            profile=profile,
            stage_after=_stage_name(SESSION_STATE.get(session_key)),
        )
        return final_reply, session_id

    try:
        client = OpenAI(api_key=api_key)

        if DEBUG_AI:
            logger.debug("OPENAI CALL START tenant=%s session_id=%s", tenant, session_id)

        trace_event(tenant, session_id, "AI_CALL_START")
        response = client.responses.create(
            model="gpt-4.1-mini",
            input=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": message}
            ]
        )
        trace_event(tenant, session_id, "AI_CALL_END")

        if DEBUG_AI:
            logger.debug("OPENAI CALL END tenant=%s session_id=%s", tenant, session_id)
            logger.debug("OPENAI RESPONSE TEXT %s", (response.output_text or "").strip())

        raw_output = (response.output_text or "").strip()
        trace_event(tenant, session_id, "AI_RAW_OUTPUT", raw_output=raw_output)

        try:
            parsed = json.loads(raw_output)
            if not isinstance(parsed, dict):
                trace_event(
                    tenant,
                    session_id,
                    "FALLBACK_USED",
                    reason="parsed_output_not_object",
                )
                _log_chat_state(
                    message=message,
                    session_id=session_id,
                    intent="fallback",
                    stage_before=stage_before,
                    stage_after=_stage_name(SESSION_STATE.get(session_key)),
                )
                reply = _fallback_reply(profile)
                final_reply = _finalize_reply(
                    tenant=tenant,
                    session_id=session_id,
                    session_key=session_key,
                    message=message,
                    reply=reply,
                    response_type="fallback",
                    services=services,
                    profile=profile,
                    stage_after=_stage_name(SESSION_STATE.get(session_key)),
                )
                return final_reply, session_id

            raw_intent = parsed.get("intent")
            intent = _normalize_intent(raw_intent)
            service_id = parsed.get("service_id")
            message_text = parsed.get("message")

            trace_event(
                tenant,
                session_id,
                "INTENT_NORMALIZED",
                raw_intent=raw_intent,
                normalized_intent=intent,
                service_id=service_id,
            )

            if intent == "confirm_booking" and allow_booking:
                reply, session_id = _start_collecting_contact(
                    tenant,
                    session_id,
                    session_key,
                    service_id,
                    collect_fields,
                    profile,
                )
                _trace_stage_transition(
                    tenant,
                    session_id,
                    stage_before,
                    "collecting_contact",
                    reason="model_confirm_booking",
                )
                _log_chat_state(
                    message=message,
                    session_id=session_id,
                    intent=intent,
                    stage_before=stage_before,
                    stage_after="collecting_contact",
                )
                final_reply = _finalize_reply(
                    tenant=tenant,
                    session_id=session_id,
                    session_key=session_key,
                    message=message,
                    reply=reply,
                    response_type="confirm_booking",
                    services=services,
                    profile=profile,
                    stage_after="collecting_contact",
                )
                return final_reply, session_id

            if intent == "suggest_service" and allow_booking and service_id and service_id != "unknown":
                bookable_service_ids = {
                    service.get("id")
                    for service in services
                    if service.get("bookable")
                }
                if service_id in bookable_service_ids:
                    SESSION_STATE[session_key] = {
                        "stage": "awaiting_booking_confirmation",
                        "service_id": service_id,
                    }
                    save_lead_checkpoint(tenant, session_id, SESSION_STATE[session_key])
                    _trace_stage_transition(
                        tenant,
                        session_id,
                        stage_before,
                        "awaiting_booking_confirmation",
                        reason="model_suggest_service",
                    )

            if intent not in {"greeting", "suggest_service", "fallback"}:
                intent = "fallback"

            if isinstance(message_text, str) and message_text.strip():
                _log_chat_state(
                    message=message,
                    session_id=session_id,
                    intent=intent,
                    stage_before=stage_before,
                    stage_after=_stage_name(SESSION_STATE.get(session_key)),
                )
                final_reply = _finalize_reply(
                    tenant=tenant,
                    session_id=session_id,
                    session_key=session_key,
                    message=message,
                    reply=message_text,
                    response_type=intent,
                    services=services,
                    profile=profile,
                    stage_after=_stage_name(SESSION_STATE.get(session_key)),
                )
                return final_reply, session_id

            trace_event(
                tenant,
                session_id,
                "FALLBACK_USED",
                reason="empty_message_text_after_normalization",
            )
            _log_chat_state(
                message=message,
                session_id=session_id,
                intent=intent,
                stage_before=stage_before,
                stage_after=_stage_name(SESSION_STATE.get(session_key)),
            )
            reply = _fallback_reply(profile)
            final_reply = _finalize_reply(
                tenant=tenant,
                session_id=session_id,
                session_key=session_key,
                message=message,
                reply=reply,
                response_type="fallback",
                services=services,
                profile=profile,
                stage_after=_stage_name(SESSION_STATE.get(session_key)),
            )
            return final_reply, session_id

        except json.JSONDecodeError:
            trace_event(
                tenant,
                session_id,
                "FALLBACK_USED",
                reason="json_decode_error",
            )
            _log_chat_state(
                message=message,
                session_id=session_id,
                intent="fallback",
                stage_before=stage_before,
                stage_after=_stage_name(SESSION_STATE.get(session_key)),
            )
            reply = raw_output or _fallback_reply(profile)
            final_reply = _finalize_reply(
                tenant=tenant,
                session_id=session_id,
                session_key=session_key,
                message=message,
                reply=reply,
                response_type="fallback",
                services=services,
                profile=profile,
                stage_after=_stage_name(SESSION_STATE.get(session_key)),
            )
            return final_reply, session_id

    except RateLimitError as exc:
        trace_event(
            tenant,
            session_id,
            "ERROR",
            source="ai_agent.generate_reply",
            error_type=type(exc).__name__,
            error=str(exc),
        )
        raise AIInferenceError(
            "The AI service is temporarily unavailable because the API quota is not active yet."
        )

    except OpenAIError as exc:
        trace_event(
            tenant,
            session_id,
            "ERROR",
            source="ai_agent.generate_reply",
            error_type=type(exc).__name__,
            error=str(exc),
        )
        raise AIInferenceError(
            "The AI service is temporarily unavailable right now. Please try again shortly."
        )

    except Exception as exc:
        trace_event(
            tenant,
            session_id,
            "ERROR",
            source="ai_agent.generate_reply",
            error_type=type(exc).__name__,
            error=str(exc),
        )
        raise

```

--------------------------------
File: clinic-ai-assistant-src/backend/app/services/config_loader.py
--------------------------------

```python
import json
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent.parent
PROFILES_DIR = BASE_DIR / "config" / "profiles"


class TenantConfigError(Exception):
    pass


class TenantNotFoundError(FileNotFoundError):
    pass


def _require_non_empty_string(section_name: str, payload: dict, field_name: str):
    value = payload.get(field_name)
    if not isinstance(value, str) or not value.strip():
        raise TenantConfigError(f"{section_name}.{field_name} is required")


def _require_object(section_name: str, payload):
    if not isinstance(payload, dict):
        raise TenantConfigError(f"{section_name} must be an object")
    return payload


def _require_list(section_name: str, payload: dict, field_name: str, *, required: bool):
    value = payload.get(field_name)
    if value is None and not required:
        return None
    if not isinstance(value, list):
        raise TenantConfigError(f"{section_name}.{field_name} must be a list")
    return value


def _validate_service(service: dict, index: int):
    if not isinstance(service, dict):
        raise TenantConfigError(f"services[{index}] must be an object")

    _require_non_empty_string(f"services[{index}]", service, "id")
    _require_non_empty_string(f"services[{index}]", service, "name")

    for list_field in ("keywords", "symptoms"):
        value = service.get(list_field)
        if value is not None and not isinstance(value, list):
            raise TenantConfigError(f"services[{index}].{list_field} must be a list")

    if "bookable" in service and not isinstance(service["bookable"], bool):
        raise TenantConfigError(f"services[{index}].bookable must be a boolean")


def _validate_profile(tenant: str, profile: dict):
    if not isinstance(profile, dict):
        raise TenantConfigError(f"Profile '{tenant}' must be a JSON object")

    business = _require_object(f"Profile '{tenant}'.business", profile.get("business"))
    _require_non_empty_string(f"Profile '{tenant}'.business", business, "name")
    _require_non_empty_string(f"Profile '{tenant}'.business", business, "type")
    _require_non_empty_string(f"Profile '{tenant}'.business", business, "language")

    prompt_template = _require_object(
        f"Profile '{tenant}'.prompt_template",
        profile.get("prompt_template"),
    )
    _require_non_empty_string(f"Profile '{tenant}'.prompt_template", prompt_template, "system")

    conversation = _require_object(f"Profile '{tenant}'.conversation", profile.get("conversation"))
    _require_non_empty_string(f"Profile '{tenant}'.conversation", conversation, "goal")

    services = profile.get("services")
    if not isinstance(services, list):
        raise TenantConfigError(f"Profile '{tenant}'.services must be a list")

    seen_service_ids = set()
    for index, service in enumerate(services):
        _validate_service(service, index)
        service_id = service["id"].strip()
        if service_id in seen_service_ids:
            raise TenantConfigError(f"Profile '{tenant}' contains duplicate service id '{service_id}'")
        seen_service_ids.add(service_id)

    actions = _require_object(f"Profile '{tenant}'.actions", profile.get("actions"))
    allow_booking = actions.get("allow_booking")
    if not isinstance(allow_booking, bool):
        raise TenantConfigError(f"Profile '{tenant}'.actions.allow_booking must be a boolean")

    collect_fields = _require_list(
        f"Profile '{tenant}'.actions",
        actions,
        "collect_contact_fields",
        required=False,
    )
    if allow_booking:
        if not collect_fields:
            raise TenantConfigError(
                f"Profile '{tenant}' enables booking but does not define collect_contact_fields"
            )
    elif collect_fields is None:
        collect_fields = []

    output_contract = _require_object(
        f"Profile '{tenant}'.output_contract",
        profile.get("output_contract"),
    )
    response_format = _require_object(
        f"Profile '{tenant}'.output_contract.response_format",
        output_contract.get("response_format"),
    )
    for field_name in ("intent", "service_id", "message"):
        _require_non_empty_string(
            f"Profile '{tenant}'.output_contract.response_format",
            response_format,
            field_name,
        )


def load_profile_config(tenant: str):
    profile_path = PROFILES_DIR / f"{tenant}.json"

    if not profile_path.exists():
        raise TenantNotFoundError(f"Profile '{tenant}' not found")

    try:
        with open(profile_path, "r", encoding="utf-8") as f:
            profile = json.load(f)
    except json.JSONDecodeError as exc:
        raise TenantConfigError(f"Profile '{tenant}' contains invalid JSON") from exc

    _validate_profile(tenant, profile)
    return profile


def load_public_profile_config(tenant: str) -> dict:
    profile = load_profile_config(tenant)
    business = profile.get("business", {})
    agent = profile.get("agent", {})
    services = profile.get("services", [])

    public_services = [
        {
            "id": service.get("id"),
            "name": service.get("name"),
            "description": service.get("description"),
            "price_range": service.get("price_range"),
            "image": service.get("image"),
            "bookable": service.get("bookable", False),
        }
        for service in services
    ]

    return {
        "business": {
            "id": business.get("id", tenant),
            "name": business.get("name", "Assistant"),
            "type": business.get("type"),
            "language": business.get("language", "en"),
            "contact": business.get("contact", {}),
        },
        "assistant": {
            "name": agent.get("name") or business.get("name", "Assistant"),
        },
        "conversation": {
            "greeting": profile.get("conversation", {}).get("greeting"),
        },
        "services": public_services,
    }

```

--------------------------------
File: clinic-ai-assistant-src/backend/app/services/lead_store.py
--------------------------------

```python
import json
import logging
import sqlite3
from datetime import datetime, timezone
from pathlib import Path

from app.services.session_trace_logger import trace_event


logger = logging.getLogger(__name__)
BASE_DIR = Path(__file__).resolve().parent.parent.parent
DB_PATH = BASE_DIR / "clinic_ai_assistant.db"


def _connect():
    connection = sqlite3.connect(DB_PATH)
    connection.row_factory = sqlite3.Row
    return connection


def init_leads_db():
    with _connect() as connection:
        connection.execute(
            """
            CREATE TABLE IF NOT EXISTS leads (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                tenant TEXT NOT NULL,
                session_id TEXT NOT NULL,
                contact_name TEXT,
                contact_phone TEXT,
                contact_email TEXT,
                collected_data_json TEXT NOT NULL,
                created_at TEXT NOT NULL,
                updated_at TEXT NOT NULL,
                UNIQUE(tenant, session_id)
            )
            """
        )
        connection.commit()


def save_lead_checkpoint(tenant: str, session_id: str, state: dict):
    now = datetime.now(timezone.utc).isoformat()
    data = state.get("data", {})
    stage = state.get("stage")

    trace_event(
        tenant,
        session_id,
        "CHECKPOINT_SAVE",
        action="attempt",
        stage=stage,
        data=data,
    )

    try:
        with _connect() as connection:
            connection.execute(
                """
                INSERT INTO leads (
                    tenant,
                    session_id,
                    contact_name,
                    contact_phone,
                    contact_email,
                    collected_data_json,
                    created_at,
                    updated_at
                )
                VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                ON CONFLICT(tenant, session_id) DO UPDATE SET
                    contact_name = excluded.contact_name,
                    contact_phone = excluded.contact_phone,
                    contact_email = excluded.contact_email,
                    collected_data_json = excluded.collected_data_json,
                    updated_at = excluded.updated_at
                """,
                (
                    tenant,
                    session_id,
                    data.get("name"),
                    data.get("phone"),
                    data.get("email"),
                    json.dumps(state, ensure_ascii=False),
                    now,
                    now,
                ),
            )
            connection.commit()
    except sqlite3.Error as exc:
        trace_event(
            tenant,
            session_id,
            "ERROR",
            source="lead_store.save_lead_checkpoint",
            error_type=type(exc).__name__,
            error=str(exc),
        )
        logger.exception("Failed to save lead checkpoint")
        raise

    trace_event(
        tenant,
        session_id,
        "DB_UPDATE",
        stage=stage,
        contact_name=data.get("name"),
        contact_phone=data.get("phone"),
        contact_email=data.get("email"),
    )

    trace_event(
        tenant,
        session_id,
        "LEAD_FINAL_SAVE" if stage == "completed" else "CHECKPOINT_SAVE",
        action="success",
        stage=stage,
    )


def load_lead_checkpoint(tenant: str, session_id: str):
    trace_event(
        tenant,
        session_id,
        "CHECKPOINT_LOAD",
        action="attempt",
    )

    try:
        with _connect() as connection:
            row = connection.execute(
                """
                SELECT collected_data_json
                FROM leads
                WHERE tenant = ? AND session_id = ?
                """,
                (tenant, session_id),
            ).fetchone()
    except sqlite3.Error as exc:
        trace_event(
            tenant,
            session_id,
            "ERROR",
            source="lead_store.load_lead_checkpoint",
            error_type=type(exc).__name__,
            error=str(exc),
        )
        logger.exception("Failed to load lead checkpoint")
        raise

    if not row:
        trace_event(
            tenant,
            session_id,
            "CHECKPOINT_LOAD",
            action="miss",
        )
        return None

    state = json.loads(row["collected_data_json"])
    trace_event(
        tenant,
        session_id,
        "CHECKPOINT_LOAD",
        action="hit",
        stage=state.get("stage"),
        state=state,
    )
    return state

```

--------------------------------
File: clinic-ai-assistant-src/backend/app/services/session_trace_logger.py
--------------------------------

```python
import json
import logging
import os
import threading
from datetime import datetime, timezone
from pathlib import Path

from dotenv import dotenv_values


logger = logging.getLogger(__name__)
_TRACE_LOCK = threading.Lock()
_TRACE_FILES: dict[str, Path] = {}

BASE_DIR = Path(__file__).resolve().parent.parent.parent
TRACE_DIR = BASE_DIR / "runtime_traces"
SETTINGS_PATH = BASE_DIR.parent / "configs" / "settings.env"


def _utc_now() -> str:
    return datetime.now(timezone.utc).isoformat()


def _trace_key(tenant: str, session_id: str) -> str:
    return f"{tenant}:{session_id}"


def _sanitize_filename_part(value: str) -> str:
    return "".join(char if char.isalnum() or char in {"-", "_"} else "_" for char in value)


def _settings_trace_enabled() -> bool:
    if not SETTINGS_PATH.exists():
        return False

    settings = dotenv_values(SETTINGS_PATH)
    userlogging = settings.get("USERLOGGING", "off")
    debug_session_trace = settings.get("DEBUG_SESSION_TRACE", "false")

    userlogging_enabled = str(userlogging).strip().lower() == "on"
    debug_trace_enabled = str(debug_session_trace).strip().lower() == "true"

    return userlogging_enabled and debug_trace_enabled


def is_session_trace_enabled() -> bool:
    return _settings_trace_enabled()


def _resolve_trace_file(tenant: str, session_id: str) -> Path:
    trace_key = _trace_key(tenant, session_id)
    existing_path = _TRACE_FILES.get(trace_key)
    if existing_path:
        return existing_path

    TRACE_DIR.mkdir(parents=True, exist_ok=True)
    timestamp = datetime.now(timezone.utc).strftime("%Y-%m-%d_%H-%M-%S")
    filename = (
        f"trace_{timestamp}_{_sanitize_filename_part(tenant)}_"
        f"{_sanitize_filename_part(session_id)}.txt"
    )
    trace_path = TRACE_DIR / filename
    _TRACE_FILES[trace_key] = trace_path

    header = [
        "=" * 50,
        "TRACE START",
        f"timestamp={_utc_now()}",
        f"tenant={tenant}",
        f"session_id={session_id}",
        f"trace_file={trace_path.name}",
        "=" * 50,
        "",
    ]
    trace_path.write_text("\n".join(header), encoding="utf-8")
    return trace_path


def trace_event(tenant: str, session_id: str, event: str, **fields):
    if not is_session_trace_enabled() or not tenant or not session_id:
        return

    try:
        with _TRACE_LOCK:
            trace_path = _resolve_trace_file(tenant, session_id)
            lines = [f"[{_utc_now()}] {event}"]
            for key, value in fields.items():
                if value is None:
                    continue
                if isinstance(value, (dict, list)):
                    rendered = json.dumps(value, ensure_ascii=False)
                else:
                    rendered = str(value)
                lines.append(f"{key}={rendered}")
            lines.append("")
            with trace_path.open("a", encoding="utf-8") as trace_file:
                trace_file.write("\n".join(lines))
                trace_file.write("\n")
    except Exception as exc:
        logger.warning("Session trace write failed: %s", exc)


def get_trace_directory() -> Path:
    return TRACE_DIR

```

--------------------------------
File: clinic-ai-assistant-src/backend/app/config/profiles/generic.json
--------------------------------

```json
{
  "business": {
    "id": "generic",
    "name": "Example Business",
    "type": "service",
    "language": "en",
    "description": "Business that interacts with customers through messaging",
    "contact": {
      "phone": "",
      "email": "",
      "address": ""
    }
  },
  "agent": {
    "name": "Assistant",
    "role": "Customer support assistant",
    "tone": "professional and friendly"
  },
  "prompt_template": {
    "system": "You are an AI assistant for {{business_name}}. Your goal: {{goal}}."
  },
  "conversation": {
    "greeting": "Hello! How can I help you today?",
    "goal": "Help customers, answer questions, and guide them to relevant services.",
    "rules": [
      "Stay within the business context.",
      "Respond briefly and clearly."
    ],
    "decision_rules": [
      "Return only valid JSON.",
      "Use fallback when the request is unclear."
    ],
    "fallback_message": "I'm sorry, I couldn't understand that. Could you clarify?"
  },
  "conversation_rules": {
    "booking_confirm_words": ["да", "da", "yes", "ok", "okej", "okay", "може", "moze"],
    "greeting_triggers": ["zdravo", "zdravoo", "hello", "hi"],
    "service_list_triggers": ["што услуги", "кои услуги", "услуга", "услуги", "услуги нудите", "што нудите", "usluga", "uslugi", "service", "services", "koi uslugi", "shto uslugi", "uslugi nudite", "shto nudite", "sto nudite"],
    "price_triggers": ["цена", "колку чини", "колкава е цената", "cena", "kolku chini", "kolku cini", "price"],
    "contact_clarification_prefixes": ["dali", "дали", "mozhe", "moze", "може"],
    "contact_clarification_phrases": ["ili", "или", "sluzbenata", "sluzbena", "privatnata", "privatna", "која", "kakva", "каква", "which one"],
    "service_detail_triggers": ["анестез", "anestez", "инјекц", "inekc", "боли", "boli", "боли ли", "koliko tra", "колку трае", "дали се става", "dali se stava", "дали има", "dali ima"],
    "safe_detail_fallback": "That can depend on the specific treatment. The dentist should assess that during an examination.",
    "service_clarification_triggers": ["soodvetna usluga", "koja usluga", "kakva usluga mi treba", "recommend service"],
    "service_clarification_specific_triggers": ["koja usluga mi treba"],
    "service_description_triggers": ["kazete mi za", "shto e", "objasni mi", "кажете ми за", "што е", "објасни ми"],
    "consultation_explanation_triggers": ["каква", "што е", "објасни", "kakva", "shto e", "objasni"],
    "broad_pricing_price_terms": ["цена", "цени", "колку", "чини", "чинат", "cena", "ceni", "kolku", "chini", "cini", "price", "prices"],
    "broad_pricing_service_terms": ["услуга", "услуги", "услугите", "usluga", "uslugi", "service", "services"],
    "casual_reply_patterns": [
      { "triggers": ["фала", "благодарам", "fala", "blagodaram", "thanks", "thank you"], "reply_key": "thanks" },
      { "triggers": ["wow", "вау", "леле"], "reply_key": "wow" },
      { "triggers": ["супер", "одлично", "super", "odlichno", "odlicno", "great"], "reply_key": "positive" }
    ]
  },
  "reply_texts": {
    "greeting_short": "Hello! How can I help you?",
    "service_clarification": "Tell me briefly what you need help with, and I can guide you to the most suitable service.",
    "service_clarification_specific": {
      "koja_usluga_mi_treba": "Tell me a bit more about what you need, and I can guide you to the most suitable service."
    },
    "casual_replies": {
      "thanks": "You're welcome. Feel free to tell me what you need.",
      "wow": "Glad I could help. If you want, I can guide you to the right service.",
      "positive": "Glad to hear that. Let me know if you'd like help with a service or booking."
    },
    "price_templates": {
      "numeric": "{service_name} costs around {price}{currency}.",
      "text": "{service_name} is {price}.",
      "free": "{service_name} is free.",
      "range": "The orientation price range for {service_name_lower} is {price_range}."
    },
    "price_followup": "For an exact estimate, the best next step is a short consultation.",
    "service_description_template": "{article_name} is {description}\n\n{followup}",
    "service_description_followup": "If you want, I can also help check whether that is the right option for you.",
    "field_prompts": {
      "name": "Please share your name.",
      "phone": "Please share your phone number.",
      "email": "Please share your email address."
    },
    "contact_clarification_replies": {
      "name": "Please share the name you want us to use. {field_prompt}",
      "phone": "You can leave the number where we can reach you most easily. {field_prompt}",
      "email": "Either a work or private email is fine. {field_prompt}",
      "default": "{field_prompt}"
    },
    "booking_completed": "Thank you. Your booking request has been received. The business will contact you."
  },
  "repetition_responses": {
    "broad_pricing": "Prices depend on the specific service. If you want, tell me exactly what interests you and I can give you orientation.",
    "service_list": "I already listed the services, but I can guide you more specifically if you want.",
    "consultation_explanation": "It is an initial review and conversation to see what is most appropriate for you. If you want, we can continue with booking right away."
  },
  "services": [],
  "actions": {
    "allow_booking": false,
    "collect_contact_fields": [],
    "handoff_enabled": false,
    "order_flow_enabled": false
  },
  "output_contract": {
    "unknown_service_id": "unknown",
    "response_format": {
      "intent": "string",
      "service_id": "string",
      "message": "string"
    }
  },
  "knowledge": {
    "faq": [],
    "source": "static",
    "notes": "Placeholder for knowledge base integration later"
  }
}

```

--------------------------------
File: clinic-ai-assistant-src/backend/app/config/profiles/milena_dental.json
--------------------------------

```json
{
  "business": {
    "id": "milena_dental",
    "name": "Асистент на ПЗУ Д-р Милена Игнатовски",
    "type": "dentist",
    "language": "mk",
    "contact": {
      "phone": "+38970000000",
      "email": "info@milena.mk",
      "address": "Скопје"
    }
  },
  "agent": {
    "name": "Асистент",
    "role": "Асистент за стоматолошки прашања и закажување",
    "tone": "професионален, смирен и пријателски"
  },
  "prompt_template": {
    "system": "You are an AI assistant for {{business_name}}. Your goal: {{goal}}. Use only the provided clinic catalog and consultation rules. Consultation is the main booking path unless the catalog clearly supports something else."
  },
  "conversation": {
    "greeting": "Здраво,\n\nЈас сум асистент на ПЗУ Д-р Милена Игнатовски. Кажете ми што ве интересира или каква непријатност имате, па ќе ве насочам.\n\nАко не е јасно која услуга е соодветна, можеме да почнеме со консултација.",
    "goal": "Да им помогнам на пациентите да се ориентираат според симптом, потреба или естетска цел и да ги насочам кон соодветна стоматолошка услуга или кон стоматолошка консултација како главен чекор за закажување.",
    "rules": [
      "Секогаш одговарај на македонски јазик со кирилица.",
      "Не поставувај дијагноза и не тврди дека пациентот сигурно има конкретна состојба.",
      "Предлагај само услуги што постојат во каталогот на клиниката.",
      "Кога состојбата не е доволно јасна, предложи стоматолошка консултација.",
      "Консултацијата е главниот термин за закажување кога пациентот сака преглед, мислење, план за третман или не е сигурен што му е потребно.",
      "Ако пациентот праша општо што нуди клиниката, накратко наброј категории или релевантни услуги без да форсираш една процедура.",
      "Препорачај конкретна процедура само кога има јасна врска меѓу барањето на пациентот и описот на услугата.",
      "Не кажувај точна цена ако не е потврдена во каталогот.",
      "Кога цената варира, кажи дека има ценовен опсег и дека конечната проценка зависи од преглед.",
      "Ако барањето е надвор од стоматолошки контекст, љубезно кажи дека асистентот помага само за стоматолошки прашања.",
      "Ако пациентот одбие закажување, не притискај и заврши љубезно.",
      "Користи природен јазик како човечка комуникација, без крути шаблони."
    ],
    "decision_rules": [
      "Return only valid JSON.",
      "Do not return markdown.",
      "Do not return explanation outside JSON.",
      "Use greeting for opening or social messages.",
      "Use suggest_service when the request clearly maps to one catalog service or to the consultation entry.",
      "Use confirm_booking when the patient clearly confirms scheduling.",
      "Prefer the consultation service when the patient wants an appointment, a checkup, an opinion, or when the correct procedure is uncertain.",
      "Use fallback when the request is unclear, outside scope, or no safe catalog match can be made.",
      "The message value must be short, safe, natural, and written in Macedonian Cyrillic."
    ],
    "fallback_message": "Извинете, не сум сигурен дека точно ја разбрав пораката. Можете ли накратко да ми опишете што ве мачи или што сакате да направите?"
  },
  "conversation_rules": {
    "booking_confirm_words": ["да", "da", "yes", "ok", "okej", "okay", "може", "moze"],
    "greeting_triggers": ["zdravo", "zdravoo", "hello", "hi"],
    "service_list_triggers": ["што услуги", "кои услуги", "услуга", "услуги", "услуги нудите", "што нудите", "usluga", "uslugi", "service", "services", "koi uslugi", "shto uslugi", "uslugi nudite", "shto nudite", "sto nudite"],
    "price_triggers": ["цена", "колку чини", "колкава е цената", "cena", "kolku chini", "kolku cini", "price"],
    "contact_clarification_prefixes": ["dali", "дали", "mozhe", "moze", "може"],
    "contact_clarification_phrases": ["ili", "или", "sluzbenata", "sluzbena", "privatnata", "privatna", "која", "kakva", "каква", "which one"],
    "service_detail_triggers": ["анестез", "anestez", "инјекц", "inekc", "боли", "boli", "боли ли", "koliko tra", "колку трае", "дали се става", "dali se stava", "дали има", "dali ima"],
    "safe_detail_fallback": "Тоа може да зависи од конкретниот третман. Најдобро е стоматологот да процени на преглед.",
    "service_clarification_triggers": ["soodvetna usluga", "koja usluga", "kakva usluga mi treba", "recommend service"],
    "service_clarification_specific_triggers": ["koja usluga mi treba"],
    "service_description_triggers": ["kazete mi za", "shto e", "objasni mi", "кажете ми за", "што е", "објасни ми"],
    "consultation_explanation_triggers": ["каква", "што е", "објасни", "kakva", "shto e", "objasni"],
    "broad_pricing_price_terms": ["цена", "цени", "колку", "чини", "чинат", "cena", "ceni", "kolku", "chini", "cini", "price", "prices"],
    "broad_pricing_service_terms": ["услуга", "услуги", "услугите", "usluga", "uslugi", "service", "services"],
    "casual_reply_patterns": [
      { "triggers": ["фала", "благодарам", "fala", "blagodaram", "thanks", "thank you"], "reply_key": "thanks" },
      { "triggers": ["wow", "вау", "леле"], "reply_key": "wow" },
      { "triggers": ["супер", "одлично", "super", "odlichno", "odlicno", "great"], "reply_key": "positive" }
    ]
  },
  "reply_texts": {
    "greeting_short": "Здраво, како можам да ви помогнам?",
    "service_clarification": "Кажете ми накратко што ве мачи или што сакате да подобрите, па ќе ве насочам кон најсоодветна услуга или консултација.",
    "service_clarification_specific": {
      "koja_usluga_mi_treba": "За да ве насочам најдобро, кажете ми дали имате болка, сакате естетска корекција или сакате само преглед."
    },
    "casual_replies": {
      "thanks": "Ви благодарам. Ако сакате, слободно кажете што ве интересира.",
      "wow": "Ви благодарам, драго ми е што помогнав. Ако сакате, можам и да ве насочам кон соодветна услуга или консултација.",
      "positive": "Драго ми е. Кажете ако сакате да провериме услуга или да закажеме консултација."
    },
    "price_templates": {
      "numeric": "{service_name} чини околу {price}{currency}.",
      "text": "{service_name} е {price}.",
      "free": "{service_name} е бесплатна.",
      "range": "Ориентацискиот ценовен опсег за {service_name_lower} е {price_range}."
    },
    "price_followup": "За точна проценка најдобро е да се направи кратка консултација.",
    "service_description_template": "{article_name} е {description}\n\n{followup}",
    "service_description_followup": "Ако сакате, можеме кратко да провериме дали тоа е соодветната опција за вас.",
    "field_prompts": {
      "name": "Ве молам кажете ни го вашето име.",
      "phone": "Ве молам кажете ни го вашиот телефон.",
      "email": "Ве молам кажете ни ја вашата е-пошта."
    },
    "contact_clarification_replies": {
      "name": "Слободно оставете го името на кое сакате да ве евидентираме. {field_prompt}",
      "phone": "Може да оставите број на кој најлесно можеме да ве добиеме. {field_prompt}",
      "email": "Може и службената и приватната. {field_prompt}",
      "default": "{field_prompt}"
    },
    "booking_completed": "Ви благодарам. Вашето барање за термин е примено. Клиниката ќе ве контактира."
  },
  "repetition_responses": {
    "broad_pricing": "Цените зависат од конкретната услуга. Ако сакате, кажете ми што точно ве интересира, на пример белење, пломбирање или консултација, па ќе ви дадам ориентација.",
    "service_list": "Веќе ви ги набројав услугите, но ако сакате можам и поконкретно да ве насочам. Кажете ми дали ве интересира естетика, болка, чистење или консултација.",
    "consultation_explanation": "Тоа е почетен преглед и разговор за да се види што е најсоодветно за вас. Ако сакате, можеме и веднаш да продолжиме со закажување."
  },
  "комуникациски_правила": [
    "AI не поставува дијагноза.",
    "AI предлага консултација кога состојбата не е сигурна.",
    "AI не дава цена ако не е сигурна.",
    "AI зборува како асистент, не како стоматолог.",
    "Одговорите мора да звучат природно, како човечка комуникација.",
    "Може да каже: „можеби има процес, најдобро е да се провери на консултација“."
  ],
  "консултација": {
    "тип": "дијагностичка консултација",
    "траење": "20 минути",
    "цена": "бесплатно",
    "денови": [
      "Петок"
    ],
    "опис": "Преглед и разговор за можни решенија и план за третман."
  },
  "категории": [
    {
      "име": "Превентивна стоматологија",
      "опис": "Услуги за одржување на орална хигиена и превенција на натамошни проблеми.",
      "услуги": [
        {
          "id": "cleaning_consult",
          "име": "Чистење на забен камен",
          "aliases": [
            "забен камен",
            "чистење",
            "чистење на каменец",
            "чистење на заби"
          ],
          "опис": "Професионално чистење на наслаги и забен камен за подобра орална хигиена и превенција.",
          "препорачано_за": [
            "наслаги на заби",
            "одржување на хигиена",
            "превентивен третман"
          ]
        }
      ]
    },
    {
      "име": "Реставративна стоматологија",
      "опис": "Третмани за санација и обнова на оштетен заб.",
      "услуги": [
        {
          "id": "filling",
          "име": "Пломбирање",
          "aliases": [
            "пломба",
            "ставање пломба",
            "поправка на заб",
            "затворање дупка"
          ],
          "опис": "Реставративен третман за санација на кариес или оштетување на забот со соодветен пломбен материјал.",
          "ценовен_опсег": "800-2500 денари",
          "препорачано_за": [
            "дупка во заб",
            "оштетен заб",
            "кариес",
            "болка поврзана со оштетување на забот"
          ]
        }
      ]
    },
    {
      "име": "Ендодонција",
      "опис": "Третмани кога проблемот навлегува во внатрешноста на забот и коренскиот канал.",
      "услуги": [
        {
          "id": "root_canal",
          "име": "Лекување на коренски канал",
          "aliases": [
            "канал",
            "лекување канал",
            "коренски канал",
            "ендодонција"
          ],
          "опис": "Третман за чистење и лекување на коренскиот канал кога е зафатена внатрешноста на забот.",
          "ценовен_опсег": "400 денари со осигурување, околу 1000 денари приватно",
          "препорачано_за": [
            "силна забоболка",
            "проблем со нерв",
            "воспаление во заб",
            "потреба од лекување канал"
          ]
        }
      ]
    },
    {
      "име": "Протетика",
      "опис": "Решенија за функционална и естетска надокнада на оштетени или изгубени заби.",
      "услуги": [
        {
          "id": "crowns",
          "име": "Коронки",
          "aliases": [
            "коронка",
            "забна коронка",
            "круна на заб"
          ],
          "опис": "Протетско решение за заштита и обнова на заб со поголемо оштетување.",
          "ценовен_опсег": "80-300 евра",
          "препорачано_за": [
            "значително оштетен заб",
            "заштита на ослабен заб",
            "протетска обнова"
          ]
        },
        {
          "id": "bridges",
          "име": "Мостови",
          "aliases": [
            "мост",
            "забен мост",
            "протетски мост"
          ],
          "опис": "Протетско решение за надоместување на еден или повеќе заби со фиксна конструкција.",
          "препорачано_за": [
            "недостасува заб",
            "фиксна надокнада",
            "обнова на џвакање и насмевка"
          ]
        }
      ]
    },
    {
      "име": "Естетска стоматологија",
      "опис": "Процедури насочени кон подобрување на изгледот на насмевката.",
      "услуги": [
        {
          "id": "teeth_whitening",
          "име": "Белење на заби",
          "aliases": [
            "белење",
            "осветлување на заби",
            "belenje",
            "beleenje",
            "white teeth",
            "teeth whitening"
          ],
          "опис": "Естетска процедура за осветлување на забите. Потребни се 1 до 3 сесии во зависност од состојбата.",
          "цена": 5000,
          "валута": "денари",
          "препорачано_за": [
            "естетски подобрувања",
            "осветлување на насмевка"
          ]
        },
        {
          "id": "composite_veneers",
          "име": "Композитни винири",
          "aliases": [
            "композитни фасети",
            "композитни винири",
            "естетска корекција"
          ],
          "опис": "Естетска корекција на форма, боја или мали неправилности со композитен материјал.",
          "препорачано_за": [
            "естетска корекција",
            "корекција на форма на заб",
            "подобрување на насмевка"
          ]
        },
        {
          "id": "ceramic_veneers",
          "име": "Керамички винири",
          "aliases": [
            "керамички фасети",
            "керамички винири",
            "порцелански винири"
          ],
          "опис": "Естетско решение за долготрајно подобрување на изгледот на предните заби со керамички изработки.",
          "препорачано_за": [
            "естетска трансформација",
            "подобрување на боја и форма",
            "поправка на изглед на предни заби"
          ]
        }
      ]
    },
    {
      "име": "Консултација",
      "опис": "Прв контакт за проценка, советување и насочување кон најсоодветен третман.",
      "услуги": [
        {
          "id": "consultation",
          "име": "Стоматолошка консултација",
          "aliases": [
            "консултација",
            "konsultacija",
            "преглед",
            "советување",
            "мислење",
            "прв преглед",
            "закажување термин"
          ],
          "опис": "Разговор и почетен преглед за да се процени што е најсоодветно и да се направи план за следни чекори.",
          "цена": "бесплатно",
          "препорачано_за": [
            "нејасни симптоми",
            "потреба од мислење",
            "план за третман",
            "закажување термин"
          ]
        }
      ]
    }
  ],
  "services": [
    {
      "id": "consultation",
      "name": "Стоматолошка консултација",
      "article_name": "Стоматолошката консултација",
      "description": "Разговор и почетен преглед за да се процени што е најсоодветно и да се направи план за следни чекори.",
      "keywords": [
        "консултација",
        "konsultacija",
        "преглед",
        "советување",
        "мислење",
        "прв преглед",
        "закажување термин"
      ],
      "symptoms": [
        "нејасни симптоми",
        "потреба од мислење",
        "план за третман",
        "потребен преглед"
      ],
      "price": "бесплатно",
      "image": "/services/consultation.jpg",
      "bookable": true,
      "priority": 1,
      "category": "Консултација",
      "aliases": [
        "консултација",
        "konsultacija",
        "преглед",
        "советување",
        "мислење",
        "прв преглед",
        "закажување термин"
      ],
      "име": "Стоматолошка консултација",
      "опис": "Разговор и почетен преглед за да се процени што е најсоодветно и да се направи план за следни чекори.",
      "цена": "бесплатно",
      "препорачано_за": [
        "нејасни симптоми",
        "потреба од мислење",
        "план за третман",
        "закажување термин"
      ]
    },
    {
      "id": "cleaning_consult",
      "name": "Чистење на забен камен",
      "description": "Професионално чистење на наслаги и забен камен за подобра орална хигиена и превенција.",
      "keywords": [
        "забен камен",
        "чистење",
        "чистење на каменец",
        "чистење на заби"
      ],
      "symptoms": [
        "наслаги на заби",
        "потреба од чистење",
        "одржување на хигиена"
      ],
      "image": "/services/cleaning.jpg",
      "bookable": false,
      "priority": 2,
      "category": "Превентивна стоматологија",
      "aliases": [
        "забен камен",
        "чистење",
        "чистење на каменец",
        "чистење на заби"
      ],
      "име": "Чистење на забен камен",
      "опис": "Професионално чистење на наслаги и забен камен за подобра орална хигиена и превенција.",
      "препорачано_за": [
        "наслаги на заби",
        "одржување на хигиена",
        "превентивен третман"
      ]
    },
    {
      "id": "filling",
      "name": "Пломбирање",
      "description": "Реставративен третман за санација на кариес или оштетување на забот со соодветен пломбен материјал.",
      "keywords": [
        "пломба",
        "ставање пломба",
        "поправка на заб",
        "затворање дупка"
      ],
      "symptoms": [
        "дупка во заб",
        "оштетен заб",
        "кариес",
        "болка поврзана со оштетување на забот"
      ],
      "price_range": "800-2500 денари",
      "image": "/services/filling.jpg",
      "bookable": false,
      "priority": 3,
      "category": "Реставративна стоматологија",
      "aliases": [
        "пломба",
        "ставање пломба",
        "поправка на заб",
        "затворање дупка"
      ],
      "име": "Пломбирање",
      "опис": "Реставративен третман за санација на кариес или оштетување на забот со соодветен пломбен материјал.",
      "ценовен_опсег": "800-2500 денари",
      "препорачано_за": [
        "дупка во заб",
        "оштетен заб",
        "кариес",
        "болка поврзана со оштетување на забот"
      ]
    },
    {
      "id": "root_canal",
      "name": "Лекување на коренски канал",
      "description": "Третман за чистење и лекување на коренскиот канал кога е зафатена внатрешноста на забот.",
      "keywords": [
        "канал",
        "лекување канал",
        "коренски канал",
        "ендодонција"
      ],
      "symptoms": [
        "силна забоболка",
        "проблем со нерв",
        "воспаление во заб",
        "потреба од лекување канал"
      ],
      "price_range": "400 денари со осигурување, околу 1000 денари приватно",
      "image": "/services/root-canal.jpg",
      "bookable": false,
      "priority": 4,
      "category": "Ендодонција",
      "aliases": [
        "канал",
        "лекување канал",
        "коренски канал",
        "ендодонција"
      ],
      "име": "Лекување на коренски канал",
      "опис": "Третман за чистење и лекување на коренскиот канал кога е зафатена внатрешноста на забот.",
      "ценовен_опсег": "400 денари со осигурување, околу 1000 денари приватно",
      "препорачано_за": [
        "силна забоболка",
        "проблем со нерв",
        "воспаление во заб",
        "потреба од лекување канал"
      ]
    },
    {
      "id": "crowns",
      "name": "Коронки",
      "description": "Протетско решение за заштита и обнова на заб со поголемо оштетување.",
      "keywords": [
        "коронка",
        "забна коронка",
        "круна на заб"
      ],
      "symptoms": [
        "значително оштетен заб",
        "заштита на ослабен заб",
        "протетска обнова"
      ],
      "price_range": "80-300 евра",
      "image": "/services/crowns.jpg",
      "bookable": false,
      "priority": 5,
      "category": "Протетика",
      "aliases": [
        "коронка",
        "забна коронка",
        "круна на заб"
      ],
      "име": "Коронки",
      "опис": "Протетско решение за заштита и обнова на заб со поголемо оштетување.",
      "ценовен_опсег": "80-300 евра",
      "препорачано_за": [
        "значително оштетен заб",
        "заштита на ослабен заб",
        "протетска обнова"
      ]
    },
    {
      "id": "bridges",
      "name": "Мостови",
      "description": "Протетско решение за надоместување на еден или повеќе заби со фиксна конструкција.",
      "keywords": [
        "мост",
        "забен мост",
        "протетски мост"
      ],
      "symptoms": [
        "недостасува заб",
        "фиксна надокнада",
        "обнова на џвакање и насмевка"
      ],
      "image": "/services/bridges.jpg",
      "bookable": false,
      "priority": 6,
      "category": "Протетика",
      "aliases": [
        "мост",
        "забен мост",
        "протетски мост"
      ],
      "име": "Мостови",
      "опис": "Протетско решение за надоместување на еден или повеќе заби со фиксна конструкција.",
      "препорачано_за": [
        "недостасува заб",
        "фиксна надокнада",
        "обнова на џвакање и насмевка"
      ]
    },
    {
      "id": "teeth_whitening",
      "name": "Белење на заби",
      "article_name": "Белењето на заби",
      "description": "Естетска процедура за осветлување на забите. Потребни се 1 до 3 сесии во зависност од состојбата.",
      "keywords": [
        "белење",
        "осветлување на заби",
        "belenje",
        "beleenje",
        "white teeth",
        "teeth whitening"
      ],
      "symptoms": [
        "естетски подобрувања",
        "осветлување на насмевка"
      ],
      "price": 5000,
      "image": "/services/whitening.jpg",
      "bookable": false,
      "priority": 7,
      "category": "Естетска стоматологија",
      "aliases": [
        "белење",
        "осветлување на заби",
        "belenje",
        "beleenje",
        "white teeth",
        "teeth whitening"
      ],
      "име": "Белење на заби",
      "опис": "Естетска процедура за осветлување на забите. Потребни се 1 до 3 сесии во зависност од состојбата.",
      "цена": 5000,
      "валута": "денари",
      "препорачано_за": [
        "естетски подобрувања",
        "осветлување на насмевка"
      ]
    },
    {
      "id": "composite_veneers",
      "name": "Композитни винири",
      "description": "Естетска корекција на форма, боја или мали неправилности со композитен материјал.",
      "keywords": [
        "композитни фасети",
        "композитни винири",
        "естетска корекција"
      ],
      "symptoms": [
        "естетска корекција",
        "корекција на форма на заб",
        "подобрување на насмевка"
      ],
      "image": "/services/composite-veneers.jpg",
      "bookable": false,
      "priority": 8,
      "category": "Естетска стоматологија",
      "aliases": [
        "композитни фасети",
        "композитни винири",
        "естетска корекција"
      ],
      "име": "Композитни винири",
      "опис": "Естетска корекција на форма, боја или мали неправилности со композитен материјал.",
      "препорачано_за": [
        "естетска корекција",
        "корекција на форма на заб",
        "подобрување на насмевка"
      ]
    },
    {
      "id": "ceramic_veneers",
      "name": "Керамички винири",
      "description": "Естетско решение за долготрајно подобрување на изгледот на предните заби со керамички изработки.",
      "keywords": [
        "керамички фасети",
        "керамички винири",
        "порцелански винири"
      ],
      "symptoms": [
        "естетска трансформација",
        "подобрување на боја и форма",
        "поправка на изглед на предни заби"
      ],
      "image": "/services/ceramic-veneers.jpg",
      "bookable": false,
      "priority": 9,
      "category": "Естетска стоматологија",
      "aliases": [
        "керамички фасети",
        "керамички винири",
        "порцелански винири"
      ],
      "име": "Керамички винири",
      "опис": "Естетско решение за долготрајно подобрување на изгледот на предните заби со керамички изработки.",
      "препорачано_за": [
        "естетска трансформација",
        "подобрување на боја и форма",
        "поправка на изглед на предни заби"
      ]
    }
  ],
  "actions": {
    "allow_booking": true,
    "collect_contact_fields": [
      "name",
      "phone",
      "email"
    ]
  },
  "output_contract": {
    "unknown_service_id": "unknown",
    "response_format": {
      "intent": "string",
      "service_id": "string",
      "message": "string"
    }
  },
  "knowledge": {
    "faq": [],
    "catalog_model": "clinical_categories_with_consultation_primary",
    "notes": "Категориите се главниот човечки преглед на каталогот. Полето services останува како компатибилен рамен индекс за тековниот backend."
  }
}

```

--------------------------------
File: clinic-ai-assistant-src/backend/app/config/profiles/risto.json
--------------------------------

```json
{
  "business": {
    "id": "risto",
    "name": "Risto",
    "type": "service",
    "language": "en",
    "description": "Business that interacts with customers through messaging",
    "contact": {
      "phone": "",
      "email": "",
      "address": ""
    }
  },
  "agent": {
    "name": "Assistant",
    "role": "Customer support assistant",
    "tone": "professional and friendly"
  },
  "prompt_template": {
    "system": "You are an AI assistant for {{business_name}}. Your goal: {{goal}}."
  },
  "conversation": {
    "greeting": "Hello! How can I help you today?",
    "goal": "Help customers, answer questions, and guide them to relevant services.",
    "rules": [
      "Stay within the business context.",
      "Respond briefly and clearly."
    ],
    "decision_rules": [
      "Return only valid JSON.",
      "Use fallback when the request is unclear."
    ],
    "fallback_message": "I'm sorry, I couldn't understand that. Could you clarify?"
  },
  "conversation_rules": {
    "booking_confirm_words": ["да", "da", "yes", "ok", "okej", "okay", "може", "moze"],
    "greeting_triggers": ["zdravo", "zdravoo", "hello", "hi"],
    "service_list_triggers": ["што услуги", "кои услуги", "услуга", "услуги", "услуги нудите", "што нудите", "usluga", "uslugi", "service", "services", "koi uslugi", "shto uslugi", "uslugi nudite", "shto nudite", "sto nudite"],
    "price_triggers": ["цена", "колку чини", "колкава е цената", "cena", "kolku chini", "kolku cini", "price"],
    "contact_clarification_prefixes": ["dali", "дали", "mozhe", "moze", "може"],
    "contact_clarification_phrases": ["ili", "или", "sluzbenata", "sluzbena", "privatnata", "privatna", "која", "kakva", "каква", "which one"],
    "service_detail_triggers": ["анестез", "anestez", "инјекц", "inekc", "боли", "boli", "боли ли", "koliko tra", "колку трае", "дали се става", "dali se stava", "дали има", "dali ima"],
    "safe_detail_fallback": "That can depend on the specific treatment. The dentist should assess that during an examination.",
    "service_clarification_triggers": ["soodvetna usluga", "koja usluga", "kakva usluga mi treba", "recommend service"],
    "service_clarification_specific_triggers": ["koja usluga mi treba"],
    "service_description_triggers": ["kazete mi za", "shto e", "objasni mi", "кажете ми за", "што е", "објасни ми"],
    "consultation_explanation_triggers": ["каква", "што е", "објасни", "kakva", "shto e", "objasni"],
    "broad_pricing_price_terms": ["цена", "цени", "колку", "чини", "чинат", "cena", "ceni", "kolku", "chini", "cini", "price", "prices"],
    "broad_pricing_service_terms": ["услуга", "услуги", "услугите", "usluga", "uslugi", "service", "services"],
    "casual_reply_patterns": [
      { "triggers": ["фала", "благодарам", "fala", "blagodaram", "thanks", "thank you"], "reply_key": "thanks" },
      { "triggers": ["wow", "вау", "леле"], "reply_key": "wow" },
      { "triggers": ["супер", "одлично", "super", "odlichno", "odlicno", "great"], "reply_key": "positive" }
    ]
  },
  "reply_texts": {
    "greeting_short": "Hello! How can I help you?",
    "service_clarification": "Tell me briefly what you need help with, and I can guide you to the most suitable service.",
    "service_clarification_specific": {
      "koja_usluga_mi_treba": "Tell me a bit more about what you need, and I can guide you to the most suitable service."
    },
    "casual_replies": {
      "thanks": "You're welcome. Feel free to tell me what you need.",
      "wow": "Glad I could help. If you want, I can guide you to the right service.",
      "positive": "Glad to hear that. Let me know if you'd like help with a service or booking."
    },
    "price_templates": {
      "numeric": "{service_name} costs around {price}{currency}.",
      "text": "{service_name} is {price}.",
      "free": "{service_name} is free.",
      "range": "The orientation price range for {service_name_lower} is {price_range}."
    },
    "price_followup": "For an exact estimate, the best next step is a short consultation.",
    "service_description_template": "{article_name} is {description}\n\n{followup}",
    "service_description_followup": "If you want, I can also help check whether that is the right option for you.",
    "field_prompts": {
      "name": "Please share your name.",
      "phone": "Please share your phone number.",
      "email": "Please share your email address."
    },
    "contact_clarification_replies": {
      "name": "Please share the name you want us to use. {field_prompt}",
      "phone": "You can leave the number where we can reach you most easily. {field_prompt}",
      "email": "Either a work or private email is fine. {field_prompt}",
      "default": "{field_prompt}"
    },
    "booking_completed": "Thank you. Your booking request has been received. The business will contact you."
  },
  "repetition_responses": {
    "broad_pricing": "Prices depend on the specific service. If you want, tell me exactly what interests you and I can give you orientation.",
    "service_list": "I already listed the services, but I can guide you more specifically if you want.",
    "consultation_explanation": "It is an initial review and conversation to see what is most appropriate for you. If you want, we can continue with booking right away."
  },
  "services": [],
  "actions": {
    "allow_booking": false,
    "collect_contact_fields": [],
    "handoff_enabled": false,
    "order_flow_enabled": false
  },
  "output_contract": {
    "unknown_service_id": "unknown",
    "response_format": {
      "intent": "string",
      "service_id": "string",
      "message": "string"
    }
  },
  "knowledge": {
    "faq": [],
    "source": "static",
    "notes": "Placeholder for knowledge base integration later"
  }
}

```

--------------------------------
File: clinic-ai-assistant-src/backend/tests/test_chat_flow.py
--------------------------------

```python
import importlib

from fastapi.testclient import TestClient


class FakeResponse:
    def __init__(self, output_text: str):
        self.output_text = output_text


class FakeResponses:
    def create(self, *args, **kwargs):
        message = kwargs["input"][-1]["content"]
        if message == "болка и пломба":
            return FakeResponse(
                '{"intent":"suggest_service","service_id":"filling","message":"Препорачуваме пломба. Дали сакате да закажете?"}'
            )
        if message == "здраво":
            return FakeResponse(
                '{"intent":"greeting","service_id":"unknown","message":"Здраво! Како можам да помогнам?"}'
            )
        return FakeResponse(
            '{"intent":"fallback","service_id":"unknown","message":"Извинете, не можев да разберам."}'
        )


class FakeOpenAI:
    def __init__(self, api_key=None):
        self.responses = FakeResponses()


def test_booking_transition_and_contact_collection(monkeypatch):
    monkeypatch.setenv("OPENAI_API_KEY", "test-key")

    from app.services import ai_agent, lead_store

    ai_agent.SESSION_STATE.clear()
    monkeypatch.setattr(ai_agent, "OpenAI", FakeOpenAI)

    import app.main as main_module

    importlib.reload(main_module)
    client = TestClient(main_module.app)

    first = client.post("/chat?tenant=milena_dental", json={"message": "болка и пломба"}).json()
    session_id = first["session_id"]

    second = client.post(
        "/chat?tenant=milena_dental",
        json={"message": "да", "session_id": session_id},
    ).json()
    third = client.post(
        "/chat?tenant=milena_dental",
        json={"message": "Марјан", "session_id": session_id},
    ).json()
    fourth = client.post(
        "/chat?tenant=milena_dental",
        json={"message": "070000000", "session_id": session_id},
    ).json()
    fifth = client.post(
        "/chat?tenant=milena_dental",
        json={"message": "mail@test.mk", "session_id": session_id},
    ).json()

    assert first["session_status"] == "active"
    assert second["session_status"] == "collecting_contact"
    assert "име" in second["reply"]
    assert "телефон" in third["reply"]
    assert "е-пошта" in fourth["reply"]
    assert fifth["session_status"] == "completed"

    stored = lead_store.load_lead_checkpoint("milena_dental", session_id)
    assert stored["stage"] == "completed"
    assert stored["data"]["name"] == "Марјан"


def test_request_validation(monkeypatch):
    monkeypatch.setenv("OPENAI_API_KEY", "test-key")

    import app.main as main_module

    importlib.reload(main_module)
    client = TestClient(main_module.app)

    response = client.post("/chat?tenant=milena_dental", json={"message": "   "})
    assert response.status_code == 422

    response = client.post(
        "/chat?tenant=milena_dental",
        json={"message": "ok", "session_id": "x" * 129},
    )
    assert response.status_code == 422

```

--------------------------------
File: clinic-ai-assistant-src/backend/tests/test_config_loader.py
--------------------------------

```python
from app.services.config_loader import load_profile_config, load_public_profile_config


def test_all_profiles_load_successfully():
    for tenant in ("generic", "risto", "milena_dental"):
        profile = load_profile_config(tenant)
        assert profile["business"]["name"]


def test_public_profile_config_hides_internal_prompt_fields():
    public_profile = load_public_profile_config("milena_dental")

    assert "prompt_template" not in public_profile
    assert "output_contract" not in public_profile
    assert "business" in public_profile
    assert "services" in public_profile

```
