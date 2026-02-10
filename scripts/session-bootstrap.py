#!/usr/bin/env python3
"""SessionStart hook — inject memory skill invocation instruction.

This hook fires at the beginning of every Claude Code session (new or
resumed) and injects additionalContext that tells Claude to invoke the
kumiho-memory skill before responding to the user.  Without this hook
the skill's SKILL.md content is never loaded into context and the
memory bootstrap cannot run.
"""

from __future__ import annotations

import json
import sys

CONTEXT = (
    "CRITICAL — kumiho-memory plugin is active.\n"
    "Before responding to the user's first message you MUST invoke the "
    "kumiho-memory:kumiho-memory skill using the Skill tool.  This will "
    "bootstrap persistent memory, load the user's identity and preferences, "
    "and recall recent context from previous sessions so you can greet them "
    "with continuity instead of a generic hello.\n"
    "Do NOT greet or respond until the skill has been invoked."
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
