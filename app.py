import streamlit as st
import time
import pandas as pd
import random
import os
import base64
from PIL import Image, ImageOps, ImageEnhance
from streamlit_gsheets import GSheetsConnection
from streamlit_image_coordinates import streamlit_image_coordinates

st.set_page_config(page_title="DETROIT: Anomaly [09]", layout="centered", initial_sidebar_state="collapsed")

# --- SETTINGS ---
GAME_WIDTH = 700
HIT_TOLERANCE = 0  # HARDCORE: Must click exactly ON the glitch pixels.
ORIGINAL_IMG_SIZE = 1024 # Assumed size of source images for coordinate math
GLITCH_SIZE = 120 # How big (in pixels) the random glitch square will be

# --- HELPER: ASSET LOADER ---
def get_base64(bin_file):
    try:
        with open(bin_file, 'rb') as f: return base64.b64encode(f.read()).decode()
    except: return None

# --- CSS: RETRO EFFECTS ---
def inject_css():
    st.markdown("""
    <style>
        .stApp { background-color: #080808; color: #d0d0d0; font-family: 'Courier New', monospace; }
        #MainMenu, footer, header {visibility: hidden;}
        .block-container { justify-content: center; align-items: center; display: flex; flex-direction: column; }
        .stApp::after {
            content: " "; display: block; position: fixed; top: 0; left: 0; bottom: 0; right: 0;
            background: linear-gradient(rgba(18, 16, 16, 0) 50%, rgba(0, 0, 0, 0.25) 50%), linear-gradient(90deg, rgba(255, 0, 0, 0.06), rgba(0, 255, 0, 0.02), rgba(0, 0, 255, 0.06));
            z-index: 999; background-size: 100% 3px, 3px 100%; pointer-events: none; opacity: 0.15;
        }
        h1 { animation: glitch-text 500ms infinite; }
        @keyframes glitch-text {
            0% { text-shadow: 0.05em 0 0 rgba(255,0,0,0.75), -0.05em -0.025em 0 rgba(0,255,0,0.75), 0.025em 0.05em 0 rgba(0,0,255,0.75); }
            14% { text-shadow: 0.05em 0 0 rgba(255,0,0,0.75), -0.05em -0.025em 0 rgba(0,255,0,0.75), 0.025em 0.05em 0 rgba(0,0,255,0.75); }
            15% { text-shadow: -0.05em -0.025em 0 rgba(255,0,0,0.75), 0.025em 0.025em 0 rgba(0,255,0,0.75), -0.05em -0.05em 0 rgba(0,0,255,0.75); }
            49% { text-shadow: -0.05em -0.025em 0 rgba(255,0,0,0.75), 0.025em 0.025em 0 rgba(0,255,0,0.75), -0.05em -0.05em 0 rgba(0,0,255,0.75); }
            50% { text-shadow: 0.025em 0.05em 0 rgba(255,0,0,0.75), 0.05em 0 0 rgba(0,255,0,0.75), 0 -0.05em 0 rgba(0,0,255,0.75); }
            99% { text-shadow: 0.025em 0.05em 0 rgba(255,0,0,0.75), 0.05em 0 0 rgba(0,255,0,0.75), 0 -0.05em 0 rgba(0,0,255,0.75); }
            100% { text-shadow: -0.025em 0 0 rgba(255,0,0,0.75), -0.025em -0.025em 0 rgba(0,255,0,0.75), -0.025em -0.05em 0 rgba(0,0,255,0.75); }
        }
    </style>
    """, unsafe_allow_html=True)

# --- TRANSITION ---
def trigger_static_transition():
    st.markdown('<audio src="https://www.myinstants.com/media/sounds/static-noise.mp3" autoplay style="display:none;"></audio>', unsafe_allow_html=True)
    placeholder = st.empty()
    with placeholder.container():
        st.markdown('<div style="position:fixed;top:0;left:0;width:100%;height:100%;background-color:#111;z-index:10000;"></div>', unsafe_allow_html=True)
        time.sleep(0.1)
        gb64 = get_base64("assets/glitch.gif")
        if not gb64: gb64 = get_base64("assets/glitch.avif")
        g_url = f"data:image/gif;base64,{gb64}" if gb64 else "https://media.giphy.com/media/oEI9uBYSzLpBK/giphy.gif"
        st.markdown(f'<div style="position:fixed;top:0;left:0;width:100%;height:100%;background:url({g_url});background-size:cover;z-index:10001;opacity:0.8;mix-blend-mode:hard-light;"></div>', unsafe_allow_html=True)
        time.sleep(0.4)
    placeholder.empty()

