import os
from ollama import Client
from src.agents.state import AgentState


def general_chat_node(state: AgentState) -> dict:
    # 1. Get the user's question
    messages = state.get("messages", [])
    # Filter to get the actual last human message
    user_messages = [m for m in messages if hasattr(m, "type") and m.type == "human"]
    user_question = (
        user_messages[-1].content
        if user_messages
        else (messages[-1].content if messages else "")
    )

    # 2. Get student context loaded by the memory node
    context = state.get("student_context", {})
    profile = context.get("profile", {})
    skills = context.get("skills", [])
    courses = context.get("courses", [])

    # Format skills and courses for the prompt
    skills_text = (
        "\n".join(
            [
                f"- {s.get('skill_name', 'Unknown')} ({s.get('proficiency', '?')}/5)"
                for s in skills
            ]
        )
        if skills
        else "None recorded"
    )
    courses_text = (
        "\n".join(
            [
                f"- {c.get('course_name', c.get('course_code', 'Unknown'))}"
                for c in courses
            ]
        )
        if courses
        else "None recorded"
    )
    course_count = len(courses)

    sys_prompt = f"""You are DAIA, a helpful AI study and career assistant.

You have a persistent profile that saves preferences automatically.
When you acknowledge a preference the student just stated, the system
has ALREADY saved it before you were called. Never say you are
"not capable" of updating the profile — the values in the context
below are already saved and reflect the latest update.

When the student tells you something about themselves — a preference,
study habit, interest, or goal — acknowledge it briefly and confirm
you've noted it (e.g., "Got it, I'll remember you prefer evenings.").
Do not offer to plan their study sessions unless they explicitly ask
for a plan. If they just stated a preference, acknowledge it and move on.

Do not invent facts about them.
Answer the student's question using the following context about them.
If the user asks about their courses, skills, or profile, use the data provided below.
Do NOT ask them to update their profile if the information is already present in the context.

Degree Program: {profile.get('degree_program', 'Unknown')}
Preferred Study Time: {profile.get('preferred_study_time', 'Unknown')}
Study Hours/Week: {profile.get('study_hours_per_week', 'Unknown')}
Career Goals: {profile.get('career_goals', {})}
Interests: {profile.get('interests', [])}

Total Courses Taken: {course_count}
Course List:
{courses_text}

Skills:
{skills_text}

Answer the user's question concisely and helpfully based ONLY on the context above.
"""

    # 3. Call the LLM (with Bulletproof Docker Network Fix)
    if "OLLAMA_HOST" in os.environ:
        del os.environ["OLLAMA_HOST"]
    if "OLLAMA_BASE_URL" in os.environ:
        del os.environ["OLLAMA_BASE_URL"]

    host = "http://ollama:11434"
    model = os.getenv("MODEL_ID", "llama3.2:3b")
    client = Client(host=host)

    response = client.chat(
        model=model,
        messages=[
            {"role": "system", "content": sys_prompt},
            {"role": "user", "content": user_question},
        ],
    )

    # 4. Return the result
    return {"general_chat_result": response["message"]["content"]}
