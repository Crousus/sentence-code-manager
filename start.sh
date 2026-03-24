#!/bin/bash
# Start the Manifesto Classifier Dashboard
# Usage: ./start.sh

set -e
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

echo "=== Manifesto Classifier Dashboard ==="
echo ""

# -- Backend --
PYTHON="$SCRIPT_DIR/../rlang/venv/bin/python"
if [ ! -f "$PYTHON" ]; then
  PYTHON="$(which python3)"
fi

echo "[1/2] Starting FastAPI backend on http://localhost:8000 ..."
cd "$SCRIPT_DIR/backend"
"$PYTHON" -m uvicorn main:app --host 0.0.0.0 --port 8000 --reload &
BACKEND_PID=$!
echo "      Backend PID: $BACKEND_PID"
cd "$SCRIPT_DIR"

# Give backend a moment to start
sleep 2

# -- Frontend --
echo "[2/2] Starting Next.js frontend on http://localhost:3000 ..."
cd "$SCRIPT_DIR/frontend"

# Source nvm if needed
export NVM_DIR="$HOME/.nvm"
[ -s "$NVM_DIR/nvm.sh" ] && source "$NVM_DIR/nvm.sh"

npm run dev &
FRONTEND_PID=$!
echo "      Frontend PID: $FRONTEND_PID"

echo ""
echo "Dashboard: http://localhost:3000"
echo "API docs:  http://localhost:8000/docs"
echo ""
echo "Press Ctrl+C to stop both services."

# Cleanup on exit
trap "echo ''; echo 'Stopping...'; kill $BACKEND_PID $FRONTEND_PID 2>/dev/null; exit 0" INT TERM

wait $BACKEND_PID $FRONTEND_PID
