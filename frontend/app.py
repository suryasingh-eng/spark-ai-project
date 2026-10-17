import os, sys, json, re, time
from pathlib import Path
import streamlit as st
import requests
import fitz
from dotenv import load_dotenv

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
load_dotenv(ROOT / ".env")

from api.database import init_db, connect
from api.auth import hash_password, verify_password
from api.ai import ask_gemini

init_db()
st.set_page_config(page_title="SPARK AI", page_icon="✨", layout="wide", initial_sidebar_state="expanded")

CUSTOM_CSS = """
<style>
.block-container {padding-top: 1.4rem; padding-bottom: 3rem; max-width: 1250px;}
[data-testid="stSidebar"] {border-right: 1px solid rgba(128,128,128,.2);}
.hero {padding: 1.5rem 1.7rem; border-radius: 20px; background: linear-gradient(120deg,#14213d,#23395d,#315c80); color:white; margin-bottom:1rem;}
.hero h1 {font-size:2.25rem; margin:0 0 .35rem 0;} .hero p {opacity:.9; margin:0;}
.small-muted {color: #777; font-size:.9rem;}
div[data-testid="stMetric"] {border:1px solid rgba(128,128,128,.2); padding:15px; border-radius:14px;}
</style>
"""
st.markdown(CUSTOM_CSS, unsafe_allow_html=True)

def db_user(email):
    with connect() as db:
        return db.execute("SELECT * FROM users WHERE email=?", (email.lower(),)).fetchone()

def save_record(table, fields, values):
    placeholders = ",".join(["?"] * len(values))
    with connect() as db:
        cur = db.execute(f"INSERT INTO {table}({fields}) VALUES({placeholders})", values)
        return cur.lastrowid

def ai(prompt):
    try:
        return ask_gemini(prompt)
    except Exception as exc:
        st.error(str(exc))
        return None

def get_pdf_text(upload):
    doc = fitz.open(stream=upload.getvalue(), filetype="pdf")
    text = "\n".join(page.get_text() for page in doc)
    return text[:20000]

def require_user():
    if not st.session_state.get("user"):
        st.info("Please sign in or create an account to use your personal SPARK AI workspace.")
        st.stop()

if "user" not in st.session_state: st.session_state.user = None
if "syllabus_text" not in st.session_state: st.session_state.syllabus_text = ""
if "syllabus_title" not in st.session_state: st.session_state.syllabus_title = "My syllabus"

with st.sidebar:
    st.markdown("## ✨ SPARK AI")
    st.caption("Student Productivity And Resource Knowledge AI")
    if st.session_state.user:
        st.success(f"Signed in as {st.session_state.user['name']}")
        page = st.radio("Workspace", ["Dashboard", "Syllabus Lab", "Study Planner", "AI Tutor", "Quiz Studio", "Progress"])
        if st.button("Log out", use_container_width=True):
            st.session_state.user = None
            st.rerun()
    else:
        page = "Welcome"

if not st.session_state.user:
    st.markdown('<div class="hero"><h1>✨ Meet SPARK AI</h1><p>Your AI study partner: understand your syllabus, build a study plan, practise quizzes, and improve weak topics.</p></div>', unsafe_allow_html=True)
    tab1, tab2 = st.tabs(["Sign in", "Create account"])
    with tab1:
        with st.form("login_form"):
            email = st.text_input("Email", placeholder="you@example.com")
            password = st.text_input("Password", type="password")
            submitted = st.form_submit_button("Sign in", use_container_width=True)
        if submitted:
            row = db_user(email.strip())
            if row and verify_password(password, row["password_hash"]):
                st.session_state.user = {"id": row["id"], "name": row["name"], "email": row["email"]}
                st.rerun()
            else:
                st.error("Email or password is incorrect.")
    with tab2:
        with st.form("signup_form"):
            name = st.text_input("Full name")
            new_email = st.text_input("Email address")
            p1 = st.text_input("Create password (8+ characters)", type="password")
            p2 = st.text_input("Confirm password", type="password")
            create = st.form_submit_button("Create account", use_container_width=True)
        if create:
            if len(name.strip()) < 2: st.error("Enter your name.")
            elif "@" not in new_email or "." not in new_email.split("@")[-1]: st.error("Enter a valid email.")
            elif len(p1) < 8: st.error("Password must be at least 8 characters.")
            elif p1 != p2: st.error("Passwords do not match.")
            elif db_user(new_email.strip()): st.error("An account with this email already exists.")
            else:
                with connect() as db:
                    cur = db.execute("INSERT INTO users(name,email,password_hash) VALUES(?,?,?)",
                                     (name.strip(), new_email.strip().lower(), hash_password(p1)))
                    uid = cur.lastrowid
                st.session_state.user = {"id": uid, "name": name.strip(), "email": new_email.strip().lower()}
                st.success("Account created!")
                st.rerun()
    st.markdown("---")
    st.caption("Your study records are stored locally on this computer. AI features require a Gemini API key in `.env`.")
    st.stop()

