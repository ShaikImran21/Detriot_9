import streamlit as st
import time
import pandas as pd
import random
import base64
from streamlit_gsheets import GSheetsConnection
from streamlit_image_coordinates import streamlit_image_coordinates

st.set_page_config(page_title="DETROIT: ANOMALY [09]", layout="centered", initial_sidebar_state="collapsed")

# --- SETTINGS ---
GAME_WIDTH = 700
HIT_TOLERANCE = 60
MOVE_DELAY = 5.0
NATIVE_SIZE = 1024

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
        
        /* CRT SCANLINE OVERLAY */
        .stApp::after {
            content: " "; display: block; position: fixed; top: 0; left: 0; bottom: 0; right: 0;
            background: linear-gradient(rgba(18, 16, 16, 0) 50%, rgba(0, 0, 0, 0.25) 50%), linear-gradient(90deg, rgba(255, 0, 0, 0.06), rgba(0, 255, 0, 0.02), rgba(0, 0, 255, 0.06));
            z-index: 999; background-size: 100% 3px, 3px 100%; pointer-events: none; opacity: 0.15;
        }
        
        /* TITLE GLITCH ANIMATION */
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

# --- DYNAMIC "HYPER-GLITCH" ANIMATION ---
def inject_glitch_css(l, t, w, h):
    # NOTE: Double braces {{ }} are used for actual CSS, single braces { } for Python variables.
    st.markdown(f"""
    <style>
        div[data-testid="stImage"] {{ position: relative !important; display: inline-block !important; overflow: hidden !important; }}
        div[data-testid="stImage"]::before {{
            content: ""; position: absolute;
            left: {l}%; top: {t}%; width: {w}%; height: {h}%;
            z-index: 900; pointer-events: none;
            background: rgba(255, 0, 255, 0.2);
            border: 2px solid #0f0;
            mix-blend-mode: hard-light;
            animation: hyper-glitch 0.2s infinite linear alternate-reverse;
        }}
        @keyframes hyper-glitch {{
            0% {{ backdrop-filter: invert(0) blur(0px); transform: translate(0,0) skew(0deg); }}
            20% {{ backdrop-filter: invert(0.8) hue-rotate(90deg) blur(2px); transform: translate(-5px, 2px) skew(5deg); }}
            40% {{ backdrop-filter: invert(0.2) hue-rotate(180deg) contrast(2); transform: translate(5px, -5px) skew(-5deg); }}
            60% {{ backdrop-filter: sepia(1) hue-rotate(270deg) saturate(5); transform: translate(-5px, 5px) scale(1.1); }}
            80% {{ backdrop-filter: invert(1) blur(1px); transform: translate(2px, -2px) skew(2deg); }}
            100% {{ backdrop-filter: invert(0) blur(0px); transform: translate(0,0) skew(0deg); }}
        }}
    </style>
    """, unsafe_allow_html=True)

# --- TRANSITION EFFECT ---
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

# --- GAME DATA ---
LEVEL_FILES = [
    "assets/level1.png", "assets/level2.png", "assets/level3.png",
    "assets/level4.png", "assets/level5.png", "assets/level6.png",
    "assets/level7.png", "assets/level8.png", "assets/level9.png"
]

# --- INIT ---
inject_css()
if 'game_state' not in st.session_state:
    st.session_state.update({
        'game_state': 'menu', 'current_level': 0, 'start_time': 0.0, 'player_tag': 'UNK',
        'last_move_time': time.time(), 'gx':0, 'gy':0, 'gw':0, 'gh':0
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

# --- RANDOMIZER ---
def move_glitch():
    st.session_state.gw = random.randint(100, 250)
    st.session_state.gh = random.randint(100, 250)
    st.session_state.gx = random.randint(50, NATIVE_SIZE - st.session_state.gw - 50)
    st.session_state.gy = random.randint(50, NATIVE_SIZE - st.session_state.gh - 50)
    st.session_state.last_move_time = time.time()

# --- GAME LOOP ---
st.title("DETROIT: ANOMALY [09]")

if st.session_state.game_state == 'playing':
    if time.time() - st.session_state.last_move_time > MOVE_DELAY:
        move_glitch()
        st.rerun()

if st.session_state.game_state == "menu":
    tag = st.text_input("OPERATIVE TAG (3 CHARS):", max_chars=3).upper()
    if st.button(">> START SIMULATION <<", type="primary"):
        if len(tag) == 3:
            random.seed(time.time())
            move_glitch()
            st.session_state.update({'game_state': 'playing', 'player_tag': tag, 'start_time': time.time(), 'current_level': 0})
            st.rerun()
    st.markdown("### TOP AGENTS")
    st.dataframe(get_leaderboard(), hide_index=True, use_container_width=True)

elif st.session_state.game_state == "playing":
    lvl_idx = st.session_state.current_level
    elapsed = time.time() - st.session_state.last_move_time
    time_left = max(0.0, MOVE_DELAY - elapsed)
    st.progress(time_left / MOVE_DELAY, text=f"SECTOR 0{lvl_idx + 1} // SHIFT IN {time_left:.1f}s")

    # Inject Glitch
    l_pct = (st.session_state.gx / NATIVE_SIZE) * 100
    t_pct = (st.session_state.gy / NATIVE_SIZE) * 100
    w_pct = (st.session_state.gw / NATIVE_SIZE) * 100
    h_pct = (st.session_state.gh / NATIVE_SIZE) * 100
    inject_glitch_css(l_pct, t_pct, w_pct, h_pct)

    coords = streamlit_image_coordinates(LEVEL_FILES[lvl_idx], key=f"lvl_{lvl_idx}_{st.session_state.last_move_time}", width=GAME_WIDTH)

    if coords:
        if time.time() - st.session_state.last_move_time > MOVE_DELAY:
             st.toast("TOO SLOW! TARGET SHIFTED.", icon="⚠️")
             move_glitch()
             time.sleep(0.5)
             st.rerun()
        else:
            scale = NATIVE_SIZE / GAME_WIDTH
            cx, cy = coords['x'] * scale, coords['y'] * scale
            x1, y1 = st.session_state.gx, st.session_state.gy
            x2, y2 = x1 + st.session_state.gw, y1 + st.session_state.gh

            if (x1 - HIT_TOLERANCE) <= cx <= (x2 + HIT_TOLERANCE) and \
               (y1 - HIT_TOLERANCE) <= cy <= (y2 + HIT_TOLERANCE):
                trigger_static_transition()
                if lvl_idx < 8:
                    st.session_state.current_level += 1
                    move_glitch()
                    st.rerun()
                else:
                    st.session_state.final_time = time.time() - st.session_state.start_time
                    st.session_state.game_state = 'game_over'
                    st.rerun()
            else:
                 st.toast("MISS! RELOCATING...", icon="❌")
                 move_glitch()
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
    st.dataframe(get_leaderboard(), hide_index=True, use_container_width=True)