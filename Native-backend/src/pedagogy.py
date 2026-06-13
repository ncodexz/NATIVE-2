# pedagogy.py
# Pedagogical injection system
# Decides when and what to inject into the conversation

from database import get_user_context, get_connection
from level_detector import get_user_level

# How often to inject corrections (every N turns)
INJECTION_INTERVAL = 5

def get_pending_corrections(user_id: int) -> list:
    """Gets the most frequent unresolved errors for this user."""
    conn = get_connection()
    c = conn.cursor()
    c.execute("""
        SELECT error_type, original, correction, COUNT(*) as count
        FROM errors e
        JOIN sessions s ON e.session_id = s.id
        WHERE s.user_id = ?
        GROUP BY original
        ORDER BY count DESC
        LIMIT 3
    """, (user_id,))
    errors = c.fetchall()
    conn.close()
    return [
        {
            "type": e[0],
            "original": e[1],
            "correction": e[2],
            "count": e[3]
        }
        for e in errors
    ]

def should_inject(turn_count: int, user_id: int) -> bool:
    """Decides if pedagogical injection should happen this turn."""
    if turn_count > 0 and turn_count % INJECTION_INTERVAL == 0:
        corrections = get_pending_corrections(user_id)
        return len(corrections) > 0
    return False

def build_injection(user_id: int) -> str:
    """Builds the injection instruction for the character."""
    corrections = get_pending_corrections(user_id)
    level = get_user_level(user_id)

    if not corrections:
        return ""

    top = corrections[0]
    count = top["count"]

    if level in ["A1", "A2"]:
        # Very gentle for beginners
        injection = f"""In your next response, very naturally and briefly address this:
The user has said '{top['original']}' instead of '{top['correction']}' {count} times.
Find a natural moment to use '{top['correction']}' in your response so they hear it correctly.
Do NOT explicitly correct them — just use the correct form naturally."""

    elif level in ["B1", "B2"]:
        # More direct but still natural
        injection = f"""In your next response, naturally integrate this correction:
The user repeatedly says '{top['original']}' instead of '{top['correction']}' ({count} times).
Use a natural conversational moment to gently highlight this.
Example approach: echo their sentence with the correct form before continuing.
Keep it brief — one natural correction then move on."""

    else:
        # Advanced users can handle more direct feedback
        injection = f"""The user has a recurring pattern: '{top['original']}' → should be '{top['correction']}' ({count} times).
Find a natural moment to address this directly but briefly.
After the correction, immediately continue the conversation naturally."""

    return injection

def build_pronunciation_injection(scores: dict, user_id: int) -> str:
    """Builds injection for pronunciation issues."""
    accuracy = scores.get("accuracy", 0)
    fluency = scores.get("fluency", 0)

    if accuracy < 50:
        return """The user's pronunciation was unclear this turn.
Naturally ask them to repeat: 'Sorry, could you say that again? 
I want to make sure I get you right.'"""

    if fluency < 40:
        return """The user seems to be struggling with fluency.
Slow down your response slightly and ask an easy question
to give them a chance to rebuild confidence."""

    return ""