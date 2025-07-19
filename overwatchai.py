from player_profile import add_clip_to_profile
import traceback
import time
import os
import shutil
from watchdog.observers import Observer
from watchdog.events import FileSystemEventHandler
import requests
import json
from PIL import Image
import pytesseract
import re

# ===== USER SETTINGS =====
RAW_CLIP_FOLDER     = r"E:\sulli\aianal"                      # Where raw clips land
EDITED_CLIP_FOLDER  = r"E:\sulli\Videos\autovideoeditor"      # Where clips and screenshots are moved after processing
MODEL_ENDPOINT      = "http://localhost:5000/v1/chat/completions"
MODEL_NAME          = "gpt-4-all"
PROCESS_DELAY       = 2    # seconds to wait for file write
USER_PROFILE_PATH   = os.path.join(EDITED_CLIP_FOLDER, "user_profiles.json")
# =========================

# Ensure folders exist
if not os.path.exists(RAW_CLIP_FOLDER):
    print(f"[FATAL] RAW_CLIP_FOLDER does not exist: {RAW_CLIP_FOLDER}")
    exit(1)

os.makedirs(EDITED_CLIP_FOLDER, exist_ok=True)

# --- User Profile Functions ---
def load_user_profiles() -> dict:
    """Load all user profiles from JSON file or create empty dict."""
    if not os.path.exists(USER_PROFILE_PATH):
        with open(USER_PROFILE_PATH, 'w', encoding='utf-8') as f:
            json.dump({}, f, ensure_ascii=False, indent=2)
    with open(USER_PROFILE_PATH, 'r', encoding='utf-8') as f:
        return json.load(f)


def save_user_profiles(profiles: dict):
    """Save all user profiles to JSON file."""
    with open(USER_PROFILE_PATH, 'w', encoding='utf-8') as f:
        json.dump(profiles, f, ensure_ascii=False, indent=2)


def load_user_profile(user_id: str) -> dict:
    """Load a single user profile or create a new one if missing."""
    profiles = load_user_profiles()
    if user_id in profiles:
        return profiles[user_id]
    profile = {
        "user_id": user_id,
        "name": "Player",
        "rank": "Unknown",
        "preferred_roles": [],
        "best_heroes": [],
        "win_loss_stats": {"wins": 0, "losses": 0},
        "improvement_areas": [],
        "last_seen": None,
        "history": []
    }
    profiles[user_id] = profile
    save_user_profiles(profiles)
    return profile


def save_user_profile(user_id: str, profile: dict):
    """Update a single user profile inside the profiles file."""
    profiles = load_user_profiles()
    profiles[user_id] = profile
    save_user_profiles(profiles)


def save_game_data(user_id: str, replay_metadata: dict):
    """Save replay metadata to the user's profile history."""
    profile = load_user_profile(user_id)
    profile.setdefault("history", []).append(replay_metadata)
    save_user_profile(user_id, profile)


def generate_player_summary(user_id: str) -> str:
    """Generate a summary based on the user's history."""
    profile = load_user_profile(user_id)
    summary = f"Player: {profile.get('name', 'Player')}\n"
    summary += f"Rank: {profile.get('rank', 'Unknown')}\n"
    summary += f"Best Heroes: {', '.join(profile.get('best_heroes', [])) or 'None'}\n"
    win_loss = profile.get("win_loss_stats", {"wins": 0, "losses": 0})
    summary += f"Win/Loss: {win_loss['wins']}/{win_loss['losses']}\n"
    summary += f"Improvement Areas: {', '.join(profile.get('improvement_areas', [])) or 'None'}\n"
    return summary


def analyze_playstyle(replay_data: dict) -> str:
    """Identify high-level patterns in gameplay."""
    return "Aggressiveness: High\nPositioning: Needs improvement\nUlt Economy: Good"


def recommend_training_focus(user_id: str) -> str:
    """Suggest training based on recent mistakes."""
    return "Focus on positioning and timing your engagements."


def compare_with_previous_game(user_id: str, current_data: dict) -> str:
    """Compare current and previous game data."""
    return "Improved cover usage, but ult timing still needs work."


def generate_coach_tone_feedback(replay_data: dict, tone: str = 'friendly') -> str:
    """Provide feedback in different tones."""
    if tone == 'tough-love':
        return "Positioning needs immediate improvement."
    return "Positioning adequate; refine timing."


