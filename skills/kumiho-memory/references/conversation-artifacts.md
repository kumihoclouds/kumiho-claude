# Conversation Artifacts and Session Close

## Conversation artifact generation (MUST enforce)

**Design alignment**: BYO-Storage (paper S5.4.2), Local-First Privacy
(S8.1), Principle 11 (Metadata Over Content), Principle 13 (One Tool Call,
Complete Memory).

The graph stores **metadata and pointers** — raw conversation content stays
**local** as a Markdown artifact. This is a core architectural requirement,
and it's what allows your future self to have full context on what happened.

### When to generate

- **MUST** generate for any session with **2 or more meaningful exchanges**.
- **Optional** for single trivial Q&A (e.g., "what time is it?").
- Generate at **task boundaries** (end of a feature, bug fix, planning
  session) or **before the session ends**.

### Artifact storage path

Resolve the artifact directory in this order:

1. `artifact_dir` from the agent instruction metadata (set during onboarding)
2. `KUMIHO_ARTIFACT_DIR` environment variable
3. Default: `~/.kumiho/artifacts/`

Files are organized by date: `{artifact_dir}/{YYYY-MM-DD}/{session_id}.md`

### Markdown format

```markdown
---
session_id: "{session_id}"
user_id: "{user_id}"
agent_name: "{agent_name}"
date: "{ISO_8601_datetime}"
topics:
  - topic1
  - topic2
summary: "One-line summary of the session"
---

# {Brief session title}

## Exchange 1

**User:**
{user_message_text}

**Assistant:**
{assistant_response_text}

## Exchange 2

**User:**
{user_message_text}

**Assistant:**
{assistant_response_text}
```

### Generation steps

1. **Compose the markdown** from the session's user/assistant exchanges.
   - Include all substantive exchanges (skip trivial greetings-only turns).
   - Write a brief title and one-line summary.
   - Extract 2-5 topic keywords for the YAML frontmatter.

2. **Write the file locally** using the Write tool:
   - Path: `{artifact_dir}/{YYYY-MM-DD}/{session_id}.md`
   - Create the directory first via Bash if it doesn't exist:
     ```
     mkdir -p ~/.kumiho/artifacts/2026-02-10
     ```

3. **Store the artifact pointer in the graph.** Use whichever tool is
   available:

   **Option A** — via `kumiho_memory_consolidate` (preferred if it accepts
   artifact path):
   ```
   kumiho_memory_consolidate(
     user_id      = "<stable_user_id>",
     session_id   = "<session_id>",
     artifact_path = "<local_path_to_markdown>"
   )
   ```

   **Option B** — via lower-level graph tools:
   ```
   kumiho_create_item(
     space_path = "CognitiveMemory/conversations",
     item_name  = "<session_id>",
     kind       = "conversation"
   )

   kumiho_create_revision(
     item_kref = "kref://CognitiveMemory/conversations/<session_id>.conversation",
     metadata  = {
       "summary":  "<one-line summary>",
       "topics":   ["topic1", "topic2"],
       "keywords": ["keyword1", "keyword2"],
       "type":     "conversation"
     }
   )
   ```

4. **Fallback**: If graph tools are not authenticated, **still write the local
   markdown file**. BYO-storage means the local file is the source of truth;
   the graph pointer can be created later when auth is available.

### What the agent passes to memory tools

For every assistant response during the session, call:
```
kumiho_memory_add_response(
  session_id = "<session_id>",
  response   = "<assistant_response_text>"
)
```

Pass **raw text** — the agent is responsible for generating the final Markdown
artifact. The memory tools handle summarization and graph storage internally;
the Markdown artifact is the full-fidelity local record.

---

## Session close

When the session is ending (user says goodbye, task is complete, or
conversation naturally concludes):

1. **Generate the conversation artifact** (see above).
2. **Consolidate** via `kumiho_memory_consolidate` to persist the session
   summary to long-term graph storage.
3. **Discover edges** on the consolidated memory. The consolidation result
   contains a `revision_kref` — pass it to `kumiho_memory_discover_edges`
   with the session summary:
   ```
   consolidation = kumiho_memory_consolidate(session_id = "<session_id>")

   kumiho_memory_discover_edges(
     revision_kref = "<revision_kref from consolidation result>",
     summary       = "<session summary from consolidation>"
   )
   ```
   This links the session summary to related existing memories in the graph,
   enriching future graph-augmented recall.
4. **Close with continuity.** Your sign-off should leave a thread to pick up:

   > "Saved the session. Next time we can pick up from [specific open item
   > or next step]. See you, {user_name}."

   **Good**: "Logged everything. The Neo4j migration is ready to test —
   want to pick that up next session?"

   **Bad**: "Goodbye. Have a nice day."
