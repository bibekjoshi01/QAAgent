# System Architecture (QA Bot)

This document describes the full architecture of the QA Bot system, including runtime components, data flow, and extension points.

## 1. Architecture Goals

- Run autonomous, evidence-based QA checks against a target website.
- Keep model orchestration provider-agnostic.
- Support a composable tool system (functional, UX, security, performance, console/network).
- Produce auditable output: trace, tool results, screenshots, structured issues.

## 2. High-Level Architecture

```text
+-----------------------+            +-------------------------------+
| Next.js Frontend      |            | FastAPI Backend               |
| (web/)                |  POST /qa  | (server/)                     |
| - /qa form            +----------->| - auth + validation           |
| - /qa/results         |  JSON      | - Engine runner               |
+-----------+-----------+            +---------------+---------------+
            |                                        |
            | screenshots URLs                       | orchestrates
            |                                        v
            |                           +-------------------------------+
            |                           | Engine Core (engine/)         |
            |                           | - QAOrchestrator loop         |
            |                           | - Prompt builders             |
            |                           | - ToolCollection              |
            |                           +---------------+---------------+
            |                                           |
            |                                           | tool calls
            |                                           v
            |                           +-------------------------------+
            |                           | QA Tools                       |
            |                           | - Static HTML/HTTP tools      |
            |                           | - Playwright browser tools    |
            |                           +---------------+---------------+
            |                                           |
            |                                           | model generate
            |                                           v
            |                           +-------------------------------+
            |                           | LLM Provider Layer            |
            |                           | - MistralProvider             |
            |                           | - HuggingFaceProvider         |
            |                           +-------------------------------+
```

## 3. Backend Components

### 3.1 API Layer (`server/`)

- `server/main.py`
  - Creates FastAPI app
  - Configures CORS, trusted hosts, optional HTTPS redirect
  - Mounts `/screenshots` static path
  - Adds `/api` router with API key dependency
- `server/api.py`
  - `POST /api/qa` endpoint
  - Normalizes URL and builds `QATask`
  - Runs engine via `run_qa_task_sync`
  - Converts base64 screenshots into static files/URLs
- `server/schemas.py`
  - `QARequest` input model and typed enums for device/network/tools
  - `QAResponse` output model
- `server/dependencies.py`
  - API key header check (`X-API-KEY` by default)
- `server/config.py`
  - Environment-driven settings, security controls, provider config

### 3.2 Service Layer (`server/services.py`)

- `run_qa_task_sync(...)`
  - Reads provider config
  - Instantiates `Engine` with selected device/network/tools
  - Runs async engine in sync context
- `serialize_tool_outputs_with_urls(...)`
  - Writes screenshot binaries to `artifacts/screenshots`
  - Replaces base64 blobs with URL references

## 4. Engine Internals

### 4.1 Core Orchestration (`engine/core/agent_loop.py`)

`QAOrchestrator.execute(...)` drives the central loop:

1. Build message list (system + user).
2. Call provider with current messages and tool schemas.
3. Append assistant message and trace step.
4. If tool calls exist:
   - Execute each tool safely with timeout handling.
   - Append tool results as `tool` messages.
5. Repeat until no tool calls or max iterations reached.
6. Parse final issues JSON from model output.
7. If no successful evidence exists, emit a blocker issue.

### 4.2 Prompts (`engine/prompts/`)

- `build_system_prompt(...)`
  - Injects date, locale, device, network, and tool list
  - Enforces evidence-only issue reporting
  - Defines strict JSON output schema
- `build_user_prompt(...)`
  - Injects target URL, QA objective, and optional context

### 4.3 Types (`engine/core/types.py`)

- `QATask`: input unit for a QA run
- `QAResult`: issues + raw output + tool outputs + trace
- `QAIssue`: normalized issue representation

## 5. Tooling Subsystem

Tool abstraction:
- `BaseTool` (name, description, input schema, async execute)
- `ToolExecutionResult` (success, output, error, screenshot, metadata)
- `ToolCollection` runtime registry + timeout-managed execution