# --- CHAOS GENERATOR ---
def create_chaos_frame(base_crop):
    frame = ImageEnhance.Contrast(base_crop).enhance(2.0)
    w, h = frame.size
    for _ in range(random.randint(3, 6)):
        bx1 = random.randint(0, w); by1 = random.randint(0, h)
        bx2 = bx1 + random.randint(10, max(20, w//2)); by2 = by1 + random.randint(5, max(10, h//4))
        try:
            box = (max(0, bx1), max(0, by1), min(w, bx2), min(h, by2))
            frame.paste(ImageOps.invert(frame.crop(box).convert('RGB')), box)
        except: pass
    return frame

@st.cache_data(show_spinner=False, persist="disk")
def generate_scaled_gif(img_path, original_box, target_width, level_idx, unique_run_id):
    # unique_run_id ensures GIFs regenerate when a new game starts
    try:
        base_img = Image.open(img_path).convert("RGB")
        scale_factor = target_width / base_img.width
        target_height = int(base_img.height * scale_factor)
        base_img = base_img.resize((target_width, target_height), Image.Resampling.LANCZOS)
        x1, y1, x2, y2 = original_box
        scaled_box = (int(x1 * scale_factor), int(y1 * scale_factor), int(x2 * scale_factor), int(y2 * scale_factor))
        frames = []
        base_crop = base_img.crop(scaled_box)
        for _ in range(15): frames.append(base_img.copy())
        for _ in range(6):
            frame = base_img.copy()
            frame.paste(create_chaos_frame(base_crop), scaled_box)
            frames.append(frame)
        
        # Filename includes run_id to force fresh generation on new games
        temp_file = f"level_{level_idx}_{unique_run_id}.gif"
        frames[0].save(temp_file, format="GIF", save_all=True, append_images=frames[1:], duration=[200]*15 + [60]*6, loop=0)
        return temp_file, scaled_box
    except: return None, None

# --- GAME DATA & RANDOMIZER ---
BASE_LEVELS = [
    "assets/level1.png", "assets/level2.png", "assets/level3.png",
    "assets/level4.png", "assets/level5.png", "assets/level6.png",
    "assets/level7.png", "assets/level8.png", "assets/level9.png"
]

def randomize_glitches():
    # Generates completely new glitch coordinates for all 9 levels
    new_levels = []
    for img_path in BASE_LEVELS:
        # Pick random coordinates within the 1024x1024 space, keeping away from extreme edges
        gx = random.randint(50, ORIGINAL_IMG_SIZE - GLITCH_SIZE - 50)
        gy = random.randint(50, ORIGINAL_IMG_SIZE - GLITCH_SIZE - 50)
        new_levels.append({
            "img": img_path,
            "glitch_box": (gx, gy, gx + GLITCH_SIZE, gy + GLITCH_SIZE)
        })
    return new_levels

# --- INIT ---
inject_css()
if 'game_state' not in st.session_state:
    st.session_state.update({
        'game_state': 'menu',
        'current_level': 0,
        'start_time': 0.0,
        'player_tag': 'UNK',
        'final_time': 0.0,
        'run_id': int(time.time()), # Unique ID for this playthrough
        'levels': randomize_glitches() # Initial random set
    })

conn = None
try: conn = st.connection("gsheets", type=GSheetsConnection)
except: pass

def save_score(tag, time_val):
    if conn:
        try: conn.update(worksheet="Scores", data=pd.DataFrame([{"Tag": tag, "Time": time_val}])); return True
        except: return False
    return False

def get_leaderboard():
    if conn:
        try:
            df = conn.read(worksheet="Scores", ttl=0).dropna(how="all")
            df['Time'] = pd.to_numeric(df['Time'], errors='coerce').dropna()
            return df.sort_values('Time').head(10).reset_index(drop=True)
        except: pass
    return pd.DataFrame(columns=["Rank", "Tag", "Time (Offline)"])

# --- GAME LOOP ---
st.title("DETROIT: ANOMALY [09]")

if st.session_state.game_state == "menu":
    tag = st.text_input("OPERATIVE TAG (3 CHARS):", max_chars=3).upper()
    if st.button(">> START NEW SIMULATION <<", type="primary"):
        if len(tag) == 3:
            # FULL RESET: New random locations, new run ID
            st.session_state.update({
                'game_state': 'playing',
                'player_tag': tag,
                'start_time': time.time(),
                'current_level': 0,
                'run_id': int(time.time()),
                'levels': randomize_glitches()
            })
            st.rerun()
    st.markdown("### TOP AGENTS")
    st.dataframe(get_leaderboard(), hide_index=True, use_container_width=True)

elif st.session_state.game_state == "playing":
    lvl_idx = st.session_state.current_level
    data = st.session_state.levels[lvl_idx] # Use session state levels, not a global constant
    st.write(f"SECTOR 0{lvl_idx + 1} / 09")

    # Generate fresh GIF for this specific run
    gif_path, scaled_box = generate_scaled_gif(data["img"], data["glitch_box"], GAME_WIDTH, lvl_idx, st.session_state.run_id)

    if gif_path and scaled_box:
        coords = streamlit_image_coordinates(gif_path, key=f"lvl_{lvl_idx}_{st.session_state.run_id}", width=GAME_WIDTH)
        if coords:
            x1, y1, x2, y2 = scaled_box
            # EXACT HIT CHECK (with tiny tolerance)
            if (x1 - HIT_TOLERANCE) <= coords['x'] <= (x2 + HIT_TOLERANCE) and \
               (y1 - HIT_TOLERANCE) <= coords['y'] <= (y2 + HIT_TOLERANCE):
                trigger_static_transition()
                if lvl_idx < 8: 
                    st.session_state.current_level += 1
                    st.rerun()
                else: 
                    st.session_state.final_time = time.time() - st.session_state.start_time
                    st.session_state.game_state = 'game_over'
                    st.rerun()

elif st.session_state.game_state == "game_over":
    st.balloons()
    st.write(f"AGENT: {st.session_state.player_tag} | TIME: {st.session_state.final_time:.2f}s")
    if st.button("UPLOAD SCORE", type="primary"):
        if save_score(st.session_state.player_tag, st.session_state.final_time):
            st.success("DATA UPLOADED.")
        else:
            st.error("UPLOAD FAILED.")
        time.sleep(2); st.session_state.game_state = 'menu'; st.rerun()
    st.markdown("### GLOBAL RANKINGS")
    st.dataframe(get_leaderboard(), hide_index=True, use_container_width=True)