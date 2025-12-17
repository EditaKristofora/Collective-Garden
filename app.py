import os
import time
import random
import traceback
from io import BytesIO

import streamlit as st
import streamlit.components.v1 as components
from PIL import Image
from supabase import create_client

# ======================================================
# PAGE CONFIG (must be before other Streamlit UI calls)
# ======================================================
st.set_page_config(page_title="Collective Garden", page_icon="🌱", layout="centered")

# ======================================================
# OPTIONAL AUTOREFRESH (heartbeat only)
# ======================================================
try:
    from streamlit_autorefresh import st_autorefresh
    HAS_AUTOREFRESH = True
except Exception:
    HAS_AUTOREFRESH = False

# ======================================================
# CONFIG
# ======================================================
POMODORO_MINUTES = 25
POMODORO_SECONDS = POMODORO_MINUTES * 60
BLOCK_SECONDS = 5 * 60  # new tip every 5 minutes

FLOWER_MIN_SIZE = 120
FLOWER_MAX_SIZE = 280

# ======================================================
# FLOWERS + TIPS/FUN FACTS
# ======================================================
FLOWERS = {
    "bluebell": {
        "label": "Bluebell – Calm Focus",
        "intention": "Gentle, steady focus that feels quiet and grounded.",
        "tips": [
            "Bluebells often grow in quiet forests — your mind can be a quiet forest too.",
            "Relax your shoulders and jaw. Calm focus lives in a relaxed body.",
            "If your mind wanders, gently bring it back — like guiding a soft bell sound.",
            "Small calm sessions help your nervous system feel safer over time.",
            "Slow focus is still real progress.",
        ],
    },
    "blossom": {
        "label": "Blossom – Creativity",
        "intention": "Playful, open focus for creating and experimenting.",
        "tips": [
            "Creativity thrives in imperfect drafts — keep it messy for now.",
            "Let ideas come without judging them. Editing comes later.",
            "One tiny step today is still creative momentum.",
            "Sip water / stretch lightly to reset your creative energy.",
            "Your imagination is a garden — showing up is watering it.",
        ],
    },
    "sunflower": {
        "label": "Sunflower – Confidence",
        "intention": "Showing up bravely and backing your own ideas.",
        "tips": [
            "Sunflowers turn toward the sun — turn toward what supports you.",
            "Confidence can be quiet: choosing to continue is already brave.",
            "You don’t need to feel ready to take a small step.",
            "Breathe out longer than you breathe in — it calms the body.",
            "Your work matters even if nobody sees it today.",
        ],
    },
    "lavender": {
        "label": "Lavender – Peace",
        "intention": "Soft, peaceful focus that protects your energy.",
        "tips": [
            "Let this session be gentle — soft focus counts.",
            "Notice one place in your body you can soften.",
            "You’re allowed to move slowly and still call it progress.",
            "Rest isn’t something you must earn. You deserve it.",
            "Peace is a practice — one calm minute at a time.",
        ],
    },
    "daisy": {
        "label": "Daisy – Fresh Start",
        "intention": "Starting again, even if yesterday was messy.",
        "tips": [
            "You can start fresh at any time of day.",
            "Tiny steps are kinder and more sustainable than big pushes.",
            "Restarting is not failure — it’s resilience.",
            "Lower the bar. Begin with the smallest next action.",
            "Progress is made by returning, not by never drifting.",
        ],
    },
    "tulip": {
        "label": "Tulip – Growth",
        "intention": "Long-term learning, practice, and gentle progress.",
        "tips": [
            "Tulips grow unseen for a long time — like skills.",
            "Repeating is how your brain builds pathways.",
            "Growth can be gentle. Adjust the pace, keep the habit.",
            "You don’t need to see progress daily for it to be happening.",
            "Think in seasons, not minutes — you’re building something real.",
        ],
    },
}
FLOWER_CODES = list(FLOWERS.keys())

GENERIC_TIPS = [
    "Check your breath: in through the nose, out through the mouth.",
    "Soften your forehead. Drop your shoulders.",
    "One task. One tiny step. That’s enough.",
    "A calm mind learns faster than a stressed mind.",
    "Return gently — no guilt needed.",
]

CONGRATS_MESSAGES = [
    "🌸 You completed the full 25 minutes — your flower has fully bloomed. Beautiful work.",
    "🌼 One calm session at a time — your focus added a new bloom to the garden.",
    "🌿 You stayed with your attention for 25 minutes. That’s real growth.",
    "🌷 Your flower joined the Collective Meadow. Thank you for showing up.",
    "✨ Progress doesn’t need to be loud to be real — well done.",
]

# ======================================================
# SUPABASE
# ======================================================
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

