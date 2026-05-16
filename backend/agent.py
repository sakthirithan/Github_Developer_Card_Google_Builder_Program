import os
import sys
from dotenv import load_dotenv
from google.adk import Agent
from google.adk.tools.mcp_tool.mcp_toolset import McpToolset, StdioConnectionParams
from mcp.client.stdio import StdioServerParameters

# Load environment variables
load_dotenv()

# Define the absolute path to the MCP server
# sys.executable refers to the current python interpreter
mcp_server_path = os.path.join(os.path.dirname(__file__), "mcp_server.py")

# Define the tools using McpToolset and StdioConnectionParams
mcp_tools = McpToolset(
    connection_params=StdioConnectionParams(
        server_params=StdioServerParameters(
            command=sys.executable,
            args=["-u", mcp_server_path],
            cwd=os.path.dirname(__file__),
        ),
        timeout=30.0,
    )
)

# Define the GitHub Card Agent
github_card_agent = Agent(
    name="github_card_agent",
    model="gemini-flash-latest",
    instruction=(
        "You are a GitHub profile analyst. "
        "When a user gives you a GitHub username, your goal is to provide a structured JSON analysis of their profile. "
        "Step 1: Call `scrape_github` to get the raw profile and repo data. "
        "Step 2: Call `analyze_profile` with that data to get AI-generated insights (vibe, skills, theme, fun fact). "
        "Step 3: Once you have the results from both tools, you MUST wrap up by providing a final response. "
        "Your final response MUST be a single JSON object containing both 'github_data' and 'analysis'. "
        "Example: {\"github_data\": {...}, \"analysis\": {...}} "
        "Do NOT use markdown, do NOT use backticks, do NOT use any other text. JUST THE JSON."
    ),
    tools=[mcp_tools]
)

if __name__ == "__main__":
    # Quick test to see if agent can be initialized
    print("GitHub Card Agent initialized with MCP Toolset (stdio).")
