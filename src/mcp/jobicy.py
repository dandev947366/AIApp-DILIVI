"""Jobicy job search via the public REST API.

Public API
----------
- `search_jobs_mcp(query, geo, limit)`         — generic keyword search
- `search_jobs_for_student(student_db_id, …)`  — ranks against the student's
  skills + interests + career goals.

Design notes
------------
- No MCP transport, no async bridging.
- Scoring is done only against the job **title** and **stack** (never the
  description — substring matches there produce false positives).
- Generic terms ("science", "object-oriented programming", etc.) are
  filtered out before scoring and never used as a tag hint.
- Tag hints are tried in priority order (goals → interests → skills), and
  each attempt automatically falls back to worldwide results if the
  location filter yields nothing.
"""

import re
import httpx
from src.tools.jobs_db import save_jobs_to_db

JOBICY_API_URL = "https://jobicy.com/api/v2/remote-jobs"
DEFAULT_TIMEOUT = 20.0
USER_AGENT = "DAIA-JobSearch/1.0"
FETCH_SLICE = 50  # ask Jobicy for more than we return, then rank
MIN_SCORE = 5  # a job must actually overlap the profile to be shown


# ------------------------------------------------------------------
# filtering
# ------------------------------------------------------------------

# Generic terms that don't identify a role. Filtered from scoring and
# never used as a tag hint.
_GENERIC_SKILLS = {
    "science",
    "computer science",
    "engineering",
    "technology",
    "information technology",
    "it",
    "software",
    "hardware",
    "operating systems",
    "systems",
    "networks",
    "databases",
    "data",
    "data structures",
    "programming",
    "algorithms",
    "object-oriented programming",
    "object oriented programming",
    "programming languages",
    "software development",
    "analysis",
    "design",
    "management",
    "mathematics",
    "math",
    "physics",
    "chemistry",
    "biology",
    "research",
    "communication",
    "teamwork",
    "problem solving",
    "english",
    "french",
    "spanish",
    "german",
    "leadership",
    "sales",
    "marketing",
    "support",
    "consulting",
    "office",
    "excel",
    "word",
}

# Role words that are useful when matching a title but bad as tag hints
# (Jobicy doesn't have a "machine learning engineer" tag, only the tech
# terms inside it).
_ROLE_WORDS = {
    "engineer",
    "scientist",
    "developer",
    "analyst",
    "manager",
    "specialist",
    "researcher",
    "architect",
    "consultant",
    "designer",
    "lead",
    "senior",
    "junior",
    "intern",
    "graduate",
    "associate",
    "director",
    "head",
    "principal",
    "expert",
}


def _is_meaningful_skill(name: str) -> bool:
    n = (name or "").strip().lower()
    if len(n) < 3:
        return False
    return n not in _GENERIC_SKILLS


def _tokenize_phrase(phrase: str) -> list[str]:
    """Split 'machine learning engineer' into meaningful tokens."""
    words = re.findall(r"[A-Za-z][A-Za-z0-9+#.]*", phrase or "")
    out = []
    for w in words:
        lw = w.lower()
        if lw in _ROLE_WORDS or not _is_meaningful_skill(lw):
            continue
        out.append(w)
    return out


# ------------------------------------------------------------------
# formatting helpers
# ------------------------------------------------------------------


def _as_text(value) -> str:
    """Jobicy returns some fields as str, others as list[str]. Normalize."""
    if value is None:
        return ""
    if isinstance(value, (list, tuple)):
        return ", ".join(
            str(v).strip() for v in value if v is not None and str(v).strip()
        )
    return str(value).strip()


def _format_job(job: dict, matched: list[str] | None = None, score: int = 0) -> str:
    title = _as_text(job.get("jobTitle")) or "Untitled"
    company = _as_text(job.get("companyName"))
    geo = _as_text(job.get("jobGeo"))
    url = _as_text(job.get("url"))

    header = f"**{title}**"
    if company:
        header += f" at {company}"
    if geo:
        header += f" — {geo}"

    salary = ""
    if job.get("salaryMin") or job.get("salaryMax"):
        lo = _as_text(job.get("salaryMin"))
        hi = _as_text(job.get("salaryMax"))
        cur = _as_text(job.get("salaryCurrency"))
        period = _as_text(job.get("salaryPeriod"))
        bits = "-".join(p for p in (lo, hi) if p)
        if bits:
            salary = f" — {bits} {cur}".rstrip()
            if period:
                salary += f"/{period}"

    lines = [f"- {header}{salary}"]
    if url:
        lines.append(f"  {url}")

    techs = _as_text(job.get("jobIndustry"))
    if techs:
        lines.append(f"  Stack: {techs}")

    if matched:
        lines.append(f"  ✅ Matched: {', '.join(matched)} (score {score})")

    return "\n".join(lines)


def _matches_keyword(job: dict, keyword: str) -> bool:
    kw = (keyword or "").strip().lower()
    if not kw:
        return True
    haystack = " ".join(
        [
            _as_text(job.get("jobTitle")),
            _as_text(job.get("jobDescription")),
            _as_text(job.get("jobIndustry")),
            _as_text(job.get("jobExcerpt")),
        ]
    ).lower()
    return kw in haystack


