#!/usr/bin/env bash
# CLARKE context refresh hook for OpenClaw
#
# On session start:
# 1. Fetches dynamic context from CLARKE and writes it into SOUL.md/AGENTS.md
# 2. Outputs a status greeting (e.g., "CLARKE is healthy | 2 agents, 1 policy | /clarke for dashboard")
#
# The greeting is printed to stdout so OpenClaw displays it in the session start message.

set -euo pipefail

python -c "
import sys, os
clarke_repo = os.environ.get('CLARKE_REPO', '')
if clarke_repo and clarke_repo not in sys.path:
    sys.path.insert(0, clarke_repo)
from openclaw.lib.context_writer import refresh
refresh()
" 2>/dev/null || echo "CLARKE is offline | start with: make dev"
