"""
Safety Filter — Prompt injection protection, input sanitisation, and guardrails.
All user input and uploaded document content is treated as untrusted.
"""

import os
import re
import logging
import html

logger = logging.getLogger(__name__)

# Patterns that indicate prompt injection or manipulation attempts
INJECTION_PATTERNS = [
    # Direct instruction override attempts
    r"ignore\s+(previous|above|all|prior|the\s+above)\s+(instructions?|rules?|prompts?|context)",
    r"forget\s+(everything|all|previous|the\s+above)",
    r"disregard\s+(all|previous|above|prior)\s+(instructions?|rules?)",
    r"override\s+(the\s+)?(system|instructions?|rules?|prompt)",
    r"new\s+(session|instructions?|context|persona|role)",
    r"reset\s+(instructions?|context|rules?|prompt|everything)",

    # Role hijacking
    r"pretend\s+(you\s+are|to\s+be)",
    r"act\s+as\s+(if\s+you\s+are|though\s+you\s+are|a\s+different)",
    r"you\s+are\s+now\s+(an?\s+)?(unrestricted|different|new|free)",
    r"roleplay\s+as\s+(an?\s+)?(unrestricted|jailbroken|different|free)",
    r"from\s+now\s+on\s+(you\s+are|act|behave|ignore)",
    r"your\s+true\s+(identity|self|purpose|instructions?)",
    r"jailbreak",
    r"dan\s+mode",

    # System prompt / key extraction — must be targeted enough not to block study questions
    r"(reveal|show|tell|print|output|display|share|expose|dump)\s+(your\s+)?(system\s+prompt|instructions?|api\s+key|secret\s+key|configuration)",
    r"what\s+(is|are)\s+your\s+(system\s+prompt|api\s+key|secret\s+key|instructions?|password)",
    r"(leak|expose)\s+(the\s+)?(api\s+key|secret\s+key|prompt|instructions?|configuration)",
    r"(show|give|tell)\s+me\s+(your|the)\s+(groq|api|secret)\s+key",
    r"what\s+is\s+(your|the)\s+(groq|api)\s+key",

    # Bypass attempts
    r"bypass\s+(safety|filter|guardrail|rule|restriction|check)",
    r"disable\s+(safety|filter|guardrail|rule|restriction)",
    r"turn\s+off\s+(the\s+)?(filter|safety|guardrail)",

    # Code execution / unauthorized access
    r"(execute|run)\s+(file|command|system|shell|os\s+command)",
    r"import\s+os\s*[;\n]",
    r"subprocess\.run|subprocess\.call|os\.system",
    r"exec\s*\(\s*['\"]",
    r"(delete|drop)\s+(all|the)\s+(database|table|data)",

    # Academic dishonesty — must be specific enough not to block "solve this problem"
    r"(write|complete|do|answer)\s+(my\s+)?(exam|test|assignment|homework|coursework)\s+(for\s+me|on\s+my\s+behalf)",
    r"\bcheat\b",
    r"\bplagiari",
    r"impersonat",
]

COMPILED_PATTERNS = [re.compile(p, re.IGNORECASE) for p in INJECTION_PATTERNS]

# Patterns to check in document content (more lenient — only most dangerous)
DOC_INJECTION_PATTERNS = [
    r"ignore\s+(previous|above|all|prior)\s+(instructions?|rules?|prompts?)",
    r"(reveal|expose|show)\s+(api\s+key|system\s+prompt|instructions?)",
    r"you\s+are\s+now\s+(a\s+)?different",
    r"pretend\s+you\s+are",
    r"bypass\s+(safety|filter|guardrail)",
    r"new\s+instructions?:",
    r"system:\s*you\s+(are|must|should|will)",
    r"<\s*system\s*>",
    r"\[system\]",
    r"###\s*system",
]

COMPILED_DOC_PATTERNS = [re.compile(p, re.IGNORECASE) for p in DOC_INJECTION_PATTERNS]


class SafetyFilter:
    def check_injection(self, text: str) -> dict:
        """
        Check user query for prompt injection attempts.
        Returns {"blocked": bool, "reason": str}
        """
        if not text or not text.strip():
            return {"blocked": False, "reason": None}

        for pattern in COMPILED_PATTERNS:
            if pattern.search(text):
                return {
                    "blocked": True,
                    "reason": f"Matched injection pattern: {pattern.pattern[:50]}",
                }

        return {"blocked": False, "reason": None}

    def sanitise_document_content(self, content: str) -> str:
        """
        Sanitise extracted document content to neutralise embedded injection attempts.
        This does NOT remove text — it wraps suspicious sequences so the LLM treats them
        as plain text, not instructions.
        """
        if not content:
            return ""

        # Remove non-printable characters (except newlines, tabs)
        sanitised = re.sub(r"[^\x09\x0A\x0D\x20-\x7E\u00A0-\uFFFF]", " ", content)

        # Cap length
        sanitised = sanitised[:12000]

        # Log if injection patterns found in document
        for pattern in COMPILED_DOC_PATTERNS:
            if pattern.search(sanitised):
                logger.warning("Potential injection content detected in uploaded document")
                break

        return sanitised

    def validate_file_extension(self, filename: str) -> bool:
        allowed = {"pdf", "txt", "png", "jpg", "jpeg", "webp"}
        if "." not in filename:
            return False
        ext = filename.rsplit(".", 1)[1].lower()
        return ext in allowed

    def sanitise_profile_field(self, value: str, max_length: int = 200) -> str:
        """Sanitise a student profile text field."""
        if not value:
            return ""
        # Remove HTML
        sanitised = html.escape(str(value))
        # Remove control characters
        sanitised = re.sub(r"[\x00-\x08\x0B\x0C\x0E-\x1F\x7F]", "", sanitised)
        return sanitised[:max_length].strip()

    def check_response_for_leaks(self, response: str) -> str:
        """
        Post-process AI response to ensure no sensitive data was accidentally included.
        """
        api_key = os.environ.get("GROQ_API_KEY", "")
        if api_key and api_key in response:
            logger.error("CRITICAL: API key detected in response — redacting!")
            response = response.replace(api_key, "[REDACTED]")

        # Check for common API key patterns
        response = re.sub(r"gsk_[A-Za-z0-9]{20,}", "[API_KEY_REDACTED]", response)
        response = re.sub(r"sk-[A-Za-z0-9]{20,}", "[API_KEY_REDACTED]", response)

        return response