# ------------------------------------------------------------------
# scoring
# ------------------------------------------------------------------


def _score_job_against_profile(
    job: dict,
    skills: list[dict],
    interests: list[str],
    career_goal_terms: list[str] | None = None,
) -> tuple[int, list[str]]:
    """Score on title and stack only (never description)."""
    title = _as_text(job.get("jobTitle")).lower()
    stack = _as_text(job.get("jobIndustry")).lower()

    score = 0
    matched: set[str] = set()

    def _add_hit(term: str, weight: int) -> None:
        nonlocal score
        t = (term or "").strip()
        if not t:
            return
        kw = t.lower()
        if kw in title:
            score += weight * 3
            matched.add(t)
        elif kw in stack:
            score += weight * 2
            matched.add(t)

    # Career goals — highest weight.
    for goal in career_goal_terms or []:
        for token in _tokenize_phrase(goal):
            _add_hit(token, 3)

    # Interests.
    for interest in interests or []:
        for token in _tokenize_phrase(str(interest)):
            _add_hit(token, 2)

    # Skills (proficiency-weighted).
    for skill in skills or []:
        name = (skill.get("skill_name") or "").strip()
        if not _is_meaningful_skill(name):
            continue
        try:
            prof = max(1, min(5, int(skill.get("proficiency") or 3)))
        except (TypeError, ValueError):
            prof = 3
        _add_hit(name, prof)

    return score, sorted(matched)


def _fetch_jobicy(params: dict) -> list[dict]:
    response = httpx.get(
        JOBICY_API_URL,
        params=params,
        timeout=DEFAULT_TIMEOUT,
        follow_redirects=True,
        headers={"User-Agent": USER_AGENT},
    )
    response.raise_for_status()
    return response.json().get("jobs") or []


# ------------------------------------------------------------------
# generic search
# ------------------------------------------------------------------


def search_jobs_mcp(query: str = "", geo: str = "", limit: int = 5) -> str:
    """Generic Jobicy keyword search."""
    try:
        params = {"count": min(max(int(limit or 5), 1), 50)}
        if geo:
            params["geo"] = geo.strip().lower()
        if query:
            params["tag"] = query.strip()

        jobs = _fetch_jobicy(params)

        if query:
            refined = [j for j in jobs if _matches_keyword(j, query)]
            if refined:
                jobs = refined

        jobs = jobs[: max(1, int(limit or 5))]

        # Save to DB for the Job Market sidebar
        if jobs:
            save_jobs_to_db(jobs)

        if not jobs:
            return (
                f"No jobs found for query={query!r} geo={geo!r}. "
                "Try a broader keyword or remove the location filter."
            )

        header = f"Found {len(jobs)} job(s) on Jobicy"
        if query:
            header += f" matching **{query}**"
        if geo:
            header += f" in **{geo}**"

        return header + ":\n\n" + "\n\n".join(_format_job(j) for j in jobs)

    except httpx.HTTPStatusError as exc:
        return (
            f"Jobicy API returned {exc.response.status_code} for "
            f"query={query!r} geo={geo!r}."
        )
    except Exception as exc:
        return (
            f"Job search failed: `{type(exc).__name__}: {exc}`. "
            "Check network access to jobicy.com from the backend container."
        )


# ------------------------------------------------------------------
# student-aware search
# ------------------------------------------------------------------


def _build_search_hints(
    extra_query: str,
    profile: dict,
    skills: list[dict],
) -> list[str]:
    """
    Return ordered tag hints.

    Priority:
      1. explicit query from the user's message
      2. career goals (short term, long term)
      3. interests
      4. top 3 meaningful skills (no role words)
    """
    hints: list[str] = []
    seen: set[str] = set()

    def _add(term: str) -> None:
        term = (term or "").strip()
        if not term:
            return
        key = term.lower()
        if key in seen:
            return
        seen.add(key)
        hints.append(term)

    _add(extra_query)

    goals = profile.get("career_goals") or {}
    if isinstance(goals, dict):
        for key in ("short_term", "long_term"):
            if isinstance(goals.get(key), str):
                _add(goals[key])
        for k, v in goals.items():
            if k not in ("short_term", "long_term") and isinstance(v, str):
                _add(v)

    for interest in profile.get("interests") or []:
        _add(str(interest))

    meaningful = [
        s
        for s in skills
        if _is_meaningful_skill(s.get("skill_name", ""))
        and s.get("skill_name", "").lower() not in _ROLE_WORDS
    ]
    meaningful.sort(key=lambda s: s.get("proficiency") or 0, reverse=True)
    for s in meaningful[:3]:
        _add(s.get("skill_name", ""))

    return hints


