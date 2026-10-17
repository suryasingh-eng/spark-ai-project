# SPARK AI — Autonomous Student Success Agent

**SPARK** = Student Productivity And Resource Knowledge AI

A Python-based student AI application with:
- Syllabus/PDF upload and topic extraction
- Personalized study-plan generation
- AI tutor/chat
- Quiz generation and grading
- Progress tracking and weak-topic identification
- Local account signup/login
- FastAPI backend + Streamlit web interface
- SQLite database by default (no PostgreSQL setup required)

## One-time requirement
Generative AI features use Google's Gemini API. Get an API key from Google AI Studio and paste it into `.env` as `GEMINI_API_KEY=...`. Keep the key private. API access/usage may be subject to Google's current terms and limits.

## Run on macOS
1. Extract this folder.
2. Double-click `run_mac.command`. If macOS blocks it, open Terminal in this folder and run:
   `chmod +x run_mac.command && ./run_mac.command`
3. On first run, the script installs dependencies and opens `.env`. Paste your Gemini API key after `GEMINI_API_KEY=`, save, and return to Terminal.
4. The app opens at `http://localhost:8501`. API docs are at `http://127.0.0.1:8000/docs`.

The script creates a local `.venv` and `spark_ai.db` automatically.

## Run manually
```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
cp .env.example .env
# Edit .env and add GEMINI_API_KEY
python -m uvicorn api.main:app --reload --port 8000
# In another Terminal tab:
source .venv/bin/activate
streamlit run frontend/app.py
```

## Main features
1. **Dashboard** — study overview, recent activity, and weak topics.
2. **Syllabus Lab** — upload PDF or paste syllabus text; extract and save it.
3. **Study Planner** — create a plan based on available days and daily study time.
4. **AI Tutor** — ask questions in simple language; request examples and exam-ready answers.
5. **Quiz Studio** — generate MCQs, answer them, and record results.
6. **Progress** — review quiz performance and identify topics to revise.

## Data and security notes
- The database is local to this machine. Do not upload confidential documents.
- This is a hackathon-ready MVP, not a production identity/security system.
- For a public deployment, add HTTPS, robust rate limiting, secure secret management, stronger session management, and proper cloud database/storage.
- Never commit `.env`, passwords, or API keys to GitHub.


## Create a desktop app icon (macOS)
After extracting the project and completing the first-run setup, open this folder in Finder and double-click `Create_SPARK_AI_App.command`. If macOS blocks it, open Terminal in this folder and run:
```bash
chmod +x Create_SPARK_AI_App.command
./Create_SPARK_AI_App.command
```
It creates `~/Applications/SPARK AI.app` and a `SPARK AI.app` icon on your Desktop. Double-click that icon to start the local services and open the app in your browser. The project folder must stay in the same location after creating the app.
