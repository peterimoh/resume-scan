"""DeepSeek LLM integration for HR and ATS resume analysis.

Configuration is read from a ``.env`` file in the project directory (with
environment variables as fallback):

    DEEPSEEK_API_KEY=sk-...
    DEEPSEEK_BASE_URL=https://api.deepseek.com
    DEEPSEEK_MODEL=deepseek-chat
"""

from __future__ import annotations

import json
import os
import time
from pathlib import Path

import requests

BASE_DIR = Path(__file__).resolve().parent
ENV_PATH = BASE_DIR / ".env"


def _load_env(path: Path) -> dict:
    """Parse a minimal .env file (KEY=VALUE lines, # comments)."""
    if not path.exists():
        return {}
    env: dict = {}
    for raw in path.read_text(encoding="utf-8").splitlines():
        line = raw.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, _, value = line.partition("=")
        key = key.strip()
        value = value.strip()
        if len(value) >= 2 and value[0] == value[-1] and value[0] in "\"'":
            value = value[1:-1]
        env[key] = value
    return env


_env = _load_env(ENV_PATH)


def _cfg(name: str, default: str) -> str:
    return _env.get(name, os.environ.get(name, default))


API_KEY = _cfg("DEEPSEEK_API_KEY", "")
BASE_URL = _cfg("DEEPSEEK_BASE_URL", "https://api.deepseek.com").rstrip("/")
MODEL = _cfg("DEEPSEEK_MODEL", "deepseek-chat")


def _chat_stream(messages: list[dict], temperature: float = 0.2):
    """Yield completion deltas from the DeepSeek chat API (server-sent events).

    Retries transient failures (429/5xx/connection errors) a few times, then
    raises if it still cannot get a response.
    """
    if not API_KEY:
        raise RuntimeError(
            "DEEPSEEK_API_KEY is not set. Add it to the .env file in this directory."
        )

    headers = {
        "Authorization": f"Bearer {API_KEY}",
        "Content-Type": "application/json",
    }
    payload = {
        "model": MODEL,
        "messages": messages,
        "temperature": temperature,
        "max_tokens": 8192,
        "stream": True,
    }

    last_error: Exception | None = None
    for attempt in range(3):
        try:
            resp = requests.post(
                f"{BASE_URL}/chat/completions",
                headers=headers,
                json=payload,
                stream=True,
                timeout=(30, 120),
            )
        except requests.exceptions.RequestException as exc:
            last_error = exc
            time.sleep(2 ** attempt)
            continue

        if resp.status_code in (429, 500, 502, 503, 504):
            last_error = RuntimeError(f"DeepSeek API returned {resp.status_code}.")
            resp.close()
            time.sleep(2 ** attempt)
            continue

        if resp.status_code != 200:
            body = resp.text[:500]
            resp.close()
            raise RuntimeError(f"DeepSeek API returned {resp.status_code}: {body}")

        truncated = False
        try:
            for raw in resp.iter_lines():
                if not raw:
                    continue
                line = raw.decode("utf-8", errors="replace").strip()
                if not line.startswith("data:"):
                    continue
                data = line[5:].strip()
                if data == "[DONE]":
                    break
                try:
                    chunk = json.loads(data)
                except json.JSONDecodeError:
                    continue
                choices = chunk.get("choices") or []
                if not choices:
                    continue
                choice = choices[0]
                content = (choice.get("delta") or {}).get("content")
                if content:
                    yield content
                if choice.get("finish_reason") == "length":
                    truncated = True
        except requests.exceptions.RequestException as exc:
            last_error = exc
            yield "\n\n> The response stream was interrupted before completion."
        finally:
            resp.close()

        if truncated:
            yield "\n\n> Note: the response was truncated (output limit reached)."
        return

    raise RuntimeError(f"DeepSeek request failed after retries: {last_error}")


_HR_SYSTEM = (
    "You are a senior HR manager and technical recruiter with 15+ years of "
    "experience screening and hiring for technical roles. You review resumes "
    "with the rigor and skepticism of a real hiring manager. You are direct, "
    "specific, and evidence-based. You never flatter; you point out strengths "
    "and weaknesses with concrete references to the resume and the target role."
)

_HR_USER = """You are screening a candidate for the following role.

--- JOB DESCRIPTION ---
{job}
--- END JOB DESCRIPTION ---

Here is the candidate's resume (plain text, as extracted by an ATS).

--- RESUME ---
{resume}
--- END RESUME ---

Perform a full HR review and respond in clean Markdown with these sections:

1. **Overall Fit Verdict** — one of: Strong fit / Moderate fit / Weak fit / Not a fit, with a one-sentence justification.
2. **What Stands Out** — the 3-5 strongest, most differentiating aspects of this candidate for this role.
3. **Flaws & Weaknesses** — specific gaps, inconsistencies, vague or unquantified claims, red flags, or anything that weakens the candidacy.
4. **Achievements Tied to the Role** — notable achievements in the resume that directly map to the role's requirements; explicitly connect each achievement to a requirement.
5. **What the Role Wants That's Missing** — requirements from the job description not evidenced in the resume.
6. **HR Scrutiny Notes** — anything else a careful HR would flag (tenure gaps, job-hopping, progression anomalies, formatting, missing basics).
7. **Recommended Next Steps** — the most impactful changes the candidate should make.

Be specific and quote from the resume or job description where useful. If the job description is vague, state your assumptions.
"""

_ATS_SYSTEM = (
    "You are an expert in Applicant Tracking Systems (ATS) and technical "
    "recruiting. You know exactly how ATS software parses, keyword-matches, and "
    "ranks resumes. You evaluate resumes for both keyword relevance and "
    "parseability."
)

_ATS_USER = """Compare the resume against the target role and assess ATS performance.

--- JOB DESCRIPTION ---
{job}
--- END JOB DESCRIPTION ---

--- RESUME ---
{resume}
--- END RESUME ---

Respond in clean Markdown with these sections:

1. **Estimated Match Score** — a percentage and one-sentence summary of how relevant this resume is to the role.
2. **Matched Keywords & Skills** — skills and terms from the job description that appear in the resume (group them logically).
3. **Missing Keywords & Skills** — important terms from the job description that are absent from the resume, ranked by how much they would hurt ATS ranking.
4. **Parseability Assessment** — how well an ATS parses this resume: sections detected, ordering, and any content an ATS might fail to read or mis-categorize (e.g. multi-column layouts, tables, graphics, headers/footers, non-standard headings, contact info placement).
5. **Missing Standard Sections** — expected sections (summary, skills, experience, education, etc.) that are absent.
6. **Actionable Fixes** — concrete, prioritized changes to improve ATS ranking and parseability.
"""


def analyze_hr(resume_text: str, job_description: str):
    """Yield an HR review of the resume against the role (markdown stream)."""
    messages = [
        {"role": "system", "content": _HR_SYSTEM},
        {
            "role": "user",
            "content": _HR_USER.format(job=job_description, resume=resume_text),
        },
    ]
    yield from _chat_stream(messages)


def analyze_ats(resume_text: str, job_description: str):
    """Yield an ATS keyword + parseability assessment (markdown stream)."""
    messages = [
        {"role": "system", "content": _ATS_SYSTEM},
        {
            "role": "user",
            "content": _ATS_USER.format(job=job_description, resume=resume_text),
        },
    ]
    yield from _chat_stream(messages)
