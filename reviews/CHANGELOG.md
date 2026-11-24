# Changes

## 2027.2.0 (2026-11-24)

- Added: `cut-off-or-too-big` and `cut-off-what-next` (day 1, session 2): telling a reply cut off by the output limit from a request too large for the context window, from the response metadata.
- Added: `connection-per-call` and `one-client-reused` (day 1, session 2): connection set-up per model call, and one client made once and reused. `llm.client()` in the labs now reuses its client; Lab 1.2 checks it.
- Added: `buffered-stream` and `find-the-buffer` (day 1, session 4): finding the server on the way that buffers a streamed reply, from first and last byte at each hop. Lab 1.4 has a look-at cell with a buffering relay.
- Added: `deadline-trace` and `pass-the-deadline` (day 2, session 3): passing the caller's deadline down the chain and not starting work that cannot finish. Lab 2.3 has a look-at cell, `status_by`.
- Added: `bad-body-status` and `client-error-reply` (day 4, session 4): a body that is not JSON answered with 4xx, never 5xx, and what the client does next. Lab 4.4 has a look-at cell that checks it on Wasil's app.
- Fixed: the trip-status call in `wasil.py` and in the Lab 2.3 solution now returns at its timeout instead of waiting for the slow call to end.
- Questions: five practice questions in `assessments/bank.json` (`lo1-cut-off-reply`, `lo1-client-reuse`, `lo7-buffered-stream`, `lo3-caller-deadline`, `lo7-bad-json-status`), and one more checkpoint question at the end of Labs 1.2, 1.4, 2.3 and 4.4.
- Sources: RFC 9110, the gRPC deadlines guide and the HTTPX clients page. Every new figure is computed by `labs/_tools/call_artifacts.py`.
