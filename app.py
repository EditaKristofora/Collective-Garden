import traceback
import streamlit as st
from PIL import Image, ImageDraw
import time
import os
from supabase import create_client

# -------------------------------
# SUPABASE CLIENT
# -------------------------------
@st.cache_resource
def get_supabase():
    try:
        url = st.secrets["supabase"]["url"]
        key = st.secrets["supabase"]["key"]
        return create_client(url, key)
    except Exception:
        return None

supabase = get_supabase()

# -------------------------------
# CONFIG
# -------------------------------
POMODORO_MINUTES = 25
POMODORO_SECONDS = POMODORO_MINUTES * 60

FLOWER_MIN_SIZE = 120
FLOWER_MAX_SIZE = 280
BLOCK_SECONDS = 5 * 60  # New tip every 5 minutes

# -------------------------------
# FLOWER DEFINITIONS
# -------------------------------
FLOWERS = {
    "bluebell": {
        "label": "Bluebell – Calm Focus",
        "intention": "Gentle, steady focus that feels quiet and grounded.",
        "tips": [
            "Bluebells often grow in quiet forests — your mind can be a quiet forest too.",
            "You don’t have to be fast; calm, steady focus is still progress.",
            "If your mind wanders, gently bring it back, like guiding a soft bell sound.",
            "Relax your shoulders and jaw. Calm focus lives in a relaxed body.",
            "Tiny pockets of calm like this session help your nervous system feel safer."
        ],
    },
    "blossom": {
        "label": "Blossom – Creativity",
        "intention": "Playful, open focus for creating, exploring, and experimenting.",
        "tips": [
            "Creativity thrives in imperfect drafts. You don’t need to get it right on the first try.",
            "Notice one tiny detail you enjoy about what you’re creating right now.",
            "Let ideas come without judging them — you can tidy them up later.",
            "A short stretch or sip of water can gently reset your creative energy.",
            "Your imagination is a garden. You’re watering it just by showing up."
        ],
    },
    "sunflower": {
        "label": "Sunflower – Confidence",
        "intention": "Showing up bravely and backing your own ideas.",
        "tips": [
            "Sunflowers turn toward the sun — today, turn toward what supports you.",
            "You don’t have to feel 100% ready to take a small step.",
            "Your past efforts are roots you can stand on, not proof you’ll fail.",
            "Confidence can be quiet: just choosing to keep going is already brave.",
            "Even if nobody sees this work, it still matters that you did it."
        ],
    },
    "lavender": {
        "label": "Lavender – Peace",
        "intention": "Slow, peaceful focus that protects your energy.",
        "tips": [
            "Lavender is often linked to calm and rest — let this session be gentle.",
            "You’re allowed to move slowly and still call it progress.",
            "Notice one place in your body you can soften right now.",
            "You don’t have to earn rest with productivity. You deserve both.",
            "Even if today feels messy, this moment of peace still counts."
        ],
    },
    "daisy": {
        "label": "Daisy – Fresh Start",
        "intention": "Starting again, even if yesterday was messy.",
        "tips": [
            "Daisies feel like morning energy — you can start fresh at any time of day.",
            "You’re not behind; you’re just starting from where you are now.",
            "Tiny steps are kinder and more sustainable than huge pushes.",
            "You can restart this session as many times as you need. That’s not failure.",
            "Today’s you knows more than yesterday’s you. That’s already growth."
        ],
    },
    "tulip": {
        "label": "Tulip – Growth",
        "intention": "Long-term learning, practice, and small steps forward.",
        "tips": [
            "Tulips spend a long time growing unseen before they bloom — like your skills.",
            "You don’t have to see progress every day for growth to be happening.",
            "Repeating something is not a waste; it’s how your brain builds pathways.",
            "Treat this session as one brick in a path, not the whole road.",
            "Growth can be gentle. You’re allowed to adjust the pace."
        ],
    },
}

