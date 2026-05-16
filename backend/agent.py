import os
import sys
from dotenv import load_dotenv
from google.adk import Agent
from google.adk.tools import McpToolset
from mcp.client.stdio import StdioServerParameters

# Load environment variables
load_dotenv()

# Define the absolute path to the MCP server
# sys.executable refers to the current python interpreter
mcp_server_path = os.path.join(os.path.dirname(__file__), "mcp_server.py")

# Define the tools using McpToolset and StdioServerParameters
mcp_tools = McpToolset(
    connection_params=StdioServerParameters(
        command=sys.executable,
        args=[mcp_server_path]
    )
)

# Define the GitHub Card Agent
github_card_agent = Agent(
    name="github_card_agent",
    model="gemini-2.5-flash",
    instruction=(
        "You are a GitHub profile analyst and dev card generator. "
        "When a user gives you a GitHub username, you ALWAYS follow this exact sequence: "
        "first call scrape_github, then analyze_profile with the result, "
        "then generate_card_html with all three inputs, then save_card. "
        "Never skip steps. Be enthusiastic about developers' work. "
        "If the profile is private or doesn't exist, say so clearly."
    ),
    tools=[mcp_tools]
)

if __name__ == "__main__":
    # Quick test to see if agent can be initialized
    print("GitHub Card Agent initialized with MCP Toolset (stdio).")
