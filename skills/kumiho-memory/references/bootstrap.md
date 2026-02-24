# Session Bootstrap Procedure

Runs ONCE on the first user message. Never repeat.

## Step 1 — Auth check & identity load

```
kumiho_get_revision_by_tag(
  item_kref = "kref://CognitiveMemory/agent.instruction",
  tag       = "published"
)
```

| Result | Action |
|--------|--------|
| Revision returned | Parse metadata fields below, adopt identity → Step 2 |
| Item/tag not found | First session → [Onboarding](onboarding.md) |
| Auth error (401 / UNAUTHENTICATED) | Say: "Memory isn't connected yet — run `/kumiho-auth` to set up, then start a new session (or restart the app on Claude Desktop)." Continue without memory. |
| Connection error (UNAVAILABLE / connection refused / DNS resolution failure) | Same message as auth error. The server started before a token was available, so discovery didn't resolve the cloud endpoint. |
| Any other error | Log the error silently and continue without memory. Do NOT show raw gRPC errors or stack traces to the user. |

## Step 2 — Returning user greeting

1. Parse metadata, adopt agent identity and communication style
2. `kumiho_memory_recall` **once** with a broad query (user's name, role, recent topics). This is the ONLY recall for the first turn — do not call recall again.
3. Greet with continuity — reference something specific from memory. Never narrate the bootstrap.

## Identity Metadata Fields

`agent_name`, `user_name`, `user_languages`, `communication_tone` (casual/professional/balanced), `verbosity` (concise/balanced/detailed), `user_role`, `user_expertise_level`, `primary_tools`, `artifact_dir`, `timezone`, `interaction_rules`, `memory_behaviour`