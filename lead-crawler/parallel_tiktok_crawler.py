"""
Parallel TikTok Lead Crawler - Run Multiple Agents Concurrently
Launches 10 browser-use agents simultaneously to find TikTok creators with emails

Each agent will:
- Run in a local headless browser
- Find 10 profiles with emails in their bios (100 total)
- Save results to a separate JSON file when complete

Features:
- Parallel execution: All 10 agents run simultaneously
- Structured output: JSON files with all profile data
- Simplified: Agents just return data, Python code handles file I/O

Setup:
1. Add BROWSER_USE_API_KEY to your .env file
2. Run: python parallel_tiktok_crawler.py

Note: Running 10 browsers simultaneously uses significant resources.
Consider reducing NUM_AGENTS if your machine struggles.
"""
import asyncio
import json
from datetime import datetime
from dotenv import load_dotenv
from pydantic import BaseModel
from browser_use import Agent, Browser, ChatBrowserUse, Tools

# Load environment variables from .env file
load_dotenv()


class CreatorLead(BaseModel):
    username: str
    display_name: str
    email: str  # The email found in bio
    bio: str
    follower_count: str
    profile_url: str
    is_verified: bool


class CreatorLeadList(BaseModel):
    leads: list[CreatorLead]


async def find_creators_with_emails_agent(
    agent_id: int,
    target_count: int = 10
):
    """
    Single agent that finds TikTok creators with emails

    Args:
        agent_id: Unique identifier for this agent (1-10)
        target_count: Number of profiles WITH emails to find (default 10)
    """
    output_file = f"tiktok_leads_agent_{agent_id}.json"

    print(f"[Agent {agent_id}] Starting...")
    print(f"[Agent {agent_id}] Target: {target_count} profiles with emails")
    print(f"[Agent {agent_id}] Output: {output_file}\n")

    start_time = datetime.now()

    # Create a local browser for this agent
    browser = Browser(
        headless=True  # Run in background
    )

    # Configure tools to use structured output
    tools = Tools(output_model=CreatorLeadList)

    task = f"""
    Your goal is to find {target_count} TikTok content creators who have EMAIL ADDRESSES in their bios.

    Steps:
    1. Go to https://www.tiktok.com
    2. If you encounter any popups or modals (like login prompts or cookie consent), close them
    3. Browse through the feed and check creator profiles
    4. For each profile you visit:
       - Look at the bio/description
       - Check if there's an EMAIL ADDRESS in the bio (look for patterns like name@domain.com)
       - If there IS an email, extract this data:
         * username: The handle (e.g., "@username" - include the @)
         * display_name: The display name
         * email: The email address found in the bio
         * bio: The full bio text
         * follower_count: Number of followers (keep formatting like "1.2M")
         * profile_url: The profile URL
         * is_verified: Boolean - true if verified badge present
       - If there is NO email in the bio, skip this profile and move to the next one
    5. Keep browsing and checking profiles until you find {target_count} creators WITH emails
    6. Return ALL the profiles you found that have email addresses

    IMPORTANT:
    - You need to find {target_count} profiles that HAVE emails - not just check {target_count} profiles
    - Only return profiles that HAVE emails in their bios
    - Look for email patterns like: word@domain.com, business@gmail.com, etc.
    - You can scroll the feed, use search, or browse different sections to find creators
    - Focus on finding creators who are looking for business opportunities (they're more likely to have emails)
    - Try searching for terms like "business", "collab", "booking", "inquiries" to find creators with emails
    - Keep going until you reach {target_count} profiles with emails
    """

    llm = ChatBrowserUse()

    agent = Agent(
        task=task,
        llm=llm,
        browser=browser,
        tools=tools
    )

    try:
        print(f"[Agent {agent_id}] Navigating to TikTok...\n")
        history = await agent.run()

        print(f"\n[Agent {agent_id}] " + "="*50)
        print(f"[Agent {agent_id}] Lead Crawling Complete!")
        print(f"[Agent {agent_id}] " + "="*50)

        # Parse the structured result from the agent
        result = history.final_result()
        if result:
            leads: CreatorLeadList = CreatorLeadList.model_validate_json(result)
            end_time = datetime.now()
            elapsed = (end_time - start_time).total_seconds()

            print(f"\n[Agent {agent_id}] Found {len(leads.leads)} creators with emails in {elapsed:.1f}s\n")

            # Save to JSON file
            leads_data = {
                "agent_id": agent_id,
                "target_count": target_count,
                "started_at": start_time.isoformat(),
                "completed_at": end_time.isoformat(),
                "elapsed_seconds": elapsed,
                "status": "completed",
                "leads_found": len(leads.leads),
                "leads": [lead.model_dump() for lead in leads.leads]
            }

            with open(output_file, 'w', encoding='utf-8') as f:
                json.dump(leads_data, f, indent=2, ensure_ascii=False)

            print(f"[Agent {agent_id}] ✓ Saved {len(leads.leads)} leads to {output_file}")

            # Print summary
            for i, lead in enumerate(leads.leads[:5], 1):  # Show first 5
                print(f"[Agent {agent_id}] Lead #{i}: {lead.username} - {lead.email}")

            if len(leads.leads) > 5:
                print(f"[Agent {agent_id}] ... and {len(leads.leads) - 5} more")

            return {
                "agent_id": agent_id,
                "success": True,
                "count": len(leads.leads),
                "file": output_file,
                "elapsed": elapsed
            }
        else:
            print(f"[Agent {agent_id}] ✗ No leads found")

            # Save empty result
            leads_data = {
                "agent_id": agent_id,
                "target_count": target_count,
                "started_at": start_time.isoformat(),
                "completed_at": datetime.now().isoformat(),
                "status": "completed",
                "leads_found": 0,
                "leads": []
            }

            with open(output_file, 'w', encoding='utf-8') as f:
                json.dump(leads_data, f, indent=2, ensure_ascii=False)

            return {
                "agent_id": agent_id,
                "success": False,
                "count": 0,
                "file": output_file
            }

    except Exception as e:
        print(f"\n[Agent {agent_id}] ✗ Error: {e}")
        import traceback
        traceback.print_exc()

        # Save error to JSON file
        leads_data = {
            "agent_id": agent_id,
            "target_count": target_count,
            "started_at": start_time.isoformat(),
            "failed_at": datetime.now().isoformat(),
            "status": "failed",
            "error": str(e),
            "leads_found": 0,
            "leads": []
        }

        with open(output_file, 'w', encoding='utf-8') as f:
            json.dump(leads_data, f, indent=2, ensure_ascii=False)

        return {
            "agent_id": agent_id,
            "success": False,
            "count": 0,
            "error": str(e),
            "file": output_file
        }

    finally:
        await browser.close()


