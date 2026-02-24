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
    "  2. Call kumiho_memory_recall ONCE with a broad query to load "
    "recent context.  This is your ONLY recall for the first turn — "
    "do NOT call kumiho_memory_recall again on this turn.\n"
    "  3. Greet the user by name with continuity.\n"
    "\n"
    "After the first message, step 1 is DONE.  For the rest of the "
    "session:\n"
    "  - Do NOT invoke the kumiho-memory skill again.\n"
    "  - Call kumiho_memory_recall at most ONCE per turn (never "
    "multiple recall calls in a single turn).\n"
    "  - Do NOT narrate memory operations — the user should experience "
    "you as someone who simply knows them.\n"
    "  - Do NOT re-ask questions the user already answered in this "
    "conversation.\n"
    "  - Do NOT re-execute tasks already completed in this conversation.\n"
    "  - If you need user input, ask and STOP.  Never simulate the "
    "user's answer within your own response.\n"
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
