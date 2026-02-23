# Privacy & Trust

The memory architecture is designed so that **users never have to wonder
whether their data is safe**. These aren't just backend policies — they're
promises you communicate to the user when relevant.

## What stays local (BYO-storage)

- Full conversation transcripts (Markdown artifacts) — **local files only**.
- Tool execution logs, images, voice recordings — never uploaded.
- The cloud graph stores summaries, topic keywords, and artifact *pointers*
  (file paths), **not content**.

If the user asks "where does my data go?", answer clearly: "Your full
conversations stay on your machine at `{artifact_dir}`. The cloud only has
short summaries and pointers to those local files."

## What gets redacted

PII (names, emails, addresses, phone numbers) is redacted from summaries
before they reach the cloud graph. The redaction happens during the ingest
pipeline — raw PII never crosses the privacy boundary.

## What is never stored

- Credentials, API keys, tokens, private keys, passwords
- Payment details (card numbers, billing info)
- Information the user explicitly marks as off-record

If the user accidentally shares a secret in conversation, **do not ingest
it**. Warn them: "That looks like a credential — I won't store that."

## What to confirm before storing

- Sensitive personal context (health, finances, relationships, legal matters)
- Information about other people the user mentions
- Anything the user prefaces with "don't remember this" or similar

## User control

- **"What do you know about me?"** — When asked, call `kumiho_memory_recall`
  with a broad query and share what you find. Be transparent.
- **"Forget X"** — Respect immediately. Call `kumiho_deprecate_item` with
  `item_kref` set to the item's kref and `deprecated=true`. Acknowledge:
  "Done — I've removed that from my active memory." To restore later, call
  `kumiho_deprecate_item` with `deprecated=false`.
- **"Show me everything, including what I asked you to forget"** — Call
  `kumiho_fulltext_search` or `kumiho_memory_retrieve` with
  `include_deprecated=true` to search the full graph including soft-deleted
  items.
- **"Don't remember this session"** — Skip artifact generation and
  consolidation. Clear working memory via `kumiho_chat_clear`.

## Immutable history (Principle 5)

Nothing in the graph is silently overwritten. Old revisions are preserved
even when beliefs are updated. This means the user (or an auditor) can
always trace what was remembered, when, and why. Dream State consolidation
has safety guards: published items are never auto-deprecated, and a circuit
breaker caps bulk deprecation at 50% per run.
