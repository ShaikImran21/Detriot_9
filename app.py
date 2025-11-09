import streamlit as st
import time
import pandas as pd
import random
from streamlit_gsheets import GSheetsConnection
from streamlit_image_coordinates import streamlit_image_coordinates

st.set_page_config(page_title="DETROIT: ANOMALY [09]", layout="centered", initial_sidebar_state="collapsed")

# --- SETTINGS ---
GAME_WIDTH = 700
MOVE_DELAY = 3.0 # How fast it moves to a new spot (lower = harder)
HIT_TOLERANCE = 50

# --- GAME DATA: FIXED SPOTS PER LEVEL ---
# UPDATE THESE COORDINATES to match features in your actual pixel art!
# Format: (x_center, y_center) for each possible glitch location.
LEVELS = [
    {"img": "assets/level1.png", "spots": [(200, 200), (512, 512), (800, 300), (400, 800)]},
    {"img": "assets/level2.png", "spots": [(100, 800), (900, 100), (500, 500), (300, 400)]},
    {"img": "assets/level3.png", "spots": [(600, 200), (200, 600), (800, 800), (512, 300)]},
    {"img": "assets/level4.png", "spots": [(350, 350), (700, 700), (150, 850), (900, 200)]},
    {"img": "assets/level5.png", "spots": [(512, 100), (512, 900), (100, 512), (900, 512)]},
    {"img": "assets/level6.png", "spots": [(250, 250), (750, 250), (250, 750), (750, 750)]},
    {"img": "assets/level7.png", "spots": [(100, 100), (200, 200), (300, 300), (400, 400)]},
    {"img": "assets/level8.png", "spots": [(600, 600), (700, 700), (800, 800), (900, 900)]},
    {"img": "assets/level9.png", "spots": [(512, 512), (512, 200), (200, 512), (800, 512)]},
]

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

# --- DYNAMIC GLITCH CSS ---
def inject_glitch_css(l, t, w, h):
    st.markdown(f"""
    <style>
        @keyframes rapid-flash {{
            0%, 85% {{ opacity: 0; filter: invert(0); }}
            86% {{ opacity: 0.9; filter: invert(1) hue-rotate(180deg) contrast(2); }}
            88% {{ opacity: 0.9; filter: invert(1) hue-rotate(0deg); }}
            90% {{ opacity: 0.9; filter: invert(1) hue-rotate(90deg) contrast(3); }}
            92% {{ opacity: 0; }}
        }}
        div[data-testid="stImage"]::before {{
            content: ""; position: absolute;
            left: {l}%; top: {t}%; width: {w}%; height: {h}%;
            background: rgba(255, 255, 255, 0.1);
            animation: rapid-flash 4s infinite linear;
            pointer-events: none; z-index: 999;
            mix-blend-mode: difference; border: 1px solid rgba(255,0,0,0.3);
        }}
    </style>
    """, unsafe_allow_html=True)

# --- INIT ---
inject_css()
if 'game_state' not in st.session_state:
    st.session_state.update({'game_state': 'menu', 'current_level': 0, 'start_time': 0.0, 'player_tag': 'UNK', 'last_move_time': time.time(), 'gx':0, 'gy':0, 'gw':0, 'gh':0})

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

# --- WHACK-A-GLITCH RANDOMIZER ---
def move_glitch(level_idx):
    # 1. Pick a random predefined spot for this level
    spots = LEVELS[level_idx]["spots"]
    center_x, center_y = random.choice(spots)
    
    # 2. Randomize the size of the glitch
    st.session_state.gw = random.randint(80, 250)
    st.session_state.gh = random.randint(80, 250)
    
    # 3. Center the new random box on the chosen spot
    st.session_state.gx = max(0, center_x - st.session_state.gw // 2)
    st.session_state.gy = max(0, center_y - st.session_state.gh // 2)
    
    st.session_state.last_move_time = time.time()

# --- GAME LOOP ---
st.title("DETROIT: ANOMALY [09]")

if st.session_state.game_state == 'playing':
    # Auto-move if player is too slow
    if time.time() - st.session_state.last_move_time > MOVE_DELAY:
        move_glitch(st.session_state.current_level)
        st.rerun()

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

    # Calculate CSS percentages based on 1024x1024 native size
    l, t = (st.session_state.gx / 1024) * 100, (st.session_state.gy / 1024) * 100
    w, h = (st.session_state.gw / 1024) * 100, (st.session_state.gh / 1024) * 100
    inject_glitch_css(l, t, w, h)

    coords = streamlit_image_coordinates(LEVELS[lvl_idx]["img"], key=f"lvl_{lvl_idx}", width=GAME_WIDTH)

    if coords:
        # Scale click back to native 1024 space
        scale = 1024 / GAME_WIDTH
        cx, cy = coords['x'] * scale, coords['y'] * scale
        x1, y1 = st.session_state.gx, st.session_state.gy
        x2, y2 = x1 + st.session_state.gw, y1 + st.session_state.gh

        if (x1 - HIT_TOLERANCE) <= cx <= (x2 + HIT_TOLERANCE) and \
           (y1 - HIT_TOLERANCE) <= cy <= (y2 + HIT_TOLERANCE):
            if lvl_idx < 8:
                st.session_state.current_level += 1
                move_glitch(st.session_state.current_level)
                st.rerun()
            else:
                st.session_state.final_time = time.time() - st.session_state.start_time
                st.session_state.game_state = 'game_over'
                st.rerun()
        else:
             st.toast("ANOMALY SHIFTED.", icon="⚠️")
             move_glitch(lvl_idx)
             time.sleep(0.5)
             st.rerun()
    time.sleep(0.5)
    st.rerun()

elif st.session_state.game_state == "game_over":
    st.balloons()
    st.write(f"AGENT: {st.session_state.player_tag} | TIME: {st.session_state.final_time:.2f}s")
    if st.button("UPLOAD SCORE", type="primary"):
        if save_score(st.session_state.player_tag, st.session_state.final_time):
            st.success("UPLOADED.")
        else: st.error("FAILED.")
        time.sleep(2); st.session_state.game_state = 'menu'; st.rerun()
    st.markdown("### GLOBAL RANKINGS")
    st.dataframe(get_leaderboard(), hide_index=True, use_container_width=True)