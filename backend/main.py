import os
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import HTMLResponse, FileResponse
from pydantic import BaseModel

from google.genai import types as genai_types

# Lazy imports for optional dependencies so `uvicorn main:app` can start
# even if ADK or agent dependencies are not installed in the environment.
Runner = None
InMemorySessionService = None
InMemoryMemoryService = None
github_card_agent = None

# Initialize FastAPI app
app = FastAPI(title="GitHub Dev Card Generator API")

# Enable CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Initialize ADK Services and Runner
runner = None

def init_runner():
    """Attempt to import and initialize the ADK runner lazily.
    Returns initialized runner or raises ImportError/Exception which callers can handle.
    """
    global Runner, InMemorySessionService, InMemoryMemoryService, github_card_agent, runner
    if runner is not None:
        return runner
    try:
        from google.adk import Runner as _Runner
        from google.adk.sessions import InMemorySessionService as _InMemSess
        from google.adk.memory import InMemoryMemoryService as _InMemMem
        from agent import github_card_agent as _agent
    except Exception as e:
        raise

    # assign to module-level names
    Runner = _Runner
    InMemorySessionService = _InMemSess
    InMemoryMemoryService = _InMemMem
    github_card_agent = _agent

    session_service = InMemorySessionService()
    memory_service = InMemoryMemoryService()
    runner = Runner(
        app_name="github_card_agent",
        agent=github_card_agent,
        session_service=session_service,
        memory_service=memory_service,
        auto_create_session=True
    )
    return runner

class GenerateRequest(BaseModel):
    username: str

def _event_text(event):
    if not event:
        return ""
    content = getattr(event, "content", None)
    if not content:
        return ""
    parts = getattr(content, "parts", []) or []
    texts = []
    for part in parts:
        text = getattr(part, "text", None)
        if text:
            texts.append(str(text))
    return " ".join(texts).strip()


@app.post("/generate")
async def generate_card(request: GenerateRequest):
    """
    Triggers the ADK agent to generate a dev card for the given username.
    """
    username = request.username
    if not username:
        raise HTTPException(status_code=400, detail="Username is required")

    try:
        # Initialize runner lazily (if ADK deps are not installed, return informative error)
        try:
            _runner = init_runner()
        except Exception as e:
            raise HTTPException(status_code=500, detail=f"Failed to initialize ADK runner: {e}")

        # Use username as session_id to maintain context for that user
        session_id = f"session_{username}"
        message = f"Generate a dev card for {username}"

        new_message = genai_types.UserContent(parts=[genai_types.Part(text=message)])
        events = list(_runner.run(user_id=username, session_id=session_id, new_message=new_message))
        
        # Log events for debugging
        # (Removed print that crashes on Windows with emojis)
            
        agent_response = "\n".join([_event_text(event) for event in events if _event_text(event)])
        if not agent_response:
             agent_response = "Agent performed actions but gave no text response."

        # Parse the agent's response as JSON
        try:
            print(f"DEBUG: Agent Response: '{agent_response}'")
            # Clean up potential markdown wrapper
            clean_json = agent_response.strip()
            if clean_json.startswith("```json"):
                clean_json = clean_json[7:-3].strip()
            elif clean_json.startswith("```"):
                clean_json = clean_json[3:-3].strip()
            
            import json
            profile_data = json.loads(clean_json)
            
            return {
                "status": "success",
                "username": username,
                "data": profile_data
            }
        except Exception as e:
            return {
                "status": "partial_success",
                "username": username,
                "agent_response": agent_response,
                "detail": f"Failed to parse agent response as JSON: {e}"
            }

    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/card/{username}", response_class=HTMLResponse)
async def get_card(username: str):
    """
    Serves the saved HTML card for a specific user.
    """
    file_path = f"static/cards/{username}.html"
    if not os.path.exists(file_path):
        raise HTTPException(status_code=404, detail="Card not found")
    
    with open(file_path, "r", encoding="utf-8") as f:
        return f.read()

@app.get("/", response_class=HTMLResponse)
async def serve_index():
    """
    Serves the main frontend application.
    """
    file_path = "static/index.html"
    if not os.path.exists(file_path):
        raise HTTPException(status_code=404, detail="Frontend not found")
    
    with open(file_path, "r", encoding="utf-8") as f:
        return f.read()

@app.get("/health")
async def health():
    """
    Health check endpoint for Cloud Run.
    """
    return {"status": "healthy"}

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8083)
