"""
Smart Study Generator — Flask Backend
Groq API integration using qwen/qwen3.8-27b model
GROQ_API_KEY is loaded from environment only — never exposed to frontend
"""

import os
import json
import uuid
import logging
import re
from datetime import datetime
from pathlib import Path

from flask import Flask, request, jsonify, send_from_directory, session
from flask_cors import CORS
from dotenv import load_dotenv
from werkzeug.utils import secure_filename

# Load .env from project root (parent of the backend/ directory this file lives in).
# This works whether the server is started from smart-study-agent/ or smart-study-agent/backend/.
_ENV_PATH = Path(__file__).parent.parent / ".env"
load_dotenv(dotenv_path=_ENV_PATH, override=False)

# ── Logging setup ────────────────────────────────────────────────────────────
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    handlers=[
        logging.FileHandler("app.log"),
        logging.StreamHandler(),
    ],
)
logger = logging.getLogger(__name__)

# ── App setup ────────────────────────────────────────────────────────────────
BASE_DIR = Path(__file__).parent.parent
UPLOAD_FOLDER = BASE_DIR / "uploads"
DATA_FOLDER = BASE_DIR / "data"
FRONTEND_FOLDER = BASE_DIR / "frontend"

UPLOAD_FOLDER.mkdir(exist_ok=True)
DATA_FOLDER.mkdir(exist_ok=True)

ALLOWED_EXTENSIONS = {"pdf", "txt", "png", "jpg", "jpeg", "webp"}
MAX_CONTENT_LENGTH = int(os.environ.get("MAX_FILE_SIZE_MB", 10)) * 1024 * 1024

app = Flask(__name__, static_folder=str(FRONTEND_FOLDER), static_url_path="")
app.secret_key = os.environ.get("FLASK_SECRET_KEY", os.urandom(32))
app.config["MAX_CONTENT_LENGTH"] = MAX_CONTENT_LENGTH
app.config["UPLOAD_FOLDER"] = str(UPLOAD_FOLDER)

# Allow local frontend during development
CORS(app, supports_credentials=True, origins=["http://localhost:5000", "http://127.0.0.1:5000"])

# ── Import internal modules ───────────────────────────────────────────────────
from agent import SmartStudyAgent
from utils.safety import SafetyFilter
from utils.progress import ProgressTracker

safety_filter = SafetyFilter()
agent = SmartStudyAgent()

# ── Helpers ───────────────────────────────────────────────────────────────────

def allowed_file(filename: str) -> bool:
    return "." in filename and filename.rsplit(".", 1)[1].lower() in ALLOWED_EXTENSIONS


def get_session_id() -> str:
    if "session_id" not in session:
        session["session_id"] = str(uuid.uuid4())
    return session["session_id"]


def session_data_path(session_id: str) -> Path:
    return DATA_FOLDER / f"{session_id}.json"


def load_session_data(session_id: str) -> dict:
    path = session_data_path(session_id)
    if path.exists():
        with open(path, "r", encoding="utf-8") as f:
            return json.load(f)
    return {
        "profile": {},
        "uploaded_material": "",
        "progress": {
            "subjects": {},
            "completed_topics": [],
            "quiz_scores": [],
            "weak_topics": [],
            "study_plan": None,
            "milestones": [],
        },
        "conversation_history": [],
        "created_at": datetime.utcnow().isoformat(),
    }


def save_session_data(session_id: str, data: dict) -> None:
    path = session_data_path(session_id)
    with open(path, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2, ensure_ascii=False)


# ── Routes ─────────────────────────────────────────────────────────────────────

@app.route("/")
def index():
    return send_from_directory(str(FRONTEND_FOLDER), "index.html")


@app.route("/api/health", methods=["GET"])
def health():
    groq_key_set = bool(os.environ.get("GROQ_API_KEY"))
    groq_reachable = False
    groq_error = None

    if groq_key_set:
        # Actually probe the Groq API with a tiny request to confirm the key + model work.
        try:
            from groq import Groq as _Groq
            _model = os.environ.get("GROQ_MODEL", "qwen/qwen3.8-27b")
            _c = _Groq(api_key=os.environ["GROQ_API_KEY"])
            _r = _c.chat.completions.create(
                model=_model,
                messages=[{"role": "user", "content": "ping"}],
                max_tokens=5,
            )
            groq_reachable = bool(_r.choices[0].message.content)
        except Exception as exc:
            groq_error = type(exc).__name__
            logger.warning("Health-check Groq probe failed: %s", exc)

    return jsonify({
        "status": "ok",
        "groq_configured": groq_key_set,
        "groq_connected": groq_reachable,
        "groq_error": groq_error,
        "model": os.environ.get("GROQ_MODEL", "qwen/qwen3.8-27b"),
        "upload_folder": str(UPLOAD_FOLDER),
        "timestamp": datetime.utcnow().isoformat(),
    })


@app.route("/api/session", methods=["GET"])
def get_session():
    sid = get_session_id()
    data = load_session_data(sid)
    # Return safe subset — no raw material, no conversation internals
    return jsonify({
        "session_id": sid,
        "profile": data.get("profile", {}),
        "progress": data.get("progress", {}),
        "has_material": bool(data.get("uploaded_material", "").strip()),
    })


