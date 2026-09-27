"""Diagnostic: test Groq connectivity and find the correct Qwen model slug."""
import sys, os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'backend'))
from dotenv import load_dotenv
load_dotenv()

from groq import Groq

client = Groq(api_key=os.environ["GROQ_API_KEY"])

# 1. List all available models
print("=== Available Groq Models ===")
try:
    models = client.models.list()
    qwen_models = [m.id for m in models.data if 'qwen' in m.id.lower()]
    all_models = [m.id for m in models.data]
    print("Qwen models available:", qwen_models)
    print("Total models:", len(all_models))
except Exception as e:
    print("Could not list models:", e)

# 2. Test the current MODEL_ID
current_model = os.environ.get("GROQ_MODEL", "qwen/qwen3-8b")
print(f"\n=== Testing model: {current_model} ===")
try:
    resp = client.chat.completions.create(
        model=current_model,
        messages=[{"role": "user", "content": "Say hello in one word."}],
        max_tokens=20,
    )
    print("SUCCESS:", resp.choices[0].message.content)
except Exception as e:
    print("FAILED:", type(e).__name__, str(e))

# 3. Try known Qwen slugs
candidates = [
    "qwen/qwen3-8b",
    "qwen/qwen3-8b-fp8",
    "qwen-qwen3-8b",
    "qwen2.5-72b-instruct",
    "qwen2.5-coder-32b-instruct",
    "qwen/qwen2.5-72b-instruct",
]
print("\n=== Testing candidate model slugs ===")
for slug in candidates:
    try:
        resp = client.chat.completions.create(
            model=slug,
            messages=[{"role": "user", "content": "Hi"}],
            max_tokens=5,
        )
        print(f"  OK: {slug}")
    except Exception as e:
        short = str(e)[:80]
        print(f"  FAIL {slug}: {short}")