GENERIC_TIPS = [
    "It’s okay if you don’t feel ultra-productive. Being here is enough.",
    "Soft focus is still focus. You don’t have to be perfect.",
    "Check in with your breath: in through the nose, out through the mouth.",
    "Notice one thing you’re grateful for in this moment.",
    "You are allowed to take care of your mind while you work."
]

# -------------------------------
# CONGRATULATORY MESSAGES
# -------------------------------
CONGRATS_MESSAGES = [
    "🌸 You completed the full 25 minutes — your flower has fully bloomed. Beautiful work.",
    "🌼 One calm session at a time — your focus just added a new bloom to the garden.",
    "🌿 You stayed with your attention for 25 minutes. That’s real, meaningful growth.",
    "🌷 Your flower is now part of the Collective Garden. Thank you for showing up.",
    "🌻 You nurtured your focus with care and patience. That effort matters.",
    "🍃 A full session completed — gentle focus can be powerful too.",
    "✨ You honored your time and energy today. Your flower is glowing.",
    "🪴 Another bloom has joined the meadow, thanks to your steady presence.",
    "💛 You gave yourself 25 minutes of calm attention. That’s something to be proud of.",
    "🌺 You finished the session — progress doesn’t need to be loud to be real."
]


FLOWER_CODES = list(FLOWERS.keys())

# -------------------------------
# IMAGE LOADING
# -------------------------------
from io import BytesIO

def _safe_open_image(path: str):
    """
    Loads an image into memory (detached from file handle) so Streamlit can re-encode it safely.
    Returns PIL.Image or None if it fails.
    """
    try:
        with open(path, "rb") as f:
            data = f.read()
        img = Image.open(BytesIO(data))
        img.load()
        return img.convert("RGBA").copy()
    except Exception:
        return None


@st.cache_data
def load_images():
    # Meadow
    meadow_img = None
    for name in ["meadow_bg.png", "meadow_bg.PNG", "meadow_bg.Png"]:
        path = os.path.join("assets", name)
        if os.path.exists(path):
            meadow_img = _safe_open_image(path)
            if meadow_img is not None:
                break

    # Flower stages: flower_images[code][stage]
    flower_images = {}
    for code in FLOWER_CODES:
        stages = {}
        for stage in range(1, 5):
            p1 = os.path.join("assets", f"flower_{code}_stage{stage}.png")
            p2 = os.path.join("assets", f"flower_{code}_stage{stage}.PNG")

            img = None
            if os.path.exists(p1):
                img = _safe_open_image(p1)
            elif os.path.exists(p2):
                img = _safe_open_image(p2)

            if img is not None:
                stages[stage] = img

        # Optional fallback to old single-file style
        if not stages:
            b1 = os.path.join("assets", f"flower_{code}.png")
            b2 = os.path.join("assets", f"flower_{code}.PNG")
            if os.path.exists(b1):
                img = _safe_open_image(b1)
                if img is not None:
                    stages[4] = img
            elif os.path.exists(b2):
                img = _safe_open_image(b2)
                if img is not None:
                    stages[4] = img

        flower_images[code] = stages

    return meadow_img, flower_images


meadow_img, flower_images = load_images()

def get_flower_stage(progress: float) -> int:
    # progress is 0.0 to 1.0
    if progress < 0.25:
        return 1
    elif progress < 0.50:
        return 2
    elif progress < 0.75:
        return 3
    else:
        return 4


# -------------------------------
# SESSION STATE
# -------------------------------
if "session_active" not in st.session_state:
    st.session_state.session_active = False

if "start_time" not in st.session_state:
    st.session_state.start_time = None

if "flower_code" not in st.session_state:
    st.session_state.flower_code = "bluebell"

# -------------------------------
# PAGE CONFIG
# -------------------------------
def main():
    st.set_page_config(
        page_title="Collective Garden",
        page_icon="🌱",
        layout="centered"
)

    st.title("🌱 Collective Garden")
    st.caption("Grow your focus, bloom together.")
