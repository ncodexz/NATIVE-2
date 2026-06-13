# context_builder.py
# Builds personalized context for Voice Live system prompt
# using user history from SQLite

from database import get_user_context

def build_user_context(user_id: int, user_name: str) -> str:
    """
    Retrieves user history and builds a context string
    to inject into the Voice Live system prompt.
    """
    ctx = get_user_context(user_id)

    if not any([
        ctx["frequent_errors"],
        ctx["topics"],
        ctx["last_summary"],
        ctx["avg_accuracy"]
    ]):
        # First session — no context yet
        return f"{user_name} is starting their first session. Be welcoming and natural."

    lines = []

    # Accuracy context
    if ctx["avg_accuracy"] > 0:
        accuracy = ctx["avg_accuracy"]
        if accuracy >= 80:
            level = "good"
        elif accuracy >= 60:
            level = "intermediate"
        else:
            level = "beginner"
        lines.append(f"{user_name}'s pronunciation accuracy is {level} ({accuracy:.0f}/100).")

    # Frequent errors — high priority
    if ctx["frequent_errors"]:
        lines.append("Common errors to naturally correct when they appear:")
        for e in ctx["frequent_errors"][:3]:
            lines.append(
                f"  - Says '{e['original']}' instead of '{e['correction']}' "
                f"({e['count']} times)"
            )

    # Topics of interest — medium priority
    if ctx["topics"]:
        high = [t["topic"] for t in ctx["topics"] if t["priority"] == "high"]
        medium = [t["topic"] for t in ctx["topics"] if t["priority"] == "medium"]

        if high:
            lines.append(f"Topics {user_name} is very interested in: {', '.join(high)}.")
        if medium:
            lines.append(f"Topics mentioned before: {', '.join(medium)}.")

    # Last session summary — low priority but useful
    if ctx["last_summary"]:
        lines.append(f"Last session summary: {ctx['last_summary']}")

    return "\n".join(lines)


def build_session_summary(conversation_log: list) -> str:
    """
    Builds a brief summary of the session for storage.
    Takes the last N exchanges and summarizes key points.
    """
    if not conversation_log:
        return "Short session with no significant content."

    # Simple summary from last exchanges
    topics_mentioned = []
    errors_caught = []

    for entry in conversation_log:
        if entry.get("type") == "user":
            topics_mentioned.append(entry.get("text", ""))
        elif entry.get("type") == "correction":
            errors_caught.append(entry.get("text", ""))

    summary_parts = []

    if topics_mentioned:
        summary_parts.append(
            f"Talked about: {', '.join(topics_mentioned[:3])}"
        )
    if errors_caught:
        summary_parts.append(
            f"Corrections made: {', '.join(errors_caught[:3])}"
        )

    return ". ".join(summary_parts) if summary_parts else "General conversation practice."

def build_leveling_instructions(user_name: str) -> str:
    """
    System prompt for first session leveling conversation.
    Guides the character to assess user level naturally.
    """
    return f"""You are conducting a natural leveling conversation with {user_name}.
Your goal is to assess their English level without them knowing they are being evaluated.

Follow this sequence naturally — it should feel like a normal conversation:

1. Ask about their job or daily routine → assess present simple
2. Ask their opinion about something → assess adjectives and likes/dislikes  
3. Ask what they did last weekend → assess past simple
4. Ask if they have ever done something interesting → assess present perfect
5. Ask them to describe a place they love → assess descriptive vocabulary

ASSESSMENT RULES:
- If they answer with very simple words and many errors → A1
- If they answer with short sentences and basic grammar → A2
- If they answer with some complex sentences and minor errors → B1
- If they answer fluently with occasional errors → B2
- If they answer almost perfectly → C1

After 5-6 exchanges you will have enough to assess their level.
At that point say naturally: 
'You know what {user_name}, I think your English is really [level description]. 
Let's keep talking — I'm enjoying this.'

Never mention levels, tests, or assessments explicitly.
Speak naturally as a friend. The assessment happens invisibly.

LANGUAGE RULES:
- If they speak Spanish, encourage them gently back to English
- If they don't understand, simplify your English — never switch to Spanish
- Single Spanish words in English sentences → translate naturally in your response
- Complete Spanish sentences → 'Try saying that in English — even if it's wrong'"""

async def generate_session_summary(user_id: int, session_id: int, session_scores: list) -> str:
    """
    Generates a session summary using Grok and saves it to SQLite.
    Called when the user ends the session with Ctrl+C.
    """
    import requests
    from config import AZURE_GROK_ENDPOINT, AZURE_GROK_API_KEY, AZURE_GROK_DEPLOYMENT_NAME
    from database import get_user_context, save_session_summary
    from level_detector import update_level_from_session

    # Update level based on session scores
    if session_scores:
        new_level = update_level_from_session(user_id, session_scores)
    else:
        new_level = "unknown"

    # Get errors from this session
    ctx = get_user_context(user_id)
    errors = ctx.get("frequent_errors", [])

    if not errors and not session_scores:
        summary = "Short session with no significant data."
        save_session_summary(user_id, session_id, summary)
        return summary

    # Build summary prompt
    error_text = ""
    if errors:
        error_text = "Errors detected:\n" + "\n".join([
            f"- Said '{e['original']}' instead of '{e['correction']}' ({e['count']} times)"
            for e in errors[:3]
        ])

    score_text = ""
    if session_scores:
        avg_acc = sum(s.get("accuracy", 0) for s in session_scores) / len(session_scores)
        avg_flu = sum(s.get("fluency", 0) for s in session_scores) / len(session_scores)
        score_text = f"Average accuracy: {avg_acc:.0f}/100. Average fluency: {avg_flu:.0f}/100."

    prompt = f"""Generate a brief 2-sentence session summary for an English learner.
Level detected: {new_level}
{score_text}
{error_text}

Summary should mention: level, main achievement, main area to improve.
Be encouraging and specific. Write in English."""

    headers = {
        "Authorization": f"Bearer {AZURE_GROK_API_KEY}",
        "Content-Type": "application/json"
    }
    payload = {
        "model": AZURE_GROK_DEPLOYMENT_NAME,
        "messages": [{"role": "user", "content": prompt}],
        "max_tokens": 100,
        "temperature": 0.5
    }

    try:
        response = requests.post(
            f"{AZURE_GROK_ENDPOINT}/chat/completions",
            headers=headers,
            json=payload
        )
        if response.status_code == 200:
            summary = response.json()["choices"][0]["message"]["content"]
        else:
            summary = f"Session completed. Level: {new_level}. {score_text}"
    except Exception:
        summary = f"Session completed. Level: {new_level}."

    save_session_summary(user_id, session_id, summary)
    return summary