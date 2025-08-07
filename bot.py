# bot.py

import os
import requests
import tweepy
import time, random
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

API_KEY = os.getenv("API_KEY")
API_SECRET = os.getenv("API_SECRET")
ACCESS_TOKEN = os.getenv("ACCESS_TOKEN")
ACCESS_SECRET = os.getenv("ACCESS_SECRET")
OPENROUTER_API_KEY = os.getenv("OPENROUTER_API_KEY")

# ---------- AI Tweet via OpenRouter ----------
def generate_tweet():
    headers = {
        "Authorization": f"Bearer {OPENROUTER_API_KEY}",
        "Content-Type": "application/json",
        "HTTP-Referer": "https://laygraphs.com",
        "X-Title": "Laygraphs Braves Bot",
    }
    data = {
        "model": "openrouter/auto",
        "messages": [
            {
                "role": "system",
                "content": (
                    "You are a Braves fan with dry sarcasm, deadpan humor, and analytical bite. "
                    "Write like a human. Stay under 280 characters. No hashtags unless essential. "
                    "No prefaces like 'Here is a tweet'."
                ),
            },
            {"role": "user", "content": "Write ONE fresh Braves tweet in that voice."},
        ],
        "temperature": 0.85,
        "max_tokens": 120,
    }
    r = requests.post(
        "https://openrouter.ai/api/v1/chat/completions",
        headers=headers,
        json=data,
        timeout=60,
    )
    r.raise_for_status()
    text = r.json()["choices"][0]["message"]["content"].strip()
    return text[:280]

# ---------- Post with Twitter API v2 ----------
def post_tweet():
    # Use Tweepy v2 Client with user context (works on Essential tier)
    client = tweepy.Client(
        consumer_key=API_KEY,
        consumer_secret=API_SECRET,
        access_token=ACCESS_TOKEN,
        access_token_secret=ACCESS_SECRET,
    )

    tweet_text = generate_tweet()
    resp = client.create_tweet(text=tweet_text)
    print("Tweeted:", tweet_text, "\nTweet ID:", resp.data.get("id"))

if __name__ == "__main__":
    # Jitter 0–15 minutes so scheduled runs feel human
    time.sleep(random.randint(0, 900))
    post_tweet()