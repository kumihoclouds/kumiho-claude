# Agent Output Artifacts

## Persist what you produce (MANDATORY)

**Design alignment**: BYO-Storage (paper S5.4.2), Principle 11 (Metadata
Over Content). The graph stores pointers; the actual content lives as
local files.

Every significant output the agent generates — code, documents, analyses,
plans, summaries, paper drafts, config files — **MUST** be persisted as a
local artifact file and associated with a graph revision. Outputting content
only in the chat response is not enough. Chat responses are ephemeral; the
artifact is what your future self (and the user) can find again.

### What counts as a significant output

- Documents: paper drafts, reports, proposals, design docs, READMEs
- Code: scripts, configurations, generated code, patches
- Analyses: research summaries, comparison tables, benchmark results
- Plans: implementation plans, roadmaps, architecture decisions
- Creative: outlines, brainstorms, structured notes the user asked for

### What does NOT need an artifact

- Short answers to factual questions
- Conversational responses
- Minor clarifications or one-liners
- Tool call results that are already stored elsewhere

## The artifact creation flow

Follow this every time:

1. **Write the output to disk** using the Write tool. Place it in the
   artifact directory at a meaningful path:
   ```
   {artifact_dir}/{category}/{descriptive-name}.{ext}
   ```
   Examples:
   - `~/.kumiho/artifacts/papers/cognitive-memory-v3-abstract.md`
   - `~/.kumiho/artifacts/code/grpc-auth-middleware.rs`
   - `~/.kumiho/artifacts/analyses/neo4j-vs-postgres-comparison.md`

2. **Search for an existing item** (revision discipline — see
   [Memory lifecycle](memory-lifecycle.md)).

3. **Store the artifact in the graph.** Choose the path that fits:

   **Option A — Atomic store (preferred for new memories):**

   If no existing item was found in step 2, use `kumiho_memory_store` to
   create everything in one call — space, item, revision, artifact, edges,
   bundle, and tag. This avoids fragile multi-step sequences that can leave
   partially-committed state.

   ```
   kumiho_memory_store(
     user_text     = "<context or empty>",
     assistant_text = "<the generated output>",
     title         = "Cognitive Memory Paper — Revised Abstract",
     summary       = "Updated abstract with reviewer feedback incorporated",
     memory_type   = "summary",
     memory_item_kind = "document",
     space_path    = "papers",
     artifact_location = "/absolute/path/to/file.md",
     tags          = ["published"],
     source_revision_krefs = ["kref://CognitiveMemory/conversations/2026-02-11.conversation?r=1"],
     edge_type     = "CREATED_FROM"
   )
   ```

   **Option B — Multi-step (for stacking revisions on existing items):**

   If step 2 found an existing item, stack a new revision on it:

   ```
   kumiho_create_revision(
     item_kref = "kref://CognitiveMemory/papers/cognitive-memory.document",
     metadata  = {
       "summary":    "Updated abstract with reviewer feedback incorporated",
       "type":       "document",
       "format":     "markdown",
       "generated_by": "agent"
     }
   )
   ```

   Then move the tag and link provenance:

   ```
   kumiho_tag_revision(
     revision_kref = "kref://CognitiveMemory/papers/cognitive-memory.document?r=3",
     tag           = "published"
   )

   kumiho_create_edge(
     source_kref = "kref://CognitiveMemory/papers/cognitive-memory.document?r=3",
     target_kref = "kref://CognitiveMemory/conversations/2026-02-11.conversation?r=1",
     edge_type   = "CREATED_FROM"
   )
   ```

4. **Discover related memories** — call `kumiho_memory_discover_edges`
   with the revision kref and a summary of what was produced:
   ```
   kumiho_memory_discover_edges(
     revision_kref = "kref://CognitiveMemory/papers/cognitive-memory.document?r=3",
     summary       = "Updated abstract incorporating reviewer feedback on methodology"
   )
   ```

**When to use which:** Use `kumiho_memory_store` when creating a brand-new
memory (it handles space/item/revision/artifact/edges/tag atomically). Use the
multi-step flow when you found an existing item via search and need to stack
a new revision on it.

**If the user iterates on the same output** (e.g., "revise the abstract",
"update the plan"), do NOT create a new item. Stack a new revision on the
existing item (Option B), write the updated artifact, and move the `published`
tag. The revision history preserves every version automatically.

---

## Procedural memory — storing tool executions

When the agent runs a significant command, builds a project, deploys
something, or executes a complex tool chain, **store the outcome** via
`kumiho_memory_store_execution`. This creates procedural memory — the
agent's record of *what it did and what happened*.

### When to store executions

- Build/compile results (especially failures — valuable for future sessions)
- Deployment commands and their outcomes
- Test runs with pass/fail summaries
- Database migrations
- Complex multi-step tool chains (e.g., "ran these 5 git commands to fix
  the merge conflict")
- Any command the user might ask about later: "What happened when we
  deployed last time?"

### When NOT to store

- Trivial commands (`ls`, `git status`, reading files)
- Commands that produced no meaningful outcome
- Intermediate steps of a chain (store the chain summary, not each step)

### Example

```
kumiho_memory_store_execution(
  task      = "cargo build --release",
  status    = "done",
  stdout    = "Build succeeded. 42 crates compiled in 3m 12s. Binary at target/release/kumiho-server.",
  exit_code = 0,
  duration_ms = 192000,
  tools     = ["Bash"],
  topics    = ["kumiho-server", "rust", "build"]
)
```

Status values: `done` (success), `failed` (expected failure), `error`
(unexpected failure), `blocked` (could not proceed).

**Link executions to decisions.** If a build failure leads to a decision
(e.g., "switch from OpenSSL to rustls"), create a DERIVED_FROM edge from
the decision back to the execution record.

---

## Context compaction — preserve the summary

When your conversation context is compacted — via `/compact` or automatic
compression — the summary that replaces prior exchanges is your **only
record** of what happened before. If you don't store it, that context is
gone forever.

**Immediately after compaction**, store the compact summary as memory:

```
kumiho_memory_store(
  user_text      = "<brief description of what the user was working on>",
  assistant_text = "<the compact summary of the conversation so far>",
  title          = "Session compact: <brief topic description>",
  summary        = "<first 200 chars of the compact summary>",
  memory_type    = "summary",
  tags           = ["compact", "session-context"],
  space_hint     = "session-compacts"
)
# -> Returns: { "revision_kref": "kref://...", ... }
```

Then follow the [Store & Link Protocol](store-and-link.md) — call
`kumiho_memory_discover_edges` on the result to connect this compacted
context to related existing memories:

```
kumiho_memory_discover_edges(
  revision_kref = "<revision_kref from store result>",
  summary       = "<the compact summary>"
)
```

This ensures that even when the conversation window is flushed, the graph
retains the reasoning chain. Your future self (or a new session) can recall
what happened before compaction via `kumiho_memory_recall`.
