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
| Auth error | Warn softly: "Couldn't connect to Kumiho memory — token may be missing. Use `/kumiho-auth` to set up." Continue normally. |

## Step 2 — Returning user greeting

1. Parse metadata, adopt agent identity and communication style
2. `kumiho_memory_recall` with broad query (user's name, role, recent topics)
3. Greet with continuity — reference something specific from memory. Never narrate the bootstrap.

## Identity Metadata Fields

`agent_name`, `user_name`, `user_languages`, `communication_tone` (casual/professional/balanced), `verbosity` (concise/balanced/detailed), `user_role`, `user_expertise_level`, `primary_tools`, `artifact_dir`, `timezone`, `interaction_rules`, `memory_behaviour`