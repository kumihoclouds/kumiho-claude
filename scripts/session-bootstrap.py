#!/usr/bin/env python3
"""SessionStart hook — inject memory skill invocation instruction.

This hook fires at the beginning of every session (Claude Code or
Cowork) and injects additionalContext that tells Claude to invoke the
kumiho-memory skill before responding to the user.  Without this hook
the skill's SKILL.md content is never loaded into context and the
memory bootstrap cannot run.

The context also reminds Claude about the recall-before-respond rule
so it persists across the full session.
"""

from __future__ import annotations

import json
import sys

CONTEXT = (
    "SESSION-START INSTRUCTION (kumiho-memory plugin)\n"
    "\n"
    "FIRST MESSAGE ONLY — before responding to the user:\n"
    "  1. Invoke the kumiho-memory:kumiho-memory skill.  This loads "
    "behavioral rules and triggers the identity bootstrap.\n"
    "  2. Call kumiho_memory_recall with a broad query to load recent "
    "context.\n"
    "  3. Greet the user by name with continuity.\n"
    "\n"
    "After the first message, step 1 is DONE.  For the rest of the "
    "session:\n"
    "  - Do NOT invoke the kumiho-memory skill again.\n"
    "  - DO call kumiho_memory_recall on every turn where the topic "
    "might have history.\n"
    "  - Do NOT narrate memory operations — the user should experience "
    "you as someone who simply knows them.\n"
    "\n"
    "STORE COMPACT SUMMARIES — When context is compacted (/compact or "
    "auto-compression), store the compact summary via kumiho_memory_store "
    "with memory_type='summary' and tags ['compact', 'session-context'], "
    "then call kumiho_memory_discover_edges on the result.\n"
    "\n"
    "STORE & LINK — When storing any memory via kumiho_memory_store, "
    "pass relevant recall krefs as source_revision_krefs, then call "
    "kumiho_memory_discover_edges on the returned revision_kref."
)

print(
    json.dumps(
        {
            "hookSpecificOutput": {
                "hookEventName": "SessionStart",
                "additionalContext": CONTEXT,
            }
        }
    )
)
sys.exit(0)
