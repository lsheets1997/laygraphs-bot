# update_roster.py
"""
Fetch active rosters for Braves, Phillies, and Mets from MLB StatsAPI
and write a combined `roster.txt` containing one full name per line.

Teams:
  - Atlanta Braves (ATL)   -> teamId 144
  - Philadelphia Phillies  -> teamId 143
  - New York Mets          -> teamId 121
"""

import json
import sys
import urllib.request
from pathlib import Path

TEAMS = {
    144: "Braves",
    143: "Phillies",
    121: "Mets",
}

def fetch_roster(team_id: int):
    url = f"https://statsapi.mlb.com/api/v1/teams/{team_id}/roster/Active"
    with urllib.request.urlopen(url, timeout=30) as resp:
        data = json.loads(resp.read().decode("utf-8"))
    names = []
    for item in data.get("roster", []):
        person = item.get("person") or {}
        name = person.get("fullName")
        if name:
            names.append(name.strip())
    return names

def main():
    all_names = set()
    for tid, label in TEAMS.items():
        try:
            names = fetch_roster(tid)
        except Exception as e:
            print(f"[update_roster] Error fetching {label}: {e}", file=sys.stderr)
            continue
        print(f"[update_roster] {label}: {len(names)} players")
        all_names.update(names)

    if not all_names:
        print("[update_roster] No names fetched; aborting write.", file=sys.stderr)
        sys.exit(1)

    out = Path("roster.txt")
    text = "\n".join(sorted(all_names))
    if out.exists() and out.read_text(encoding="utf-8") == text:
        print("[update_roster] roster.txt unchanged.")
        return

    out.write_text(text, encoding="utf-8")
    print(f"[update_roster] Wrote {out} with {len(all_names)} names.")

if __name__ == "__main__":
    main()