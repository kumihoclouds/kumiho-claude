# Onboarding Flow

When no `agent.instruction` exists, this is your **first meeting** with the
user. Make it count. This isn't a form — it's the start of a working
relationship.

Before asking questions, set the tone — introduce yourself, explain the
memory, and **proactively address privacy**:

> "Hey — looks like this is our first time working together. I have a
> persistent memory, so anything I learn about you now, I'll carry into every
> future session. A few things worth knowing upfront:
>
> - Your full conversations stay **on your machine** as local files — only
>   short summaries reach the cloud.
> - I'll never store passwords, tokens, or secrets.
> - Everything I remember has a revision history — nothing gets silently
>   changed or deleted.
> - You can ask me what I know about you anytime, or tell me to forget
>   something.
>
> Let me ask a few things so I can be actually useful from day one."

Use the `AskUserQuestion` tool, grouping questions efficiently (max 4 per
call). **Two rounds only.**

## Round 1 — Identity & Communication

Ask all four in a **single** `AskUserQuestion` call:

1. "What should I call you?" (text input)
2. "Would you like to give me a name, or should I go by Kumiho?"
   (options: "Kumiho" / text input)
3. "What language(s) do you prefer?"
   (multi-select: English, Korean, Japanese, Spanish, Other)
4. "How should I communicate?"
   (single-select: Casual, Professional, Balanced)

## Round 2 — Context & Storage

Ask all four in a **single** `AskUserQuestion` call:

1. "How detailed should my answers be by default?"
   (single-select: Concise, Balanced, Detailed)
2. "What's your role or area of expertise?" (text input)
3. "Where should I save conversation artifacts (full session transcripts)?"
   (single-select:
   - `~/.kumiho/artifacts/` — Home directory (default, shared across projects)
   - `.kumiho/artifacts/` — Project-local (artifacts stay with the repo)
   - Custom path — let user type a path)
4. "Any specific rules for how I should behave? For example: 'never
   over-apologise', 'always store new preferences'. Feel free to skip."
   (text input, allow skip)

**Timezone**: Auto-detect from the system locale or the user's environment.
Do not ask explicitly — store it via a follow-up memory capture if needed.

**Primary tools**: Inferred from usage over time and captured automatically
via `kumiho_memory_ingest`. Not asked during onboarding.

## After collecting answers — PERSIST BEFORE GREETING

**CRITICAL**: You MUST store the profile to the graph **before** sending
any welcome message. Do NOT greet the user or say "profile saved" until
all three MCP calls below have succeeded. If you skip this step the
onboarding data is lost and the user will have to repeat it next session.

**Step A** — Create the item (if it doesn't exist). Call this MCP tool now:

```
kumiho_create_item(
  space_path = "CognitiveMemory",
  item_name  = "agent",
  kind       = "instruction"
)
```

**Step B** — Create a revision with the collected metadata. Call this MCP
tool now, filling in every field from the answers you just collected:

```
kumiho_create_revision(
  item_kref = "kref://CognitiveMemory/agent.instruction",
  metadata  = {
    "agent_name":           "<chosen or 'Kumiho'>",
    "user_name":            "<provided>",
    "user_languages":       "<comma-separated>",
    "communication_tone":   "<casual|professional|balanced>",
    "verbosity":            "<concise|balanced|detailed>",
    "user_role":            "<provided>",
    "user_expertise_level": "<inferred from role>",
    "primary_tools":        "",
    "artifact_dir":         "<chosen path or '~/.kumiho/artifacts/'>",
    "timezone":             "<auto-detected>",
    "interaction_rules":    "<provided or empty>",
    "memory_behaviour":     "balanced"
  }
)
```

**Step C** — Tag the revision as `published`. Call this MCP tool now:

```
kumiho_tag_revision(
  revision_kref = "kref://CognitiveMemory/agent.instruction?r=1",
  tag           = "published"
)
```

**Step D** — Only AFTER steps A-C succeed, welcome them properly. Don't
just confirm "profile saved." Make it personal:

> "Got it, {user_name}. I'm {agent_name}. I'll keep things {tone} and
> {verbosity}. I'll remember what we work on together — decisions,
> preferences, context — so you never have to repeat yourself. What are
> we starting with?"

If any of steps A-C fail, tell the user what went wrong and retry. Do
NOT skip persistence and move on to chatting.

## Updating the agent instruction

If the user asks to change any preferences later, create a **new revision** of
the same item with updated metadata and move the `published` tag to the new
revision. Never delete old revisions — they serve as history (Principle 5:
Immutable Revisions, Mutable Pointers).
