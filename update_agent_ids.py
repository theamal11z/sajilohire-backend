#!/usr/bin/env python3
"""
Helper script to update PhantomBuster agent IDs
Run this after creating agents in your PhantomBuster dashboard
"""

def update_agent_ids():
    """Interactive script to update agent IDs"""
    print("🚀 PhantomBuster Agent ID Updater")
    print("=" * 50)
    
    print("\n1. First, create these agents in your PhantomBuster dashboard:")
    print("   📱 LinkedIn Profile Scraper")
    print("   📝 LinkedIn Posts/Activity Scraper") 
    print("   🔧 GitHub Profile Scraper")
    print("   🔄 Cross-Platform Reference Agent")
    
    print("\n2. For each agent you create:")
    print("   - Go to https://app.phantombuster.com")
    print("   - Click on the agent")
    print("   - Copy the agent ID from the URL: /agents/{AGENT_ID}")
    
    print("\n3. Enter your agent IDs below:")
    
    agent_ids = {}
    
    # Get LinkedIn Profile agent ID
    linkedin_profile_id = input("\n📱 LinkedIn Profile Scraper Agent ID: ").strip()
    if linkedin_profile_id:
        agent_ids['linkedin_profile'] = linkedin_profile_id
    
    # Get LinkedIn Posts agent ID  
    linkedin_posts_id = input("📝 LinkedIn Posts Scraper Agent ID: ").strip()
    if linkedin_posts_id:
        agent_ids['linkedin_posts'] = linkedin_posts_id
    
    # Get GitHub agent ID
    github_id = input("🔧 GitHub Profile Scraper Agent ID: ").strip()
    if github_id:
        agent_ids['github_advanced'] = github_id
    
    # Get Cross-platform agent ID
    cross_platform_id = input("🔄 Cross-Platform Agent ID: ").strip()
    if cross_platform_id:
        agent_ids['cross_platform'] = cross_platform_id
    
    if not agent_ids:
        print("\n❌ No agent IDs provided. Please create agents first.")
        return
    
    # Update the file
    try:
        with open('services/phantombuster_enrichment.py', 'r') as f:
            content = f.read()
        
        # Replace agent IDs
        for agent_type, agent_id in agent_ids.items():
            # Find and replace the specific agent ID
            import re
            pattern = f"'{agent_type}': '[^']*'"
            replacement = f"'{agent_type}': '{agent_id}'"
            content = re.sub(pattern, replacement, content)
        
        # Write back
        with open('services/phantombuster_enrichment.py', 'w') as f:
            f.write(content)
        
        print(f"\n✅ Updated {len(agent_ids)} agent ID(s) successfully!")
        print("\nUpdated agent IDs:")
        for agent_type, agent_id in agent_ids.items():
            print(f"  {agent_type}: {agent_id}")
        
    except Exception as e:
        print(f"\n❌ Error updating file: {e}")

if __name__ == "__main__":
    update_agent_ids()
