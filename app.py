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
HIT_TOLERANCE = 80

# --- CONNECTION DOCTOR (DEBUGGER) ---
# This will appear at the top of your app to tell you if it's working.
# Once it works, you can delete this section.
with st.expander("🔌 CONNECTION STATUS (Click to view)", expanded=True):
    try:
        conn = st.connection("gsheets", type=GSheetsConnection)
        st.success("✅ SECRETS FOUND: Streamlit can see your credentials.")
        try:
            test_df = conn.read(worksheet="Scores", ttl=0)
            st.success("✅ READ PERMISSION: Can read the 'Scores' tab.")
            st.info(f"Current Leaderboard Entries: {len(test_df)}")
        except Exception as e:
            st.error(f"❌ READ FAILED: Could not read 'Scores' tab. Did you rename 'Sheet1' to 'Scores'?")
            st.error(f"Error details: {e}")
    except Exception as e:
        st.error("❌ SECRETS MISSING: details not found in .streamlit/secrets.toml")

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
            z-index: 999; background-size: 100% 3px, 3px 100%; pointer-events: none; opacity: 0.2;
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
def generate_scaled_gif(img_path, original_box, target_width, level_idx):
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
        temp_file = f"level_{level_idx}_chaos.gif"
        frames[0].save(temp_file, format="GIF", save_all=True, append_images=frames[1:], duration=[200]*15 + [60]*6, loop=0)
        return temp_file, scaled_box
    except: return None, None

# --- GAME DATA ---
LEVELS = [
    {"img": "assets/level1.png", "glitch_box": (460, 410, 540, 530)}, 
    {"img": "assets/level2.png", "glitch_box": (610, 420, 860, 840)}, 
    {"img": "assets/level3.png", "glitch_box": (165, 495, 220, 605)}, 
    {"img": "assets/level4.png", "glitch_box": (650, 640, 910, 875)}, 
    {"img": "assets/level5.png", "glitch_box": (450, 190, 520, 310)}, 
    {"img": "assets/level6.png", "glitch_box": (445, 305, 565, 605)}, 
    {"img": "assets/level7.png", "glitch_box": (770, 360, 915, 505)}, 
    {"img": "assets/level8.png", "glitch_box": (495, 150, 560, 215)}, 
    {"img": "assets/level9.png", "glitch_box": (440, 380, 510, 455)}, 
]

# --- INIT ---
inject_css()
if 'game_state' not in st.session_state:
    st.session_state.update({'game_state': 'menu', 'current_level': 0, 'start_time': 0.0, 'player_tag': 'UNK', 'final_time': 0.0})

# --- LEADERBOARD FUNCTIONS ---
def save_score(tag, time_val):
    try:
        conn = st.connection("gsheets", type=GSheetsConnection)
        conn.update(worksheet="Scores", data=pd.DataFrame([{"Tag": tag, "Time": time_val}]))
        return True
    except: return False

def get_leaderboard():
    try:
        conn = st.connection("gsheets", type=GSheetsConnection)
        df = conn.read(worksheet="Scores", ttl=0).dropna(how="all")
        df['Time'] = pd.to_numeric(df['Time'], errors='coerce').dropna()
        return df.sort_values('Time').head(10).reset_index(drop=True)
    except: return pd.DataFrame(columns=["Rank", "Tag", "Time (Offline)"])

# --- GAME LOOP ---
st.title("DETROIT: ANOMALY [09]")

if st.session_state.game_state == "menu":
    tag = st.text_input("OPERATIVE TAG (3 CHARS):", max_chars=3).upper()
    if st.button(">> START SIMULATION <<", type="primary"):
        if len(tag) == 3:
            st.session_state.update({'game_state': 'playing', 'player_tag': tag, 'start_time': time.time(), 'current_level': 0})
            st.rerun()
    st.markdown("### TOP AGENTS")
    st.dataframe(get_leaderboard(), hide_index=True)

elif st.session_state.game_state == "playing":
    lvl_idx = st.session_state.current_level
    data = LEVELS[lvl_idx]
    st.write(f"SECTOR 0{lvl_idx + 1} / 09")

    gif_path, scaled_box = generate_scaled_gif(data["img"], data["glitch_box"], GAME_WIDTH, lvl_idx)

    if gif_path and scaled_box:
        coords = streamlit_image_coordinates(gif_path, key=f"lvl_{lvl_idx}", width=GAME_WIDTH)
        if coords:
            x1, y1, x2, y2 = scaled_box
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
            st.error("UPLOAD FAILED. CHECK PERMISSIONS.")
        time.sleep(2); st.session_state.game_state = 'menu'; st.rerun()
    st.markdown("### GLOBAL RANKINGS")
    st.dataframe(get_leaderboard(), hide_index=True)