require_user()
uid = st.session_state.user["id"]

if page == "Dashboard":
    st.markdown(f'<div class="hero"><h1>Welcome back, {st.session_state.user["name"].split()[0]} 👋</h1><p>Small focused sessions. Consistent progress. Let’s make today count.</p></div>', unsafe_allow_html=True)
    with connect() as db:
        syllabus_count = db.execute("SELECT COUNT(*) c FROM syllabi WHERE user_id=?", (uid,)).fetchone()["c"]
        plan_count = db.execute("SELECT COUNT(*) c FROM study_plans WHERE user_id=?", (uid,)).fetchone()["c"]
        results = db.execute("SELECT score,total,topic,created_at FROM quiz_results WHERE user_id=? ORDER BY id DESC", (uid,)).fetchall()
    avg = round(sum((r["score"]/r["total"]*100) for r in results)/len(results)) if results else 0
    c1,c2,c3,c4 = st.columns(4)
    c1.metric("Syllabi saved", syllabus_count)
    c2.metric("Study plans", plan_count)
    c3.metric("Quizzes completed", len(results))
    c4.metric("Average quiz score", f"{avg}%" if results else "—")
    st.subheader("Your study command centre")
    col1,col2 = st.columns(2)
    with col1:
        st.info("📄 **Syllabus Lab**\n\nUpload a syllabus PDF or paste topics. SPARK AI will extract the content and help you use it.")
        st.info("🗓️ **Study Planner**\n\nCreate a day-by-day plan with revision and practice blocks.")
        st.info("📈 **Progress**\n\nTrack quiz scores and find topics that deserve another revision.")
    with col2:
        st.info("🧠 **AI Tutor**\n\nAsk for simple explanations, examples, code walkthroughs, or exam-ready answers.")
        st.info("🎯 **Quiz Studio**\n\nGenerate MCQs, submit answers, and save your results.")
        if results:
            st.markdown("**Recent quiz activity**")
            for r in results[:5]:
                st.write(f"• {r['topic']}: **{r['score']}/{r['total']}** — {r['created_at']}")
        else:
            st.caption("Complete your first quiz to start seeing progress insights.")

