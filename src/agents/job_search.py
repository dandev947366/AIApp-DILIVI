# src/agents/job_search.py
"""Job Search Agent: Fetches live remote jobs via Jobicy and ranks them
against the student's saved skills and interests."""

import os
import re
import traceback

from langchain_core.messages import AIMessage, HumanMessage, SystemMessage
from langchain_ollama import ChatOllama

from src.config import MODEL_ID, OLLAMA_TIMEOUT
from src.agents.state import AgentState
from src.mcp.jobicy import (
    search_jobs_mcp,
    search_jobs_for_student,
    _is_meaningful_skill,
)

# Bulletproof Docker network fix
# NOTE: this deletes env vars at import time. Keep it only if `src/config`
# does not already expose OLLAMA_BASE_URL; otherwise remove and rely on it.
if "OLLAMA_HOST" in os.environ:
    del os.environ["OLLAMA_HOST"]
if "OLLAMA_BASE_URL" in os.environ:
    del os.environ["OLLAMA_BASE_URL"]

OLLAMA_HOST_DOCKER = "http://ollama:11434"

llm = ChatOllama(
    model=MODEL_ID,
    base_url=OLLAMA_HOST_DOCKER,
    timeout=OLLAMA_TIMEOUT,
    temperature=0.1,
)

SYSTEM_PROMPT = """You are an expert Technical Recruiter.

You are given a student's query and a list of LIVE remote jobs from Jobicy,
already ranked against the student's skills and interests.

Format the jobs into a clean markdown list. For each job include:
- the Job Title and Company as the heading,
- the salary when present,
- the URL as a markdown link,
- the "Matched" line **exactly as it appears in the input** — never invent
  match reasons and never claim a skill fits a job unless the input says so.

If the input message starts with "I couldn't find" or "I don't have any",
repeat that message verbatim. Do not list any jobs.

Do not add any conclusion, summary, encouragement, or commentary after the
list. Do not speculate about market trends. Stop after the last job."""


# ------------------------------------------------------------------
# Helpers
# ------------------------------------------------------------------

_STOPWORDS = {
    "find",
    "me",
    "jobs",
    "job",
    "that",
    "match",
    "matches",
    "my",
    "skills",
    "interests",
    "a",
    "an",
    "the",
    "in",
    "at",
    "for",
    "with",
    "and",
    "or",
    "please",
    "show",
    "search",
    "remote",
    "location",
    "of",
    "on",
    "to",
    "looking",
    "want",
    "would",
    "like",
    "any",
    "some",
    "good",
    "best",
    "give",
    "list",
    "tell",
    "about",
    "new",
    "now",
    "currently",
    "postings",
    "posting",
    "vacancies",
    "vacancy",
    "role",
    "roles",
}

_LOCATION_ALIASES = {
    "finland": "finland",
    "france": "france",
    "germany": "germany",
    "spain": "spain",
    "italy": "italy",
    "netherlands": "netherlands",
    "portugal": "portugal",
    "belgium": "belgium",
    "switzerland": "switzerland",
    "sweden": "sweden",
    "norway": "norway",
    "denmark": "denmark",
    "uk": "uk",
    "united kingdom": "uk",
    "europe": "europe",
    "usa": "usa",
    "united states": "usa",
    "canada": "canada",
    "australia": "australia",
    "remote": "",
    "anywhere": "",
}


def _extract_location(question: str) -> str:
    """Return a Jobicy geo slug (or "" to skip the geo filter)."""
    q = (question or "").lower()
    for word, slug in _LOCATION_ALIASES.items():
        if word in q:
            return slug
    return ""


def _extract_keyword(question: str, exclude: set[str] | None = None) -> str:
    """Pick the most specific technical term from the user's question."""
    exclude = {e.lower() for e in (exclude or set()) if e}
    tokens = re.findall(r"[A-Za-z][A-Za-z0-9+#.]{1,}", question or "")

    candidates = [
        t for t in tokens if t.lower() not in _STOPWORDS and t.lower() not in exclude
    ]
    if not candidates:
        return ""

    # The longest candidate is usually the most specific tech term.
    return max(candidates, key=len)


