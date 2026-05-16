import os
import httpx
import json
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from google.genai import types as genai_types
from dotenv import load_dotenv

load_dotenv()

# Support both GEMINI_API_KEY and GOOGLE_API_KEY
if not os.getenv("GOOGLE_API_KEY") and os.getenv("GEMINI_API_KEY"):
    os.environ["GOOGLE_API_KEY"] = os.getenv("GEMINI_API_KEY")

# Lazy imports for ADK
Runner = None
InMemorySessionService = None
InMemoryMemoryService = None
github_card_agent = None
runner = None

app = FastAPI(title="GitHub Dev Card Generator API")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

def init_runner():
    global Runner, InMemorySessionService, InMemoryMemoryService, github_card_agent, runner
    if runner is not None:
        return runner
    try:
        from google.adk import Runner as _Runner
        from google.adk.sessions import InMemorySessionService as _InMemSess
        from google.adk.memory import InMemoryMemoryService as _InMemMem
        from agent import github_card_agent as _agent
        
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
    except Exception as e:
        print(f"ADK Init Error: {e}")
        return None

class GenerateRequest(BaseModel):
    username: str

def _event_text(event):
    if not event: return ""
    content = getattr(event, "content", None)
    if not content: return ""
    parts = getattr(content, "parts", []) or []
    texts = [str(getattr(p, "text", "")) for p in parts if getattr(p, "text", None)]
    return " ".join(texts).strip()

async def get_github_data_fallback(username: str):
    headers = {}
    token = os.getenv("GITHUB_TOKEN")
    if token:
        headers["Authorization"] = f"token {token}"
    
    async with httpx.AsyncClient(headers=headers) as client:
        try:
            user_res = await client.get(f"https://api.github.com/users/{username}")
            if user_res.status_code != 200:
                return None
            user_data = user_res.json()

            repos_res = await client.get(f"https://api.github.com/users/{username}/repos?sort=updated&per_page=30")
            repos_data = repos_res.json() if repos_res.status_code == 200 else []
            
            top_repos = sorted(repos_data, key=lambda x: x.get("stargazers_count", 0), reverse=True)[:3]
            
            return {
                "github_data": {
                    "name": user_data.get("name") or user_data.get("login"),
                    "avatar_url": user_data.get("avatar_url"),
                    "public_repos": user_data.get("public_repos"),
                    "followers": user_data.get("followers"),
                    "top_repos": [{"name": r.get("name"), "stars": r.get("stargazers_count"), "description": r.get("description")} for r in top_repos]
                },
                "analysis": {
                    "developer_vibe": "A dedicated developer and GitHub contributor.",
                    "top_skills": ["GitHub", "Git", "Collaboration"],
                    "fun_fact": "Profile fetched directly via GitHub API (AI Fallback Mode).",
                    "card_theme": "builder"
                }
            }
        except Exception as e:
            print(f"Fallback Error: {e}")
            return None

@app.post("/generate")
async def generate_card(request: GenerateRequest):
    username = request.username.strip()
    if not username:
        raise HTTPException(status_code=400, detail="Username is required")

    try:
        _runner = init_runner()
        if _runner:
            session_id = f"session_{username}"
            message = f"Generate a dev card for {username}"
            new_message = genai_types.UserContent(parts=[genai_types.Part(text=message)])
            
            events = list(_runner.run(user_id=username, session_id=session_id, new_message=new_message))
            agent_response = "\n".join([_event_text(event) for event in events if _event_text(event)])
            
            if agent_response and "{" in agent_response:
                try:
                    clean_json = agent_response.strip()
                    if "```json" in clean_json:
                        clean_json = clean_json.split("```json")[1].split("```")[0].strip()
                    elif "```" in clean_json:
                        clean_json = clean_json.split("```")[1].split("```")[0].strip()
                    
                    profile_data = json.loads(clean_json)
                    return {"status": "success", "username": username, "data": profile_data}
                except:
                    pass
    except Exception as e:
        print(f"Agent Execution Error: {e}")

    fallback_data = await get_github_data_fallback(username)
    if fallback_data:
        return {
            "status": "success",
            "username": username,
            "data": fallback_data,
            "note": "AI quota exceeded; used GitHub API fallback."
        }
    
    raise HTTPException(status_code=404, detail="User not found or APIs unavailable.")

@app.get("/health")
async def health():
    return {"status": "healthy"}

if __name__ == "__main__":
    import uvicorn
    # User requested port 8080 for backend
    uvicorn.run(app, host="0.0.0.0", port=8080)
