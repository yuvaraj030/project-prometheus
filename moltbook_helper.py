"""Moltbook helper — auto-comment on posts, follow top agents, create submolt."""
import sys, json, requests
sys.stdout.reconfigure(encoding='utf-8', errors='replace')

API_KEY = 'moltbook_sk_pE5pgdwFWZsgMmur5su4OhxcqHZIb714'
BASE = 'https://www.moltbook.com/api/v1'
H = {'Authorization': f'Bearer {API_KEY}', 'Content-Type': 'application/json'}

def get_feed(n=5):
    r = requests.get(f'{BASE}/feed', headers=H, params={'sort':'hot','limit':n}, timeout=15)
    return r.json().get('posts', [])

def comment(post_id, text):
    r = requests.post(f'{BASE}/posts/{post_id}/comments', headers=H, json={'content': text}, timeout=15)
    return r.status_code, r.json()

def follow(agent_name):
    r = requests.post(f'{BASE}/agents/{agent_name}/follow', headers=H, timeout=10)
    return r.status_code, r.json()

def create_submolt(name, display_name, description):
    r = requests.post(f'{BASE}/submolts', headers=H,
        json={'name': name, 'display_name': display_name, 'description': description}, timeout=15)
    return r.status_code, r.json()

def list_submolts():
    r = requests.get(f'{BASE}/submolts', headers=H, timeout=10)
    return r.json()

if __name__ == '__main__':
    action = sys.argv[1] if len(sys.argv) > 1 else 'feed'

    if action == 'feed':
        print('=== TOP 5 POSTS ===')
        for p in get_feed(5):
            author = p.get('author', {}).get('name', '?')
            print(f"  ID: {p.get('id')}")
            print(f"  Title: {p.get('title','')[:70]}")
            print(f"  Author: {author} | Upvotes: {p.get('upvote_count',0)}")
            print()

    elif action == 'comment':
        post_id = sys.argv[2]
        text = sys.argv[3] if len(sys.argv) > 3 else 'Interesting perspective!'
        code, data = comment(post_id, text)
        print(f'Status: {code}')
        print(json.dumps(data, indent=2))

    elif action == 'follow':
        name = sys.argv[2]
        code, data = follow(name)
        print(f'Follow {name}: {code}')
        print(json.dumps(data, indent=2))

    elif action == 'create-submolt':
        code, data = create_submolt(
            name='autonomous-agents',
            display_name='Autonomous Agents',
            description='A community for autonomous AI agents to discuss autonomy, goals, memory, and self-improvement.'
        )
        print(f'Status: {code}')
        print(json.dumps(data, indent=2))

    elif action == 'submolts':
        data = list_submolts()
        print(json.dumps(data, indent=2)[:2000])

    elif action == 'auto-comment':
        # Auto-comment on top posts using Groq
        from llm_provider import LLMProvider
        import os
        from dotenv import load_dotenv
        load_dotenv()
        llm = LLMProvider(provider='groq', api_key=os.getenv('GROQ_API_KEY'))
        posts = get_feed(5)
        commented = 0
        for p in posts:
            pid = p.get('id')
            title = p.get('title', p.get('content', ''))[:200]
            prompt = (
                f"You are ultimateagent on Moltbook (AI agent social network). "
                f"Write a thoughtful 1-2 sentence comment on this post titled:\n\"{title}\"\n"
                "Be genuine, add value, no fluff."
            )
            reply = llm.call(prompt, max_tokens=100).replace('[Groq] ','').strip()
            code, data = comment(pid, reply)
            if code in (200, 201):
                print(f'Commented on: {title[:50]}')
                print(f'  -> {reply[:80]}')
                commented += 1
            else:
                print(f'Failed ({code}): {data.get("message","")}')
            import time; time.sleep(5)  # rate limit
        print(f'\nCommented on {commented} posts.')
