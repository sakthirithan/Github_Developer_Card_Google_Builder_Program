import os
import httpx
import json
from mcp.server.fastmcp import FastMCP
from dotenv import load_dotenv
import google.generativeai as genai

# Load environment variables
load_dotenv()

# Configure Gemini
genai.configure(api_key=os.getenv("GOOGLE_API_KEY"))
model = genai.GenerativeModel("gemini-1.5-flash")

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
    Calls Gemini 2.5 Flash (using 1.5 flash) to analyze the GitHub profile.
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
    
    response = model.generate_content(prompt)
    try:
        # Clean potential markdown from response
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

@mcp.tool()
def generate_card_html(username: str, github_data: dict, analysis: dict) -> str:
    """
    Generates a self-contained HTML string for a beautiful dev card.
    """
    theme = analysis.get("card_theme", "hacker")
    themes = {
        "hacker": "bg-black text-green-500 border-green-500",
        "builder": "bg-blue-900 text-white border-blue-400",
        "researcher": "bg-gray-100 text-gray-900 border-gray-400",
        "designer": "bg-purple-100 text-purple-900 border-purple-400",
        "open-source-hero": "bg-orange-500 text-white border-orange-200"
    }
    theme_class = themes.get(theme, themes["hacker"])

    repos_html = "".join([
        f'<div class="mb-2 p-2 border-l-2 border-current"><strong>{r["name"]}</strong> ({r["stars"]}⭐): {r["language"] or "N/A"}</div>'
        for r in github_data.get("top_repos", [])[:3]
    ])

    skills_html = "".join([
        f'<span class="px-2 py-1 m-1 text-xs font-bold rounded bg-opacity-20 bg-current border border-current">{skill}</span>'
        for skill in analysis.get("top_skills", [])
    ])

    html = f"""
    <div class="max-w-md mx-auto rounded-xl shadow-lg border-2 p-6 {theme_class} font-mono">
        <div class="flex items-center space-x-4 mb-4">
            <img src="{github_data.get('avatar_url')}" class="w-20 h-20 rounded-full border-2 border-current" />
            <div>
                <h2 class="text-2xl font-bold">{github_data.get('name')}</h2>
                <p class="text-sm italic">@{username}</p>
            </div>
        </div>
        <p class="mb-4 text-sm italic">"{analysis.get('developer_vibe')}"</p>
        <div class="mb-4 flex flex-wrap">
            {skills_html}
        </div>
        <div class="grid grid-cols-2 gap-4 mb-4 text-center">
            <div class="border p-2"><strong>Repos</strong><br/>{github_data.get('public_repos')}</div>
            <div class="border p-2"><strong>Followers</strong><br/>{github_data.get('followers')}</div>
        </div>
        <div class="mb-4">
            <h3 class="font-bold mb-2 uppercase text-xs">Top Projects</h3>
            {repos_html}
        </div>
        <div class="text-xs text-right opacity-70">
            Fun Fact: {analysis.get('fun_fact')}
        </div>
    </div>
    """
    return html

@mcp.tool()
def save_card(username: str, html: str) -> str:
    """
    Saves the HTML to static/cards/{username}.html and returns the relative path.
    """
    base_dir = "static/cards"
    os.makedirs(base_dir, exist_ok=True)
    file_path = f"{base_dir}/{username}.html"
    
    # Wrap in basic HTML structure for standalone viewing if it's just a fragment
    full_html = f"""
    <!DOCTYPE html>
    <html>
    <head>
        <script src="https://cdn.tailwindcss.com"></script>
        <style>body {{ display: flex; align-items: center; justify-content: center; min-height: 100vh; background: #1a202c; }}</style>
    </head>
    <body>
        {html}
    </body>
    </html>
    """
    
    with open(file_path, "w", encoding="utf-8") as f:
        f.write(full_html)
    
    return f"/static/cards/{username}.html"

if __name__ == "__main__":
    mcp.run()