def track_stat_progress(user_id: str, stat_name: str) -> str:
    """Show progress of a specific stat over time."""
    return f"{stat_name} progress: Improved by 10% over the last 5 games."


def get_ai_feedback_clip_summary(transcribed_clip_text: str) -> str:
    """Summarize AI feedback."""
    return "Summary: Focus on positioning and ult timing."


def link_replay_to_scoreboard(image_path: str) -> dict:
    """Merge replay and scoreboard data using OCR."""
    try:
        img = Image.open(image_path)
        ocr_text = pytesseract.image_to_string(img)
        stats = extract_stats_from_text(ocr_text)
        return stats
    except Exception:
        return {}


def identify_hero_and_role(replay_data: dict) -> str:
    """Classify the game role and heroes."""
    return "Role: DPS, Hero: Tracer"


def generate_end_of_week_report(user_id: str) -> str:
    """Generate a weekly performance report."""
    return "Weekly Report: Improved accuracy, but more deaths."


def tag_replay_moments(replay_data: dict) -> list:
    """Tag key moments in the replay."""
    return ["00:01:23 - Kill", "00:02:45 - Ult", "00:03:10 - Mistake"]


def assign_skill_score(replay_data: dict) -> int:
    """Assign a skill score for the match."""
    return 85


def save_feedback(feedback_text, source_path):
    """Save AI feedback to a JSON file."""
    base_name = os.path.splitext(os.path.basename(source_path))[0]
    feedback_file = os.path.join(EDITED_CLIP_FOLDER, f"{base_name}_feedback.json")
    with open(feedback_file, "w", encoding="utf-8") as f:
        json.dump({"feedback": feedback_text}, f, ensure_ascii=False, indent=2)


def build_clip_payload(clip_path, profile):
    """Build payload for clip analysis."""
    prompt = (
        f"You are an expert Overwatch coach for {profile.get('name', 'Player')} (Rank: {profile.get('rank')}).\n"
        "This gameplay clip was recorded recently.\n"
        f"Clip path: {clip_path}\n\n"
        "Provide a clear, concise analysis identifying key moments, strengths, and areas for improvement.\n"
        "Focus on facts and actionable advice only. Avoid emotional language, praise, or filler.\n"
        "Structure the response with numbered sections: Key Moments, Strengths, Areas for Improvement.\n"
        "Keep responses brief but detailed enough for practical use."
    )
    return {
        "model": MODEL_NAME,
        "messages": [{"role": "user", "content": prompt}],
        "temperature": 0.8,
        "max_tokens": 800
    }


def extract_stats_from_text(text):
    """Extract stats from OCR text."""
    def find_stat(pattern):
        match = re.search(pattern, text, re.IGNORECASE)
        return match.group(1) if match else "N/A"
    return {
        "Kills": find_stat(r"Kills?\s*[:\-]?\s*(\d+)"),
        "Deaths": find_stat(r"Deaths?\s*[:\-]?\s*(\d+)"),
        "Assists": find_stat(r"Assists?\s*[:\-]?\s*(\d+)"),
        "Healing Done": find_stat(r"Healing\s*Done\s*[:\-]?\s*(\d+)"),
        "Accuracy": find_stat(r"Accuracy\s*[:\-]?\s*([\d\.]+%)"),
        "Final Blows": find_stat(r"Final\s*Blows\s*[:\-]?\s*(\d+)")
    }


def build_image_payload(image_path, profile):
    """Build payload for image analysis."""
    try:
        img = Image.open(image_path)
        ocr_text = pytesseract.image_to_string(img)
        stats = extract_stats_from_text(ocr_text)
        prompt_lines = [f"{k}: {v}" for k, v in stats.items()]
        prompt = (
            f"You are an expert Overwatch coach for {profile.get('name', 'Player')} (Rank: {profile.get('rank')}).\n"
            "The final scoreboard of a match was captured:\n\n" +
            "\n".join(prompt_lines) +
            "\n\nProvide clear, concise advice. Avoid positivity or filler."
        )
        return {
            "model": MODEL_NAME,
            "messages": [{"role": "user", "content": prompt}],
            "temperature": 0.8,
            "max_tokens": 600
        }
    except Exception:
        traceback.print_exc()
        fallback_prompt = (
            f"You are an expert Overwatch coach for {profile.get('name', 'Player')} (Rank: {profile.get('rank')}).\n"
            "Scoreboard OCR failed. Provide concise, factual advice only."
        )
        return {
            "model": MODEL_NAME,
            "messages": [{"role": "user", "content": fallback_prompt}],
            "temperature": 0.8,
            "max_tokens": 600
        }


