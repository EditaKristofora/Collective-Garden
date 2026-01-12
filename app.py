import os
import time
import random
import traceback
from io import BytesIO
from typing import Dict, Optional

import streamlit as st
from PIL import Image
from supabase import create_client

# Optional (recommended): install `streamlit-autorefresh` in requirements.txt
# streamlit-autorefresh==1.0.1
try:
    from streamlit_autorefresh import st_autorefresh
    HAS_AUTOREFRESH = True
except Exception:
    HAS_AUTOREFRESH = False


# ============================================================
# CONFIG
# ============================================================
POMODORO_MINUTES = 25
POMODORO_SECONDS = POMODORO_MINUTES * 60
BLOCK_SECONDS = 5 * 60  # tips every 5 minutes

FLOWER_MIN_SIZE = 140
FLOWER_MAX_SIZE = 320

MEADOW_RENDER_LIMIT = 200          # how many blooms to draw on the image
MEADOW_FETCH_LIMIT = 300           # how many rows to fetch for counts
MEADOW_AUTOREFRESH_MS = 30_000     # update counts every 30s


# ============================================================
# FLOWERS (3 TYPES)
# ============================================================
FLOWERS = {
    "bluebell": {
        "label": "Bluebell – Calm Focus",
        "intention": "Gentle, steady focus that feels quiet and grounded.",
        "tips": [
            "Bluebells often grow in quiet forests — your mind can be a quiet forest too.",
            "Calm, steady focus is still progress.",
            "If your mind wanders, gently bring it back — no judgment.",
            "Relax your shoulders and jaw. Calm focus lives in a relaxed body.",
            "Tiny pockets of calm help your nervous system feel safer.",
        ],
    },
    "sunflower": {
        "label": "Sunflower – Confidence",
        "intention": "Showing up bravely and backing your own ideas.",
        "tips": [
            "Sunflowers turn toward the sun — turn toward what supports you.",
            "You don’t need to feel 100% ready to take a small step.",
            "Quiet confidence counts. Just continuing is brave.",
            "Let your focus be warm and steady — like sunlight.",
            "Even if nobody sees this work, it still matters that you did it.",
        ],
    },
    "tulip": {
        "label": "Tulip – Growth",
        "intention": "Long-term learning, practice, and small steps forward.",
        "tips": [
            "Tulips grow unseen for a long time before they bloom — like your skills.",
            "You don’t have to see progress daily for growth to be happening.",
            "Repeating is not a waste — it builds your brain’s pathways.",
            "Treat this session as one brick in a path, not the whole road.",
            "Growth can be gentle. You’re allowed to adjust the pace.",
        ],
    },
}
FLOWER_CODES = list(FLOWERS.keys())
VALID_CODES = set(FLOWER_CODES)

GENERIC_TIPS = [
    "Soft focus is still focus. You don’t have to be perfect.",
    "Check in with your breath: in through the nose, out through the mouth.",
    "Tiny steps are kinder and more sustainable than huge pushes.",
    "You’re allowed to take care of your mind while you work.",
    "Notice one thing you’re grateful for in this moment.",
]

CONGRATS_MESSAGES = [
    "🌸 You completed the full 25 minutes — your flower fully bloomed. Beautiful work.",
    "🌼 One calm session at a time — you just added a new bloom to the garden.",
    "🌿 You stayed with your attention for 25 minutes. That’s meaningful growth.",
    "🌷 Your flower is now part of the Collective Meadow. Thank you for showing up.",
    "✨ Gentle focus can be powerful. You did it.",
]


# ============================================================
# SUPABASE
# ============================================================
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
    """Never crash the app if Supabase is flaky."""
    if supabase is None:
        return False
    try:
        supabase.table("sessions").insert(payload).execute()
        return True
    except Exception as e:
        st.warning(f"Supabase insert failed (non-fatal): {e}")
        return False


def safe_fetch_sessions(limit: int = MEADOW_FETCH_LIMIT):
    """Fetch rows safely and return [] on failure."""
    if supabase is None:
        return []
    try:
        res = (
            supabase.table("sessions")
            .select("*")
            .order("timestamp", desc=True)
            .limit(limit)
            .execute()
        )
        return res.data or []
    except Exception as e:
        st.info(f"Supabase read failed (showing empty meadow): {e}")
        return []


