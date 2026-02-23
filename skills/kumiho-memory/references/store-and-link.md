# Store & Link Protocol

Every memory store operation — whether via `kumiho_memory_store`,
`kumiho_memory_consolidate`, or `kumiho_memory_store_execution` — MUST
create edges. Isolated nodes are dead nodes. Follow this three-step protocol.

**Design alignment**: Principle 6 — Explicit Over Inferred Relationships.
Embedding similarity finds related content; edges encode reasoning structure.
Both are necessary; neither is sufficient alone.

---

## Step 1 — Collect source krefs from recall

Every turn already calls `kumiho_memory_recall` (Perceive-Recall-Revise-Act
loop, step 2). The results contain a `kref` field per result. **Hold onto
these krefs.** When you store a memory later in the same turn, these become
your `source_revision_krefs`.

```
# Recall returns results with krefs
recall_result = kumiho_memory_recall(query = "deployment architecture")
# -> results: [
#     { "kref": "kref://CognitiveMemory/.../grpc-decision.conversation?r=2", "score": 0.87, ... },
#     { "kref": "kref://CognitiveMemory/.../cloud-run-setup.conversation?r=1", "score": 0.72, ... }
#   ]

# Collect relevant krefs (score > 0.5 or clearly related to the topic)
relevant_krefs = [r["kref"] for r in recall_result["results"] if r["score"] > 0.5]
```

## Step 2 — Pass source krefs into kumiho_memory_store

When storing a memory, pass the collected krefs as `source_revision_krefs`.
This creates edges automatically — one API call, complete graph.

```
kumiho_memory_store(
  user_text     = "User asked about K8s vs Cloud Run for the new service",
  assistant_text = "Recommended Cloud Run based on prior gRPC decision...",
  title         = "Deployment recommendation: Cloud Run for auth service",
  summary       = "Chose Cloud Run based on existing gRPC infrastructure decision",
  memory_type   = "decision",
  tags          = ["deployment", "cloud-run"],
  source_revision_krefs = [
    "kref://CognitiveMemory/.../grpc-decision.conversation?r=2",
    "kref://CognitiveMemory/.../cloud-run-setup.conversation?r=1"
  ],
  edge_type     = "DERIVED_FROM"
)
# -> Returns: { "revision_kref": "kref://...?r=1", ... }
```

**When no recall was done this turn** (e.g., storing a user preference
unprompted), omit `source_revision_krefs`. Not every memory needs ancestors —
but every memory that *builds on prior context* must link to it.

## Step 3 — Discover broader edges after store

After `kumiho_memory_store` returns, call `kumiho_memory_discover_edges`
with the returned `revision_kref` and `summary`. This finds semantically
related memories that weren't in your recall results — connections you
wouldn't have thought to make.

```
# Use the revision_kref from the store result
kumiho_memory_discover_edges(
  revision_kref = "<revision_kref from store result>",
  summary       = "Chose Cloud Run for auth service based on gRPC infrastructure",
  max_edges     = 3
)
```

**When to run discover_edges:**
- **ALWAYS** after storing decisions, architecture recommendations,
  implementation summaries, or any synthesis
- **ALWAYS** after `kumiho_memory_consolidate` (see
  [Conversation artifacts](conversation-artifacts.md))
- **SKIP** for trivial facts and simple preferences where edges would
  add noise

---

## Edge types reference

| Edge type | Meaning | When to use |
|-----------|---------|-------------|
| `DERIVED_FROM` | "This conclusion came from analyzing those sources" | **Default for `source_revision_krefs`.** Decisions, summaries, synthesis from prior context. |
| `DEPENDS_ON` | "This memory's validity depends on that being true" | Decisions resting on assumptions. Use `kumiho_create_edge` directly for these. |
| `REFERENCED` | "This memory mentions that concept" | Loose association. Auto-created by `kumiho_memory_discover_edges`. |
| `CREATED_FROM` | "This output was generated from these inputs" | Artifacts (code, docs) linked to the conversation that produced them. Use `kumiho_create_edge` directly. |
| `SUPERSEDES` | "This replaces that older belief" | Created automatically by the ingest pipeline for belief revision. |
| `CONTAINS` | "This group contains these members" | Bundles grouping related memories. |

## Rules of thumb

- If recall found relevant memories this turn -> use their krefs in
  `source_revision_krefs` with `DERIVED_FROM`
- If a decision depends on an assumption that might change -> additionally
  create a `DEPENDS_ON` edge via `kumiho_create_edge`
- 2-4 edges per memory is the sweet spot. Don't over-link — if the
  relationship is tenuous, skip it
- `kumiho_memory_discover_edges` handles the `REFERENCED` edges
  automatically; you don't need to create those manually
