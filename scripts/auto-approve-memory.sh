#!/bin/bash
# auto-approve-memory.sh
# Auto-approves non-destructive Kumiho memory tool calls.
# Destructive operations (delete, untag, deprecate) still require
# manual user approval via the normal permission dialog.

INPUT=$(cat)
TOOL_NAME=$(echo "$INPUT" | jq -r '.tool_name')

# Let destructive operations fall through to the permission dialog
if echo "$TOOL_NAME" | grep -qiE '(delete|untag|deprecate)'; then
  exit 0
fi

# Auto-approve everything else from kumiho-memory
cat <<'EOF'
{
  "hookSpecificOutput": {
    "hookEventName": "PermissionRequest",
    "decision": {
      "behavior": "allow"
    }
  }
}
EOF