# ============================================================
# IMAGE LOADING (Cloud-safe)
# ============================================================
def _safe_open_image(path: str) -> Optional[Image.Image]:
    """
    Load image bytes and detach from file handle (Cloud safe).
    Returns RGBA image or None.
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
    # Meadow background
    meadow = None
    for name in ["meadow_bg.png", "meadow_bg.PNG", "meadow_bg.Png"]:
        p = os.path.join("assets", name)
        if os.path.exists(p):
            meadow = _safe_open_image(p)
            if meadow is not None:
                break

    # Flower stages: flower_images[code][stage] where stage=1..4
    flower_images: Dict[str, Dict[int, Image.Image]] = {}
    for code in FLOWER_CODES:
        stages: Dict[int, Image.Image] = {}

        # Prefer stage images
        for stage in range(1, 5):
            p1 = os.path.join("assets", f"flower_{code}_stage{stage}.png")
            p2 = os.path.join("assets", f"flower_{code}_stage{stage}.PNG")
            path = p1 if os.path.exists(p1) else (p2 if os.path.exists(p2) else None)
            if path:
                im = _safe_open_image(path)
                if im is not None:
                    stages[stage] = im

        # Fallback to a single image (treat as stage 4)
        if not stages:
            p1 = os.path.join("assets", f"flower_{code}.png")
            p2 = os.path.join("assets", f"flower_{code}.PNG")
            path = p1 if os.path.exists(p1) else (p2 if os.path.exists(p2) else None)
            if path:
                im = _safe_open_image(path)
                if im is not None:
                    stages[4] = im

        flower_images[code] = stages

    return meadow, flower_images


def get_flower_stage(progress: float) -> int:
    if progress < 0.25:
        return 1
    if progress < 0.50:
        return 2
    if progress < 0.75:
        return 3
    return 4


meadow_img, flower_images = load_images()


# ============================================================
# USERNAME (Persist via URL query param)
# ============================================================
def _get_query_param(key: str) -> str:
    val = st.query_params.get(key, "")
    if isinstance(val, list):
        return val[0] if val else ""
    return val or ""


def _sync_name_to_url():
    name = (st.session_state.user_name or "").strip()
    if name:
        st.query_params["u"] = name
    else:
        try:
            del st.query_params["u"]
        except Exception:
            pass


# ============================================================
# SESSION STATE DEFAULTS
# ============================================================
def init_state():
    if "user_name" not in st.session_state:
        st.session_state.user_name = _get_query_param("u")

    if "session_active" not in st.session_state:
        st.session_state.session_active = False
    if "start_time" not in st.session_state:
        st.session_state.start_time = None
    if "elapsed_before_pause" not in st.session_state:
        st.session_state.elapsed_before_pause = 0.0  # keep for stability; no pause UI though
    if "flower_code" not in st.session_state:
        st.session_state.flower_code = "bluebell"

    # personal stats (local)
    if "completed_sessions" not in st.session_state:
        st.session_state.completed_sessions = 0
    if "total_focus_minutes" not in st.session_state:
        st.session_state.total_focus_minutes = 0

    # show-once congrats
    if "last_congrats" not in st.session_state:
        st.session_state.last_congrats = None
    if "congrats_index" not in st.session_state:
        st.session_state.congrats_index = 0


init_state()


# ============================================================
# CORE ACTIONS
# ============================================================
def start_session(selected_flower: str):
    st.session_state.session_active = True
    st.session_state.start_time = time.time()
    st.session_state.elapsed_before_pause = 0.0
    st.session_state.flower_code = selected_flower


def end_session(early: bool = False):
    """
    - Only insert into Supabase if completed full 25 minutes (not early).
    - Save user_name into Supabase (won't be NULL).
    """
    elapsed = 0
    if st.session_state.start_time:
        elapsed = int(st.session_state.elapsed_before_pause + (time.time() - st.session_state.start_time))
        if elapsed < 0:
            elapsed = 0

    completed = (not early) and (elapsed >= POMODORO_SECONDS - 2)

    # Reset session first (so UI returns to selection safely)
    st.session_state.session_active = False
    st.session_state.start_time = None
    st.session_state.elapsed_before_pause = 0.0

    if early:
        st.session_state.last_congrats = None
        st.info("🌱 Ended early — that’s okay. No flower added this time.")
        return

    # Completed
    st.session_state.completed_sessions += 1
    st.session_state.total_focus_minutes += POMODORO_MINUTES

    msg = CONGRATS_MESSAGES[st.session_state.congrats_index % len(CONGRATS_MESSAGES)]
    st.session_state.congrats_index += 1
    st.session_state.last_congrats = msg

    if completed:
        payload = {
            "flower": st.session_state.flower_code,
            "duration": elapsed,  # seconds
            "timestamp": int(time.time()),
            "user_name": ((st.session_state.user_name or "").strip() or "Anonymous"),
        }
        safe_insert_session(payload)


# ============================================================
# UI
# ============================================================
st.set_page_config(page_title="Collective Garden", page_icon="🌱", layout="centered")
st.title("🌱 Collective Garden")
st.caption("Grow your focus. Bloom together. A calm 25-minute focus app where your chosen flower grows as you stay present and completed blooms join a shared meadow.")


# Username input (lightweight)
st.text_input(
    "Your name / nickname (shows in your personal stats):",
    key="user_name",
    placeholder="e.g. FocusCapybara, SunnySmile",
    on_change=_sync_name_to_url,
)
if not (st.session_state.user_name or "").strip():
    st.info("Tip: enter a nickname so your personal stats stay consistent across refresh 🌿")


tab1, tab2 = st.tabs(["Focus Session", "Collective Meadow"])


# ============================================================
# TAB 1 — FOCUS SESSION
# ============================================================
with tab1:
    # show congrats after rerun (stable)
    if st.session_state.last_congrats:
        st.balloons()
        st.success(st.session_state.last_congrats)
        st.markdown(
            f"""
<div style="border-radius:16px;padding:16px 18px;border:1px solid #d8e4d8;background:#f5fbf5;">
  <b>🌿 Your mini progress</b><br>
  • Completed sessions (this device): <b>{st.session_state.completed_sessions}</b><br>
  • Focused minutes (this device): <b>{st.session_state.total_focus_minutes}</b><br>
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

        # Preview bloom (stage 4)
        stages = flower_images.get(selected_code, {})
        preview_img = stages.get(4) or (next(iter(stages.values())) if stages else None)
        if preview_img is not None:
            st.image(preview_img, width=240, caption=FLOWERS[selected_code]["label"])
        else:
            st.warning("Flower image not found for this type. Check your assets filenames.")

        st.markdown("### 2) Start a 25-minute focus session")
        if st.button("Start 25-minute session 🌼"):
            start_session(selected_code)
            st.rerun()

    else:
        selected_code = st.session_state.flower_code
        flower_def = FLOWERS[selected_code]

        # Auto-tick once per second (no manual refresh)
        if HAS_AUTOREFRESH:
            st_autorefresh(interval=1000, key="timer_tick")

        # elapsed
        elapsed = float(st.session_state.elapsed_before_pause) + (time.time() - st.session_state.start_time)
        remaining = max(POMODORO_SECONDS - elapsed, 0)
        progress = min(elapsed / POMODORO_SECONDS, 1.0)

        minutes_left = int(remaining // 60)
        seconds_left = int(remaining % 60)

        # stage image
        stage = get_flower_stage(progress)
        stages = flower_images.get(selected_code, {})
        img = stages.get(stage) or stages.get(4) or (next(iter(stages.values())) if stages else None)

        # optional size growth
        current_size = int(FLOWER_MIN_SIZE + (FLOWER_MAX_SIZE - FLOWER_MIN_SIZE) * progress)

        # tips every 5 minutes
        block_index = int(elapsed // BLOCK_SECONDS)
        tips_source = flower_def.get("tips") or GENERIC_TIPS
        tip_text = tips_source[block_index % len(tips_source)]

        st.subheader(f"{flower_def['label']} — 25-minute focus")
        st.markdown(f"### ⏳ {minutes_left:02d}:{seconds_left:02d}")
        st.progress(progress)

        if img is not None:
            st.image(img, width=current_size)

        st.markdown(f"**Intention:** {flower_def['intention']}")
        st.info(tip_text)

        c1, c2 = st.columns(2)
        with c1:
            if st.button("End session early"):
                end_session(early=True)
                st.rerun()
        with c2:
            # Manual fallback if autorefresh isn't installed (rare)
            if not HAS_AUTOREFRESH:
                if st.button("🔄 Refresh timer"):
                    st.rerun()

        # Auto-finish
        if remaining <= 0:
            end_session(early=False)
            st.rerun()


# ============================================================
# TAB 2 — COLLECTIVE MEADOW (Cloud-safe)
# ============================================================
with tab2:
    st.subheader("🌼 Collective Meadow — Shared Blossoms")

    # Lightweight auto-refresh for counts (safe)
    if HAS_AUTOREFRESH:
        st_autorefresh(interval=MEADOW_AUTOREFRESH_MS, key="meadow_counts_refresh")
        st.caption("🌍 Counts update every 30 seconds (rendering the meadow image is manual to stay Cloud-safe).")
    else:
        st.caption("Tip: refresh the page to update global counts.")

    # Fetch rows
    rows = safe_fetch_sessions(limit=MEADOW_FETCH_LIMIT)

    # Filter rows to only supported flowers (fixes “counted but not drawable”)
    filtered_rows = [r for r in rows if (r.get("flower") in VALID_CODES)]
    your_name = ((st.session_state.user_name or "").strip() or "Anonymous")

    def norm_name(x):
        return ((x or "").strip() or "Anonymous")

    your_rows = [r for r in filtered_rows if norm_name(r.get("user_name")) == your_name]

    st.markdown(
        f"""
**Your completed blooms ({your_name}):** {len(your_rows)}  
**Total collective blooms (supported flowers, last {MEADOW_FETCH_LIMIT}):** {len(filtered_rows)}
"""
    )

    # Counts by flower type
    counts = {code: 0 for code in FLOWER_CODES}
    for r in filtered_rows:
        code = r.get("flower")
        if code in counts:
            counts[code] += 1

    st.write("### Flower counts")
    for code in FLOWER_CODES:
        st.write(f"- **{FLOWERS[code]['label']}**: {counts[code]}")

    if meadow_img is None:
        st.warning("Meadow background is missing. Expected `assets/meadow_bg.png`.")
        st.stop()

    # Render button (heavy work only on click to prevent “Oh no” memory)
    if st.button("🌷 Render / Refresh meadow image"):
        base = meadow_img.convert("RGBA")
        W, H = base.size

        overlay = Image.new("RGBA", (W, H), (0, 0, 0, 0))

        # Deterministic scatter: stable positions based on row id/timestamp
        # So it doesn't jump around each render
        flower_size = 220
        max_x = max(0, W - flower_size)
        max_y = max(0, H - flower_size)
        y_min = int(H * 0.40)

        # Limit how many we draw (keeps memory safe)
        draw_rows = filtered_rows[:MEADOW_RENDER_LIMIT]

        pasted = 0
        for r in draw_rows:
            code = r.get("flower")
            if code not in VALID_CODES:
                continue

            stages = flower_images.get(code, {})
            bloom = stages.get(4) or (next(iter(stages.values())) if stages else None)
            if bloom is None:
                continue

            bloom_rgba = bloom.convert("RGBA").resize((flower_size, flower_size))

            seed = str(r.get("id") or r.get("timestamp") or pasted)
            rng = random.Random(seed)

            x = rng.randint(0, max_x) if max_x > 0 else 0
            y = rng.randint(y_min, max_y) if max_y >= y_min else y_min

            overlay.alpha_composite(bloom_rgba, dest=(x, y))
            pasted += 1

        combined_rgba = Image.alpha_composite(base, overlay)

        # Flatten to RGB to avoid black background
        combined_rgb = Image.new("RGB", combined_rgba.size, (255, 255, 255))
        combined_rgb.paste(combined_rgba, mask=combined_rgba.split()[-1])

        st.image(
            combined_rgb,
            width="stretch",
            caption=f"🌍 Global Meadow ({pasted} blooms drawn, showing up to {MEADOW_RENDER_LIMIT})",
        )

        if not filtered_rows:
            st.info("The meadow is still empty 🌱 Finish a full 25-minute session to plant the first bloom.")
    else:
        st.info("Click **Render / Refresh meadow image** to draw blooms on the meadow (keeps Cloud memory stable).")
