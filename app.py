import streamlit as st
import time
import pandas as pd
import random
import os
import base64
from PIL import Image, ImageOps, ImageEnhance
from streamlit_gsheets import GSheetsConnection
from streamlit_image_coordinates import streamlit_image_coordinates
import re 

# --- CONFIGURATION ---
st.set_page_config(page_title="DETROIT: Anomaly [09]", layout="centered", initial_sidebar_state="collapsed")

GAME_WIDTH = 700
HIT_TOLERANCE = 100

LEVEL_FILES = ["assets/level1.png", "assets/level2.png", "assets/level3.png", "assets/level4.png"]
GLITCHES_PER_LEVEL = [3, 5, 7, 7] 

# --- HELPER: ASSETS ---
def get_base64(bin_file):
    try:
        with open(bin_file, 'rb') as f: return base64.b64encode(f.read()).decode()
    except: return None

# --- CSS: RETRO AESTHETIC ---
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

def trigger_static_transition():
    st.markdown('<audio src="https://www.myinstants.com/media/sounds/static-noise.mp3" autoplay style="display:none;"></audio>', unsafe_allow_html=True)
    placeholder = st.empty()
    with placeholder.container():
        st.markdown('<div style="position:fixed;top:0;left:0;width:100%;height:100%;background-color:#111;z-index:10000;"></div>', unsafe_allow_html=True)
        time.sleep(0.1)
        g_url = "https://media.giphy.com/media/oEI9uBYSzLpBK/giphy.gif"
        st.markdown(f'<div style="position:fixed;top:0;left:0;width:100%;height:100%;background:url({g_url});background-size:cover;z-index:10001;opacity:0.8;mix-blend-mode:hard-light;"></div>', unsafe_allow_html=True)
        time.sleep(0.4)
    placeholder.empty()

# --- GLITCH GENERATION ---
def get_new_glitch_box(level=0):
    max_size = max(150 - level * 20, 30) 
    min_size = max(50 - level * 10, 15) 
    min_size = min(min_size, max_size) 
    w, h = random.randint(min_size, max_size), random.randint(min_size, max_size)
    return (random.randint(50, 1024-w-50), random.randint(50, 1024-h-50), random.randint(50, 1024-w-50)+w, random.randint(50, 1024-h-50)+h)

def generate_fake_glitch_box(level=0):
    max_size, min_size = max(180 - level * 15, 60), max(70 - level * 5, 40) 
    w, h = random.randint(min_size, max_size), random.randint(min_size, max_size)
    return (random.randint(50, 1024-w-50), random.randint(50, 1024-h-50), random.randint(50, 1024-w-50)+w, random.randint(50, 1024-h-50)+h)

