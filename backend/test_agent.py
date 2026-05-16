import os
import sys
from google import genai
from google.genai import types as genai_types
from agent import github_card_agent
from google.adk import Runner
from google.adk.sessions import InMemorySessionService
from google.adk.memory import InMemoryMemoryService

def test():
    session_service = InMemorySessionService()
    memory_service = InMemoryMemoryService()
    runner = Runner(
        app_name="test_app",
        agent=github_card_agent,
        session_service=session_service,
        memory_service=memory_service,
        auto_create_session=True
    )

    username = "sakthirithan"
    message = f"Generate a dev card for {username}"
    new_message = genai_types.UserContent(parts=[genai_types.Part(text=message)])
    
    print(f"Starting runner for {username}...")
    try:
        events = runner.run(user_id=username, session_id=f"test_{username}", new_message=new_message)
        for event in events:
            print(f"EVENT: {event}")
            if hasattr(event, 'content') and event.content:
                for part in event.content.parts:
                    if hasattr(part, 'text'):
                        print(f"TEXT: {part.text}")
                    if hasattr(part, 'thought'):
                        print(f"THOUGHT: {part.thought}")
                    if hasattr(part, 'call'):
                        print(f"CALL: {part.call}")
    except Exception as e:
        print(f"ERROR: {e}")

if __name__ == "__main__":
    test()
