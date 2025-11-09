import streamlit as st
import time
import pandas as pd
import random
import os
import base64
from PIL import Image, ImageOps, ImageEnhance
from streamlit_gsheets import GSheetsConnection
from streamlit_image_coordinates import streamlit_image_coordinates

st.set_page_config(page_title="DETROIT: ANOMALY [09]", layout="centered", initial_sidebar_state="collapsed")

# --- SETTINGS ---
GAME_WIDTH = 700
HIT_TOLERANCE = 50  # Standard tolerance
MOVE_DELAY = 5.0    # Invisible timer duration

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

# --- CSS ---
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
        /* Smooth image loading to reduce flicker */
        img { transition: opacity 0.3s ease-in-out; }
    </style>
    """, unsafe_allow_html=True)

def inject_glitch_css(l, t, w, h):
    # The visible glitch box
    st.markdown(f"""
    <style>
        div[data-testid="stImage"] {{ position: relative !important; display: inline-block !important; overflow: hidden !important; }}
        div[data-testid="stImage"]::before {{
            content: ""; position: absolute;
            left: {l}%; top: {t}%; width: {w}%; height: {h}%;
            z-index: 900; pointer-events: none;
            background: rgba(255, 0, 255, 0.4); border: 2px solid #00ff00; mix-blend-mode: hard-light;
            animation: violent-flash 0.15s infinite;
        }}
        @keyframes violent-flash {{
            0%, 100% {{ opacity: 1; filter: invert(0) hue-rotate(0deg); }}
            50% {{ opacity: 0.8; filter: invert(1) hue-rotate(180deg); }}
        }}
    </style>
    """, unsafe_allow_html=True)

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
    if conn:
        try:
            df = conn.read(worksheet="Scores", ttl=0).dropna(how="all")
            df['Time'] = pd.to_numeric(df['Time'], errors='coerce').dropna()
            return df.sort_values('Time').head(10).reset_index(drop=True)
        except: pass
    return pd.DataFrame(columns=["Rank", "Tag", "Time (Offline)"])

def move_glitch(level_idx):
    spots = LEVELS[level_idx]["spots"]
    # Try to pick a new spot different from the last one
    current_spot = (st.session_state.gx + st.session_state.gw//2, st.session_state.gy + st.session_state.gh//2)
    possible_spots = [s for s in spots if s != current_spot] or spots
    
    center_x, center_y = random.choice(possible_spots)
    st.session_state.gw = random.randint(100, 220)
    st.session_state.gh = random.randint(100, 220)
    st.session_state.gx = max(0, center_x - st.session_state.gw // 2)
    st.session_state.gy = max(0, center_y - st.session_state.gh // 2)
    st.session_state.last_move_time = time.time()

# --- GAME LOOP ---
st.title("DETROIT: ANOMALY [09]")

if st.session_state.game_state == "menu":
    tag = st.text_input("OPERATIVE TAG (3 CHARS):", max_chars=3).upper()
    if st.button(">> START SIMULATION <<", type="primary"):
        if len(tag) == 3:
            move_glitch(0)
            st.session_state.update({'game_state': 'playing', 'player_tag': tag, 'start_time': time.time(), 'current_level': 0})
            st.rerun()
    st.markdown("### TOP AGENTS")
    st.dataframe(get_leaderboard(), hide_index=True, use_container_width=True)

elif st.session_state.game_state == "playing":
    lvl_idx = st.session_state.current_level
    st.write(f"SECTOR 0{lvl_idx + 1} / 09")

    # Calculate CSS for 1024x1024 native assets
    l, t = (st.session_state.gx / 1024) * 100, (st.session_state.gy / 1024) * 100
    w, h = (st.session_state.gw / 1024) * 100, (st.session_state.gh / 1024) * 100
    inject_glitch_css(l, t, w, h)

    # NO AUTO-REFRESH LOOP HERE. IT WAITS FOR YOU TO CLICK.
    coords = streamlit_image_coordinates(LEVELS[lvl_idx]["img"], key=f"lvl_{lvl_idx}_{st.session_state.last_move_time}", width=GAME_WIDTH)

    if coords:
        # Check if they waited too long
        if time.time() - st.session_state.last_move_time > MOVE_DELAY:
             st.toast("TOO SLOW! ANOMALY SHIFTED.", icon="⚠️")
             move_glitch(lvl_idx)
             time.sleep(0.5)
             st.rerun()
        else:
            # Check hit accuracy
            scale = 1024 / GAME_WIDTH
            cx, cy = coords['x'] * scale, coords['y'] * scale
            x1, y1 = st.session_state.gx, st.session_state.gy
            x2, y2 = x1 + st.session_state.gw, y1 + st.session_state.gh

            if (x1 - HIT_TOLERANCE) <= cx <= (x2 + HIT_TOLERANCE) and \
               (y1 - HIT_TOLERANCE) <= cy <= (y2 + HIT_TOLERANCE):
                # HIT!
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
                 st.toast("MISS! SIGNAL LOST.", icon="❌")
                 move_glitch(lvl_idx)
                 time.sleep(0.5)
                 st.rerun()

elif st.session_state.game_state == "game_over":
    st.balloons()
    st.write(f"AGENT: {st.session_state.player_tag} | TIME: {st.session_state.final_time:.2f}s")
    if st.button("UPLOAD SCORE", type="primary"):
        if save_score(st.session_state.player_tag, st.session_state.final_time):
            st.success("UPLOADED.")
        else: st.error("FAILED (Check Connection).")
        time.sleep(2); st.session_state.game_state = 'menu'; st.rerun()
    st.markdown("### GLOBAL RANKINGS")
    st.dataframe(get_leaderboard(), hide_index=True, use_container_width=True)