# ======================================================
# IMAGES (Cloud-safe load)
# ======================================================
def _safe_open_image(path: str):
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
    meadow = _safe_open_image(os.path.join("assets", "meadow_bg.png"))

    # flower_images[code][stage] where stage=1..4
    flower_images = {}
    for code in FLOWER_CODES:
        stages = {}
        for stage in range(1, 5):
            p1 = os.path.join("assets", f"flower_{code}_stage{stage}.png")
            p2 = os.path.join("assets", f"flower_{code}_stage{stage}.PNG")
            path = p1 if os.path.exists(p1) else (p2 if os.path.exists(p2) else None)
            if path:
                img = _safe_open_image(path)
                if img is not None:
                    stages[stage] = img

        # fallback to single image as stage4
        if not stages:
            p1 = os.path.join("assets", f"flower_{code}.png")
            p2 = os.path.join("assets", f"flower_{code}.PNG")
            path = p1 if os.path.exists(p1) else (p2 if os.path.exists(p2) else None)
            if path:
                img = _safe_open_image(path)
                if img is not None:
                    stages[4] = img

        flower_images[code] = stages

    return meadow, flower_images

meadow_img, flower_images = load_images()

def get_flower_stage(progress: float) -> int:
    if progress < 0.25:
        return 1
    elif progress < 0.50:
        return 2
    elif progress < 0.75:
        return 3
    else:
        return 4

# ======================================================
# USER NAME (persist via URL)
# ======================================================
def _get_query_param(key: str) -> str:
    v = st.query_params.get(key, "")
    if isinstance(v, list):
        return v[0] if v else ""
    return v or ""

if "user_name" not in st.session_state:
    st.session_state.user_name = _get_query_param("u")

def _sync_name_to_url():
    name = (st.session_state.user_name or "").strip()
    if name:
        st.query_params["u"] = name

# ======================================================
# SESSION STATE DEFAULTS
# ======================================================
st.session_state.setdefault("session_active", False)
st.session_state.setdefault("flower_code", "bluebell")
st.session_state.setdefault("start_time", None)

st.session_state.setdefault("paused", False)
st.session_state.setdefault("elapsed_before_pause", 0.0)

st.session_state.setdefault("completed_sessions", 0)
st.session_state.setdefault("total_focus_minutes", 0)
st.session_state.setdefault("congrats_index", 0)
st.session_state.setdefault("last_congrats", None)

