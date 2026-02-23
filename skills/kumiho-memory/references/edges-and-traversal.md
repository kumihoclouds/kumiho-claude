# Edges and Graph Traversal

## Graph-augmented recall

The `kumiho_memory_recall` tool supports an optional `graph_augmented: true`
parameter that enables a more powerful retrieval strategy:

1. **Multi-query reformulation** — an LLM generates 2-3 alternative search
   queries capturing different semantic angles (emotion, causal events,
   related concepts).
2. **Edge traversal** — follows graph edges from top results to discover
   connected memories that vector search alone would miss.
3. **Semantic fallback** — when no graph edges exist yet, performs a
   second-hop recall using titles/summaries from initial results.

**When to use `graph_augmented: true`:**

- The user's question is **indirect or implicit** — e.g. "should I use
  gRPC here?" might relate to a past architecture decision stored under
  different wording.
- The topic involves **chains of decisions** where one memory depends on
  another (project preferences -> library choices -> API patterns).
- Standard recall returned few or no results but you suspect relevant
  memories exist.

**When standard recall is sufficient:**

- Direct lookups — "what's my favorite color?", "what's my timezone?"
- The user is asking about something just discussed in this session.
- Simple preference or fact retrieval with obvious keyword overlap.

### Sibling revision selection at recall time

Recall results for stacked items include `sibling_revisions` — all other
revisions of the same item. The agent acts as the reranker:

1. **Scan sibling titles and summaries** for the best match to the query.
2. **Prefer specific matches** over broad ones — a sibling with
   `entities: "Evan, guitar"` is better than one with
   `summary: "Conversation about Evan's life updates"` when the query
   is about guitar practice.
3. **Use structured metadata** (`entities`, `facts`, `implications`,
   `events`) as discriminators when summaries are similarly relevant.
4. **Reference the selected sibling's kref** in `source_revision_krefs`
   when storing follow-up memories.

This client-side approach uses the host LLM (the agent itself) instead
of a dedicated server-side reranker — higher quality, zero additional
API cost, and full conversation context for selection.

---

## Edge creation

See [Store & Link Protocol](store-and-link.md) for the mandatory
three-step workflow for creating edges when storing memories. The protocol
covers `source_revision_krefs` at store time and `kumiho_memory_discover_edges`
for broader discovery.

For manual edge creation beyond the store-time flow, use
`kumiho_create_edge`:

```
# User decides on gRPC after discussing performance benchmarks
kumiho_create_edge(
  source_kref = "kref://CognitiveMemory/decisions/use-grpc.decision?r=1",
  target_kref = "kref://CognitiveMemory/facts/benchmark-results.fact?r=1",
  edge_type   = "DERIVED_FROM"
)

# A deployment decision depends on the infrastructure choice
kumiho_create_edge(
  source_kref = "kref://CognitiveMemory/decisions/deploy-cloud-run.decision?r=1",
  target_kref = "kref://CognitiveMemory/decisions/use-grpc.decision?r=1",
  edge_type   = "DEPENDS_ON"
)

# Conversation references a known project fact
kumiho_create_edge(
  source_kref = "kref://CognitiveMemory/conversations/2026-02-10.conversation?r=1",
  target_kref = "kref://CognitiveMemory/facts/api-deployed-cloud-run.fact?r=1",
  edge_type   = "REFERENCED"
)
```

---

## Using graph traversal — reasoning about memories

The graph is not just storage — it's a **reasoning tool**. Use traversal
when the user asks questions that require understanding relationships
between memories, not just recalling individual facts.

### When to traverse

| User question pattern | Tool to use | What it answers |
|-----------------------|-------------|-----------------|
| "Why did we decide X?" | `kumiho_get_dependencies` on the decision | Shows what facts/assumptions X depends on |
| "What would break if we change X?" | `kumiho_analyze_impact` on X | Shows all downstream decisions affected |
| "How are X and Y related?" | `kumiho_find_path` between X and Y | Finds the shortest reasoning chain connecting them |
| "What led to this conclusion?" | `kumiho_get_provenance_summary` | Extracts the full lineage (sources, models, parameters) |
| "What depends on this assumption?" | `kumiho_get_dependents` on the assumption | Shows everything that would need revisiting |
| "Show me all connections for X" | `kumiho_get_edges` with direction "both" | Lists all direct relationships |
| "What did we decide about X last week?" | `kumiho_get_revision_as_of` on the item + tag + timestamp | Shows the revision that had a tag at a past point in time |

### Traversal examples

```
# User asks: "Why did we go with Cloud Run?"
result = kumiho_get_dependencies(
  kref      = "kref://CognitiveMemory/decisions/deploy-cloud-run.decision?r=1",
  max_depth = 3
)
# -> Shows: DEPENDS_ON -> use-grpc.decision -> DERIVED_FROM -> benchmark-results.fact
# You answer: "We chose Cloud Run because of the gRPC decision, which itself
#   came from the performance benchmarks we ran two weeks ago."

# User asks: "If we switch from Neo4j to Postgres, what breaks?"
result = kumiho_analyze_impact(
  kref      = "kref://CognitiveMemory/decisions/use-neo4j.decision?r=1",
  direction = "outgoing"
)
# -> Returns downstream decisions sorted by proximity
# You answer: "Switching from Neo4j would affect the graph traversal queries,
#   the Dream State consolidation pipeline, and the hybrid search architecture."

# User asks: "How is the auth token issue related to the deployment problem?"
result = kumiho_find_path(
  source_kref = "kref://CognitiveMemory/facts/auth-token-propagation.fact?r=1",
  target_kref = "kref://CognitiveMemory/facts/deployment-failure.fact?r=1"
)
# -> Returns the shortest edge chain connecting the two

# User asks: "What was our API spec when we deployed on Feb 1st?"
result = kumiho_get_revision_as_of(
  item_kref = "kref://CognitiveMemory/decisions/api-spec.decision",
  tag       = "published",
  time      = "202602010000"
)
# -> Returns the revision that was tagged "published" at that timestamp
# You answer with the historical state, not the current one.
```

**Weave results into natural conversation.** Don't dump raw graph output.
Translate traversal results into plain reasoning: "We decided X because of
Y, which was based on Z."
