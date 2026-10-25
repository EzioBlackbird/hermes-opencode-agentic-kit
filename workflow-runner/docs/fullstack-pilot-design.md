# Full-Stack Workflow Pilot Design

Version: 1
Status: Awaiting explicit user approval
Requirements: `fullstack-pilot-requirements.md`

## Recommended stack

- Backend: Python standard-library HTTP server bound to `127.0.0.1` only.
- Database: SQLite through Python's standard library, with parameterized queries and a connection per request.
- Frontend: semantic HTML, CSS, and JavaScript served by the same process and origin.
- Testing: Python unittest for API/database integration, plus an available browser automation tool for real UI interactions.

This avoids package installation for the pilot application. The workflow runner retains its existing jsonschema dependency. A local HTTP server is sufficient for this development-only fixture; no production deployment is proposed.

## API contract

- `GET /api/tasks`: HTTP 200, `{"data": [{"id": 1, "title": "Example", "createdAt": "ISO-8601 UTC timestamp"}]}`.
- `POST /api/tasks`: JSON object containing exactly `title`; HTTP 201 with `{"data": {"id": 1, "title": "Example", "createdAt": "ISO-8601 UTC timestamp"}}`.
- Invalid JSON, unexpected fields, invalid title, or request bodies over 8 KiB: HTTP 400 with `{"error": {"code": "INVALID_REQUEST", "message": "Readable explanation"}}`.
- Unexpected server errors: HTTP 500 with a generic JSON error; details are logged locally.
- Unknown route: HTTP 404; unsupported API method: HTTP 405.

## Persistence

One `tasks` table: integer primary key, non-null title, non-null UTC creation timestamp. Initialization is idempotent. Database location and port are configurable through `PILOT_DB_PATH` and `PILOT_PORT`, with documented local defaults and `.env.example`. The application reads process environment; a dotenv loader is not assumed.

## Frontend

A labeled title field, submit button, live status region, and task list. Disable submission while the create request is pending. Preserve the title after errors. Use textContent for all user values. Use relative same-origin fetch URLs. Use a readable single-column layout that fits a small mobile viewport.

## Workspace and execution

Create a new dedicated local Git repository rather than repurposing existing user files. Install project-local executor skills and bind the approved requirements and design by hashes. Capture command output and browser evidence under attempt artifacts.

## Task sequence

1. Prepare project artifacts, approval records, bounded contracts, and verification harness.
2. Write and review behavioral tests. A red checkpoint must fail on missing behavior, not missing imports or a broken environment. If no meaningful red fixture exists, split test scaffolding from the TDD implementation task.
3. Delegate the API, persistence, and minimal UI vertical slice to OpenCode within explicit allowed paths.
4. Independently verify API validation, persistence, and the unchanged test suite.
5. Exercise browser submission, reload, error handling, inert HTML rendering, and mobile viewport layout.
6. Restart the server with the same database and recheck persisted content.
7. Review criteria and source; accept only when all required evidence is available. Stop pilot-owned processes after evidence capture.

## Success and escalation

Missing approvals, unexpected source changes, failed checks, or incomplete browser evidence block acceptance. Product scope changes require renewed approval. Preserve partial work on failure. Keep Kanban projection on a dedicated non-dispatching ticket.

## Approval boundary

Approval must explicitly refer to this design, including the proposed Python/SQLite/vanilla frontend stack. A separate requirement approval is recorded even if the user approves both documents in one message.