@app.route("/api/profile", methods=["POST"])
def save_profile():
    sid = get_session_id()
    data = load_session_data(sid)

    body = request.get_json(silent=True) or {}
    profile = {
        "name": str(body.get("name", ""))[:100].strip(),
        "education_level": str(body.get("education_level", ""))[:100].strip(),
        "course": str(body.get("course", ""))[:200].strip(),
        "semester": str(body.get("semester", ""))[:50].strip(),
        "subjects": [str(s)[:100].strip() for s in body.get("subjects", [])[:10]],
        "exam_date": str(body.get("exam_date", ""))[:20].strip(),
        "learning_style": str(body.get("learning_style", ""))[:50].strip(),
        "study_hours_per_day": str(body.get("study_hours_per_day", "2"))[:10].strip(),
        "preparation_level": str(body.get("preparation_level", "beginner"))[:30].strip(),
    }

    data["profile"] = profile

    # Reset progress subjects when profile changes
    for subj in profile.get("subjects", []):
        if subj not in data["progress"]["subjects"]:
            data["progress"]["subjects"][subj] = {
                "topics_completed": 0,
                "topics_total": 0,
                "quiz_scores": [],
                "status": "not_started",
            }

    save_session_data(sid, data)
    logger.info("Profile saved for session %s", sid[:8])
    return jsonify({"success": True, "profile": profile})


@app.route("/api/upload", methods=["POST"])
def upload_file():
    sid = get_session_id()

    if "file" not in request.files:
        return jsonify({"error": "No file provided"}), 400

    file = request.files["file"]
    if not file.filename:
        return jsonify({"error": "Empty filename"}), 400

    if not allowed_file(file.filename):
        return jsonify({"error": f"File type not allowed. Supported: {', '.join(ALLOWED_EXTENSIONS)}"}), 400

    safe_name = secure_filename(file.filename)
    unique_name = f"{uuid.uuid4().hex}_{safe_name}"
    file_path = UPLOAD_FOLDER / unique_name
    file.save(str(file_path))

    logger.info("File uploaded: %s (session %s)", safe_name, sid[:8])

    # Extract text from file
    from utils.file_processor import extract_text
    try:
        extracted_text = extract_text(str(file_path), safe_name)
    except Exception as exc:
        logger.error("File processing error: %s", exc)
        extracted_text = ""

    # Remove file after extraction
    try:
        os.remove(str(file_path))
    except Exception:
        pass

    if not extracted_text.strip():
        return jsonify({"error": "Could not extract readable text from the file. Please try a different format or ensure the file has readable content."}), 422

    # Sanitise extracted text against injection
    clean_text = safety_filter.sanitise_document_content(extracted_text)

    # Append to session material
    data = load_session_data(sid)
    current_material = data.get("uploaded_material", "")
    separator = f"\n\n--- Uploaded: {safe_name} ---\n\n"
    # Cap total material at ~12000 chars
    combined = (current_material + separator + clean_text)[-12000:]
    data["uploaded_material"] = combined
    save_session_data(sid, data)

    return jsonify({
        "success": True,
        "filename": safe_name,
        "chars_extracted": len(clean_text),
        "message": f"Successfully extracted {len(clean_text):,} characters from {safe_name}",
    })


@app.route("/api/chat", methods=["POST"])
def chat():
    sid = get_session_id()
    body = request.get_json(silent=True) or {}

    query = str(body.get("query", "")).strip()
    if not query:
        return jsonify({"error": "Query cannot be empty"}), 400
    if len(query) > 2000:
        return jsonify({"error": "Query too long (max 2000 characters)"}), 400

    # Safety check on raw query
    injection_result = safety_filter.check_injection(query)
    if injection_result["blocked"]:
        logger.warning("Injection attempt blocked (session %s): %s", sid[:8], injection_result["reason"])
        return jsonify({
            "response": (
                "⚠️ I can't process that request. It appears to contain instructions that conflict "
                "with my role as a study assistant. I'm here to help with your studies — feel free to "
                "ask me to generate study plans, explain concepts, create flashcards, or help with revision!"
            ),
            "type": "safety_block",
        })

    data = load_session_data(sid)

    # Append user message to history
    history = data.get("conversation_history", [])
    history.append({"role": "user", "content": query})
    # Keep last 10 turns
    history = history[-20:]

    try:
        result = agent.process(
            query=query,
            profile=data.get("profile", {}),
            material=data.get("uploaded_material", ""),
            progress=data.get("progress", {}),
            history=history[:-1],  # history without the current message
        )
    except Exception as exc:
        # Log full error server-side (check app.log for details); never expose key/secrets to client
        logger.error("Agent error (type=%s): %s", type(exc).__name__, exc, exc_info=True)
        user_msg = "An error occurred while generating a response. Please try again."
        # Give slightly more useful message for common configuration errors
        err_lower = str(exc).lower()
        if "api_key" in err_lower or "authentication" in err_lower or "401" in err_lower:
            user_msg = "API authentication failed. Please check your GROQ_API_KEY in the .env file."
        elif "model_not_found" in err_lower or "404" in err_lower or "does not exist" in err_lower:
            user_msg = "The configured AI model was not found. Please check GROQ_MODEL in the .env file."
        elif "rate_limit" in err_lower or "429" in err_lower:
            user_msg = "Rate limit reached. Please wait a moment and try again."
        elif "not configured" in err_lower:
            user_msg = str(exc)  # safe RuntimeError from our own code
        return jsonify({"error": user_msg}), 500

    response_text = result.get("response", "")
    response_type = result.get("type", "general")

    # Post-process: ensure no sensitive data leaked into response
    response_text = safety_filter.check_response_for_leaks(response_text)

    # Append assistant response to history
    history.append({"role": "assistant", "content": response_text})
    data["conversation_history"] = history[-20:]
    save_session_data(sid, data)

    return jsonify({
        "response": response_text,
        "type": response_type,
        "disclaimer": result.get("disclaimer"),
    })


