import streamlit as st
import time
import pandas as pd
import random
import os
import base64
import shutil
from PIL import Image, ImageOps, ImageEnhance, ImageDraw
from streamlit_gsheets import GSheetsConnection
from streamlit_image_coordinates import streamlit_image_coordinates

st.set_page_config(page_title="DETROIT: ANOMALY [09]", layout="centered", initial_sidebar_state="collapsed")

# --- SETTINGS ---
GAME_WIDTH = 700
MOVE_DELAY = 5.0
HIT_TOLERANCE = 50 # Giving a little bit of padding since it moves fast

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
    </style>
    """, unsafe_allow_html=True)

# --- TRANSITION EFFECT ---
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

# --- CORE: ANIMATED GIF GENERATOR ---
def create_glitch_frame(base_img, x, y, w, h, intensity):
    # Creates one frame where the target area is messed up
    frame = base_img.copy()
    box = (int(x), int(y), int(x+w), int(y+h))
    
    try:
        # 1. Grab the area
        glitch = frame.crop(box).convert('RGB')
        
        # 2. Apply random violent effects based on intensity
        if intensity > 0.5:
            glitch = ImageOps.invert(glitch)
        
        # 3. Random color shifts
        r, g, b = glitch.split()
        if random.random() > 0.5: glitch = Image.merge("RGB", (b, g, r))
        else: glitch = Image.merge("RGB", (r, b, g))
            
        # 4. Paste back
        frame.paste(glitch, box)
        
        # 5. Add a bright border for 1 frame to make it "pop"
        if intensity > 0.8:
            draw = ImageDraw.Draw(frame)
            draw.rectangle(box, outline="#00ff00", width=4)
            
    except: pass
    return frame

@st.cache_data(show_spinner=False, persist="disk")
def generate_active_gif(img_path, x, y, w, h, move_timestamp):
    # move_timestamp ensures we get a NEW gif every time it moves
    try:
        base_img = Image.open(img_path).convert("RGB")
        frames = []
        
        # Create 10 frames of pure chaos (approx 1 second loop, repeats)
        for _ in range(10):
            intensity = random.random() # Random intensity per frame
            frames.append(create_glitch_frame(base_img, x, y, w, h, intensity))
            
        # Save to a real file so Streamlit can read it easily
        temp_file = f"temp_{int(move_timestamp)}.gif"
        # 80ms per frame = fast, violent flashing
        frames[0].save(temp_file, format="GIF", save_all=True, append_images=frames[1:], duration=80, loop=0)
        return temp_file
    except: return None

# --- GAME DATA ---
LEVELS = [
    {"img": "assets/level1.png", "spots": [(300, 300), (500, 500), (700, 300)]},
    {"img": "assets/level2.png", "spots": [(200, 800), (800, 200), (500, 500)]},
    {"img": "assets/level3.png", "spots": [(600, 200), (200, 600), (800, 800)]},
    {"img": "assets/level4.png", "spots": [(350, 350), (700, 700), (150, 850)]},
    {"img": "assets/level5.png", "spots": [(512, 100), (512, 900), (100, 512)]},
    {"img": "assets/level6.png", "spots": [(250, 250), (750, 250), (512, 750)]},
    {"img": "assets/level7.png", "spots": [(150, 150), (850, 850), (512, 512)]},
    {"img": "assets/level8.png", "spots": [(600, 600), (700, 300), (300, 700)]},
    {"img": "assets/level9.png", "spots": [(512, 512), (512, 200), (200, 512)]},
]

# --- INIT ---
inject_css()
if 'game_state' not in st.session_state:
    st.session_state.update({'game_state': 'menu', 'current_level': 0, 'start_time': 0.0, 'player_tag': 'UNK', 'last_move_time': time.time(), 'gx':0, 'gy':0, 'gw':0, 'gh':0})

try: conn = st.connection("gsheets", type=GSheetsConnection)
except: pass

def save_score(tag, time_val):
    try: conn.update(worksheet="Scores", data=pd.DataFrame([{"Tag": tag, "Time": time_val}])); return True
    except: return False

def get_leaderboard():
    try:
        df = conn.read(worksheet="Scores", ttl=0).dropna(how="all")
        df['Time'] = pd.to_numeric(df['Time'], errors='coerce').dropna()
        return df.sort_values('Time').head(10).reset_index(drop=True)
    except: return pd.DataFrame(columns=["Rank", "Tag", "Time"])

def move_glitch(level_idx):
    spots = LEVELS[level_idx]["spots"]
    cx, cy = random.choice(spots)
    st.session_state.gw = random.randint(100, 200)
    st.session_state.gh = random.randint(100, 200)
    st.session_state.gx = max(0, cx - st.session_state.gw // 2)
    st.session_state.gy = max(0, cy - st.session_state.gh // 2)
    st.session_state.last_move_time = time.time()

# --- GAME LOOP ---
st.title("DETROIT: ANOMALY [09]")

# Auto-move timer check (happens on every interaction)
if st.session_state.game_state == 'playing':
    if time.time() - st.session_state.last_move_time > MOVE_DELAY:
        move_glitch(st.session_state.current_level)
        st.rerun()

if st.session_state.game_state == "menu":
    tag = st.text_input("OPERATIVE TAG (3 CHARS):", max_chars=3).upper()
    if st.button(">> START <<", type="primary"):
        if len(tag) == 3:
            move_glitch(0)
            st.session_state.update({'game_state': 'playing', 'player_tag': tag, 'start_time': time.time(), 'current_level': 0})
            st.rerun()
    st.dataframe(get_leaderboard(), hide_index=True)

elif st.session_state.game_state == "playing":
    lvl_idx = st.session_state.current_level
    st.write(f"SECTOR 0{lvl_idx + 1} / 09")

    # Generate the animated GIF for this specific glitch position
    gif_path = generate_active_gif(
        LEVELS[lvl_idx]["img"], 
        st.session_state.gx, st.session_state.gy, 
        st.session_state.gw, st.session_state.gh,
        st.session_state.last_move_time
    )

    if gif_path:
        # We use a NATIVE width calculation here because we are modifying the 1024x1024 image directly.
        # We let Streamlit resize the final GIF to GAME_WIDTH (700px) for display.
        coords = streamlit_image_coordinates(gif_path, key=f"lvl_{lvl_idx}_{st.session_state.last_move_time}", width=GAME_WIDTH)

        if coords:
            # Scale click back up to 1024x1024 space to match our glitch coordinates
            scale = 1024 / GAME_WIDTH
            cx, cy = coords['x'] * scale, coords['y'] * scale
            x1, y1 = st.session_state.gx, st.session_state.gy
            x2, y2 = x1 + st.session_state.gw, y1 + st.session_state.gh

            if (x1 - HIT_TOLERANCE) <= cx <= (x2 + HIT_TOLERANCE) and \
               (y1 - HIT_TOLERANCE) <= cy <= (y2 + HIT_TOLERANCE):
                # HIT!
                trigger_static_transition()
                if lvl_idx < 8:
                    st.session_state.current_level += 1
                    move_glitch(st.session_state.current_level)
                    st.rerun()
                else:
                    st.session_state.final_time = time.time() - st.session_state.start_time
                    st.session_state.game_state = 'game_over'
                    st.rerun()
            else:
                 # MISS!
                 st.toast("MISS! ANOMALY SHIFTED.", icon="⚠️")
                 move_glitch(lvl_idx)
                 time.sleep(0.5)
                 st.rerun()

elif st.session_state.game_state == "game_over":
    st.balloons()
    st.write(f"TIME: {st.session_state.final_time:.2f}s")
    if st.button("UPLOAD SCORE"):
        save_score(st.session_state.player_tag, st.session_state.final_time)
        st.success("DONE")
        time.sleep(2); st.session_state.game_state = 'menu'; st.rerun()
    st.dataframe(get_leaderboard(), hide_index=True)