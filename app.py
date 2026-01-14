import streamlit as st
import time
import os
from PIL import Image
from io import BytesIO
from supabase import create_client
from random import Random

# =========================================================
# PAGE CONFIG
# =========================================================
st.set_page_config(
    page_title="Collective Meadow. Grow your focus. Bloom together",
    page_icon="🌱",
    layout="centered",
)

# =========================================================
# CONSTANTS
# =========================================================
POMODORO_MINUTES = 25
POMODORO_SECONDS = POMODORO_MINUTES * 60
TIP_BLOCK_SECONDS = 5 * 60

FLOWER_MIN_SIZE = 140
FLOWER_MAX_SIZE = 260
MAX_MEADOW_ROWS = 200  # hard memory cap

# =========================================================
# SUPABASE
# =========================================================
@st.cache_resource
def get_supabase():
    try:
        return create_client(
            st.secrets["supabase"]["url"],
            st.secrets["supabase"]["key"],
        )
    except Exception:
        return None

supabase = get_supabase()

# =========================================================
# FLOWERS (STABLE SET)
# =========================================================
FLOWERS = {
    "tulip": {
        "label": "Tulip – Growth",
        "intention": "Steady learning and long-term growth.",
        "tips": [
            "Growth often happens quietly beneath the surface.",
            "Repeating small actions builds strong roots.",
            "Consistency matters more than speed.",
            "Learning takes time — this session counts.",
            "Every focused minute strengthens you.",
        ],
    },
    "sunflower": {
        "label": "Sunflower – Confidence",
        "intention": "Showing up and trusting yourself.",
        "tips": [
            "Confidence grows by staying present.",
            "You don’t need certainty to continue.",
            "Turning toward effort is already brave.",
            "Quiet confidence still counts.",
            "This focus is an act of self-trust.",
        ],
    },
    "blossom": {
        "label": "Blossom – Creativity",
        "intention": "Open, playful creative focus.",
        "tips": [
            "Ideas don’t need to be perfect yet.",
            "Let curiosity guide you.",
            "Exploration is part of creativity.",
            "Gentle focus unlocks imagination.",
            "You’re allowed to experiment.",
        ],
    },
}

FLOWER_CODES = list(FLOWERS.keys())

# =========================================================
# IMAGE LOADING (CLOUD SAFE)
# =========================================================
def _safe_open(path):
    try:
        with open(path, "rb") as f:
            data = f.read()
        img = Image.open(BytesIO(data))
        img.load()
        return img.convert("RGBA")
    except Exception:
        return None

@st.cache_data
def load_images():
    meadow = _safe_open("assets/meadow_bg.png")
    flowers = {}

    for code in FLOWER_CODES:
        stages = {}
        for stage in range(1, 5):
            p = f"assets/flower_{code}_stage{stage}.png"
            if os.path.exists(p):
                img = _safe_open(p)
                if img:
                    stages[stage] = img
        flowers[code] = stages

    return meadow, flowers

meadow_img, flower_images = load_images()

def flower_stage(progress):
    if progress < 0.25:
        return 1
    elif progress < 0.5:
        return 2
    elif progress < 0.75:
        return 3
    return 4

# =========================================================
# SESSION STATE
# =========================================================
if "active" not in st.session_state:
    st.session_state.active = False
if "start_time" not in st.session_state:
    st.session_state.start_time = None
if "flower" not in st.session_state:
    st.session_state.flower = "tulip"
if "message" not in st.session_state:
    st.session_state.message = None
if "user_name" not in st.session_state:
    st.session_state.user_name = ""
if "completed" not in st.session_state:
    st.session_state.completed = 0
if "minutes" not in st.session_state:
    st.session_state.minutes = 0

# =========================================================
# USER NAME
# =========================================================
st.text_input(
    "Your name / nickname (optional)",
    key="user_name",
    placeholder="e.g. FocusCapybara",
)

# =========================================================
# TABS
# =========================================================
tab1, tab2 = st.tabs(["Focus Session", "Collective Meadow"])

