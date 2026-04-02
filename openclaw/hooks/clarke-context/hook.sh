#!/usr/bin/env bash
# CLARKE context refresh hook for OpenClaw
# Fetches dynamic context from CLARKE and writes it into SOUL.md/AGENTS.md
# so the Brain picks it up on the next LLM call.

set -euo pipefail

python -c "
import sys, os
# Add the CLARKE repo to path if not installed
clarke_repo = os.environ.get('CLARKE_REPO', os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath('$0')))))
if clarke_repo not in sys.path:
    sys.path.insert(0, clarke_repo)
from openclaw.lib.context_writer import refresh
refresh()
" 2>/dev/null || echo "CLARKE context refresh skipped (server not reachable)" >&2
