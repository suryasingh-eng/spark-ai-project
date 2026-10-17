#!/bin/bash
set -e
cd "$(dirname "$0")"
echo "===================================="
echo "       SPARK AI - First Run"
echo "===================================="

if ! command -v python3 >/dev/null 2>&1; then
  echo "Python 3 is required. Install it from https://www.python.org/downloads/macos/"
  read -r -p "Press Enter to close..."
  exit 1
fi

if [ ! -d ".venv" ]; then
  python3 -m venv .venv
fi
source .venv/bin/activate
python -m pip install --upgrade pip
pip install -r requirements.txt

if [ ! -f ".env" ]; then
  cp .env.example .env
fi

if ! grep -q '^GEMINI_API_KEY=.' .env; then
  echo ""
  echo "One required setup step: add your Gemini API key to the .env file."
  echo "Opening .env in the default text editor..."
  open -t .env || true
  echo "Paste the key after GEMINI_API_KEY=, save, and close the editor."
  read -r -p "Press Enter after saving .env..."
fi

echo "Starting SPARK AI..."
python -m uvicorn api.main:app --host 127.0.0.1 --port 8000 > api.log 2>&1 &
API_PID=$!
echo "$API_PID" > .api.pid
sleep 2
python -m streamlit run frontend/app.py --server.address 127.0.0.1 --server.port 8501
kill "$API_PID" 2>/dev/null || true
rm -f .api.pid