def _try_hints(hints: list[str], geo: str) -> tuple[list[dict], str]:
    """
    Try hints one by one. First with `geo`, then without it if `geo`
    yielded nothing. Returns (jobs, hint_used).
    """
    seen_urls: set[str] = set()

    def _collect(jobs: list[dict]) -> list[dict]:
        fresh = []
        for j in jobs:
            link = _as_text(j.get("url")) or str(id(j))
            if link in seen_urls:
                continue
            seen_urls.add(link)
            fresh.append(j)
        return fresh

    # Pass 1 — with geo (if given).
    if geo:
        for hint in hints:
            params = {"count": FETCH_SLICE, "geo": geo}
            if hint:
                params["tag"] = hint
            try:
                fresh = _collect(_fetch_jobicy(params))
            except Exception:
                fresh = []
            if fresh:
                return fresh, hint

    # Pass 2 — without geo.
    for hint in hints:
        params = {"count": FETCH_SLICE}
        if hint:
            params["tag"] = hint
        try:
            fresh = _collect(_fetch_jobicy(params))
        except Exception:
            fresh = []
        if fresh:
            label = hint
            if geo:
                label = f"{hint} (worldwide — nothing in {geo!r})"
            return fresh, label

    # Pass 3 — latest jobs as a last resort.
    try:
        return _collect(_fetch_jobicy({"count": FETCH_SLICE})), "(latest jobs)"
    except Exception:
        return [], ""


def search_jobs_for_student(
    student_db_id: int,
    extra_query: str = "",
    geo: str = "",
    limit: int = 5,
) -> str:
    """Search Jobicy and rank against skills + interests + career goals."""
    try:
        from src.tools.profile import get_student_profile
        from src.tools.skills import get_student_skills
    except Exception as exc:
        return f"Profile load failed: `{type(exc).__name__}: {exc}`"

    try:
        skills = get_student_skills(student_db_id) or []
    except Exception:
        skills = []

    try:
        profile = get_student_profile(student_db_id) or {}
    except Exception:
        profile = {}

    interests = profile.get("interests") or []

    goals_dict = profile.get("career_goals") or {}
    career_goal_terms: list[str] = []
    if isinstance(goals_dict, dict):
        for value in goals_dict.values():
            if isinstance(value, str) and value.strip():
                career_goal_terms.append(value.strip())

    meaningful = [s for s in skills if _is_meaningful_skill(s.get("skill_name", ""))]

    if not meaningful and not interests and not career_goal_terms and not extra_query:
        return (
            "I don't have any skills, interests, or career goals saved for "
            "your profile yet, so I can't rank jobs against you.\n\n"
            "**Do one of these first:**\n"
            "- Import your transcript in the 📄 **Import Transcript** panel\n"
            "- Add interests or career goals to your profile\n"
            '- Or tell me a keyword, e.g. *"find Java jobs in Europe"*.'
        )

    hints = _build_search_hints(extra_query, profile, skills)
    if not hints:
        hints = [""]

    print(
        f"🔌 [JOB SEARCH] Hints: {hints[:6]} "
        f"(geo={geo!r}, {len(meaningful)} skills, "
        f"{len(interests)} interests, {len(career_goal_terms)} goals)"
    )

    raw_jobs, used_hint = _try_hints(hints, geo)

    if not raw_jobs:
        return (
            f"I couldn't reach any jobs on Jobicy for "
            f"{' / '.join(repr(h) for h in hints[:3])}"
            f"{f' in {geo!r}' if geo else ''}.\n\n"
            "**Try:**\n"
            "- a broader keyword (e.g. `developer`, `data`, `cloud`, `security`)\n"
            "- adding more interests or career goals to your profile"
        )

    scored = [
        (
            *_score_job_against_profile(job, meaningful, interests, career_goal_terms),
            job,
        )
        for job in raw_jobs
    ]
    scored.sort(key=lambda t: t[0], reverse=True)

    matched_jobs = [t for t in scored if t[0] >= MIN_SCORE][:limit]

    # Save to DB for the Job Market sidebar
    if matched_jobs:
        save_jobs_to_db([job for score, matched, job in matched_jobs])

    if not matched_jobs:
        return (
            f"I pulled {len(raw_jobs)} job(s) using **{used_hint}**, but none "
            "of them overlapped strongly enough with your profile.\n\n"
            "**Try:**\n"
            "- a broader keyword (e.g. `developer`, `data`, `cloud`)\n"
            "- removing the location filter\n"
            "- importing your transcript or adding more interests\n\n"
            f"_(Your profile has {len(meaningful)} skill(s), "
            f"{len(interests)} interest(s), and "
            f"{len(career_goal_terms)} career goal(s).)_"
        )

    header = f"Found {len(matched_jobs)} job(s) matching your profile"
    if used_hint:
        header += f" — search used: **{used_hint}**"
    header += ":"

    if geo and "worldwide" in used_hint:
        header += (
            f"\n\n_No matches found in **{geo}**, so I widened the search "
            "to worldwide remote roles._"
        )

    body = "\n\n".join(
        _format_job(job, matched, score) for score, matched, job in matched_jobs
    )

    footer = (
        f"\n\n_Ranked against your {len(meaningful)} skill(s), "
        f"{len(interests)} interest(s), and "
        f"{len(career_goal_terms)} career goal(s)._"
    )

    return f"{header}\n\n{body}{footer}"