# -------------------------------
# USER IDENTITY (PERSIST VIA URL)
# -------------------------------
def _get_query_param(key: str) -> str:
    val = st.query_params.get(key, "")
    if isinstance(val, list):
        return val[0] if val else ""
    return val or ""

if "user_name" not in st.session_state:
    st.session_state.user_name = _get_query_param("u")

def _sync_name_to_url():
    name = (st.session_state.user_name or "").strip()
    if name:
        st.query_params["u"] = name
    else:
        try:
            del st.query_params["u"]
        except Exception:
            pass

st.text_input(
    "Your name / nickname (for your personal garden):",
    key="user_name",
    placeholder="e.g. FocusFox, SunnyCoder",
    on_change=_sync_name_to_url,
)

if not (st.session_state.user_name or "").strip():
    st.info("Tip: enter a nickname so your personal garden stays after refresh 🌿")



tab1, tab2 = st.tabs(["Focus Session", "Collective Meadow"])

# -------------------------------
# SESSION CONTROL FUNCTIONS
# -------------------------------
def start_session(selected_flower: str):
    st.session_state.session_active = True
    st.session_state.start_time = time.time()
    st.session_state.flower_code = selected_flower

def end_session(early=False):
    elapsed = 0
    if st.session_state.start_time:
        elapsed = int(time.time() - st.session_state.start_time)

    if supabase is not None:
        try:
            supabase.table("sessions").insert({
                "flower": st.session_state.flower_code,
                "duration": elapsed,
                "timestamp": int(time.time())
            }).execute()
        except Exception as e:
            st.warning(f"Could not save session: {e}")

    st.session_state.session_active = False
    st.session_state.start_time = None

    if early:
        st.success("You ended the session early 🌱")
    else:
        st.success("Your flower fully bloomed 🌸")