def _fallback_markdown(jobs_text: str, user_question: str) -> str:
    """Deterministic markdown if the LLM formatting step fails."""
    if jobs_text and jobs_text.strip():
        return jobs_text
    return (
        f"I couldn't find live jobs matching **{user_question}** right now. "
        "Try a broader keyword (e.g. `developer`, `data`, `cloud`) or "
        "remove the location filter."
    )


# ------------------------------------------------------------------
# Node
# ------------------------------------------------------------------


def job_search_node(state: AgentState) -> dict:
    messages = state.get("messages", [])

    # Last human message
    user_messages = [m for m in messages if getattr(m, "type", None) == "human"]
    user_question = (
        user_messages[-1].content
        if user_messages
        else (messages[-1].content if messages else "remote software engineer")
    )

    student_id = state.get("student_id")
    context = state.get("student_context", {}) or {}
    skills = context.get("skills", []) or []

    geo = _extract_location(user_question)
    extra_query = _extract_keyword(user_question, exclude={geo} if geo else set())

    # Short queries like "find me jobs" → fall back to the student's top
    # meaningful skill, if any.
    if not extra_query and len(user_question.split()) < 4 and skills:
        try:
            meaningful = [
                s for s in skills if _is_meaningful_skill(s.get("skill_name", ""))
            ]
            if meaningful:
                top = sorted(
                    meaningful,
                    key=lambda s: s.get("proficiency") or 0,
                    reverse=True,
                )[0]
                extra_query = (top.get("skill_name") or "").strip()
                print(f"🔌 [JOB SEARCH] Fallback to top skill: {extra_query!r}")
        except Exception:
            extra_query = ""

    print(
        f"🔌 [JOB SEARCH] student_id={student_id} "
        f"geo={geo!r} extra_query={extra_query!r}"
    )

    # Fetch + rank
    jobs_text = ""
    try:
        if student_id:
            jobs_text = search_jobs_for_student(
                student_id,
                extra_query=extra_query,
                geo=geo,
                limit=5,
            )
        else:
            jobs_text = search_jobs_mcp(
                query=extra_query,
                geo=geo,
                limit=5,
            )
    except Exception as exc:
        traceback.print_exc()
        jobs_text = f"Job search failed: `{type(exc).__name__}: {exc}`"

    if not jobs_text or not jobs_text.strip():
        jobs_text = _fallback_markdown("", user_question)

    # If the search already produced an explanatory message (no matches,
    # no profile, error), skip the LLM entirely — running it on an empty
    # list only leads to hallucinated "Matched" lines.
    no_match_signals = (
        "couldn't find",
        "No jobs returned",
        "I don't have any",
        "Job search failed",
    )
    if any(sig in jobs_text for sig in no_match_signals):
        formatted = jobs_text
    else:
        user_prompt = f"""User's Request: "{user_question}"

🌍 LIVE JOB MARKET DATA (already ranked against the student's profile):
{jobs_text}

Rewrite the data as a short, friendly markdown list for the student.
Preserve every job title, company, salary, URL and "Matched" line verbatim.
Do not invent jobs or match reasons. Do not add a preamble."""

        formatted = ""
        try:
            response = llm.invoke(
                [
                    SystemMessage(content=SYSTEM_PROMPT),
                    HumanMessage(content=user_prompt),
                ]
            )
            formatted = (response.content or "").strip()
        except Exception as exc:
            traceback.print_exc()
            print(
                f"[JOB SEARCH] LLM formatting failed: " f"{type(exc).__name__}: {exc}"
            )

    if not formatted:
        formatted = _fallback_markdown(jobs_text, user_question)

    # Always populate final_response so the UI never shows a blank bubble.
    return {
        "job_search_result": formatted,
        "final_response": formatted,
        "messages": [AIMessage(content=f"[Job Search]\n{formatted}")],
    }