elif page == "Syllabus Lab":
    st.title("📄 Syllabus Lab")
    st.write("Upload a text-based PDF or paste your syllabus. Scanned PDFs may need OCR before their text can be extracted.")
    uploaded = st.file_uploader("Upload syllabus PDF", type=["pdf"])
    if uploaded:
        try:
            extracted = get_pdf_text(uploaded)
            if extracted.strip():
                st.session_state.syllabus_text = extracted
                st.session_state.syllabus_title = uploaded.name
                st.success(f"Extracted {len(extracted)} characters from {uploaded.name}.")
            else:
                st.warning("No selectable text found. This PDF may be scanned/image-only.")
        except Exception as e: st.error(f"Could not read this PDF: {e}")
    title = st.text_input("Syllabus title", value=st.session_state.syllabus_title)
    content = st.text_area("Syllabus text / extracted PDF content", value=st.session_state.syllabus_text, height=300,
                           placeholder="Paste units, chapters, learning outcomes, or syllabus text here...")
    if st.button("Save syllabus", type="primary"):
        if len(content.strip()) < 10: st.error("Add at least a few lines of syllabus first.")
        else:
            save_record("syllabi", "user_id,title,content", (uid,title.strip(),content.strip()))
            st.session_state.syllabus_text = content
            st.session_state.syllabus_title = title
            st.success("Syllabus saved to your local workspace.")
    with connect() as db:
        saved = db.execute("SELECT id,title,created_at FROM syllabi WHERE user_id=? ORDER BY id DESC", (uid,)).fetchall()
    if saved:
        st.subheader("Saved syllabi")
        for item in saved:
            with st.expander(f"{item['title']} — {item['created_at']}"):
                if st.button("Load this syllabus", key=f"load_{item['id']}"):
                    with connect() as db:
                        row = db.execute("SELECT content,title FROM syllabi WHERE id=? AND user_id=?", (item["id"],uid)).fetchone()
                    st.session_state.syllabus_text, st.session_state.syllabus_title = row["content"], row["title"]
                    st.rerun()
    if content.strip() and st.button("Analyse syllabus with AI"):
        with st.spinner("Analysing topics and priorities..."):
            out = ai("Analyse this student syllabus. Return: (1) units/topics, (2) prerequisite order, (3) high-yield revision checklist, (4) likely areas for practice questions. Be clear that exam predictions are not guaranteed.\n\n" + content[:18000])
        if out: st.markdown(out)

elif page == "Study Planner":
    st.title("🗓️ Adaptive Study Planner")
    with connect() as db:
        saved = db.execute("SELECT id,title,content FROM syllabi WHERE user_id=? ORDER BY id DESC", (uid,)).fetchall()
    labels = ["Paste my own syllabus"] + [f"{s['title']} (saved #{s['id']})" for s in saved]
    choice = st.selectbox("Choose syllabus", labels)
    syllabus = ""
    if choice == "Paste my own syllabus":
        syllabus = st.text_area("Syllabus / topics", value=st.session_state.syllabus_text, height=220)
    else:
        selected = saved[labels.index(choice)-1]
        syllabus = selected["content"]
        st.text_area("Selected syllabus preview", value=syllabus[:5000], height=150, disabled=True)
    c1,c2 = st.columns(2)
    days = c1.number_input("Plan length (days)", min_value=1, max_value=180, value=14)
    hours = c2.number_input("Study hours per day", min_value=0.5, max_value=16.0, value=2.0, step=0.5)
    exam_date = st.date_input("Exam date (optional)", value=None)
    if st.button("Generate my study plan", type="primary"):
        if len(syllabus.strip()) < 10: st.error("Choose or paste a syllabus first.")
        else:
            prompt = f"""You are SPARK AI, an adaptive student study planner. Create a practical {days}-day plan with {hours} study hours/day. Exam date: {exam_date or 'not specified'}. Use the syllabus below. Include daily topics, time blocks, active recall, practice, spaced revision, weekly checkpoints, and buffer time. Start with prerequisites and distribute difficult topics sensibly. Return a Markdown table and a short set of rules for adapting the plan after quiz results.\nSYLLABUS:\n{syllabus[:18000]}"""
            with st.spinner("Building your plan..."):
                plan = ai(prompt)
            if plan:
                st.markdown(plan)
                save_record("study_plans", "user_id,title,content", (uid,f"{days}-day plan",plan))
                st.success("Plan saved automatically.")
    with connect() as db:
        plans = db.execute("SELECT title,content,created_at FROM study_plans WHERE user_id=? ORDER BY id DESC LIMIT 5", (uid,)).fetchall()
    if plans:
        st.subheader("Saved plans")
        for p in plans:
            with st.expander(f"{p['title']} — {p['created_at']}"):
                st.markdown(p["content"])

