import streamlit as st
import time
import pandas as pd
import random
import os
import base64
import io
from PIL import Image, ImageOps, ImageEnhance, ImageFilter, ImageDraw
from streamlit_gsheets import GSheetsConnection
from streamlit_image_coordinates import streamlit_image_coordinates

st.set_page_config(page_title="DETROIT: ANOMALY [09]", layout="centered", initial_sidebar_state="collapsed")

# --- SETTINGS ---
GAME_WIDTH = 700
MOVE_DELAY = 5.0
HIT_TOLERANCE = 50

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

# --- RESTORED: HIGH-VISIBILITY TRANSITION ---
def trigger_static_transition():
    # Audio
    st.markdown('<audio src="https://www.myinstants.com/media/sounds/static-noise.mp3" autoplay style="display:none;"></audio>', unsafe_allow_html=True)
    # Visual
    placeholder = st.empty()
    with placeholder.container():
        # 1. Blackout screen
        st.markdown('<div style="position:fixed;top:0;left:0;width:100%;height:100%;background-color:#000;z-index:10000;"></div>', unsafe_allow_html=True)
        time.sleep(0.1)
        
        # 2. Blast static (using hard-light for maximum visibility)
        gb64 = get_base64("assets/glitch.gif")
        if not gb64: gb64 = get_base64("assets/glitch.avif")
        g_url = f"data:image/gif;base64,{gb64}" if gb64 else "https://media.giphy.com/media/oEI9uBYSzLpBK/giphy.gif"
        
        st.markdown(f'<div style="position:fixed;top:0;left:0;width:100%;height:100%;background:url({g_url});background-size:cover;z-index:10001;opacity:1.0;mix-blend-mode:hard-light;"></div>', unsafe_allow_html=True)
        time.sleep(0.5) # Slightly longer duration to ensure it's seen
    placeholder.empty()

# --- CORE: DATAMOSH GENERATOR ---
def create_datamosh_frame(base_img, x, y, w, h, intensity):
    frame = base_img.copy()
    # Ensure box is within bounds
    x = max(0, x); y = max(0, y)
    w = min(w, base_img.width - x); h = min(h, base_img.height - y)
    box = (int(x), int(y), int(x+w), int(y+h))
    
    try:
        glitch = frame.crop(box).convert('RGB')
        gw, gh = glitch.size
        if gw < 1 or gh < 1: return frame # Skip invalid sizes

        # Macroblocking (Digital Artifacts)
        block_size = random.randint(8, 32)
        glitch = glitch.resize((max(1, gw // block_size), max(1, gh // block_size)), Image.NEAREST)
        glitch = glitch.resize((gw, gh), Image.NEAREST)

        # Signal Corruption (Green/Pink tint)
        y_ch, cb, cr = glitch.convert('YCbCr').split()
        if random.random() > 0.5: cb = ImageEnhance.Brightness(cb).enhance(random.choice([0.0, 2.0]))
        else: cr = ImageEnhance.Brightness(cr).enhance(random.choice([0.0, 2.0]))
        glitch = Image.merge('YCbCr', (y_ch, cb, cr)).convert('RGB')

        frame.paste(glitch, box)
    except: pass
    return frame

@st.cache_data(show_spinner=False, persist="disk")
def generate_active_gif(img_path, x, y, w, h, move_timestamp):
    try:
        base_img = Image.open(img_path).convert("RGB")
        frames = []
        for _ in range(8): # 8 frames of intense datamoshing
            intensity = random.random()
            frames.append(create_datamosh_frame(base_img, x, y, w, h, intensity))
            
        temp_file = f"temp_datamosh_{int(move_timestamp)}.gif"
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
    if conn:
        try: conn.update(worksheet="Scores", data=pd.DataFrame([{"Tag": tag, "Time": time_val}])); return True
        except: return False
    return False

def get_leaderboard():
    try:
        df = conn.read(worksheet="Scores", ttl=0).dropna(how="all")
        df['Time'] = pd.to_numeric(df['Time'], errors='coerce').dropna()
        return df.sort_values('Time').head(10).reset_index(drop=True)
    except: return pd.DataFrame(columns=["Rank", "Tag", "Time"])

def move_glitch(level_idx):
    spots = LEVELS[level_idx]["spots"]
    cx, cy = random.choice(spots)
    st.session_state.gw = random.randint(150, 300) # Slightly larger for visibility
    st.session_state.gh = random.randint(150, 300)
    st.session_state.gx = max(0, cx - st.session_state.gw // 2)
    st.session_state.gy = max(0, cy - st.session_state.gh // 2)
    st.session_state.last_move_time = time.time()

# --- GAME LOOP ---
st.title("DETROIT: ANOMALY [09]")

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

    gif_path = generate_active_gif(
        LEVELS[lvl_idx]["img"], 
        st.session_state.gx, st.session_state.gy, 
        st.session_state.gw, st.session_state.gh,
        st.session_state.last_move_time
    )

    if gif_path:
        coords = streamlit_image_coordinates(gif_path, key=f"lvl_{lvl_idx}_{st.session_state.last_move_time}", width=GAME_WIDTH)

        if coords:
            scale = 1024 / GAME_WIDTH
            cx, cy = coords['x'] * scale, coords['y'] * scale
            x1, y1 = st.session_state.gx, st.session_state.gy
            x2, y2 = x1 + st.session_state.gw, y1 + st.session_state.gh

            if (x1 - HIT_TOLERANCE) <= cx <= (x2 + HIT_TOLERANCE) and \
               (y1 - HIT_TOLERANCE) <= cy <= (y2 + HIT_TOLERANCE):
                trigger_static_transition() # <--- IT'S BACK HERE
                if lvl_idx < 8:
                    st.session_state.current_level += 1
                    move_glitch(st.session_state.current_level)
                    st.rerun()
                else:
                    st.session_state.final_time = time.time() - st.session_state.start_time
                    st.session_state.game_state = 'game_over'
                    st.rerun()
            else:
                 st.toast("MISS! ANOMALY SHIFTED.", icon="⚠️")
                 move_glitch(lvl_idx)
                 time.sleep(0.5)
                 st.rerun()
                 
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