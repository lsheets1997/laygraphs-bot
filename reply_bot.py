# reply_bot.py
import os, json, time, random, datetime as dt
from typing import List, Dict, Tuple
import tweepy
import requests
from dotenv import load_dotenv

load_dotenv()

API_KEY=os.getenv("API_KEY")
API_SECRET=os.getenv("API_SECRET")
ACCESS_TOKEN=os.getenv("ACCESS_TOKEN")
ACCESS_SECRET=os.getenv("ACCESS_SECRET")
OPENROUTER_API_KEY=os.getenv("OPENROUTER_API_KEY")

# ---- Config ----
TARGET_USERNAMES = [
    "MLB", "FoulTerritoryTV", "Braves", "MLBBowman", "DOBrienATL"
]
MAX_TWEETS_PER_USER = 5
FRESH_WINDOW_MIN = int(os.getenv("FRESH_WINDOW_MIN", "20"))   # recent tweets only
SCORE_THRESHOLD = int(os.getenv("SCORE_THRESHOLD", "300"))    # likes+retweets+replies minimum
JITTER_MAX = int(os.getenv("JITTER_MAX", "15"))               # add small random delay
STATE_FILE = os.getenv("STATE_FILE", "reply_state.json")      # remember what we replied to
DRY_RUN = os.getenv("DRY_RUN") == "1"

STYLE_GUIDE = """
Voice: Atlanta Braves fan; dry sarcasm, deadpan humor, analytical bite. Confident, quick, never cringe.
Rules:
- Reply with ONE line, <= 220 chars (shorter than a full tweet, since it's a reply).
- Punctuation is ok but NEVER end with a period.
- Keep it Braves-first unless the context is league-wide.
- Use playful pettiness or sardonic stats when it fits. Avoid clichés.
- Light profanity ok ("frick"), nothing harsher.
"""

def enforce_house_style(text: str) -> str:
    t = text.strip()
    if t.endswith("..."):
        t = t[:-3] + "…"
    elif t.endswith("."):
        t = t[:-1]
    return t[:220]

def load_state() -> Dict[str, bool]:
    try:
        with open(STATE_FILE, "r") as f:
            return json.load(f)
    except Exception:
        return {}

def save_state(state: Dict[str, bool]):
    try:
        with open(STATE_FILE, "w") as f:
            json.dump(state, f)
    except Exception:
        pass  # in ephemeral CI this may not persist; good enough to reduce dupes

def make_client() -> tweepy.Client:
    return tweepy.Client(
        consumer_key=API_KEY,
        consumer_secret=API_SECRET,
        access_token=ACCESS_TOKEN,
        access_token_secret=ACCESS_SECRET,
    )

def get_user_ids(client: tweepy.Client, usernames: List[str]) -> Dict[str, str]:
    resp = client.get_users(usernames=usernames, user_fields=["public_metrics"])
    ids = {}
    for u in resp.data or []:
        ids[u.username] = u.id
    return ids

def score_metrics(pm: dict) -> int:
    return int(pm.get("like_count",0) + pm.get("retweet_count",0) + pm.get("reply_count",0))

def generate_reply(context_text: str, author: str) -> str:
    headers = {
        "Authorization": f"Bearer {OPENROUTER_API_KEY}",
        "Content-Type": "application/json",
        "HTTP-Referer": "https://laygraphs.com",
        "X-Title": "Laygraphs Braves Reply Bot",
    }
    data = {
        "model": "openrouter/auto",
        "messages": [
            {"role": "system", "content": STYLE_GUIDE.strip()},
            {"role": "user", "content":
                f"Reply to @{author}'s post with one witty line in the style. "
                f"Context:\n---\n{context_text}\n---\nNo preface, no quotes."
            },
        ],
        "temperature": 0.9,
        "max_tokens": 120,
    }
    r = requests.post("https://openrouter.ai/api/v1/chat/completions", headers=headers, json=data, timeout=25)
    r.raise_for_status()
    text = r.json()["choices"][0]["message"]["content"].strip()
    return enforce_house_style(text)

def pick_targets(client: tweepy.Client, user_ids: Dict[str, str]):
    now = dt.datetime.now(dt.timezone.utc)
    fresh = []
    for uname, uid in user_ids.items():
        r = client.get_users_tweets(
            id=uid,
            max_results=MAX_TWEETS_PER_USER,
            tweet_fields=["public_metrics","created_at","conversation_id"]
        )
        for t in r.data or []:
            age_min = (now - t.created_at).total_seconds()/60.0
            if age_min <= FRESH_WINDOW_MIN:
                score = score_metrics(t.public_metrics or {})
                fresh.append((t, uname, score, age_min))
    # High traffic first
    fresh.sort(key=lambda x: (x[2], -x[3]), reverse=True)
    return fresh

def reply_once():
    if JITTER_MAX > 0:
        time.sleep(random.randint(0, JITTER_MAX))
    state = load_state()
    client = make_client()
    user_ids = get_user_ids(client, TARGET_USERNAMES)
    candidates = pick_targets(client, user_ids)
    for t, uname, score, age_min in candidates:
        if score < SCORE_THRESHOLD:
            continue
        if str(t.id) in state:
            continue  # already replied this run
        # Generate and post reply
        reply_text = generate_reply(t.text, uname)
        if DRY_RUN:
            print(f"[DRY_RUN] Would reply to @{uname} (id={t.id}, score={score}, age={age_min:.1f}m): {reply_text}")
            state[str(t.id)] = True
            save_state(state)
            return
        resp = client.create_tweet(text=reply_text, in_reply_to_tweet_id=t.id)
        print(f"[reply] Replied to @{uname} id={t.id} score={score} age={age_min:.1f}m -> {resp.data.get('id')}")
        state[str(t.id)] = True
        save_state(state)
        return  # one reply per run
    print("[reply] No suitable high-traffic tweets found this run.")

if __name__ == "__main__":
    reply_once()