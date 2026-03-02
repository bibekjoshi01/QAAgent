# QA Bot - Full System Documentation

This repository contains an AI-powered QA platform with:
- A Python/FastAPI backend that orchestrates LLM-guided QA runs and executes QA tools.
- A Next.js frontend that submits scans and renders detailed reports.
- A modular tool + provider architecture so you can add new checks and models.

For architecture details, see [architecure.md](./architecure.md).

## 1. What This System Does

Given a target URL, the system can run an autonomous QA mission that checks:
- Functional behavior (links, forms, button/action patterns, auth/session flows)
- UX and accessibility risk signals
- Performance metrics
- Security headers, SSL, and content risks
- Browser network/console evidence

It returns:
- Structured issues (severity, category, reproducible steps)
- Tool outputs and execution trace
- Screenshots (served by backend)
- Raw model output for auditability

## 2. Tech Stack

Backend:
- Python 3.11+
- FastAPI + Uvicorn
- Playwright (headless browser automation)
- Pydantic / pydantic-settings
- LLM providers: Mistral, Hugging Face

Frontend:
- Next.js 15 (App Router)
- React 18
- TypeScript
- Tailwind CSS
- TanStack Query

## 3. Repository Structure

```text
.
|-- engine/                  # Core orchestration, providers, tools, prompts
|   |-- core/                # Agent loop + parsing + typed results
|   |-- providers/           # LLM provider abstraction + implementations
|   |-- prompts/             # System/user prompt builders
|   |-- tools/               # QA tool implementations
|-- server/                  # FastAPI app, schemas, service wiring
|-- web/                     # Next.js frontend
|-- artifacts/screenshots/   # Runtime screenshot artifacts (served by backend)
|-- tests/                   # Backend and tool tests
|-- .env.example             # Environment template
|-- requirements.txt
|-- pyproject.toml
```

## 4. Prerequisites

- Python 3.11+
- Node.js 18+
- npm or yarn
- Playwright browser binaries

## 5. Environment Variables

Create `.env` from `.env.example`:

```env
APP_ENV=local
PROVIDER_NAME=mistral
PROVIDER_MODEL=mistral-large-latest
PROVIDER_API_KEY=your_provider_key
API_AUTH_SECRET=replace_with_long_random_secret
```

Backend reads these via `server/config.py`.

Frontend environment variables (`web/.env.local`):

```env
NEXT_PUBLIC_QA_API_URL=http://localhost:8000/api/qa
NEXT_PUBLIC_QA_API_KEY=replace_with_same_api_auth_secret
```

Important:
- `NEXT_PUBLIC_QA_API_KEY` must match backend `API_AUTH_SECRET`.
- If `PROVIDER_API_KEY` is missing, backend QA execution fails by design.

## 6. Local Development Setup

### 6.1 Backend

From repository root:

```bash
python -m venv .venv
.venv\Scripts\activate
pip install -r requirements.txt
python -m playwright install chromium
uvicorn server.main:app --reload --host 0.0.0.0 --port 8000
```

Backend endpoints:
- Root health: `GET /`
- QA endpoint: `POST /api/qa`
- Screenshots static path: `/screenshots/*`
- OpenAPI docs (non-production): `/docs`

### 6.2 Frontend

From `web/`:

```bash
npm install
npm run dev
```

Default frontend URL: `http://localhost:3000`

## 7. How a Scan Works (End-to-End)

1. User submits a scan from `/qa` page (target URL + device/network/tool selections).
2. Frontend calls backend `POST /api/qa` with API key header.
3. Backend normalizes URL and creates `QATask`.
4. `Engine` initializes provider + Playwright-backed/static tools.
5. `QAOrchestrator` runs model-tool loop:
   - model proposes tool calls
   - tools execute and return structured payloads
   - tool outputs feed back into model context
6. Model emits final JSON issues payload.
7. Backend serializes tool outputs and persists base64 screenshots to `artifacts/screenshots`.
8. Backend returns issues + trace + screenshot URLs.
9. Frontend adapts backend response into report model and renders `/qa/results`.

## 8. API Contract

### `POST /api/qa`

Required header:
- `X-API-KEY: <API_AUTH_SECRET>` (header name is configurable)

Request body:

```json
{
  "url": "https://example.com",
  "context": {"mission": "autonomous_scan"},
  "device_profile": "desktop",
  "network_profile": "wifi",
  "selected_tools": ["dead_link_checker", "form_validator"]
}
```

Response body (shape):

```json
{
  "url": "https://example.com",
  "issues": [],
  "tool_outputs": [],
  "screenshots": [],
  "raw_model_output": "...",
  "trace": []
}
```

## 9. Available Tool Keys

- `dead_link_checker`
- `form_validator`
- `button_click_checker`
- `login_flow_checker`
- `session_persistence_checker`
- `accessibility_audit`
- `responsive_layout_checker`
- `touch_target_checker`
- `network_monitor`
- `console_watcher`
- `seo_metadata_checker`
- `performance_audit`
- `ssl_audit`
- `security_headers_audit`
- `security_content_audit`

Notes:
- Some tools are static HTML/HTTP analyzers.
- Others depend on the Playwright browser runtime.

## 10. Security Model

- API key authentication is required on `/api/*` routes.
- CORS origins are configurable.
- Trusted hosts can be enforced.
- HTTPS redirect can be enabled.
- In production, strict security settings should be validated and secrets rotated.

## 11. Development and Quality Commands

Backend checks:

```bash
ruff check .
mypy .
pytest -q
```

Frontend checks:

```bash
cd web
npm run typecheck
npm run lint
```

## 12. Common Failure Modes

- `401 Invalid API Key`
  - Header value does not match backend secret.
- `Provider API key not set`
  - `PROVIDER_API_KEY` missing in backend environment.
- Playwright startup errors on Windows event loop
  - Ensure proper event loop policy and Playwright browser install.
- No tools initialized
  - `selected_tools` empty or invalid keys.

## 13. Extending the System

Add a new tool:
1. Implement class extending `BaseTool`.
2. Register it in `engine/tools/maps.py`.
3. Add request schema key in `server/schemas.py` (`ToolKey` literal).
4. Expose selection in frontend type `web/types/scan.ts`.
5. Add tests under `tests/`.

Add a new provider:
1. Implement `BaseLLMProvider`.
2. Register in `ProviderRegistry`.
3. Set `PROVIDER_NAME` and `PROVIDER_MODEL` in environment.

## 14. License and Ownership

Add your organization license and contribution policy here.