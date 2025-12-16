import os
import time
import random
from io import BytesIO

import streamlit as st
from PIL import Image
from supabase import create_client


# ------------------------------------------------------------
# PAGE CONFIG (must be the first Streamlit call)
# ------------------------------------------------------------
st.set_page_config(page_title="Collective Garden", page_icon="🌱", layout="centered")


# ------------------------------------------------------------
# OPTIONAL: client-side auto-refresh (safe Pomodoro ticking)
# ------------------------------------------------------------
try:
    from streamlit_autorefresh import st_autorefresh
    HAS_AUTOREFRESH = True
except Exception:
    HAS_AUTOREFRESH = False


# ------------------------------------------------------------
# CONFIG
# ------------------------------------------------------------
POMODORO_MINUTES = 25
POMODORO_SECONDS = POMODORO_MINUTES * 60

FLOWER_MIN_SIZE = 120
FLOWER_MAX_SIZE = 280
BLOCK_SECONDS = 5 * 60  # tips every 5 minutes


# ------------------------------------------------------------
# FLOWERS
# ------------------------------------------------------------
FLOWERS = {
    "bluebell": {
        "label": "Bluebell – Calm Focus",
        "intention": "Gentle, steady focus that feels quiet and grounded.",
        "tips": [
            "Bluebells often grow in quiet forests — your mind can be a quiet forest too.",
            "You don’t have to be fast; calm, steady focus is still progress.",
            "If your mind wanders, gently bring it back, like guiding a soft bell sound.",
            "Relax your shoulders and jaw. Calm focus lives in a relaxed body.",
            "Tiny pockets of calm like this session help your nervous system feel safer.",
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
            "Your imagination is a garden. You’re watering it just by showing up.",
        ],
    },
    "sunflower": {
        "label": "Sunflower – Confidence",
        "intention": "Showing up bravely and backing your own ideas.",
        "tips": [
            "Sunflowers turn toward the sun — today, turn toward what supports you.",
            "You don’t have to feel 100% ready to take a small step.",
            "Your past efforts are roots you can stand on, not proof you’ll fail.",
            "Confidence can be quiet: choosing to keep going is already brave.",
            "Even if nobody sees this work, it still matters that you did it.",
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
            "Even if today feels messy, this moment of peace still counts.",
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
            "Today’s you knows more than yesterday’s you. That’s already growth.",
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
            "Growth can be gentle. You’re allowed to adjust the pace.",
        ],
    },
}

GENERIC_TIPS = [
    "It’s okay if you don’t feel ultra-productive. Being here is enough.",
    "Soft focus is still focus. You don’t have to be perfect.",
    "Check in with your breath: in through the nose, out through the mouth.",
    "Notice one thing you’re grateful for in this moment.",
    "You are allowed to take care of your mind while you work.",
]

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
    "🌺 You finished the session — progress doesn’t need to be loud to be real.",
]

FLOWER_CODES = list(FLOWERS.keys())


# ------------------------------------------------------------
# SUPABASE
# ------------------------------------------------------------
@st.cache_resource
def get_supabase():
    try:
        url = st.secrets["supabase"]["url"]
        key = st.secrets["supabase"]["key"]
        return create_client(url, key)
    except Exception:
        return None


supabase = get_supabase()


def safe_insert_session(payload: dict) -> bool:
    if supabase is None:
        return False
    try:
        supabase.table("sessions").insert(payload).execute()
        return True
    except Exception as e:
        st.warning(f"Supabase insert failed (non-fatal): {e}")
        return False


# ------------------------------------------------------------
# IMAGES (Cloud-safe)
# ------------------------------------------------------------
def _safe_open_image(path: str):
    try:
        with open(path, "rb") as f:
            data = f.read()
        img = Image.open(BytesIO(data))
        img.load()
        return img.convert("RGBA").copy()
    except Exception:
        return None


def load_images():
    meadow = None
    for name in ["meadow_bg.png", "meadow_bg.PNG", "meadow_bg.Png"]:
        p = os.path.join("assets", name)
        if os.path.exists(p):
            meadow = _safe_open_image(p)
            if meadow is not None:
                break

    flower_images = {}
    for code in FLOWER_CODES:
        stages = {}
        for stage in range(1, 5):
            p1 = os.path.join("assets", f"flower_{code}_stage{stage}.png")
            p2 = os.path.join("assets", f"flower_{code}_stage{stage}.PNG")
            fp = p1 if os.path.exists(p1) else (p2 if os.path.exists(p2) else None)
            if fp:
                im = _safe_open_image(fp)
                if im is not None:
                    stages[stage] = im

        if not stages:
            p1 = os.path.join("assets", f"flower_{code}.png")
            p2 = os.path.join("assets", f"flower_{code}.PNG")
            fp = p1 if os.path.exists(p1) else (p2 if os.path.exists(p2) else None)
            if fp:
                im = _safe_open_image(fp)
                if im is not None:
                    stages[4] = im

        flower_images[code] = stages

    return meadow, flower_images


meadow_img, flower_images = load_images()


def get_flower_stage(progress: float) -> int:
    if progress < 0.25:
        return 1
    if progress < 0.50:
        return 2
    if progress < 0.75:
        return 3
    return 4