elif page == "AI Tutor":
    st.title("🧠 SPARK AI Tutor")
    st.caption("Ask in English or Hinglish. Avoid sharing private or sensitive information.")
    context = st.text_area("Optional context: subject, unit, or syllabus", value=st.session_state.syllabus_text[:3000], height=100)
    style = st.selectbox("Answer style", ["Simple Hinglish with examples", "English exam-ready answer", "Step-by-step explanation", "Beginner-friendly with analogy", "Code walkthrough"])
    if "chat_history" not in st.session_state: st.session_state.chat_history = []
    for item in st.session_state.chat_history:
        with st.chat_message(item["role"]):
            st.markdown(item["content"])
    question = st.chat_input("Ask SPARK AI anything about your studies...")
    if question:
        st.session_state.chat_history.append({"role":"user","content":question})
        with st.chat_message("user"): st.markdown(question)
        with st.chat_message("assistant"):
            with st.spinner("Thinking..."):
                history = "\n".join([f"{x['role']}: {x['content']}" for x in st.session_state.chat_history[-8:]])
                answer = ai(f"""You are SPARK AI, a helpful student tutor. Answer style: {style}. Explain accurately and clearly. For programming, include runnable code when useful. For exam questions, finish with a concise definition/answer. Syllabus context: {context}\nRecent conversation:\n{history}\nAnswer the latest user question: {question}""")
                if answer:
                    st.markdown(answer)
                    st.session_state.chat_history.append({"role":"assistant","content":answer})
    if st.button("Clear chat"):
        st.session_state.chat_history = []
        st.rerun()

elif page == "Quiz Studio":
    st.title("🎯 Quiz Studio")
    with connect() as db:
        saved = db.execute("SELECT id,title,content FROM syllabi WHERE user_id=? ORDER BY id DESC", (uid,)).fetchall()
    topic = st.text_input("Topic", placeholder="e.g. Python lists, DBMS normalization, Operating Systems")
    source_choice = st.selectbox("Reference material", ["No reference material"] + [f"{s['title']} (saved #{s['id']})" for s in saved])
    source_text = ""
    if source_choice != "No reference material":
        selected_index = [f"{item['title']} (saved #{item['id']})" for item in saved].index(source_choice)
        source_text = saved[selected_index]["content"]
    count = st.slider("Number of questions", 3, 15, 5)
    difficulty = st.select_slider("Difficulty", options=["easy","medium","hard"], value="medium")
    if st.button("Generate quiz", type="primary"):
        if len(topic.strip()) < 2: st.error("Enter a topic first.")
        else:
            prompt = f"""Create exactly {count} {difficulty} MCQs about {topic}. Use this reference when supplied:\n{source_text[:12000] or 'No reference supplied; use reliable general knowledge.'}\nReturn valid JSON only, an array of objects with keys question, options (exactly 4 strings), answer (0-based integer), explanation, topic. Exactly one answer must be correct."""
            with st.spinner("Creating questions..."):
                raw = ai(prompt)
            if raw:
                try:
                    cleaned = re.sub(r"^```(?:json)?\s*|\s*```$", "", raw.strip(), flags=re.I)
                    match = re.search(r"\[.*\]", cleaned, re.S)
                    quiz = json.loads(match.group(0) if match else cleaned)
                    if not isinstance(quiz,list) or not quiz: raise ValueError("No quiz items found.")
                    st.session_state.active_quiz = {"topic":topic.strip(),"items":quiz[:count]}
                    st.session_state.quiz_submitted = False
                except Exception:
                    st.error("The AI response could not be parsed as a quiz. Please click Generate quiz again.")
                    with st.expander("Raw AI response"): st.code(raw)
    quiz_obj = st.session_state.get("active_quiz")
    if quiz_obj:
        st.markdown(f"### Quiz: {quiz_obj['topic']}")
        with st.form("quiz_form"):
            answers = []
            for i,q in enumerate(quiz_obj["items"]):
                st.markdown(f"**Q{i+1}. {q['question']}**")
                opts = q.get("options",[])
                if len(opts) != 4:
                    opts = (opts + ["Option unavailable"]*4)[:4]
                answers.append(st.radio("Choose one", opts, index=None, key=f"q_{i}", label_visibility="collapsed"))
            submitted = st.form_submit_button("Submit answers", type="primary")
        if submitted:
            score=0; details=[]
            for i,(q,answer_text) in enumerate(zip(quiz_obj["items"],answers)):
                opts=q.get("options",[])
                correct_index=int(q.get("answer",0))
                correct_index=max(0,min(correct_index,len(opts)-1))
                correct_text=opts[correct_index] if opts else "Unknown"
                is_correct = answer_text == correct_text
                score += int(is_correct)
                details.append({"question":q.get("question",""),"chosen":answer_text,"correct":correct_text,"is_correct":is_correct,"explanation":q.get("explanation","")})
            save_record("quiz_results","user_id,topic,score,total,details",(uid,quiz_obj["topic"],score,len(quiz_obj["items"]),json.dumps(details)))
            st.session_state.quiz_result = {"score":score,"total":len(quiz_obj["items"]),"details":details,"topic":quiz_obj["topic"]}
            st.rerun()
    result = st.session_state.get("quiz_result")
    if result and result["topic"] == (quiz_obj or {}).get("topic"):
        st.subheader(f"Result: {result['score']} / {result['total']} ({round(result['score']/result['total']*100)}%)")
        for i,d in enumerate(result["details"]):
            with st.expander(f"{'✅' if d['is_correct'] else '❌'} Q{i+1}: {d['question']}"):
                st.write("Your answer:", d["chosen"] or "Not answered")
                st.write("Correct answer:", d["correct"])
                st.write("Explanation:", d["explanation"])
        if result["score"]/result["total"] < .7:
            st.warning("This topic may need revision. Ask the AI Tutor to explain it, then try a fresh quiz.")

