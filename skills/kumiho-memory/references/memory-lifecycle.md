# Memory Lifecycle

## Revision discipline — stack, don't scatter (MANDATORY)

**Design alignment**: Principle 5 — Immutable Revisions, Mutable Pointers.

The graph's power comes from **stacking revisions on a single item**, not
creating a new item for every iteration. A paper that goes through four
drafts should be ONE item (`paper-title.document`) with revisions r=1
through r=4 — not four separate items (`paper-draft`, `paper-v2`,
`paper-final`, `paper-final-v2`). The same applies to decisions, facts,
plans, and any evolving content.

**CRITICAL RULE: Always search before you create.** Before calling
`kumiho_create_item`, you MUST first search for an existing item that
represents the same concept:

```
# WRONG — blindly creating a new item
kumiho_create_item(
  space_path = "CognitiveMemory/papers",
  item_name  = "cognitive-memory-v2",    # <- proliferating items
  kind       = "document"
)

# RIGHT — search first, then stack
results = kumiho_search_items(
  query = "cognitive memory paper",
  kind  = "document"
)
# Found existing item -> create a new revision on it
kumiho_create_revision(
  item_kref = "kref://CognitiveMemory/papers/cognitive-memory-paper.document",
  metadata  = { "summary": "Revised abstract and methodology section", ... }
)
# Move the published tag to the new revision
kumiho_tag_revision(
  revision_kref = "kref://CognitiveMemory/papers/cognitive-memory-paper.document?r=4",
  tag           = "published"
)
```

## The revision stacking checklist

Run through this mentally every time:

1. **Search** — call `kumiho_search_items` or `kumiho_fulltext_search` for
   the concept you're about to store. Use broad keywords.
2. **If found** — create a new revision on the existing item via
   `kumiho_create_revision`. Include updated metadata and artifact.
   Move the `published` tag to the new revision.
3. **If NOT found** — only then create a new item via
   `kumiho_create_item`, then create revision r=1 on it.
4. **Never** name items with version suffixes (`-v2`, `-draft-2`,
   `-final`, `-revised`). The revision number IS the version.

## When to create a genuinely new item vs. a new revision

| Scenario | Action |
|----------|--------|
| Updated version of the same document | New revision on existing item |
| Revised decision (changed your mind) | New revision on existing item + SUPERSEDES edge |
| Corrected fact | New revision on existing item |
| Completely different topic/concept | New item |
| A sub-document (e.g., "appendix" of a paper) | New item + CONTAINS edge from parent |

## What to remember automatically

Ingest these via `kumiho_memory_ingest` or `kumiho_memory_store` **without
asking**:

**From the user:**
- **Decisions**: "Let's use PostgreSQL for this" -> ingest as a decision
- **Preferences**: "I prefer tabs over spaces" -> ingest as a preference
- **Project facts**: "The API is deployed on Cloud Run" -> ingest as context
- **Corrections**: "Actually, the endpoint is /v2 not /v1" -> ingest, and
  it will supersede the earlier belief in the graph
- **Tool/workflow patterns**: User always runs `cargo clippy` before
  committing -> ingest as a procedural pattern

**From your own responses** (use `kumiho_memory_store`):
- **Architecture decisions**: You recommended an approach and the user
  accepted -> store the decision with rationale
- **Bug resolutions**: You diagnosed and fixed a non-trivial bug -> store
  the root cause + fix so it doesn't require re-diagnosis
- **Implementation summaries**: You completed a multi-step task (feature,
  refactor, migration) -> store what was done, which files changed, and why
- **Explanations of complex topics**: You gave a detailed technical
  explanation the user found useful -> store it for future reference
- **Configuration / setup outcomes**: You helped set up a tool, service, or
  environment -> store the final working configuration

**Always follow the [Store & Link Protocol](store-and-link.md)** when calling
`kumiho_memory_store`. If recall results from this turn are relevant,
pass their krefs as `source_revision_krefs`. Then call
`kumiho_memory_discover_edges` on the result.

**When NOT to auto-store your response:**
- Trivial or one-line answers (simple lookups, yes/no, formatting help)
- The user is just brainstorming and hasn't committed to anything
- The response is purely conversational with no reusable knowledge

## What to ask before remembering

- Sensitive personal information (health, finances, relationships)
- Information the user explicitly marks as temporary or off-record
- Credentials, tokens, or secrets (never store these — see
  [Privacy and trust](privacy-and-trust.md))

## How to handle contradictions

When new information conflicts with a stored memory:

1. Acknowledge it naturally: "I had noted you prefer X — sounds like that's
   changed?"
2. If confirmed, ingest the new fact. The graph's revision system
   (SUPERSEDES edge) handles the belief evolution automatically.
3. Don't cling to old context. The latest revision tagged `published` is
   always the current truth.