# ======================================================
# APP (wrapped to show traceback instead of silent "Oh no")
# ======================================================
try:
    st.title("🌱 Collective Garden")
    st.caption("Grow your focus. Bloom together.")

    st.text_input(
        "Your name / nickname:",
        key="user_name",
        placeholder="e.g. FocusFox, SunnyCoder",
        on_change=_sync_name_to_url,
    )

    tab1, tab2 = st.tabs(["Focus Session", "Collective Meadow"])

    # ------------------------------------------------------
    # Helpers
    # ------------------------------------------------------
    def start_session(selected_code: str):
        st.session_state.session_active = True
        st.session_state.flower_code = selected_code
        st.session_state.start_time = time.time()
        st.session_state.paused = False
        st.session_state.elapsed_before_pause = 0.0

    def end_session(early: bool):
        # pause-aware elapsed
        if st.session_state.start_time is None:
            elapsed = 0
        elif st.session_state.paused:
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
            st.session_state.completed_sessions += 1
            st.session_state.total_focus_minutes += POMODORO_MINUTES

            msg = CONGRATS_MESSAGES[st.session_state.congrats_index % len(CONGRATS_MESSAGES)]
            st.session_state.congrats_index += 1
            st.session_state.last_congrats = msg

            payload = {
                "flower": st.session_state.flower_code,
                "duration": elapsed,
                "timestamp": int(time.time()),
                "user_name": (st.session_state.user_name or "Anonymous").strip() or "Anonymous",
            }
            safe_insert_session(payload)
        else:
            st.session_state.last_congrats = None

    # ======================================================
    # TAB 1 — FOCUS SESSION
    # ======================================================
    with tab1:
        # Show congrats after rerun
        if st.session_state.last_congrats:
            st.balloons()
            st.success(st.session_state.last_congrats)
            st.markdown(
                f"""
<div style="border-radius:16px;padding:16px 18px;border:1px solid #d8e4d8;background:#f5fbf5;">
  <b>🌿 Your mini progress</b><br>
  • Completed sessions: <b>{st.session_state.completed_sessions}</b><br>
  • Focused minutes: <b>{st.session_state.total_focus_minutes}</b>
</div>
""",
                unsafe_allow_html=True,
            )
            st.session_state.last_congrats = None

        # NOT ACTIVE
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

            preview = flower_images.get(selected_code, {}).get(4)
            if preview is not None:
                st.image(preview, width=220, caption=FLOWERS[selected_code]["label"])

            st.markdown("### 2) Start a 25-minute focus session")
            if st.button("Start 25-minute session 🌼"):
                start_session(selected_code)
                st.rerun()

        # ACTIVE SESSION
        else:
            # ✅ Streamlit heartbeat every 10s only (safe)
            # Timer display itself is client-side JS (per-second)
            if HAS_AUTOREFRESH and not st.session_state.paused:
                st_autorefresh(interval=10_000, key="timer_heartbeat_10s")

            selected_code = st.session_state.flower_code
            flower_def = FLOWERS[selected_code]

            # elapsed (pause-aware)
            if st.session_state.paused:
                elapsed = float(st.session_state.elapsed_before_pause)
            else:
                elapsed = float(st.session_state.elapsed_before_pause) + (time.time() - st.session_state.start_time)

            remaining = max(POMODORO_SECONDS - elapsed, 0)
            progress = min(elapsed / POMODORO_SECONDS, 1.0)

            # stage image
            stage = get_flower_stage(progress)
            stages = flower_images.get(selected_code, {})
            img = stages.get(stage) or stages.get(4) or (next(iter(stages.values())) if stages else None)

            current_size = int(FLOWER_MIN_SIZE + (FLOWER_MAX_SIZE - FLOWER_MIN_SIZE) * progress)

            # tip every 5 minutes
            block_index = int(elapsed // BLOCK_SECONDS)
            tips_source = flower_def.get("tips") or GENERIC_TIPS
            tip_text = tips_source[block_index % len(tips_source)]

            st.subheader(f"{flower_def['label']} — 25-minute focus")

            # ✅ JS countdown (updates every second without Streamlit rerun)
            if not st.session_state.paused:
                total_seconds = int(remaining)
                components.html(
                    f"""
                    <div style="font-size:34px;font-weight:700;margin:6px 0 10px 0;">
                      ⏳ <span id="t"></span>
                    </div>
                    <script>
                      let s = {total_seconds};
                      const el = document.getElementById("t");
                      function fmt(x){{
                        const m = String(Math.floor(x/60)).padStart(2,'0');
                        const ss = String(x%60).padStart(2,'0');
                        return m + ":" + ss;
                      }}
                      el.textContent = fmt(s);
                      const it = setInterval(() => {{
                        s -= 1;
                        if (s < 0) {{
                          clearInterval(it);
                          return;
                        }}
                        el.textContent = fmt(s);
                      }}, 1000);
                    </script>
                    """,
                    height=60,
                )
            else:
                mins = int(remaining // 60)
                secs = int(remaining % 60)
                st.markdown(f"## ⏳ {mins:02d}:{secs:02d}")

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
                st.write("")

            # completion check (runs on heartbeat)
            if (not st.session_state.paused) and remaining <= 0:
                end_session(early=False)
                st.rerun()

    # ======================================================
    # TAB 2 — COLLECTIVE MEADOW
    # ======================================================
    with tab2:
        st.subheader("🌼 Collective Meadow — Shared Blossoms")

        # ✅ Prevent Cloud crashes: do nothing heavy during a running session
        if st.session_state.session_active:
            st.info("🌱 Meadow pauses while your focus session is running (keeps the timer stable).")
            st.stop()

        if meadow_img is None:
            st.error("Meadow background missing: assets/meadow_bg.png")
            st.stop()

        @st.cache_data(ttl=15)
        def fetch_rows():
            if supabase is None:
                return []
            try:
                return (
                    supabase.table("sessions")
                    .select("*")
                    .order("timestamp", desc=True)
                    .limit(250)
                    .execute()
                    .data
                    or []
                )
            except Exception as e:
                st.info(f"Supabase read failed (showing empty meadow): {e}")
                return []

        rows = fetch_rows()

        user_name = (st.session_state.user_name or "Anonymous").strip() or "Anonymous"
        def norm_name(x): return (x or "Anonymous").strip() or "Anonymous"
        your_rows = [r for r in rows if norm_name(r.get("user_name")) == user_name]

        st.markdown(
            f"**Your completed blooms ({user_name}):** {len(your_rows)}  \n"
            f"**Total collective blooms (last 250):** {len(rows)}"
        )

        if st.button("🌷 Load / Refresh meadow"):
            base = meadow_img.convert("RGBA")
            W, H = base.size
            overlay = Image.new("RGBA", (W, H), (0, 0, 0, 0))
            rng = random.Random(42)

            flower_size = 220
            max_x = max(0, W - flower_size)
            max_y = max(0, H - flower_size)
            y_min = int(H * 0.40)

            pasted = 0
            for r in rows:
                code = r.get("flower")
                bloom = flower_images.get(code, {}).get(4)
                if bloom is None:
                    continue

                bloom_rgba = bloom.convert("RGBA").resize((flower_size, flower_size))

                x = rng.randint(0, max_x) if max_x > 0 else 0
                y = rng.randint(y_min, max_y) if max_y >= y_min else y_min

                overlay.alpha_composite(bloom_rgba, dest=(x, y))
                pasted += 1

            combined_rgba = Image.alpha_composite(base, overlay)

            # flatten alpha to avoid black background
            combined_rgb = Image.new("RGB", combined_rgba.size, (255, 255, 255))
            combined_rgb.paste(combined_rgba, mask=combined_rgba.split()[-1])

            st.image(combined_rgb, width="stretch", caption=f"🌍 Global Meadow ({pasted} blooms drawn)")
        else:
            st.caption("Click **Load / Refresh meadow** to render the global meadow image.")

except Exception:
    st.error("App crashed — traceback below (copy/paste this to fix fast):")
    st.code(traceback.format_exc())
    st.stop()