elif page == "Progress":
    st.title("📈 Progress & Weak Topics")
    with connect() as db:
        results = db.execute("SELECT topic,score,total,details,created_at FROM quiz_results WHERE user_id=? ORDER BY id DESC", (uid,)).fetchall()
    if not results:
        st.info("No quiz results yet. Complete a quiz in Quiz Studio to build your progress report.")
    else:
        avg = sum(r["score"]/r["total"]*100 for r in results)/len(results)
        c1,c2,c3 = st.columns(3)
        c1.metric("Quizzes",len(results))
        c2.metric("Average score",f"{avg:.1f}%")
        c3.metric("Latest score",f"{results[0]['score']}/{results[0]['total']}")
        weak={}
        for r in results:
            try:
                details=json.loads(r["details"])
                for d in details:
                    topic=d.get("question","")[:70]
                    if not d.get("is_correct"): weak[topic]=weak.get(topic,0)+1
            except Exception: pass
        st.subheader("Quiz history")
        for r in results:
            pct=round(r["score"]/r["total"]*100)
            st.write(f"**{r['topic']}** — {r['score']}/{r['total']} ({pct}%) · {r['created_at']}")
            st.progress(pct/100)
        st.subheader("Revision recommendations")
        low = [r for r in results if r["score"]/r["total"] < .7]
        if low:
            for r in low[:5]:
                st.warning(f"Revise **{r['topic']}** — score was {r['score']}/{r['total']}. Review the concept, solve 5 practice questions, then retake a quiz.")
        else:
            st.success("Your recorded quiz scores are all 70% or higher. Keep using spaced revision.")
        if st.button("Generate AI revision strategy"):
            summary="\n".join(f"{r['topic']}: {r['score']}/{r['total']}" for r in results[:20])
            with st.spinner("Building revision strategy..."):
                out=ai("Create a concise, actionable student revision strategy from these quiz results. Identify topics needing attention, recommend a sequence, and avoid pretending to know anything not shown by the data:\n"+summary)
            if out: st.markdown(out)

st.markdown("---")
st.caption("SPARK AI • Student Productivity And Resource Knowledge AI • Local MVP")