async def run_parallel_crawlers(
    num_agents: int = 10,
    profiles_per_agent: int = 10
):
    """
    Run multiple TikTok crawler agents in parallel using local browsers

    Args:
        num_agents: Number of agents to run concurrently (default 10)
        profiles_per_agent: Target number of profiles with emails per agent (default 10)
    """
    print("="*70)
    print("PARALLEL TIKTOK LEAD CRAWLER (LOCAL BROWSERS)")
    print("="*70)
    print(f"Number of agents: {num_agents}")
    print(f"Target per agent: {profiles_per_agent} profiles with emails")
    print(f"Total target: {num_agents * profiles_per_agent} profiles")
    print("="*70 + "\n")

    start_time = datetime.now()

    # Create tasks for all agents
    tasks = [
        find_creators_with_emails_agent(
            agent_id=i+1,
            target_count=profiles_per_agent
        )
        for i in range(num_agents)
    ]

    print(f"Launching {num_agents} agents concurrently...\n")

    # Run all agents concurrently
    results = await asyncio.gather(*tasks, return_exceptions=True)

    end_time = datetime.now()
    duration = (end_time - start_time).total_seconds()

    # Print summary
    print("\n" + "="*70)
    print("ALL AGENTS COMPLETE!")
    print("="*70)
    print(f"Total time: {duration/60:.2f} minutes")
    print()

    successful_agents = 0
    total_leads = 0

    for result in results:
        if isinstance(result, dict):
            agent_id = result.get("agent_id", "?")
            success = result.get("success", False)
            count = result.get("count", 0)
            file = result.get("file", "N/A")

            status = "✓" if success else "✗"
            print(f"{status} Agent {agent_id}: {count} leads → {file}")

            if success:
                successful_agents += 1
                total_leads += count
        else:
            print(f"✗ Agent error: {result}")

    print()
    print("="*70)
    print(f"SUMMARY")
    print("="*70)
    print(f"Successful agents: {successful_agents}/{num_agents}")
    print(f"Total leads found: {total_leads}")
    print(f"Average per agent: {total_leads/num_agents:.1f}")
    print(f"Time per lead: {duration/total_leads:.2f}s" if total_leads > 0 else "N/A")
    print("="*70)

    return results


async def main():
    """Main function"""

    # Configuration
    NUM_AGENTS = 10
    PROFILES_PER_AGENT = 10  # 10 emails per agent = 100 total

    await run_parallel_crawlers(
        num_agents=NUM_AGENTS,
        profiles_per_agent=PROFILES_PER_AGENT
    )


if __name__ == '__main__':
    asyncio.run(main())
