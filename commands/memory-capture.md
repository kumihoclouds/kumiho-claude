---
description: Capture a user fact or preference into Kumiho memory
argument-hint: "<fact or preference>"
---

# Memory Capture

Store a single user fact or preference into Kumiho memory so it can be recalled
in later sessions.

## Steps

1. If no argument was provided, ask the user for the memory text to store.
2. Call `kumiho_memory_ingest` with:
   - `message`: the provided memory text
   - `user_id`: use a stable user id for this workspace
   - `context`: `"cowork-manual-capture"`
3. Confirm what was stored and mention it can be recalled with
   `kumiho_memory_recall`.

## Guardrails

- Do not store secrets (passwords, private keys, API secrets).
- If the user asks to store sensitive data, ask for confirmation first.
