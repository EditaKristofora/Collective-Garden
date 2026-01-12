import streamlit as st
import time
import os
from PIL import Image
from io import BytesIO
from supabase import create_client

# =========================================================
# CONFIG
# =========================================================
POMODORO_MINUTES = 25
POMODORO_SECONDS = POMODORO_MINUTES * 60
BLOCK_SECONDS = 5 * 60

FLOWER_MIN_SIZE = 140
FLOWER_MAX_SIZE = 260

MAX_MEADOW_ROWS = 200   # memory safety

st.set_page_config(
    page_title="Collective Garden",
    page_icon="🌱",
    layout="centered"
)

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
# FLOWERS (3 ONLY – STABLE)
# =========================================================
FLOWERS = {
    "tulip": {
        "label": "Tulip – Growth",
        "intention": "Steady learning and long-term growth.",
        "tips": [
            "Growth often happens quietly, beneath the surface.",
            "Repeating small actions builds strong roots.",
            "You don’t need to rush — consistency matters more.",
            "Learning takes time. This session is part of it.",
            "Every focused minute strengthens your foundation."
        ],
    },
    "sunflower": {
        "label": "Sunflower – Confidence",
        "intention": "Showing up and trusting yourself.",
        "tips": [
            "Confidence grows when you stay with the task.",
            "You don’t need certainty to keep going.",
            "Turning toward effort is already brave.",
            "Quiet confidence still counts.",
            "This focus is an act of self-trust."
        ],
    },
    "blossom": {
        "label": "Blossom – Creativity",
        "intention": "Open, playful creative focus.",
        "tips": [
            "Ideas don’t need to be perfect yet.",
            "Let curiosity lead this session.",
            "Exploration is part of creativity.",
            "Gentle focus unlocks imagination.",
            "You’re allowed to experiment."
        ],
    },
}

FLOWER_CODES = list(FLOWERS.keys())

# =========================================================
# IMAGES (CLOUD-SAFE LOADING)
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

def get_stage(progress: float) -> int:
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
defaults = {
    "session_active": False,
    "start_time": None,
    "paused": False,
    "elapsed_before_pause": 0.0,
    "flower_code": "tulip",
    "completed_sessions": 0,
    "total_minutes": 0,
    "last_message": None,
    "user_name": "",
}
for k, v in defaults.items():
    if k not in st.session_state:
        st.session_state[k] = v

# =========================================================
# USERNAME (CLOUD-SAFE)
# =========================================================
st.text_input(
    "Your name / nickname (optional)",
    key="user_name",
    placeholder="e.g. Edita, FocusFox"
)

# =========================================================
# TABS
# =========================================================
tab1, tab2 = st.tabs(["Focus Session", "Collective Meadow"])

# =========================================================
# SESSION HELPERS
# =========================================================
def start_session(code):
    st.session_state.session_active = True
    st.session_state.start_time = time.time()
    st.session_state.elapsed_before_pause = 0.0
    st.session_state.paused = False
    st.session_state.flower_code = code

def end_session(early: bool):
    elapsed = (
        st.session_state.elapsed_before_pause
        if st.session_state.paused
        else st.session_state.elapsed_before_pause + (time.time() - st.session_state.start_time)
    )

    completed = (not early) and elapsed >= POMODORO_SECONDS - 2

    st.session_state.session_active = False
    st.session_state.start_time = None
    st.session_state.paused = False
    st.session_state.elapsed_before_pause = 0.0

    if completed:
        st.session_state.completed_sessions += 1
        st.session_state.total_minutes += POMODORO_MINUTES
        st.session_state.last_message = "🌸 You completed 25 minutes. Your flower bloomed."

        if supabase:
            try:
                supabase.table("sessions").insert({
                    "flower": st.session_state.flower_code,
                    "duration": int(elapsed),
                    "timestamp": int(time.time()),
                    "user_name": st.session_state.user_name or "Anonymous",
                }).execute()
            except Exception:
                pass
    else:
        st.session_state.last_message = "🌱 Session ended early. No flower added."

# =========================================================
# TAB 1 — FOCUS
# =========================================================
with tab1:
    if st.session_state.last_message:
        st.success(st.session_state.last_message)
        st.session_state.last_message = None

    if not st.session_state.session_active:
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
        elapsed = (
            st.session_state.elapsed_before_pause
            if st.session_state.paused
            else st.session_state.elapsed_before_pause + (time.time() - st.session_state.start_time)
        )

        remaining = max(POMODORO_SECONDS - elapsed, 0)
        progress = min(elapsed / POMODORO_SECONDS, 1.0)

        mins = int(remaining // 60)
        secs = int(remaining % 60)

        st.subheader(f"{FLOWERS[st.session_state.flower_code]['label']}")
        st.markdown(f"### ⏳ {mins:02d}:{secs:02d}")
        st.progress(progress)

        stage = get_stage(progress)
        img = flower_images[st.session_state.flower_code].get(stage)
        if img:
            size = int(FLOWER_MIN_SIZE + (FLOWER_MAX_SIZE - FLOWER_MIN_SIZE) * progress)
            st.image(img, width=size)

        tips = FLOWERS[st.session_state.flower_code]["tips"]
        tip_index = int(elapsed // BLOCK_SECONDS) % len(tips)
        st.info(tips[tip_index])

        c1, c2 = st.columns(2)
        with c1:
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
        with c2:
            if st.button("End session"):
                end_session(True)
                st.rerun()

        if not st.session_state.paused and remaining <= 0:
            end_session(False)
            st.rerun()

        time.sleep(1)
        st.rerun()

# =========================================================
# TAB 2 — COLLECTIVE MEADOW
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

    from random import Random
    rng = Random(42)

    for r in rows:
        code = r.get("flower")
        img = flower_images.get(code, {}).get(4)
        if not img:
            continue

        size = 220
        x = rng.randint(0, max(0, W - size))
        y = rng.randint(int(H * 0.4), max(int(H * 0.4), H - size))

        base.alpha_composite(img.resize((size, size)), (x, y))

    st.image(base, width="stretch")