# -------------------------------
# TAB 1 — FOCUS SESSION
# -------------------------------
with tab1:
    # --- session state defaults
    if "session_active" not in st.session_state:
        st.session_state.session_active = False
    if "start_time" not in st.session_state:
        st.session_state.start_time = None
    if "flower_code" not in st.session_state:
        st.session_state.flower_code = "bluebell"

    if "paused" not in st.session_state:
        st.session_state.paused = False
    if "elapsed_before_pause" not in st.session_state:
        st.session_state.elapsed_before_pause = 0

    if "completed_sessions" not in st.session_state:
        st.session_state.completed_sessions = 0
    if "total_focus_minutes" not in st.session_state:
        st.session_state.total_focus_minutes = 0
    if "congrats_index" not in st.session_state:
        st.session_state.congrats_index = 0

    # store messages across reruns (THIS fixes “no congrats shown”)
    if "last_congrats" not in st.session_state:
        st.session_state.last_congrats = None
    if "last_progress_html" not in st.session_state:
        st.session_state.last_progress_html = None

    # --- helpers
    def start_session(selected_flower: str):
        st.session_state.session_active = True
        st.session_state.start_time = time.time()
        st.session_state.flower_code = selected_flower
        st.session_state.paused = False
        st.session_state.elapsed_before_pause = 0

    def end_session(early: bool):
        # pause-aware elapsed
        elapsed = 0
        if st.session_state.start_time:
            if st.session_state.paused:
                elapsed = int(st.session_state.elapsed_before_pause)
            else:
                elapsed = int(st.session_state.elapsed_before_pause + (time.time() - st.session_state.start_time))

        completed = (not early) and (elapsed >= POMODORO_SECONDS - 5)

        # SAVE ONLY IF COMPLETED (and include user_name so it won't be NULL)
        if completed and supabase is not None:
            try:
                supabase.table("sessions").insert({
                    "flower": st.session_state.flower_code,
                    "duration": elapsed,
                    "timestamp": int(time.time()),
                    "user_name": (st.session_state.user_name or "Anonymous").strip()
                }).execute()
            except Exception as e:
                st.warning(f"Could not save session: {e}")

        # Update local mini stats (optional, still nice)
        if completed:
            st.session_state.completed_sessions += 1
            st.session_state.total_focus_minutes += POMODORO_MINUTES

            msg = CONGRATS_MESSAGES[st.session_state.congrats_index % len(CONGRATS_MESSAGES)]
            st.session_state.congrats_index += 1

            # store for display AFTER rerun
            st.session_state.last_congrats = msg
            st.session_state.last_progress_html = f"""
<div style="
    border-radius: 16px;
    padding: 16px 18px;
    border: 1px solid #d8e4d8;
    background-color: #f5fbf5;
    margin-top: 10px;
">
  <b>🌿 Your mini progress</b><br>
  • Completed sessions: <b>{st.session_state.completed_sessions}</b><br>
  • Focused minutes: <b>{st.session_state.total_focus_minutes}</b><br>
  • Flowers grown: <b>{st.session_state.completed_sessions}</b>
</div>
            """
        else:
            st.session_state.last_congrats = None
            st.session_state.last_progress_html = None

        # Reset timer state
        st.session_state.session_active = False
        st.session_state.start_time = None
        st.session_state.paused = False
        st.session_state.elapsed_before_pause = 0

        if not completed:
            st.info("🌱 Ended early — that’s okay. No flower was added this time 💛")

    # ------------------------------------------------------------
    # NOT ACTIVE (selection + start)
    # ------------------------------------------------------------
    if not st.session_state.session_active:
        # Show stored congrats after rerun (THIS ensures you see it)
        if st.session_state.last_congrats:
            st.balloons()
            st.success(st.session_state.last_congrats)
            if st.session_state.last_progress_html:
                st.markdown(st.session_state.last_progress_html, unsafe_allow_html=True)

            # show once
            st.session_state.last_congrats = None
            st.session_state.last_progress_html = None

        st.subheader("1) Choose your flower (intention)")

        selected_code = st.selectbox(
            "Which flower matches your focus mood today?",
            options=FLOWER_CODES,
            format_func=lambda c: FLOWERS[c]["label"],
            index=FLOWER_CODES.index(st.session_state.flower_code) if st.session_state.flower_code in FLOWER_CODES else 0
        )

        flower_def = FLOWERS[selected_code]
        st.write(f"**Intention:** {flower_def['intention']}")

        # Preview full bloom (stage 4)
        stages = flower_images.get(selected_code, {})
        preview_img = stages.get(4) or next(iter(stages.values()), None)
        if preview_img is not None:
            st.image(preview_img, width=220, caption=FLOWERS[selected_code]["label"])

        st.markdown("### 2) Start a 25-minute focus session")
        if st.button("Start 25-minute session 🌼"):
            start_session(selected_code)
            st.rerun()

    # ------------------------------------------------------------
    # ACTIVE SESSION
    # ------------------------------------------------------------
    else:
        selected_code = st.session_state.flower_code
        flower_def = FLOWERS[selected_code]

        # pause-aware elapsed
        if st.session_state.paused:
            elapsed = st.session_state.elapsed_before_pause
        else:
            elapsed = st.session_state.elapsed_before_pause + (time.time() - st.session_state.start_time)

        remaining = max(POMODORO_SECONDS - elapsed, 0)
        progress = min(elapsed / POMODORO_SECONDS, 1.0)

        minutes_left = int(remaining // 60)
        seconds_left = int(remaining % 60)

        # growth stage image
        stage = get_flower_stage(progress)
        stages = flower_images.get(selected_code, {})
        img = stages.get(stage) or stages.get(4) or next(iter(stages.values()), None)

        # optional size growth too
        current_size = int(FLOWER_MIN_SIZE + (FLOWER_MAX_SIZE - FLOWER_MIN_SIZE) * progress)

        # tips every 5 minutes
        block_index = int(elapsed // BLOCK_SECONDS)
        tips_source = flower_def.get("tips") or GENERIC_TIPS
        tip_text = tips_source[block_index % len(tips_source)]

        st.subheader(f"{flower_def['label']} — 25-minute focus")

        if meadow_img is not None:
            st.image(meadow_img)

        st.markdown(f"### ⏳ {minutes_left:02d}:{seconds_left:02d} (total {POMODORO_MINUTES} min)")
        st.progress(progress)

        if img is not None:
            st.image(img, width=current_size)

        st.markdown(f"**Intention:** {flower_def['intention']}")
        st.info(tip_text)

        col1, col2, col3 = st.columns(3)

        with col1:
            if not st.session_state.paused:
                if st.button("Pause ⏸️"):
                    st.session_state.paused = True
                    st.session_state.elapsed_before_pause = elapsed
                    st.rerun()
            else:
                if st.button("Resume ▶️"):
                    st.session_state.paused = False
                    st.session_state.start_time = time.time()
                    st.rerun()

        with col2:
            if st.button("End session"):
                end_session(early=True)
                st.rerun()

        with col3:
            st.write("")

        # auto-tick only if not paused
        if not st.session_state.paused:
            if remaining <= 0:
                end_session(early=False)
                st.rerun()
            else:
                time.sleep(1)
                st.rerun()

# -------------------------------
# TAB 2 — COLLECTIVE MEADOW
# -------------------------------
with tab2:
    st.subheader("🌼 Collective Meadow — Shared Blossoms")

    user_name = (st.session_state.user_name or "Anonymous").strip() or "Anonymous"

    if supabase is None:
        st.info("Supabase is offline — meadow data is not available right now.")
    else:
        try:
            data = supabase.table("sessions").select("*").execute()
            rows = data.data or []
        except Exception as e:
            st.error(f"Could not load meadow data: {e}")
            rows = []

        if not rows:
            st.write("The meadow is still empty 🌱\n\nFinish a full 25-minute session to plant the first flower.")
        else:
            # Personal vs collective
            your_rows = [r for r in rows if (r.get("user_name") or "Anonymous") == user_name]

            st.write(f"**Your completed blooms ({user_name}):** {len(your_rows)}")
            st.write(f"**Total collective blooms:** {len(rows)}")

            # Collective flower counts
            flower_counts = {}
            for r in rows:
                code = r.get("flower")
                if code in FLOWERS:
                    flower_counts[code] = flower_counts.get(code, 0) + 1

            st.write("### 🌸 Collective flower counts")
            for code, count in flower_counts.items():
                st.write(f"- **{FLOWERS[code]['label']}**: {count}")

            st.write("### 🌷 Global Meadow")

            if meadow_img is None:
                st.warning("Meadow background image is missing.")
            else:
                import random
                from PIL import Image

                base = meadow_img.convert("RGBA")
                W, H = base.size
                overlay = Image.new("RGBA", base.size, (0, 0, 0, 0))

                rng = random.Random(42)
                flower_size = 180
                pasted_count = 0

                # Use ONLY stage 4 for the collective meadow
                for r in rows:
                    code = r.get("flower")
                    stages = flower_images.get(code, {})
                    flower_img = stages.get(4)

                    if flower_img is None:
                        continue

                    flower_big = flower_img.convert("RGBA").resize((flower_size, flower_size))

                    max_x = max(0, W - flower_size)
                    max_y = max(0, H - flower_size)
                    y_min = int(H * 0.40)

                    x = rng.randint(0, max_x) if max_x > 0 else 0
                    y = rng.randint(y_min, max_y) if max_y >= y_min else y_min

                    overlay.alpha_composite(flower_big, dest=(x, y))
                    pasted_count += 1

                combined = Image.alpha_composite(base, overlay)
                st.image(combined, caption=f"Collective Garden 🌱 ({pasted_count} blooms)")

def main():
    # 👇 Move ALL your existing app code that renders UI into here
    # (from st.set_page_config(...) down to tab1/tab2 rendering)
    pass


if __name__ == "__main__":
    try:
        main()
    except Exception:
        import streamlit as st
        st.error("Crash on Streamlit Cloud — traceback below:")
        st.code(traceback.format_exc())
        st.stop()