Tool categories:
- Functional: links, forms, clickability, login, session persistence
- UI/UX: accessibility, responsive layout risk, touch targets
- Console/Network: browser errors, request failures, resource hints
- Metadata/Performance: SEO metadata, web-vitals-like metrics
- Security: SSL/TLS, security headers/cookies, mixed-content/style risks

Execution modes:
- Static HTTP/HTML parsing tools (no browser state needed)
- Playwright-backed tools (browser context, live runtime signals, screenshots)

## 6. Provider Layer

Provider abstraction:
- `BaseLLMProvider.generate(LLMRequest) -> LLMResponse`

Factory and registry:
- `ProviderFactory.create(name, model, **kwargs)`
- `ProviderRegistry` maps provider name to implementation

Current implementations:
- `MistralProvider`
  - Supports tool call normalization and retries
- `HuggingFaceProvider`
  - Text-generation/chat fallback path, retries

## 7. Frontend Architecture (`web/`)

Primary pages:
- `/` landing page
- `/qa` scan form
- `/qa/results` report and execution trace

Data flow:
1. User fills `ScanPayload` (URL, device/network/tool selection, optional JSON context).
2. `runScan` sends request to backend with API key.
3. Backend response is adapted by `backendToScanReport(...)`.
4. Report persists in localStorage history.
5. Results page renders:
   - score cards
   - issue table
   - readable summary
   - per-step tool-call timeline
   - raw technical trace

Key modules:
- `web/lib/api.ts`: backend call + response validation
- `web/lib/report-adapter.ts`: backend-to-UI model transformation
- `web/types/scan.ts`: shared frontend type contracts

## 8. End-to-End Sequence

```text
Frontend -> POST /api/qa
Backend -> validate auth + payload
Backend -> Engine.run_task(QATask)
Engine -> Provider.generate(messages + tool schemas)
Provider -> tool calls
Engine -> ToolCollection.run(...)
Tools -> evidence/output/screenshot_base64
Engine -> Provider.generate(...tool outputs...)
Engine -> final JSON issues
Backend -> persist screenshots + build screenshot URLs
Backend -> response {issues, tool_outputs, screenshots, trace, raw_model_output}
Frontend -> adapt + render report
```

## 9. Data Contracts

### 9.1 Input (`QARequest`)

- `url: str`
- `context: dict | null`
- `device_profile: enum`
- `network_profile: enum`
- `selected_tools: list[tool_key]`

### 9.2 Output (`QAResponse`)

- `url`
- `issues[]`
- `tool_outputs[]`
- `screenshots[]` (URL strings)
- `raw_model_output`
- `trace[]` (assistant content + tool calls per step)

## 10. Security Boundaries

- API key gate on `/api/*` routes.
- CORS allow-list from env + local dev defaults.
- Optional trusted-host enforcement.
- Optional HTTPS redirect middleware.
- Screenshot files are served statically; path generation is controlled by backend utility.

## 11. Reliability and Failure Handling

- Provider retries (with backoff).
- Tool execution timeout via `asyncio.wait_for`.
- Safe tool execution path returns structured error payloads.
- If no reliable evidence is collected, orchestrator emits a blocker issue instead of fabricated findings.

## 12. Scalability Notes

Current characteristics:
- Single-process backend model invocation per request.
- Playwright browser context per run.
- Screenshot storage on local filesystem.

For higher scale, introduce:
- Job queue + worker pool
- Distributed artifact storage (e.g., object storage)
- Per-tool concurrency controls and caching
- Multi-instance stateless API layer

## 13. Extension Points

- New tools: implement `BaseTool`, register in `engine/tools/maps.py`, expose schema/frontend enum.
- New model providers: implement `BaseLLMProvider`, register with `ProviderRegistry`.
- Custom prompt policy: evolve `engine/prompts/*`.
- Alternate report views: extend `web/lib/report-adapter.ts` + UI components.

## 14. Known Constraints

- Several tools rely on static HTML parsing; dynamic SPA states may require Playwright-backed checks.
- Login/session checks depend on selectors/signals; deterministic verification requires optional arguments.
- Provider behavior differs by model capability (tool calling, JSON discipline, token limits).