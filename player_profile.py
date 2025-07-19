# player_profile.py

import json
import os
from datetime import datetime

PROFILE_PATH = "player_profile.json"

default_profile = {
    "player_name": "LocalHero",
    "preferred_roles": [],
    "preferred_heroes": [],
    "history": []  # List of {date, filename, summary, feedback}
}

def load_profile():
    if not os.path.exists(PROFILE_PATH):
        save_profile(default_profile)
    with open(PROFILE_PATH, "r", encoding="utf-8") as f:
        return json.load(f)

def save_profile(profile_data):
    with open(PROFILE_PATH, "w", encoding="utf-8") as f:
        json.dump(profile_data, f, indent=2)

def add_clip_to_profile(filename, summary, feedback):
    profile = load_profile()
    clip_entry = {
        "date": datetime.now().isoformat(),
        "filename": os.path.basename(filename),
        "summary": summary,
        "feedback": feedback
    }
    profile["history"].append(clip_entry)
    save_profile(profile)