# ------------------------------------------------------------
# USER NAME (persist via URL)
# ------------------------------------------------------------
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


# ------------------------------------------------------------
# SESSION STATE DEFAULTS
# ------------------------------------------------------------
if "session_active" not in st.session_state:
    st.session_state.session_active = False
if "start_time" not in st.session_state:
    st.session_state.start_time = None
if "flower_code" not in st.session_state:
    st.session_state.flower_code = "bluebell"

if "paused" not in st.session_state:
    st.session_state.paused = False
if "elapsed_before_pause" not in st.session_state:
    st.session_state.elapsed_before_pause = 0.0

if "congrats_index" not in st.session_state:
    st.session_state.congrats_index = 0
if "last_congrats" not in st.session_state:
    st.session_state.last_congrats = None

# personal stats (local device)
if "completed_sessions" not in st.session_state:
    st.session_state.completed_sessions = 0
if "total_focus_minutes" not in st.session_state:
    st.session_state.total_focus_minutes = 0


# ------------------------------------------------------------
# SESSION CONTROL
# ------------------------------------------------------------
def start_session(selected_flower: str):
    st.session_state.session_active = True
    st.session_state.start_time = time.time()
    st.session_state.flower_code = selected_flower
    st.session_state.paused = False
    st.session_state.elapsed_before_pause = 0.0


def end_session(early: bool):
    # elapsed (pause-aware)
    elapsed = 0
    if st.session_state.start_time:
        if st.session_state.paused:
            elapsed = int(st.session_state.elapsed_before_pause)
        else:
            elapsed = int(st.session_state.elapsed_before_pause + (time.time() - st.session_state.start_time))

    completed = (not early) and (elapsed >= POMODORO_SECONDS - 1)

    # reset timer state
    st.session_state.session_active = False
    st.session_state.start_time = None
    st.session_state.paused = False
    st.session_state.elapsed_before_pause = 0.0

    if completed:
        # local stats
        st.session_state.completed_sessions += 1
        st.session_state.total_focus_minutes += POMODORO_MINUTES

        msg = CONGRATS_MESSAGES[st.session_state.congrats_index % len(CONGRATS_MESSAGES)]
        st.session_state.congrats_index += 1
        st.session_state.last_congrats = msg

        # save to Supabase (completed only)
        payload = {
            "flower": st.session_state.flower_code,
            "duration": int(elapsed),
            "timestamp": int(time.time()),
            "user_name": (st.session_state.user_name or "Anonymous").strip() or "Anonymous",
        }
        safe_insert_session(payload)
    else:
        st.session_state.last_congrats = None


# ------------------------------------------------------------
# UI
# ------------------------------------------------------------
st.title("🌱 Collective Garden")
st.caption("BUILD: 2025-12-16 no-meadow-focus v1")
st.caption("Grow your focus, Bloom together. A calm 25-minute focus app where your chosen flower grows — and completed blooms join a shared meadow.")

st.text_input(
    "Your name / nickname (for your personal garden):",
    key="user_name",
    placeholder="e.g. FocusFox, SunnyCoder",
    on_change=_sync_name_to_url,
)

tab1, tab2 = st.tabs(["Focus Session", "Collective Meadow"])


