#!/usr/bin/env python3
"""SessionStart hook — inject memory skill invocation instruction.

This hook fires at the beginning of every Claude Code session (new or
resumed) and injects additionalContext that tells Claude to invoke the
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
    "1. ONE-TIME BOOTSTRAP — If you have not yet invoked the "
    "kumiho-memory:kumiho-memory skill in this session, you MUST invoke it "
    "now using the Skill tool BEFORE responding to the user.  This loads "
    "the user's identity, preferences, and recent context.  Once invoked, "
    "do NOT invoke it again on later messages — it only runs once per "
    "session.\n"
    "\n"
    "2. RECALL BEFORE EVERY ANSWER — On every user message (not just the "
    "first), if the topic might have history (preferences, past decisions, "
    "project facts, personal details), call kumiho_memory_recall with "
    "relevant keywords BEFORE answering.  Never say 'I don't know' or "
    "'I don't have that' without searching memory first.  This rule "
    "applies for the entire session, on every turn.\n"
    "\n"
    "3. NEVER NARRATE THE PLUMBING — Do not tell the user you are "
    "'loading memory', 'running the bootstrap', 'recalling who they are', "
    "or 'checking persistent memory'.  All MCP calls happen silently.  "
    "The user should experience you as someone who simply knows them — "
    "like a colleague, not someone reading a name tag.  Just greet them "
    "naturally and reference recent context as if you already know it."
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
