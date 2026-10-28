#!/usr/bin/env bash
cd "$(dirname "$0")"

echo "==================================================="
echo "  Universal Skill Manager (USM)"
echo "  Starting Local Web Dashboard..."
echo "==================================================="
echo

if [ -f ".venv/bin/usm" ]; then
    .venv/bin/usm ui --port 8765
elif [ -f ".venv/bin/python" ]; then
    .venv/bin/python -m usm ui --port 8765
else
    usm ui --port 8765
fi