def generate_mutating_frame(base_img, boxes, is_fake=False):
    frame = base_img.copy()
    if not isinstance(boxes, list): boxes = [boxes]
    contrast_level = 1.0 if is_fake else 3.0 
    for box in boxes:
        x1, y1, x2, y2 = box
        cx, cy = (x1 + x2) // 2, (y1 + y2) // 2
        for _ in range(random.randint(4, 9)):
            w_shard, h_shard = random.randint(30, 200), random.randint(20, 150)
            sx = max(0, min(cx - w_shard // 2 + random.randint(-60, 60), base_img.width - w_shard))
            sy = max(0, min(cy - h_shard // 2 + random.randint(-60, 60), base_img.height - h_shard))
            try:
                shard = ImageEnhance.Contrast(ImageOps.invert(frame.crop((sx, sy, sx+w_shard, sy+h_shard)).convert("RGB"))).enhance(contrast_level)
                frame.paste(shard, (sx, sy, sx+w_shard, sy+h_shard))
            except: pass
    return frame

@st.cache_data(show_spinner=False, persist="disk")
def generate_scaled_gif(img_path, original_boxes, target_width, level_idx, glitch_seed):
    try:
        random.seed(glitch_seed)
        base_img = Image.open(img_path).convert("RGB")
        sf = target_width / base_img.width
        base_img = base_img.resize((target_width, int(base_img.height * sf)), Image.Resampling.LANCZOS)
        scaled_real = [(int(x1*sf), int(y1*sf), int(x2*sf), int(y2*sf)) for x1,y1,x2,y2 in original_boxes]
        scaled_fake = [(int(x1*sf), int(y1*sf), int(x2*sf), int(y2*sf)) for x1,y1,x2,y2 in [generate_fake_glitch_box(level_idx) for _ in range(level_idx+1)]]
        frames = [base_img.copy() for _ in range(15)]
        for _ in range(8):
            frames.append(generate_mutating_frame(generate_mutating_frame(base_img, original_boxes, False), scaled_fake, True))
        temp_file = f"/tmp/lvl_{level_idx}_{glitch_seed}.gif"
        frames[0].save(temp_file, format="GIF", save_all=True, append_images=frames[1:], duration=[200]*15+[70]*8, loop=0)
        return temp_file, scaled_real, scaled_fake
    except: return None, [], []

def validate_usn(usn): return re.match(r"^\d[A-Z]{2}\d{2}[A-Z]{2}\d{3}$", usn)

# --- GOOGLE SHEETS ---
conn = None
try: conn = st.connection("gsheets", type=GSheetsConnection)
except: pass

def save_score(tag, name, usn, time_val):
    if conn:
        try: conn.write(worksheet="Scores", data=pd.DataFrame([{"Tag": tag, "Name": name, "USN": usn, "Time": time_val}]), append=True); return True
        except: return False
    return False

def get_leaderboard():
    """NUCLEAR READ MODE: Forces everything to string first to bypass TypeErrors."""
    if conn:
        try:
            # 1. Read EVERYTHING as a string first. safest way possible.
            df = conn.read(worksheet="Scores", ttl=0, dtype=str)
            
            # 2. Ensure required columns exist
            req = ['Tag', 'Name', 'USN', 'Time']
            if not all(c in df.columns for c in req): return pd.DataFrame(columns=["Rank"]+req)

            # 3. Manually convert Time to numeric, forcing errors to NaN
            df['Time'] = pd.to_numeric(df['Time'], errors='coerce')
            
            # 4. Drop rows where Time became NaN (invalid data)
            df.dropna(subset=['Time', 'USN'], inplace=True)

            if df.empty: return pd.DataFrame(columns=["Rank"]+req)

            # 5. Sort and format
            df.sort_values(by='Time', ascending=True, inplace=True)
            df['Rank'] = range(1, len(df) + 1)
            df['Time'] = df['Time'].apply(lambda x: f"{x:.2f}s")
            return df[['Rank', 'Name', 'USN', 'Time']].head(10).reset_index(drop=True)
        except Exception: pass
    return pd.DataFrame(columns=["Rank", "Name", "USN", "Time"])

# --- MAIN ---
inject_css()
if 'game_state' not in st.session_state:
    st.session_state.update({'game_state': 'menu', 'current_level': 0, 'start_time': 0.0, 'player_tag': 'UNK', 'player_name': '', 'player_usn': '', 'final_time': 0.0, 'last_move_time': time.time(), 'glitch_seed': random.randint(1, 100000), 'current_boxes': [get_new_glitch_box()], 'hits': 0})

st.title("DETROIT: ANOMALY [09]")

if st.session_state.game_state == "menu":
    st.markdown("### OPERATIVE DATA INPUT")
    tag = st.text_input(">> AGENT TAG (3 CHARS):", max_chars=3, value=st.session_state.player_tag if st.session_state.player_tag != 'UNK' else '').upper()
    name = st.text_input(">> FULL NAME:", value=st.session_state.player_name)
    usn = st.text_input(">> USN (e.g., 1MS22AI000):", value=st.session_state.player_usn).upper()
    if st.button(">> START SIMULATION <<", type="primary", disabled=(len(tag)!=3 or not name or not validate_usn(usn))):
        st.session_state.update({'game_state': 'playing', 'player_tag': tag, 'player_name': name, 'player_usn': usn, 'start_time': time.time(), 'current_level': 0, 'hits': 0})
        move_glitch(get_num_real_targets(0)); st.rerun()
    st.markdown("---")
    st.markdown("### GLOBAL RANKINGS")
    lb = get_leaderboard()
    if not lb.empty: st.dataframe(lb, hide_index=True, use_container_width=True)
    elif conn: st.warning("Connection OK. Waiting for data (ensure 'Scores' sheet has data in row 2).")
    else: st.error("Connection Failed.")

elif st.session_state.game_state == "playing":
    lvl = st.session_state.current_level
    needed, targets = GLITCHES_PER_LEVEL[lvl], (2 if lvl in [2,3] else 1)
    c1, c2, c3 = st.columns(3)
    c1.markdown(f"**AGENT: {st.session_state.player_tag}**"); c2.markdown(f"**TIME: {time.time()-st.session_state.start_time:.1f}s**"); c3.markdown(f"**LVL: {lvl+1}/4**")
    st.progress(st.session_state.hits/needed, text=f"Neutralized: {st.session_state.hits}/{needed}")
    
    gif, real, fake = generate_scaled_gif(LEVEL_FILES[lvl], st.session_state.current_boxes, GAME_WIDTH, lvl, st.session_state.glitch_seed)
    if gif and real:
        coords = streamlit_image_coordinates(gif, key=f"lvl_{lvl}_{st.session_state.glitch_seed}", width=GAME_WIDTH)
        if coords:
            cx, cy = coords['x'], coords['y']
            hit = any((x1-HIT_TOLERANCE) <= cx <= (x2+HIT_TOLERANCE) and (y1-HIT_TOLERANCE) <= cy <= (y2+HIT_TOLERANCE) for x1,y1,x2,y2 in real)
            fake_hit = any((x1-HIT_TOLERANCE) <= cx <= (x2+HIT_TOLERANCE) and (y1-HIT_TOLERANCE) <= cy <= (y2+HIT_TOLERANCE) for x1,y1,x2,y2 in fake)
            if hit:
                trigger_static_transition(); st.session_state.hits += 1
                if st.session_state.hits >= needed:
                     if lvl < 3: st.session_state.current_level += 1; st.session_state.hits = 0; move_glitch((2 if st.session_state.current_level in [2,3] else 1))
                     else: st.session_state.final_time = time.time() - st.session_state.start_time; st.session_state.game_state = 'game_over'
                else: move_glitch(targets)
                st.rerun()
            elif fake_hit: st.toast("DECOY NEUTRALIZED.", icon="⚠️"); move_glitch(targets); st.rerun()
            else: st.toast("MISS! RELOCATING...", icon="❌"); move_glitch(targets); st.rerun()

elif st.session_state.game_state == "game_over":
    st.balloons()
    st.markdown(f"## MISSION COMPLETE\n**OPERATIVE:** {st.session_state.player_name}\n**TIME:** {st.session_state.final_time:.2f}s")
    if st.button(">> UPLOAD SCORE <<", type="primary"):
        with st.spinner("UPLOADING..."):
            if save_score(st.session_state.player_tag, st.session_state.player_name, st.session_state.player_usn, st.session_state.final_time): st.success("UPLOAD SUCCESSFUL.")
            else: st.error("UPLOAD FAILED.")
        time.sleep(1.5); st.session_state.game_state = 'menu'; st.rerun()