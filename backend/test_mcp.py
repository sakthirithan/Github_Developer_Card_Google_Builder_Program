import asyncio
import json
import os
from mcp_server import scrape_github, analyze_profile, generate_card_html, save_card

async def test_end_to_end():
    username = "torvalds"
    print(f"--- Testing end-to-end for user: {username} ---")
    
    try:
        # 1. Scrape GitHub
        print("Step 1: Scraping GitHub data...")
        github_data = await scrape_github(username)
        if "error" in github_data:
            print(f"Error in scrape_github: {github_data['error']}")
            return
        
        # 2. Analyze Profile
        print("Step 2: Analyzing profile with Gemini...")
        analysis = await analyze_profile(github_data)
        if "error" in analysis:
             print(f"Warning in analyze_profile: {analysis['error']}")
        
        # 3. Generate HTML
        print("Step 3: Generating HTML card...")
        html = generate_card_html(username, github_data, analysis)
        
        # 4. Save Card (Optional but good for verification)
        print("Step 4: Saving card...")
        path = save_card(username, html)
        print(f"Card saved to: {path}")

        # Final Results
        print("\n--- Final Results ---")
        print(f"Card Theme: {analysis.get('card_theme')}")
        print(f"Developer Vibe: {analysis.get('developer_vibe')}")
        
    except Exception as e:
        print(f"An unexpected error occurred: {str(e)}")

if __name__ == "__main__":
    asyncio.run(test_end_to_end())
