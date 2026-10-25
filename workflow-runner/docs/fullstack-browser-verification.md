# Full-stack browser verification

Date: 2026-10-25
Pilot: `~/AppData/Local/Temp/opencode/fullstack-workflow-pilot-20261025`

## Observed results

- Started the pilot at `http://127.0.0.1:8765`, using a separate SQLite file outside the source tree.
- Submitted `<b>Browser pilot proof</b>` through the browser form handler. POST returned 201 and the page displayed `Task created successfully.`
- The task appeared as literal text. `.task-title b` matched zero elements.
- Reloaded the page; the created title remained visible.
- At viewport width 375, document scroll width was also 375: no horizontal overflow in the observed state.
- The title input had an associated label.
- Simulated fetch rejection in the browser. The input retained `Preserve on failure`, a network-error message appeared, and the submit button was enabled for retry. Restored fetch afterwards.
- Server logs showed successful HTML/CSS/JavaScript/API requests. The console error corresponded to a missing favicon (404), not a failed application request.
- Stopped only the identified pilot Python process after verification. Its shell exit code 1 reflects explicit process termination, not an application test result.

## Limits

These observations cover the real browser path. Subsequent source review identified unsupported-method handling; OpenCode corrected the backend and added regression tests without changing frontend assets. The runner independently passed 17 API/database tests and accepted task T001, attempt `1792904685773968500`, after an explicit review. The original worker report omitted authorized cache changes; a separately stored reconciled report corrected only that measured list, preserving the original.
