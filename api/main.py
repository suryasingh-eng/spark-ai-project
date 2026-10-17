from contextlib import asynccontextmanager
from typing import Optional
from fastapi import FastAPI, HTTPException
from pydantic import BaseModel, EmailStr, Field
from api.database import init_db, connect
from api.auth import hash_password, verify_password
from api.ai import ask_gemini

@asynccontextmanager
async def lifespan(app: FastAPI):
    init_db()
    yield

app = FastAPI(
    title="SPARK AI API",
    description="Student Productivity And Resource Knowledge AI — hackathon MVP API",
    version="1.0.0",
    lifespan=lifespan,
)

class SignupRequest(BaseModel):
    name: str = Field(min_length=2, max_length=80)
    email: EmailStr
    password: str = Field(min_length=8, max_length=128)

class LoginRequest(BaseModel):
    email: EmailStr
    password: str

class TutorRequest(BaseModel):
    question: str = Field(min_length=2, max_length=8000)
    context: Optional[str] = Field(default="", max_length=20000)
    style: str = "simple and student-friendly"

class PlanRequest(BaseModel):
    syllabus: str = Field(min_length=10, max_length=20000)
    days: int = Field(default=14, ge=1, le=180)
    hours_per_day: float = Field(default=2, ge=0.5, le=16)
    exam_date: Optional[str] = None

class QuizRequest(BaseModel):
    topic: str = Field(min_length=2, max_length=300)
    source_text: str = Field(default="", max_length=15000)
    count: int = Field(default=10, ge=3, le=30)
    difficulty: str = "medium"

@app.get("/")
def root():
    return {"app": "SPARK AI", "status": "running", "docs": "/docs"}

@app.get("/health")
def health():
    return {"status": "ok"}

@app.post("/auth/signup")
def signup(payload: SignupRequest):
    with connect() as db:
        try:
            cur = db.execute(
                "INSERT INTO users(name,email,password_hash) VALUES(?,?,?)",
                (payload.name.strip(), payload.email.lower(), hash_password(payload.password)),
            )
            return {"message": "Account created", "user_id": cur.lastrowid}
        except Exception as exc:
            if "UNIQUE" in str(exc).upper():
                raise HTTPException(status_code=409, detail="An account with this email already exists.")
            raise HTTPException(status_code=500, detail="Could not create account.")

@app.post("/auth/login")
def login(payload: LoginRequest):
    with connect() as db:
        row = db.execute(
            "SELECT id,name,email,password_hash FROM users WHERE email=?",
            (payload.email.lower(),),
        ).fetchone()
    if not row or not verify_password(payload.password, row["password_hash"]):
        raise HTTPException(status_code=401, detail="Incorrect email or password.")
    return {"message": "Login successful", "user": {"id": row["id"], "name": row["name"], "email": row["email"]}}

@app.post("/ai/tutor")
def tutor(payload: TutorRequest):
    prompt = f"""You are SPARK AI, a supportive and accurate student tutor.
Answer in {payload.style}. Explain concepts step by step, include an example when useful,
and finish with a short exam-ready definition when relevant.
Student context/syllabus: {payload.context or 'Not provided'}
Question: {payload.question}
If the question is ambiguous, state your assumption. Do not invent citations."""
    try:
        return {"answer": ask_gemini(prompt)}
    except RuntimeError as exc:
        raise HTTPException(status_code=503, detail=str(exc))

@app.post("/ai/study-plan")
def study_plan(payload: PlanRequest):
    prompt = f"""You are SPARK AI, an adaptive student study planner.
Create a practical {payload.days}-day plan with {payload.hours_per_day} study hours each day.
Exam date: {payload.exam_date or 'Not specified'}.
Use the syllabus below. Break it into daily topics, focused study blocks, practice questions,
revision, and weekly checkpoints. Prioritize prerequisites and difficult topics. Use a clear
Markdown table and include buffer/revision time. Do not claim to know the student's abilities.
SYLLABUS:
{payload.syllabus}"""
    try:
        return {"plan": ask_gemini(prompt)}
    except RuntimeError as exc:
        raise HTTPException(status_code=503, detail=str(exc))

@app.post("/ai/quiz")
def quiz(payload: QuizRequest):
    prompt = f"""Create {payload.count} {payload.difficulty} multiple-choice questions for a student.
Topic: {payload.topic}
Reference material (if provided):
{payload.source_text or 'Use reliable general knowledge.'}
Return valid JSON only as an array. Every item must have keys:
question (string), options (array of exactly 4 strings), answer (integer 0-3),
explanation (string), topic (string). Ensure exactly one correct answer per question."""
    try:
        return {"quiz_json": ask_gemini(prompt)}
    except RuntimeError as exc:
        raise HTTPException(status_code=503, detail=str(exc))
