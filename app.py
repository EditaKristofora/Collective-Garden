import streamlit as st
import time
import os
import random
from io import BytesIO
from PIL import Image
from supabase import create_client

# ======================================================
# CONFIG
# ======================================================
POMODORO_MINUTES = 25
POMODORO_SECONDS = POMODORO_MINUTES * 60
BLOCK_SECONDS = 5 * 60

FLOWER_MIN_SIZE = 120
FLOWER_MAX_SIZE = 280

st.set_page_config(
    page_title="Collective Garden",
    page_icon="🌱",
    layout="centered",
)

# ======================================================
# SUPABASE
# ======================================================
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

# ======================================================
# AUTO REFRESH (SAFE)
# ======================================================
try:
    from streamlit_autorefresh import st_autorefresh
    HAS_AUTOREFRESH = True
except Exception:
    HAS_AUTOREFRESH = False

# ======================================================
# FLOWERS
# ======================================================
FLOWERS = {
    "bluebell": {"label": "Bluebell – Calm Focus", "intention": "Gentle, steady focus."},
    "blossom": {"label": "Blossom – Creativity", "intention": "Playful, open focus."},
    "sunflower": {"label": "Sunflower – Confidence", "intention": "Brave focus."},
    "lavender": {"label": "Lavender – Peace", "intention": "Soft, peaceful focus."},
    "daisy": {"label": "Daisy – Fresh Start", "intention": "Begin again."},
    "tulip": {"label": "Tulip – Growth", "intention": "Long-term progress."},
}
FLOWER_CODES = list(FLOWERS.keys())

CONGRATS_MESSAGES = [
    "🌸 You completed 25 minutes — your flower bloomed!",
    "🌷 Your focus added a bloom to the garden.",
    "🌿 Calm focus is powerful — well done.",
    "✨ One full session completed. Beautiful work.",
    "🌼 Your flower joined the collective meadow.",
]

# ======================================================
# IMAGE LOADING (CLOUD SAFE)
# ======================================================
def safe_open(path):
    try:
        with open(path, "rb") as f:
            img = Image.open(BytesIO(f.read()))
            img.load()
            return img.convert("RGBA")
    except Exception:
        return None

@st.cache_data
def load_images():
    meadow = safe_open("assets/meadow_bg.png")

    flowers = {}
    for code in FLOWER_CODES:
        stages = {}
        for i in range(1, 5):
            img = safe_open(f"assets/flower_{code}_stage{i}.png")
            if img:
                stages[i] = img
        flowers[code] = stages
    return meadow, flowers

meadow_img, flower_images = load_images()

def flower_stage(progress):
    if progress < 0.25:
        return 1
    if progress < 0.5:
        return 2
    if progress < 0.75:
        return 3
    return 4

# ======================================================
# SESSION STATE
# ======================================================
defaults = {
    "session_active": False,
    "start_time": None,
    "paused": False,
    "elapsed_before_pause": 0.0,
    "flower_code": "bluebell",
    "completed_sessions": 0,
    "total_focus_minutes": 0,
    "congrats_index": 0,
    "last_congrats": None,
    "user_name": "",
}
for k, v in defaults.items():
    st.session_state.setdefault(k, v)

# ======================================================
# USER NAME (PERSIST VIA URL)
# ======================================================
def get_param(key):
    v = st.query_params.get(key, "")
    return v[0] if isinstance(v, list) else v

if not st.session_state.user_name:
    st.session_state.user_name = get_param("u")

def sync_name():
    if st.session_state.user_name.strip():
        st.query_params["u"] = st.session_state.user_name.strip()

st.text_input(
    "Your name / nickname:",
    key="user_name",
    placeholder="e.g. FocusFox",
    on_change=sync_name,
)

# ======================================================
# HEADER
# ======================================================
st.title("🌱 Collective Garden")
st.caption("Grow your focus. Bloom together.")

tab1, tab2 = st.tabs(["Focus Session", "Collective Meadow"])