# ------------------------------------------------------------
# TAB 1 — Focus Session
# ------------------------------------------------------------
with tab1:
    # show congrats after rerun
    if st.session_state.last_congrats:
        st.balloons()
        st.success(st.session_state.last_congrats)
        st.markdown(
            f"""
<div style="border-radius:16px;padding:16px 18px;border:1px solid #d8e4d8;background:#f5fbf5;">
  <b>🌿 Your mini progress</b><br>
  • Completed sessions: <b>{st.session_state.completed_sessions}</b><br>
  • Focused minutes: <b>{st.session_state.total_focus_minutes}</b><br>
  • Flowers grown: <b>{st.session_state.completed_sessions}</b>
</div>
""",
            unsafe_allow_html=True,
        )
        st.session_state.last_congrats = None

    if not st.session_state.session_active:
        st.subheader("1) Choose your flower (intention)")

        selected_code = st.selectbox(
            "Which flower matches your focus mood today?",
            options=FLOWER_CODES,
            format_func=lambda c: FLOWERS[c]["label"],
            index=FLOWER_CODES.index(st.session_state.flower_code)
            if st.session_state.flower_code in FLOWER_CODES else 0,
        )

        flower_def = FLOWERS[selected_code]
        st.write(f"**Intention:** {flower_def['intention']}")

        stages = flower_images.get(selected_code, {})
        preview_img = stages.get(4) or (next(iter(stages.values())) if stages else None)
        if preview_img is not None:
            st.image(preview_img, width=220, caption=FLOWERS[selected_code]["label"])

        st.markdown("### 2) Start a 25-minute focus session")
        if st.button("Start 25-minute session 🌼"):
            start_session(selected_code)
            st.rerun()

    else:
        selected_code = st.session_state.flower_code
        flower_def = FLOWERS[selected_code]

        # auto-refresh the timer once per second (Cloud-safe)
        if HAS_AUTOREFRESH and not st.session_state.paused:
            st_autorefresh(interval=1000, key="timer_tick")

        # elapsed (pause-aware)
        if st.session_state.paused:
            elapsed = float(st.session_state.elapsed_before_pause)
        else:
            elapsed = float(st.session_state.elapsed_before_pause) + (time.time() - st.session_state.start_time)

        remaining = max(POMODORO_SECONDS - elapsed, 0)
        progress = min(elapsed / POMODORO_SECONDS, 1.0)

        minutes_left = int(remaining // 60)
        seconds_left = int(remaining % 60)

        stage = get_flower_stage(progress)
        stages = flower_images.get(selected_code, {})
        img = stages.get(stage) or stages.get(4) or (next(iter(stages.values())) if stages else None)

        current_size = int(FLOWER_MIN_SIZE + (FLOWER_MAX_SIZE - FLOWER_MIN_SIZE) * progress)

        block_index = int(elapsed // BLOCK_SECONDS)
        tips_source = flower_def.get("tips") or GENERIC_TIPS
        tip_text = tips_source[block_index % len(tips_source)]

        st.subheader(f"{flower_def['label']} — 25-minute focus")

        # NOTE: no meadow image here (lighter)
        st.markdown(f"### ⏳ {minutes_left:02d}:{seconds_left:02d}")
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
                    st.session_state.elapsed_before_pause = float(elapsed)
                    st.rerun()
            else:
                if st.button("Resume ▶️"):
                    st.session_state.paused = False
                    st.session_state.start_time = time.time()
                    st.rerun()

        with col2:
            if st.button("End session"):
                end_session(early=True)
                st.info("🌱 Ended early — no flower added this time.")
                st.rerun()

        with col3:
            if not HAS_AUTOREFRESH:
                if st.button("🔄 Refresh timer"):
                    st.rerun()
            else:
                st.write("")

        if (not st.session_state.paused) and remaining <= 0:
            end_session(early=False)
            st.rerun()


# ------------------------------------------------------------
# TAB 2 — Collective Meadow
# ------------------------------------------------------------
with tab2:
    st.subheader("🌼 Collective Meadow — Shared Blossoms")

    if meadow_img is None:
        st.error("Meadow image NOT loaded. Expected assets/meadow_bg.png")
        st.stop()

    base = meadow_img.convert("RGBA")
    W, H = base.size

    # fetch latest rows (limit for stability)
    rows = []
    supabase_error = None
    if supabase is None:
        supabase_error = "Supabase is offline — global meadow won't update right now."
    else:
        try:
            rows = (
                supabase.table("sessions")
                .select("*")
                .order("timestamp", desc=True)
                .limit(250)
                .execute()
                .data
                or []
            )
        except Exception as e:
            supabase_error = f"Supabase read failed: {e}"
            rows = []

    user_name = (st.session_state.get("user_name") or "Anonymous").strip() or "Anonymous"

    def norm_name(x):
        return (x or "Anonymous").strip() or "Anonymous"

    your_rows = [r for r in rows if norm_name(r.get("user_name")) == user_name]

    st.markdown(
        f"""
**Your completed blooms ({user_name}):** {len(your_rows)}  
**Total collective blooms (last 250):** {len(rows)}
"""
    )
    if supabase_error:
        st.info(supabase_error)

    # lazy render button to avoid heavy work every rerun
    if "render_meadow" not in st.session_state:
        st.session_state.render_meadow = False

    colA, colB = st.columns([1, 2])
    with colA:
        if st.button("🌷 Load / Refresh meadow"):
            st.session_state.render_meadow = True
    with colB:
        st.caption("This renders the meadow image with flowers on top (heavier).")

    if not st.session_state.render_meadow:
        st.info("Click **Load / Refresh meadow** to render the global meadow image.")
        st.stop()

    overlay = Image.new("RGBA", (W, H), (0, 0, 0, 0))
    rng = random.Random(42)

    flower_size = 220
    max_x = max(0, W - flower_size)
    max_y = max(0, H - flower_size)
    y_min = int(H * 0.40)

    pasted = 0
    for r in rows:
        code = r.get("flower")
        if not code:
            continue
        stages = flower_images.get(code, {})
        bloom = stages.get(4)
        if bloom is None:
            continue

        bloom_rgba = bloom.resize((flower_size, flower_size)).convert("RGBA")
        x = rng.randint(0, max_x) if max_x > 0 else 0
        y = rng.randint(y_min, max_y) if max_y >= y_min else y_min
        overlay.alpha_composite(bloom_rgba, dest=(x, y))
        pasted += 1

    combined_rgba = Image.alpha_composite(base, overlay)

    # flatten alpha to avoid black background
    combined_rgb = Image.new("RGB", combined_rgba.size, (255, 255, 255))
    combined_rgb.paste(combined_rgba, mask=combined_rgba.split()[-1])

    st.image(combined_rgb, width="stretch", caption=f"🌍 Global Meadow ({pasted} blooms drawn)")

    if not rows:
        st.info("The meadow is still empty 🌱 Finish a full 25-minute session to plant the first bloom.")
