import streamlit as st
import time
import os
import random
from PIL import Image
from supabase import create_client
from io import BytesIO

# =========================================================
# CONFIG
# =========================================================
st.set_page_config(
    page_title="Collective Garden",
    page_icon="🌷",
    layout="centered"
)

POMODORO_MINUTES = 25
POMODORO_SECONDS = POMODORO_MINUTES * 60
FLOWER_MIN_SIZE = 140
FLOWER_MAX_SIZE = 260

# =========================================================
# SUPABASE (FAIL-SAFE)
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

def safe_insert(payload):
    if supabase is None:
        return
    try:
        supabase.table("sessions").insert(payload).execute()
    except Exception:
        pass

def safe_fetch():
    if supabase is None:
        return []
    try:
        return (
            supabase.table("sessions")
            .select("*")
            .order("timestamp", desc=True)
            .limit(120)
            .execute()
            .data
            or []
        )
    except Exception:
        return []

# =========================================================
# FLOWERS (ONLY 3)
# =========================================================
FLOWERS = {
    "bluebell": {
        "label": "Bluebell — Calm Focus",
        "intention": "Gentle, steady focus.",
        "tips": [
            "Calm focus is still progress.",
            "Slow attention can be powerful.",
            "Breathe gently and return to your task.",
        ],
    },
    "sunflower": {
        "label": "Sunflower — Confidence",
        "intention": "Showing up bravely.",
        "tips": [
            "Confidence doesn’t need to be loud.",
            "You don’t need to feel ready.",
            "Keep going — that’s courage.",
        ],
    },
    "tulip": {
        "label": "Tulip — Growth",
        "intention": "Steady long-term growth.",
        "tips": [
            "Growth often happens unseen.",
            "Small steps compound.",
            "Consistency beats intensity.",
        ],
    },
}

FLOWER_CODES = list(FLOWERS.keys())

# =========================================================
# IMAGE LOADING (CLOUD SAFE)
# =========================================================
def load_image(path):
    try:
        with open(path, "rb") as f:
            img = Image.open(BytesIO(f.read()))
            img.load()
            return img.convert("RGBA")
    except Exception:
        return None

@st.cache_data
def load_assets():
    meadow = load_image("assets/meadow_bg.png")

    flowers = {}
    for code in FLOWER_CODES:
        img = load_image(f"assets/flower_{code}.png")
        if img:
            flowers[code] = img

    return meadow, flowers

meadow_img, flower_images = load_assets()

# =========================================================
# SESSION STATE
# =========================================================
if "active" not in st.session_state:
    st.session_state.active = False
if "start" not in st.session_state:
    st.session_state.start = None
if "flower" not in st.session_state:
    st.session_state.flower = "tulip"
if "paused" not in st.session_state:
    st.session_state.paused = False
if "elapsed_pause" not in st.session_state:
    st.session_state.elapsed_pause = 0.0

# =========================================================
# HELPERS
# =========================================================
def start_session(code):
    st.session_state.active = True
    st.session_state.start = time.time()
    st.session_state.elapsed_pause = 0
    st.session_state.paused = False
    st.session_state.flower = code

def end_session(completed: bool):
    elapsed = int(time.time() - st.session_state.start)
    st.session_state.active = False
    st.session_state.start = None
    st.session_state.paused = False
    st.session_state.elapsed_pause = 0

    if completed:
        safe_insert({
            "flower": st.session_state.flower,
            "duration": elapsed,
            "timestamp": int(time.time()),
        })
        st.success("🌸 25 minutes completed — flower planted!")
        st.balloons()
    else:
        st.info("🌱 Session ended early.")

# =========================================================
# UI
# =========================================================
st.title("🌷 Collective Garden")
st.caption("Grow focus. Bloom together.")

tab1, tab2 = st.tabs(["Focus Session", "Collective Meadow"])

# =========================================================
# TAB 1 — FOCUS SESSION
# =========================================================
with tab1:
    if not st.session_state.active:
        st.subheader("Choose your flower")

        code = st.selectbox(
            "Focus intention",
            FLOWER_CODES,
            format_func=lambda c: FLOWERS[c]["label"],
        )

        st.write(FLOWERS[code]["intention"])

        if flower_images.get(code):
            st.image(flower_images[code], width=220)

        if st.button("Start 25-minute session 🌱"):
            start_session(code)
            st.rerun()

    else:
        # AUTO TICK (SAFE: 1 rerun per second)
        st.experimental_set_query_params(t=int(time.time()))
        time.sleep(1)

        elapsed = int(time.time() - st.session_state.start)
        remaining = max(POMODORO_SECONDS - elapsed, 0)
        progress = min(elapsed / POMODORO_SECONDS, 1.0)

        m, s = divmod(remaining, 60)

        st.subheader(FLOWERS[st.session_state.flower]["label"])
        st.markdown(f"## ⏳ {m:02d}:{s:02d}")
        st.progress(progress)

        img = flower_images.get(st.session_state.flower)
        if img:
            size = int(FLOWER_MIN_SIZE + (FLOWER_MAX_SIZE - FLOWER_MIN_SIZE) * progress)
            st.image(img, width=size)

        tip = random.choice(FLOWERS[st.session_state.flower]["tips"])
        st.info(tip)

        col1, col2 = st.columns(2)
        with col1:
            if st.button("End early"):
                end_session(False)
                st.rerun()
        with col2:
            if remaining <= 0:
                end_session(True)
                st.rerun()

        st.rerun()

# =========================================================
# TAB 2 — COLLECTIVE MEADOW
# =========================================================
with tab2:
    st.subheader("🌼 Collective Meadow")

    if meadow_img is None:
        st.warning("Meadow image missing.")
        st.stop()

    rows = safe_fetch()
    st.write(f"Total blooms: {len(rows)}")

    if not st.button("🌷 Load meadow"):
        st.info("Click to render the global meadow.")
        st.stop()

    base = meadow_img.copy()
    overlay = Image.new("RGBA", base.size, (0, 0, 0, 0))
    W, H = base.size

    for r in rows:
        img = flower_images.get(r.get("flower"))
        if not img:
            continue

        size = 200
        x = random.randint(0, max(0, W - size))
        y = random.randint(int(H * 0.4), max(0, H - size))

        overlay.alpha_composite(
            img.resize((size, size)),
            (x, y),
        )

    final = Image.alpha_composite(base, overlay)
    st.image(final, use_container_width=True)
