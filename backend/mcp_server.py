import os
import httpx
import json
from mcp.server.fastmcp import FastMCP
from dotenv import load_dotenv
from google import genai

# Load environment variables
load_dotenv()

# Configure Gemini Client
client_genai = genai.Client(api_key=os.getenv("GOOGLE_API_KEY"))

# Initialize FastMCP server
mcp = FastMCP("GitHub Dev Card Generator")

@mcp.tool()
async def scrape_github(username: str) -> dict:
    """
    Calls the GitHub REST API to fetch user profile and repository data.
    """
    headers = {}
    token = os.getenv("GITHUB_TOKEN")
    if token:
        headers["Authorization"] = f"token {token}"
    
    async with httpx.AsyncClient(headers=headers) as client:
        # Fetch User Profile
        user_res = await client.get(f"https://api.github.com/users/{username}")
        if user_res.status_code != 200:
            return {"error": f"User {username} not found"}
        user_data = user_res.json()

        # Fetch Repositories
        repos_res = await client.get(f"https://api.github.com/users/{username}/repos?sort=updated&per_page=100")
        repos_data = repos_res.json() if repos_res.status_code == 200 else []

        # Process Repos
        if not isinstance(repos_data, list):
            repos_data = []
            
        top_repos = sorted(repos_data, key=lambda x: x.get("stargazers_count", 0), reverse=True)[:6]
        top_repos_summary = [
            {
                "name": r.get("name"),
                "stars": r.get("stargazers_count"),
                "language": r.get("language"),
                "description": r.get("description")
            } for r in top_repos
        ]

        # Aggregate Languages
        languages = {}
        for r in repos_data:
            lang = r.get("language")
            if lang:
                languages[lang] = languages.get(lang, 0) + 1
        
        sorted_langs = sorted(languages.items(), key=lambda x: x[1], reverse=True)

        return {
            "name": user_data.get("name") or user_data.get("login"),
            "bio": user_data.get("bio"),
            "location": user_data.get("location"),
            "public_repos": user_data.get("public_repos"),
            "followers": user_data.get("followers"),
            "avatar_url": user_data.get("avatar_url"),
            "top_repos": top_repos_summary,
            "most_used_languages": [l[0] for l in sorted_langs[:5]]
        }

@mcp.tool()
async def analyze_profile(github_data: dict) -> dict:
    """
    Calls Gemini to analyze the GitHub profile.
    """
    prompt = f"""
    Analyze this GitHub profile data and return a JSON object:
    {json.dumps(github_data)}

    Required JSON fields:
    - developer_vibe: A 1-sentence personality description based on their repos and bio.
    - top_skills: A list of the top 3 technical skills or languages.
    - fun_fact: A clever, inferred observation about their coding style or interests.
    - card_theme: One of ["hacker", "builder", "researcher", "designer", "open-source-hero"].

    Return ONLY the JSON object.
    """
    
    response = client_genai.models.generate_content(
        model="gemini-2.0-flash",
        contents=prompt
    )
    
    try:
        text = response.text.strip()
        if text.startswith("```json"):
            text = text[7:-3].strip()
        return json.loads(text)
    except Exception as e:
        return {
            "developer_vibe": "A mysterious coder with a passion for building.",
            "top_skills": github_data.get("most_used_languages", ["Coding"])[:3],
            "fun_fact": "This developer's code is so clean it sparkles.",
            "card_theme": "hacker",
            "error": str(e)
        }

if __name__ == "__main__":
    mcp.run()
