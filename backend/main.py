import os
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import HTMLResponse, FileResponse
from pydantic import BaseModel

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
        agent=github_card_agent,
        session_service=session_service,
        memory_service=memory_service
    )
    return runner

class GenerateRequest(BaseModel):
    username: str

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

        # Run the agent synchronously for simplicity in this implementation
        # (ADK runner.run returns a response object after processing tools)
        response = _runner.run(message=message, session_id=session_id)
        
        # In a real-world scenario with tool outputs, we'd extract the final result
        # Since our agent saves the card, we'll check the filesystem for the result
        card_path = f"static/cards/{username}.html"
        if os.path.exists(card_path):
            with open(card_path, "r", encoding="utf-8") as f:
                html_content = f.read()
            return {
                "status": "success",
                "username": username,
                "card_url": f"/card/{username}",
                "html": html_content,
                "agent_response": response.text
            }
        else:
            return {
                "status": "partial_success",
                "username": username,
                "agent_response": response.text,
                "detail": "Agent finished but card file was not found."
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
    uvicorn.run(app, host="0.0.0.0", port=8080)