@app.route("/api/generate-plan", methods=["POST"])
def generate_plan():
    sid = get_session_id()
    data = load_session_data(sid)
    profile = data.get("profile", {})

    if not profile.get("subjects"):
        return jsonify({"error": "Please complete your student profile with subjects before generating a study plan."}), 400

    body = request.get_json(silent=True) or {}
    override_hours = body.get("study_hours")
    override_exam_date = body.get("exam_date")

    if override_hours:
        profile["study_hours_per_day"] = str(override_hours)
    if override_exam_date:
        profile["exam_date"] = str(override_exam_date)

    try:
        result = agent.generate_study_plan(
            profile=profile,
            material=data.get("uploaded_material", ""),
            progress=data.get("progress", {}),
        )
    except Exception as exc:
        logger.error("Study plan error (type=%s): %s", type(exc).__name__, exc, exc_info=True)
        return jsonify({"error": "Could not generate study plan. Please check the server logs and try again."}), 500

    # Save generated plan to progress
    data["progress"]["study_plan"] = {
        "generated_at": datetime.utcnow().isoformat(),
        "plan_text": result["response"],
    }
    save_session_data(sid, data)

    return jsonify({
        "response": result["response"],
        "type": "study_plan",
        "disclaimer": "📌 This study plan is an AI-generated recommendation based on the information you provided. It is not official academic guidance.",
    })


@app.route("/api/progress", methods=["GET"])
def get_progress():
    sid = get_session_id()
    data = load_session_data(sid)
    progress = data.get("progress", {})
    profile = data.get("profile", {})

    tracker = ProgressTracker(progress, profile)
    dashboard = tracker.get_dashboard()

    return jsonify(dashboard)


@app.route("/api/progress/update", methods=["POST"])
def update_progress():
    sid = get_session_id()
    data = load_session_data(sid)
    body = request.get_json(silent=True) or {}

    action = body.get("action")
    tracker = ProgressTracker(data["progress"], data.get("profile", {}))

    if action == "complete_topic":
        subject = str(body.get("subject", ""))[:100]
        topic = str(body.get("topic", ""))[:200]
        tracker.mark_topic_complete(subject, topic)

    elif action == "record_quiz":
        subject = str(body.get("subject", ""))[:100]
        topic = str(body.get("topic", ""))[:200]
        score = int(body.get("score", 0))
        total = int(body.get("total", 10))
        tracker.record_quiz_score(subject, topic, score, total)

    elif action == "add_milestone":
        milestone = str(body.get("milestone", ""))[:200]
        tracker.add_milestone(milestone)

    data["progress"] = tracker.progress
    save_session_data(sid, data)

    return jsonify({"success": True, "progress": tracker.get_dashboard()})


@app.route("/api/clear-material", methods=["POST"])
def clear_material():
    sid = get_session_id()
    data = load_session_data(sid)
    data["uploaded_material"] = ""
    save_session_data(sid, data)
    return jsonify({"success": True, "message": "Uploaded material cleared."})


@app.route("/api/reset-session", methods=["POST"])
def reset_session():
    sid = get_session_id()
    path = session_data_path(sid)
    if path.exists():
        os.remove(str(path))
    session.clear()
    return jsonify({"success": True, "message": "Session reset."})


# ── Error handlers ─────────────────────────────────────────────────────────────

@app.errorhandler(413)
def too_large(e):
    return jsonify({"error": f"File too large. Maximum size is {MAX_CONTENT_LENGTH // 1024 // 1024}MB."}), 413


@app.errorhandler(404)
def not_found(e):
    return jsonify({"error": "Endpoint not found"}), 404


@app.errorhandler(500)
def server_error(e):
    logger.error("Server error: %s", e)
    return jsonify({"error": "Internal server error"}), 500


if __name__ == "__main__":
    if not os.environ.get("GROQ_API_KEY"):
        logger.error("GROQ_API_KEY environment variable is not set! Please configure .env file.")
    debug_mode = os.environ.get("FLASK_ENV", "development") == "development"
    app.run(host="127.0.0.1", port=5000, debug=debug_mode)
