import streamlit as st
import pandas as pd
import base64
import time
import json
from streamlit_gsheets import GSheetsConnection
import streamlit.components.v1 as components

st.set_page_config(page_title="DETROIT: ANOMALY [09]", layout="centered", initial_sidebar_state="collapsed")

# --- SETTINGS ---
MOVE_DELAY_MS = 1000  # 1 SECOND per glitch! (1000 milliseconds)

# --- HELPER: LOAD FILES ---
def get_base64_image(bin_file):
    try:
        with open(bin_file, 'rb') as f:
            return f"data:image/png;base64,{base64.b64encode(f.read()).decode()}"
    except: return ""

def load_text_file(filepath):
    try:
        with open(filepath, "r") as f: return f.read()
    except: return ""

# --- LOAD RESOURCES ---
# 1. Load all 9 level images into memory as base64 strings
LEVEL_IMAGES = [get_base64_image(f"assets/level{i}.png") for i in range(1, 10)]

# 2. Load the glitch texture (preferred GIF, fallback to AVIF)
GLITCH_ASSET = get_base64_image("assets/glitch.gif")
if not GLITCH_ASSET:
    GLITCH_ASSET = get_base64_image("assets/glitch.avif")

# 3. Read the external CSS and JS files
CSS_CODE = load_text_file("style.css")
JS_CODE = load_text_file("game.js")

# --- ASSEMBLE THE FINAL HTML BLOB ---
# This combines your CSS, JS, and Python variables into one functional game page.
GAME_HTML = f"""
<!DOCTYPE html>
<html>
<head>
    <title>DETROIT_ANOMALY_CLIENT</title>
    <style>{CSS_CODE}</style>
</head>
<body>
    <div class="scanlines"></div>
    <div id="game-container">
        <div id="timer-bar"></div>
        <div id="hud">SECTOR: <span id="sector-num">01</span> / 09</div>
        
        <img id="level-img" src="">
        <div id="glitch-target"></div>
        
        <div id="game-over-screen">
            <h1>SIMULATION COMPLETE</h1>
            <p>FINAL TIME CODE:</p>
            <div class="copy-code" id="time-code" onclick="navigator.clipboard.writeText(this.innerText); this.style.background='#0f0'; this.style.color='#000'; setTimeout(()=>{{this.style.background='#000';this.style.color='#fff'}}, 200)">0.00</div>
            <p>▲ CLICK CODE TO COPY ▲</p>
        </div>
    </div>

    <script>
        // INJECT PYTHON VARIABLES INTO JS SCOPE
        const LEVELS = {json.dumps(LEVEL_IMAGES)};
        const GLITCH_ASSET = "{GLITCH_ASSET}";
        const MOVE_DELAY_MS = {MOVE_DELAY_MS};

        // INSERT MAIN GAME LOGIC
        {JS_CODE}
    </script>
</body>
</html>
"""

# --- STREAMLIT INTERFACE ---
# Glitched Title Styling (Python side)
st.markdown("""
    <style>
    @keyframes title-glitch {
        0% { text-shadow: 2px 2px #f00, -2px -2px #0ff; transform: skew(0deg); }
        90% { text-shadow: 2px 2px #f00, -2px -2px #0ff; transform: skew(0deg); }
        92% { text-shadow: -2px 2px #f00, 2px -2px #0ff; transform: skew(5deg); }
        94% { text-shadow: 2px -2px #f00, -2px 2px #0ff; transform: skew(-5deg); }
        100% { text-shadow: 2px 2px #f00, -2px -2px #0ff; transform: skew(0deg); }
    }
    .main-title {
        font-size: 3em; font-weight: 800; color: #fff; text-align: center;
        animation: title-glitch 2s infinite; margin-bottom: 20px;
    }
    </style>
    <div class="main-title">DETROIT: ANOMALY [09]</div>
    """, unsafe_allow_html=True)

# Initialize State
if 'game_state' not in st.session_state:
    st.session_state.game_state = 'menu'

# --- MENU STATE ---
if st.session_state.game_state == 'menu':
    c1, c2 = st.columns([2, 1])
    with c1:
        tag = st.text_input("OPERATIVE TAG (3 CHARS):", max_chars=3, placeholder="NEO").upper()
    with c2:
        st.write("") # alignment spacer
        st.write("")
        if st.button("INITIALIZE SEQUENCE", type="primary", use_container_width=True):
            if len(tag) == 3:
                st.session_state.player_tag = tag
                st.session_state.game_state = 'playing'
                st.rerun()
            else:
                st.error("INVALID TAG LENGTH")

# --- PLAYING STATE ---
if st.session_state.game_state == 'playing':
    # 1. Render the full JS game in an iframe
    components.html(GAME_HTML, height=720)

    # 2. Render the Score Submission UI below it
    st.markdown("---")
    st.write("### 📡 SECURE UPLINK")
    st.caption("Click the green time code above to copy it, then paste it here:")
    
    c1, c2 = st.columns([3, 1])
    with c1:
        final_time = st.text_input("TIME CODE INPUT:", label_visibility="collapsed", placeholder="PASTE CODE HERE")
    with c2:
        if st.button("TRANSMIT DATA", type="primary", use_container_width=True):
            if final_time:
                try:
                    t_val = float(final_time)
                    # Attempt to save to Google Sheets
                    conn = st.connection("gsheets", type=GSheetsConnection)
                    conn.update(worksheet="Scores", data=pd.DataFrame([{"Tag": st.session_state.player_tag, "Time": t_val}]))
                    st.success("UPLOAD SUCCESSFUL.")
                    time.sleep(2)
                    st.session_state.game_state = 'menu'
                    st.rerun()
                except Exception as e:
                    st.error(f"UPLOAD FAILED: {e}")
            else:
                st.warning("MISSING TIME CODE")
    
    if st.button("ABORT MISSION (RETURN TO MENU)"):
        st.session_state.game_state = 'menu'
        st.rerun()

# --- LEADERBOARD (ALWAYS VISIBLE) ---
try:
    conn = st.connection("gsheets", type=GSheetsConnection)
    df = conn.read(worksheet="Scores", ttl=5).dropna()
    df['Time'] = pd.to_numeric(df['Time'])
    st.markdown("### TOP OPERATIVES")
    st.dataframe(df.sort_values('Time').head(10).reset_index(drop=True), use_container_width=True)
except:
    st.caption("Leaderboard offline.")