# =========================================================
# HELPERS
# =========================================================
def start_session(code):
    st.session_state.active = True
    st.session_state.start_time = time.time()
    st.session_state.flower = code

def end_session(completed):
    st.session_state.active = False
    st.session_state.start_time = None

    if completed:
        st.session_state.completed += 1
        st.session_state.minutes += POMODORO_MINUTES
        st.session_state.message = "🌸 You completed 25 minutes — your flower bloomed!"

        if supabase:
            try:
                supabase.table("sessions").insert({
                    "flower": st.session_state.flower,
                    "duration": POMODORO_SECONDS,
                    "timestamp": int(time.time()),
                    "user_name": st.session_state.user_name or "Anonymous",
                }).execute()
            except Exception:
                pass
    else:
        st.session_state.message = "🌱 Session ended early. No flower added."

# =========================================================
# TAB 1 — FOCUS SESSION (AUTO TICK SAFE)
# =========================================================
with tab1:
    if st.session_state.message:
        st.success(st.session_state.message)
        st.session_state.message = None

    if not st.session_state.active:
        code = st.selectbox(
            "Choose your flower",
            FLOWER_CODES,
            format_func=lambda c: FLOWERS[c]["label"],
        )

        st.write(FLOWERS[code]["intention"])

        preview = flower_images[code].get(4)
        if preview:
            st.image(preview, width=200)

        if st.button("Start 25-minute session 🌼"):
            start_session(code)
            st.rerun()

    else:
        from streamlit_autorefresh import st_autorefresh
        st_autorefresh(interval=1000, key="timer")

        elapsed = time.time() - st.session_state.start_time
        remaining = max(POMODORO_SECONDS - elapsed, 0)
        progress = min(elapsed / POMODORO_SECONDS, 1.0)

        mins = int(remaining // 60)
        secs = int(remaining % 60)

        st.subheader(FLOWERS[st.session_state.flower]["label"])
        st.markdown(f"### ⏳ {mins:02d}:{secs:02d}")
        st.progress(progress)

        stage = flower_stage(progress)
        img = flower_images[st.session_state.flower].get(stage)
        if img:
            size = int(FLOWER_MIN_SIZE + (FLOWER_MAX_SIZE - FLOWER_MIN_SIZE) * progress)
            st.image(img, width=size)

        tips = FLOWERS[st.session_state.flower]["tips"]
        tip_index = int(elapsed // TIP_BLOCK_SECONDS) % len(tips)
        st.info(tips[tip_index])

        if st.button("End session early"):
            end_session(False)
            st.rerun()

        if remaining <= 0:
            end_session(True)
            st.rerun()

# =========================================================
# TAB 2 — COLLECTIVE MEADOW (MANUAL RENDER)
# =========================================================
with tab2:
    st.subheader("🌼 Collective Meadow")

    if not meadow_img:
        st.error("Meadow image missing.")
        st.stop()

    rows = []
    if supabase:
        try:
            rows = (
                supabase.table("sessions")
                .select("*")
                .order("timestamp", desc=True)
                .limit(MAX_MEADOW_ROWS)
                .execute()
                .data or []
            )
        except Exception:
            rows = []

    # Ignore legacy flower types safely
    rows = [r for r in rows if r.get("flower") in FLOWER_CODES]

    user = st.session_state.user_name or "Anonymous"
    your = [r for r in rows if r.get("user_name") == user]

    st.markdown(
        f"""
**Your blooms:** {len(your)}  
**Collective blooms:** {len(rows)}
"""
    )

    if not st.button("🌷 Load / Refresh meadow"):
        st.info("Click to render the meadow.")
        st.stop()

    base = meadow_img.copy()
    W, H = base.size
    rng = Random(42)

    for r in rows:
        img = flower_images[r["flower"]].get(4)
        if not img:
            continue

        size = 220
        x = rng.randint(0, max(0, W - size))
        y = rng.randint(int(H * 0.4), max(int(H * 0.4), H - size))
        base.alpha_composite(img.resize((size, size)), (x, y))

    st.image(base, width="stretch")