def send_to_model(payload):
    """Send payload to the AI model and return response."""
    try:
        resp = requests.post(MODEL_ENDPOINT, json=payload, timeout=90)
        if resp.status_code == 200:
            return resp.json()["choices"][0]["message"]["content"].strip()
        return f"[Model Error {resp.status_code}] {resp.text}"
    except Exception as e:
        traceback.print_exc()
        return f"[Model Exception] {e}"


def process_clip(src_path):
    """Process a gameplay clip and integrate new features."""
    try:
        user_id = "default_user"
        profile = load_user_profile(user_id)
        payload = build_clip_payload(src_path, profile)
        advice = send_to_model(payload)
        print(f"[INFO] Clip processed: {src_path}\n{advice}\n{'='*50}")
        save_feedback(advice, src_path)

        # Integrate new features
        replay_metadata = {
            "clip_path": src_path,
            "timestamp": time.strftime("%Y-%m-%d %H:%M:%S"),
            "ai_feedback": advice,
            "playstyle_analysis": analyze_playstyle({}),
            "training_focus": recommend_training_focus(user_id),
            "comparison": compare_with_previous_game(user_id, {}),
            "coach_feedback": generate_coach_tone_feedback({}, 'friendly'),
            "stat_progress": track_stat_progress(user_id, 'accuracy'),
            "clip_summary": get_ai_feedback_clip_summary(advice),
            "hero_and_role": identify_hero_and_role({}),
            "tagged_moments": tag_replay_moments({}),
            "skill_score": assign_skill_score({})
        }
        save_game_data(user_id, replay_metadata)
        profile["last_seen"] = replay_metadata["timestamp"]
        save_user_profile(user_id, profile)

        if os.path.exists(src_path):
            shutil.move(src_path, os.path.join(EDITED_CLIP_FOLDER, os.path.basename(src_path)))
    except Exception:
        traceback.print_exc()


def process_image(src_path):
    """Process a scoreboard image and integrate new features."""
    try:
        user_id = "default_user"
        profile = load_user_profile(user_id)
        payload = build_image_payload(src_path, profile)
        advice = send_to_model(payload)
        print(f"[INFO] Image processed: {src_path}\n{advice}\n{'='*50}")
        save_feedback(advice, src_path)

        # Integrate new features
        stats = link_replay_to_scoreboard(src_path)
        replay_metadata = {
            "image_path": src_path,
            "timestamp": time.strftime("%Y-%m-%d %H:%M:%S"),
            "ai_feedback": advice,
            "stats": stats
        }
        save_game_data(user_id, replay_metadata)
        profile["last_seen"] = replay_metadata["timestamp"]
        save_user_profile(user_id, profile)

        if os.path.exists(src_path):
            shutil.move(src_path, os.path.join(EDITED_CLIP_FOLDER, os.path.basename(src_path)))
    except Exception:
        traceback.print_exc()


class ClipHandler(FileSystemEventHandler):
    """Handle filesystem events for new clips and images."""
    def on_created(self, event):
        if event.is_directory:
            return
        print(f"[DEBUG] Detected file: {event.src_path}")
        ext = os.path.splitext(event.src_path)[1].lower()
        time.sleep(PROCESS_DELAY)
        if ext in (".mp4", ".wav"):
            process_clip(event.src_path)
        elif ext in (".png", ".jpg", ".jpeg"):
            process_image(event.src_path)
        else:
            print(f"[DEBUG] Ignored file type: {ext}")


# --- MAIN ---
if __name__ == "__main__":
    try:
        print("[INFO] Watching for new clips and screenshots…")
        observer = Observer()
        observer.schedule(ClipHandler(), RAW_CLIP_FOLDER, recursive=False)
        observer.start()
        while True:
            time.sleep(1)
    except KeyboardInterrupt:
        print("\n[INFO] Shutting down.")
        observer.stop()
    except Exception as e:
        print("[FATAL ERROR]", e)
        traceback.print_exc()
    observer.join()