# main.py
# NATIVE 2.0 — English learning voice agent

import sys
import asyncio
sys.path.insert(0, 'src')

from database import create_tables, create_user, create_session, get_user_context
from voice_live import NativeVoiceLive, VOICES
from context_builder import build_leveling_instructions, generate_session_summary
from level_detector import get_user_level

def select_character() -> str:
    print("\nChoose your conversation partner:")
    characters = list(VOICES.keys())
    for i, name in enumerate(characters, 1):
        print(f"  {i}. {name}")
    while True:
        try:
            choice = int(input("\nEnter number: "))
            if 1 <= choice <= len(characters):
                return characters[choice - 1]
        except ValueError:
            pass
        print("Invalid choice. Try again.")

def is_first_session(user_id: int) -> bool:
    ctx = get_user_context(user_id)
    return not any([
        ctx["frequent_errors"],
        ctx["topics"],
        ctx["last_summary"],
        ctx["avg_accuracy"]
    ])

async def main():
    print("=" * 40)
    print("   NATIVE 2.0 — English Coach")
    print("=" * 40)

    create_tables()
    name = input("\nWhat is your name? ")
    user_id = create_user(name)
    character = select_character()
    session_id = create_session(user_id, character)

    # Check if first session
    first_session = is_first_session(user_id)
    current_level = get_user_level(user_id)

    if first_session:
        print(f"\n👋 Welcome {name}! Starting your first session with {character}...")
        print("   Just have a natural conversation — enjoy it.\n")
        leveling_context = build_leveling_instructions(name)
    else:
        print(f"\nWelcome back {name}! Level: {current_level}")
        print(f"Starting session with {character}...\n")
        leveling_context = ""

    assistant = NativeVoiceLive(
        character=character,
        user_name=name,
        user_id=user_id,
        user_context=leveling_context if first_session else "",
    )

    try:
        await assistant.start()
    except KeyboardInterrupt:
        pass
    finally:
        print("\n⏳ Generating session summary...")
        summary = await generate_session_summary(
            user_id=user_id,
            session_id=session_id,
            session_scores=assistant.session_scores
        )
        print(f"\n📊 Session Summary:")
        print(f"   {summary}")
        print(f"\n👋 Great work {name}! See you next time.")

asyncio.run(main())