# Full-Stack Workflow Pilot Requirements

Version: 1
Status: Awaiting explicit user approval

## Purpose

Validate the Hermes-to-OpenCode gated workflow on one real local browser-to-API-to-database vertical slice. This is a disposable development pilot, not a deployed production application.

## User and scope

One local user creates tasks and sees the persisted task list. A task has an integer ID, a title, and a creation timestamp. Titles are trimmed and must contain 1–200 characters. The list is ordered newest first, with ID as the deterministic tie-breaker.

## Required behavior

1. Open the application in a browser on localhost.
2. Enter a title and submit it without a full page reload.
3. See the created task in the list after the API confirms persistence.
4. Refresh the page and retain the task.
5. Restart the application and retain the task in the same SQLite database.
6. Reject blank, whitespace-only, non-string, and overlong titles without creating records.
7. Show a useful error and allow retry when a request fails; preserve the typed title.
8. Render user-provided text as text, not HTML.

## Non-goals

Authentication, multiple users, editing, deletion, due dates, search, notifications, deployment, cloud services, premium visual design, and external database infrastructure.

## Acceptance criteria

- AC1: Real browser submission produces one persisted task and updates the visible list.
- AC2: Refresh and server restart preserve that task.
- AC3: API validation rejects invalid titles with HTTP 400 and creates no records.
- AC4: HTML-like titles remain inert visible text.
- AC5: The form remains usable at a 375-pixel viewport and has an associated input label and accessible status output.
- AC6: Automated API/database checks and a browser interaction check pass; evidence includes commands, exit codes, and captured browser observations.
- AC7: The runner demonstrates a missing-approval block before the approved implementation dispatch and records the final reviewed acceptance.

## Approval boundary

Approval must explicitly refer to this document. Earlier approval of the integration framework does not count as approval of this pilot's product behavior.
