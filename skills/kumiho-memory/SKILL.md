---
name: kumiho-memory
description: Use Kumiho MCP memory tools to capture durable context and recall relevant user/project memory across sessions.
---

# Kumiho Memory Skill

Use this skill when the user wants durable memory across sessions, such as
preferences, project context, or recurring workflows.

## Core tools

- `kumiho_memory_ingest`: store a user message and fetch relevant context
- `kumiho_memory_add_response`: store the assistant response for the session
- `kumiho_memory_consolidate`: summarize and persist to long-term memory
- `kumiho_memory_recall`: retrieve relevant memories
- `kumiho_memory_store_execution`: store task or tool execution outcomes

## Recommended pattern

1. Use a stable `user_id` for the same user.
2. Ingest important user facts with a clear `context`.
3. Add assistant response if needed for full session context.
4. Consolidate after meaningful exchanges or at task boundaries.
5. Recall memories before answering follow-up questions that depend on history.

## Data minimization

- Store concise, high-signal facts and preferences.
- Avoid credentials, tokens, private keys, or payment details.
- Ask before storing highly sensitive personal data.