# ======================================================
# TAB 1 — FOCUS SESSION
# ======================================================
with tab1:

    if st.session_state.last_congrats:
        st.balloons()
        st.success(st.session_state.last_congrats)
        st.markdown(
            f"""
<div style="border-radius:16px;padding:16px;border:1px solid #d8e4d8;background:#f5fbf5;">
<b>🌿 Your mini progress</b><br>
• Sessions: {st.session_state.completed_sessions}<br>
• Focus minutes: {st.session_state.total_focus_minutes}
</div>
""",
            unsafe_allow_html=True,
        )
        st.session_state.last_congrats = None

    if not st.session_state.session_active:
        st.subheader("Choose your flower")

        code = st.selectbox(
            "Focus intention",
            FLOWER_CODES,
            format_func=lambda c: FLOWERS[c]["label"],
        )

        preview = flower_images.get(code, {}).get(4)
        if preview:
            st.image(preview, width=220)

        if st.button("Start 25-minute session 🌼"):
            st.session_state.session_active = True
            st.session_state.start_time = time.time()
            st.session_state.elapsed_before_pause = 0
            st.session_state.flower_code = code
            st.rerun()

    else:
        if HAS_AUTOREFRESH and not st.session_state.paused:
            st_autorefresh(interval=1000, key="tick")

        elapsed = (
            st.session_state.elapsed_before_pause
            if st.session_state.paused
            else st.session_state.elapsed_before_pause + (time.time() - st.session_state.start_time)
        )

        remaining = max(POMODORO_SECONDS - elapsed, 0)
        progress = min(elapsed / POMODORO_SECONDS, 1)

        mins, secs = divmod(int(remaining), 60)

        st.subheader(f"{FLOWERS[st.session_state.flower_code]['label']} — Focus")
        st.markdown(f"## ⏳ {mins:02d}:{secs:02d}")
        st.progress(progress)

        stage = flower_stage(progress)
        img = flower_images[st.session_state.flower_code].get(stage)
        if img:
            size = int(FLOWER_MIN_SIZE + (FLOWER_MAX_SIZE - FLOWER_MIN_SIZE) * progress)
            st.image(img, width=size)

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
            if st.button("End early"):
                st.session_state.session_active = False
                st.info("Ended early — no flower added 🌱")
                st.rerun()

        if remaining <= 0:
            st.session_state.session_active = False
            st.session_state.completed_sessions += 1
            st.session_state.total_focus_minutes += 25

            msg = CONGRATS_MESSAGES[
                st.session_state.congrats_index % len(CONGRATS_MESSAGES)
            ]
            st.session_state.congrats_index += 1
            st.session_state.last_congrats = msg

            if supabase:
                supabase.table("sessions").insert({
                    "flower": st.session_state.flower_code,
                    "duration": int(elapsed),
                    "timestamp": int(time.time()),
                    "user_name": st.session_state.user_name or "Anonymous",
                }).execute()

            st.rerun()

# ======================================================
# TAB 2 — COLLECTIVE MEADOW
# ======================================================
with tab2:
    st.subheader("🌼 Collective Meadow")

    # IMPORTANT: prevent crashes while timer runs
    if st.session_state.session_active:
        st.info("🌱 Meadow pauses while your focus session runs.")
        st.stop()

    @st.cache_data(ttl=15)
    def fetch_rows():
        if not supabase:
            return []
        return (
            supabase.table("sessions")
            .select("*")
            .order("timestamp", desc=True)
            .limit(250)
            .execute()
            .data
            or []
        )

    rows = fetch_rows()

    st.write(f"Total blooms: {len(rows)}")

    if st.button("🌷 Load / Refresh meadow"):
        base = meadow_img.copy()
        W, H = base.size
        overlay = Image.new("RGBA", base.size, (0, 0, 0, 0))
        rng = random.Random(42)

        for r in rows:
            img = flower_images.get(r["flower"], {}).get(4)
            if not img:
                continue
            flower = img.resize((220, 220))
            x = rng.randint(0, W - 220)
            y = rng.randint(int(H * 0.4), H - 220)
            overlay.alpha_composite(flower, (x, y))

        final = Image.alpha_composite(base, overlay)
        rgb = Image.new("RGB", final.size, (255, 255, 255))
        rgb.paste(final, mask=final.split()[-1])

        st.image(rgb, width="stretch")
