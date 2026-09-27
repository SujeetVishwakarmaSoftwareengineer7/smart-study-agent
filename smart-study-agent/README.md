# Smart Study Generator — Agentic AI Application

> An intelligent, personalised AI study assistant powered by **Qwen (qwen/qwen3-8b)** via the **Groq API**.

---

## Features

- 🤖 **AI Study Agent** — Natural language Q&A for all study topics
- 📅 **Personalised Study Plans** — Adaptive daily/weekly schedules
- 📝 **Material Summarisation** — Key points from PDFs, notes, and images
- 🃏 **Flashcard Generation** — Interactive flip cards from study material
- ❓ **Quiz Generation** — Practice questions with answers
- 💡 **Concept Explanations** — Simple, level-appropriate explanations
- 🎯 **Important Topic Identification** — Syllabus and material analysis
- 📊 **Progress Dashboard** — Subject-wise tracking, quiz scores, weak areas
- ⚠️ **Weak Topic Detection** — AI-powered revision recommendations
- 📁 **Multimodal Input** — Upload PDFs, text notes, and images (with OCR)
- 🔒 **Secure by Design** — API key never exposed to frontend

---

## Quick Start (Windows)

**Just double-click `setup_and_run.bat`** — it handles everything automatically:
1. Checks for Python
2. Creates a virtual environment
3. Installs dependencies
4. Guides you through API key setup
5. Launches the application
6. Opens your browser automatically

---

## Step-by-Step Setup

### Step 1 — Install Python

Download and install **Python 3.9 or higher** from [python.org](https://www.python.org/downloads/).

> ⚠️ **Important:** During installation, check **"Add Python to PATH"**.

Verify installation:
```
python --version
```

---

### Step 2 — Get a Groq API Key

1. Go to [https://console.groq.com/keys](https://console.groq.com/keys)
2. Sign up or log in
3. Create a new API key
4. Copy the key — you'll need it in Step 4

---

### Step 3 — Set Up the Project

```bash
cd smart-study-agent
```

Create a virtual environment:
```bash
python -m venv venv
```

Activate it (Windows):
```bash
venv\Scripts\activate
```

---

### Step 4 — Configure the Environment File

Copy the example file:
```bash
copy .env.example .env
```

Open `.env` in a text editor and set your API key:
```
GROQ_API_KEY=gsk_your_actual_key_here
FLASK_SECRET_KEY=any-random-string-here
```

> 🔒 **Security:** The `.env` file contains your API key. Never commit it to version control. It is listed in `.gitignore` by default.

---

### Step 5 — Install Dependencies

```bash
pip install -r requirements.txt
```

---

### Step 6 — (Optional) Install Tesseract OCR for Image Support

To enable text extraction from uploaded images and handwritten notes:

1. Download Tesseract from: [https://github.com/UB-Mannheim/tesseract/wiki](https://github.com/UB-Mannheim/tesseract/wiki)
2. Run the installer
3. Add Tesseract to your system PATH

> Without Tesseract, PDF and TXT uploads will still work normally.

---

### Step 7 — Start the Backend

```bash
cd backend
python app.py
```

You should see:
```
* Running on http://127.0.0.1:5000
```

---

### Step 8 — Open the Application

Open your browser and go to:
```
http://localhost:5000
```

---

### Step 9 — Using the Application

1. **Complete your Student Profile** — name, course, subjects, exam date, study hours
2. **Upload Study Material** (optional) — PDFs, notes, images
3. **Ask the AI Agent** — any study question
4. **Generate a Study Plan** — personalised to your schedule
5. **Use Study Tools** — summarise, flashcards, quiz, explain
6. **Track Progress** — mark topics complete, record quiz scores
7. **Check Weak Topics** — get AI recommendations for revision

---

## Testing

### Test the AI Agent
Navigate to **Ask AI Agent** and try:
- "Explain dynamic programming in simple language"
- "Create a 7-day revision plan for my exams"
- "Give me 10 practice questions on data structures"

### Test File Upload
1. Go to **Upload Material**
2. Upload a PDF or TXT file
3. Ask the agent: "Summarise my uploaded notes"

### Test Quiz & Flashcards
1. Upload study material or specify a topic
2. Go to **Flashcards** → Generate Flashcards
3. Go to **Quiz Generator** → Generate Quiz
4. Record your quiz score in the **Progress Dashboard**

### Test Progress Tracking
1. In the **Progress Dashboard**, mark a topic as complete
2. Record a quiz score (try a low score to see weak topic detection)
3. Go to **Weak Topics** for AI revision recommendations

### Test Study Plan Generation
1. Ensure your profile has subjects and an exam date
2. Go to **Generate Study Plan**
3. Click "Generate Personalised Study Plan"

---

## Security Features

| Feature | Implementation |
|---------|---------------|
| API key security | Stored in `.env` only; never sent to browser |
| Prompt injection protection | 30+ pattern detection rules in `safety.py` |
| File upload security | Extension validation, UUID filenames, size limits |
| Content sanitisation | Uploaded content treated as reference data only |
| Response filtering | API key pattern detection in all responses |
| CORS restriction | Only localhost origins in development |

---

## Project Structure

```
smart-study-agent/
├── backend/
│   ├── app.py              # Flask API server
│   ├── agent.py            # AI agent logic (Groq integration)
│   └── utils/
│       ├── file_processor.py   # PDF/image/text extraction
│       ├── safety.py           # Injection protection & guardrails
│       └── progress.py         # Progress tracking
├── frontend/
│   └── index.html          # Complete single-page application
├── uploads/                # Temporary file storage (gitignored)
├── data/                   # Session progress data (gitignored)
├── .env.example            # Environment variable template
├── requirements.txt        # Python dependencies
├── setup_and_run.bat       # Windows one-click launcher
├── smart_study_agent_plan.md   # Complete SDLC documentation
└── README.md               # This file
```

---

## AI Ethics & Disclaimers

- All AI-generated content is clearly labelled as AI recommendations
- Topic frequency analysis is **never** presented as guaranteed exam predictions
- The application supports **learning and revision**, not cheating or academic dishonesty
- When information is unavailable, the AI states its limitations rather than fabricating answers
- Uploaded study material is used only as reference context, not for model training

---

## Deployment (Production)

For a production deployment:

```bash
pip install gunicorn
cd backend
gunicorn -w 4 -b 0.0.0.0:5000 app:app
```

Then configure nginx as a reverse proxy with SSL (recommended for any internet-facing deployment).

Set `FLASK_ENV=production` and use proper environment variables (not the `.env` file) in production.

---

## Troubleshooting

| Problem | Solution |
|---------|----------|
| "GROQ_API_KEY not set" | Check your `.env` file exists and has the correct key |
| "Server offline" in browser | Ensure `python backend/app.py` is running |
| PDF extraction fails | Ensure PyPDF2 is installed: `pip install PyPDF2` |
| Image OCR unavailable | Install Tesseract OCR (optional) |
| Port 5000 already in use | Change port: `python app.py --port 5001` or stop the other process |
| "File too large" | Default limit is 10MB — change `MAX_FILE_SIZE_MB` in `.env` |

---

## Model Information

- **Model:** `qwen/qwen3-8b`
- **Provider:** Groq API
- **API Documentation:** [https://console.groq.com/docs](https://console.groq.com/docs)

---

*Smart Study Generator — Agentic AI Application*  
*Built following the complete Agentic AI SDLC — see `smart_study_agent_plan.md`*
