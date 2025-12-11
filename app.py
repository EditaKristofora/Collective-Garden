import streamlit as st
from PIL import Image
import time
import os

# -------------------------------
# CONFIG
# -------------------------------
POMODORO_MINUTES = 25
POMODORO_SECONDS = POMODORO_MINUTES * 60

FLOWER_MIN_SIZE = 120
FLOWER_MAX_SIZE = 280
BLOCK_SECONDS = 5 * 60

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

FLOWER_CODES = list(FLOWERS.keys())


# -------------------------------
# IMAGE LOADING
# -------------------------------
@st.cache_resource
def load_images():
    images = {}
    meadow_path = os.path.join("assets", "meadow_bg.png")
    meadow_img = Image.open(meadow_path) if os.path.exists(meadow_path) else None

    for code in FLOWER_CODES:
        path = os.path.join("assets", f"flower_{code}.png")
        images[code] = Image.open(path) if os.path.exists(path) else None

    return meadow_img, images


meadow_img, flower_images = load_images()


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
st.set_page_config(
    page_title="Collective Garden",
    page_icon="🌱",
    layout="centered"
)

st.title("🌱 Collective Garden")
st.caption(
    "Grow your focus, Bloom together. A calm 25-minute focus app where your chosen flower grows as you stay present with your work."
)


def start_session(selected_flower: str):
    st.session_state.session_active = True
    st.session_state.start_time = time.time()
    st.session_state.flower_code = selected_flower


def end_session(early=False):
    st.session_state.session_active = False
    st.session_state.start_time = None
    if early:
        st.success("You ended the session. Even short moments of focus still count as growth 💚")
    else:
        st.success("Your flower is in full bloom. Thank you for giving yourself this time 🌸")


# -------------------------------
# HOME / SELECTION
# -------------------------------
if not st.session_state.session_active:
    st.subheader("1. Choose your flower (intention)")

    selected_code = st.selectbox(
        "Which flower matches your focus mood today?",
        options=FLOWER_CODES,
        format_func=lambda c: FLOWERS[c]["label"]
    )

    flower_def = FLOWERS[selected_code]
    st.write(f"**Intention:** {flower_def['intention']}")

    img = flower_images.get(selected_code)
    if img:
        st.image(img, width=180, caption=FLOWERS[selected_code]["label"])

    st.markdown("### 2. Start a 25-minute focus session")

    if st.button("Start 25-minute session 🌼"):
        start_session(selected_code)
        st.rerun()

# -------------------------------
# ACTIVE SESSION
# -------------------------------
else:
    selected_code = st.session_state.flower_code
    flower_def = FLOWERS[selected_code]
    img = flower_images.get(selected_code)

    elapsed = time.time() - st.session_state.start_time
    remaining = max(POMODORO_SECONDS - elapsed, 0)
    progress = min(elapsed / POMODORO_SECONDS, 1.0)

    minutes_left = int(remaining // 60)
    seconds_left = int(remaining % 60)

    current_size = int(
        FLOWER_MIN_SIZE + (FLOWER_MAX_SIZE - FLOWER_MIN_SIZE) * progress
    )

    phases = [
        "Your flower is just waking up.",
        "Roots are forming quietly beneath the surface.",
        "Your flower is opening gently.",
        "Your focus is in soft, steady bloom.",
        "Your flower is glowing with your attention."
    ]
    phase_index = min(int(progress * len(phases)), len(phases) - 1)
    phase_text = phases[phase_index]

    block_index = int(elapsed // BLOCK_SECONDS)
    tips_source = flower_def.get("tips") or GENERIC_TIPS
    tip_text = tips_source[block_index % len(tips_source)]

    st.subheader(f"{flower_def['label']} – 25-minute focus")

    if meadow_img:
        st.image(meadow_img)

    st.markdown(
        f"### ⏳ {minutes_left:02d}:{seconds_left:02d} "
        f"(total {POMODORO_MINUTES} min)"
    )
    st.progress(progress)

    if img:
        st.image(img, width=current_size)
    st.caption(phase_text)

    st.markdown(f"**Intention:** {flower_def['intention']}")
    st.info(tip_text)

    col1, col2 = st.columns(2)
    with col1:
        if st.button("End session early"):
            end_session(early=True)
            st.rerun()
    with col2:
        if remaining <= 0:
            end_session(early=False)
            st.balloons()
            st.rerun()
        else:
            time.sleep(1)
            st.rerun()






