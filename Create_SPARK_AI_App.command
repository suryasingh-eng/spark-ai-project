#!/bin/bash
set -e
cd "$(dirname "$0")"

PROJECT_DIR="$(pwd)"
APP_DIR="$HOME/Applications"
APP_PATH="$APP_DIR/SPARK AI.app"
DESKTOP_LINK="$HOME/Desktop/SPARK AI.app"

mkdir -p "$APP_DIR"

# Build a tiny macOS app wrapper that starts the local SPARK AI services.
APPLESCRIPT="$(mktemp)"
cat > "$APPLESCRIPT" <<'APPLESCRIPT_EOF'
on run
    set projectPath to "__PROJECT_PATH__"
    set shellCommand to "cd " & quoted form of projectPath & " && " & ¬
        "if [ ! -d .venv ]; then python3 -m venv .venv; fi; " & ¬
        "source .venv/bin/activate; python -m pip install -r requirements.txt >/tmp/spark_ai_pip.log 2>&1; " & ¬
        "if [ ! -f .env ]; then cp .env.example .env; fi; " & ¬
        "if ! grep -q '^GEMINI_API_KEY=.' .env; then open -t .env; display notification " & quoted form of "Add your Gemini API key to .env, save it, then open SPARK AI again." & " with title " & quoted form of "SPARK AI setup needed" & "; exit 0; fi; " & ¬
        "if ! lsof -nP -iTCP:8000 -sTCP:LISTEN >/dev/null 2>&1; then nohup .venv/bin/python -m uvicorn api.main:app --host 127.0.0.1 --port 8000 > api.log 2>&1 </dev/null & fi; " & ¬
        "if ! lsof -nP -iTCP:8501 -sTCP:LISTEN >/dev/null 2>&1; then nohup .venv/bin/python -m streamlit run frontend/app.py --server.address 127.0.0.1 --server.port 8501 > streamlit.log 2>&1 </dev/null & fi; " & ¬
        "sleep 3; open http://localhost:8501"
    do shell script shellCommand
end run
APPLESCRIPT_EOF

# Escape backslashes and quotes for AppleScript string
python3 - "$PROJECT_DIR" "$APPLESCRIPT" <<'PY'
import sys
project, path = sys.argv[1], sys.argv[2]
escaped = project.replace("\\", "\\\\").replace('"', '\\"')
with open(path, "r", encoding="utf-8") as f:
    s = f.read()
s = s.replace("__PROJECT_PATH__", escaped)
with open(path, "w", encoding="utf-8") as f:
    f.write(s)
PY

rm -rf "$APP_PATH"
osacompile -o "$APP_PATH" "$APPLESCRIPT"
rm -f "$APPLESCRIPT"

# Add a Desktop alias (symbolic link) to the app.
rm -f "$DESKTOP_LINK"
ln -s "$APP_PATH" "$DESKTOP_LINK"

echo ""
echo "SPARK AI app created:"
echo "  $APP_PATH"
echo "Desktop icon:"
echo "  $DESKTOP_LINK"
echo ""
echo "You can now double-click SPARK AI.app on your Desktop."
echo "First launch may ask you to install dependencies; the initial setup script does that."
echo "If the app asks for a Gemini key, edit the .env file in this project folder."
