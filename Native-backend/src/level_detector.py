# level_detector.py
# Detects user English level from pronunciation scores and conversation patterns

from database import get_connection

LEVELS = {
    "A1": {"min_accuracy": 0,  "max_accuracy": 40,  "description": "beginner"},
    "A2": {"min_accuracy": 40, "max_accuracy": 60,  "description": "elementary"},
    "B1": {"min_accuracy": 60, "max_accuracy": 75,  "description": "intermediate"},
    "B2": {"min_accuracy": 75, "max_accuracy": 85,  "description": "upper intermediate"},
    "C1": {"min_accuracy": 85, "max_accuracy": 100, "description": "advanced"},
}

def detect_level_from_scores(accuracy: float, fluency: float) -> str:
    """Detects level based on pronunciation assessment scores."""
    combined = (accuracy * 0.6) + (fluency * 0.4)
    
    for level, data in LEVELS.items():
        if data["min_accuracy"] <= combined < data["max_accuracy"]:
            return level
    return "A1"

def save_user_level(user_id: int, level: str):
    """Saves detected level to user profile."""
    conn = get_connection()
    c = conn.cursor()
    c.execute("""
        UPDATE users SET level = ? WHERE id = ?
    """, (level, user_id))
    conn.commit()
    conn.close()

def get_user_level(user_id: int) -> str:
    """Gets current user level from database."""
    conn = get_connection()
    c = conn.cursor()
    c.execute("SELECT level FROM users WHERE id = ?", (user_id,))
    result = c.fetchone()
    conn.close()
    return result[0] if result else "unknown"

def update_level_from_session(user_id: int, session_scores: list) -> str:
    """
    Updates user level after a session based on accumulated scores.
    session_scores: list of dicts with accuracy and fluency per turn
    """
    if not session_scores:
        return get_user_level(user_id)

    avg_accuracy = sum(s.get("accuracy", 0) for s in session_scores) / len(session_scores)
    avg_fluency = sum(s.get("fluency", 0) for s in session_scores) / len(session_scores)

    new_level = detect_level_from_scores(avg_accuracy, avg_fluency)
    save_user_level(user_id, new_level)
    return new_level

def get_level_instructions(level: str) -> str:
    """Returns speaking instructions for the character based on user level."""
    instructions = {
        "A1": """The user is a complete beginner (A1).
- Use only the most common 500 words
- Speak in very short sentences — maximum 5 words
- Repeat key words naturally
- Be extremely patient and encouraging
- If they don't understand, simplify further""",

        "A2": """The user is elementary level (A2).
- Use common everyday vocabulary
- Keep sentences short and clear
- Focus on present and past simple tenses
- Give extra time for responses
- Celebrate small wins naturally""",

        "B1": """The user is intermediate level (B1).
- Use natural everyday vocabulary
- Normal sentence length
- Introduce some phrasal verbs and idioms occasionally
- Correct only errors that impact communication
- Engage with more complex topics""",

        "B2": """The user is upper intermediate level (B2).
- Use rich natural vocabulary
- Discuss abstract topics naturally
- Use idioms and expressions freely
- Only correct significant errors
- Challenge them occasionally with complex structures""",

        "C1": """The user is advanced level (C1).
- Speak completely naturally as with a native speaker
- Use sophisticated vocabulary and complex structures
- Only correct very subtle or repeated errors
- Engage in deep, nuanced conversations
- Treat them as near-equal in language ability""",
    }
    return instructions.get(level, instructions["A1"])