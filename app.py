import streamlit as st
import pandas as pd
import base64
import time
import json
from streamlit_gsheets import GSheetsConnection
import streamlit.components.v1 as components

st.set_page_config(page_title="DETROIT: ANOMALY [09]", layout="centered", initial_sidebar_state="collapsed")

# --- SETTINGS ---
MOVE_DELAY_MS = 1000  # 1 SECOND to click! Hardcore.

# --- ASSET LOADER ---
def get_base64(bin_file):
    try:
        with open(bin_file, 'rb') as f:
            return f"data:image/png;base64,{base64.b64encode(f.read()).decode()}"
    except: return ""

LEVEL_IMAGES = [get_base64(f"assets/level{i}.png") for i in range(1, 10)]
# Load glitch texture (gif > avif > nothing)
GLITCH_ASSET = get_base64("assets/glitch.gif")
if not GLITCH_ASSET: GLITCH_ASSET = get_base64("assets/glitch.avif")

# --- JAVASCRIPT ENGINE ---
GAME_HTML = f"""
<!DOCTYPE html>
<html>
<head>
<style>
    body {{ margin: 0; background-color: #080808; color: #d0d0d0; font-family: 'Courier New', monospace; overflow: hidden; user-select: none; }}
    #game-container {{ position: relative; width: 700px; height: 700px; margin: 0 auto; border: 2px solid #333; overflow: hidden; }}
    #level-img {{ width: 100%; height: 100%; object-fit: cover; pointer-events: auto; }}
    
    /* --- THE FANCY GLITCH --- */
    #glitch-target {{
        position: absolute;
        z-index: 1000;
        display: none;
        border: 2px solid #0f0;
        /* DATAMOSH EFFECT LAYER */
        background-image: url('{GLITCH_ASSET}');
        background-size: cover;
        mix-blend-mode: hard-light;
        animation: violent-flash 0.1s infinite;
        cursor: crosshair;
    }}
    @keyframes violent-flash {{
        0% {{ opacity: 0.8; filter: hue-rotate(0deg) invert(0); }}
        50% {{ opacity: 0.6; filter: hue-rotate(180deg) invert(1); }}
        100% {{ opacity: 0.9; filter: hue-rotate(0deg) invert(0); }}
    }}

    #hud {{ position: absolute; top: 10px; left: 10px; z-index: 1001; background: rgba(0,0,0,0.7); padding: 5px 10px; pointer-events: none; font-size: 20px; }}
    #timer-bar {{ position: absolute; top: 0; left: 0; height: 8px; background-color: #f00; width: 100%; z-index: 1002; }}
    
    /* CRT EFFECT */
    .scanlines {{
        position: fixed; top: 0; left: 0; width: 100vw; height: 100vh; pointer-events: none; z-index: 9999;
        background: linear-gradient(rgba(18, 16, 16, 0) 50%, rgba(0, 0, 0, 0.25) 50%), linear-gradient(90deg, rgba(255, 0, 0, 0.06), rgba(0, 255, 0, 0.02), rgba(0, 0, 255, 0.06));
        background-size: 100% 4px, 3px 100%; opacity: 0.3;
    }}

    #game-over-screen {{
        display: none; position: absolute; top: 0; left: 0; width: 100%; height: 100%;
        background: rgba(0,0,0,0.95); color: #0f0; z-index: 2000;
        flex-direction: column; justify-content: center; align-items: center; text-align: center;
    }}
    .copy-code {{ font-size: 42px; font-weight: bold; color: #fff; background: #000; padding: 20px; border: 4px dashed #0f0; margin: 20px; user-select: all; cursor: pointer; }}
</style>
</head>
<body>
    <div class="scanlines"></div>
    <div id="game-container">
        <div id="timer-bar"></div>
        <div id="hud">SECTOR: <span id="sector-num">01</span> / 09</div>
        <img id="level-img" src="">
        <div id="glitch-target" onmousedown="hitGlitch(event)"></div> <div id="game-over-screen">
            <h1>SIMULATION COMPLETE</h1>
            <p>FINAL TIME:</p>
            <div class="copy-code" id="time-code" onclick="selectText(this)">0.00</div>
            <p>▲ COPY THIS CODE BELOW ▲</p>
        </div>
    </div>

<script>
    const LEVELS = {json.dumps(LEVEL_IMAGES)};
    let currentLevel = 0;
    let startTime = 0;
    let lastMoveTime = 0;
    let gameActive = false;
    let animationFrameId;

    const glitch = document.getElementById('glitch-target');
    const levelImg = document.getElementById('level-img');
    const timerBar = document.getElementById('timer-bar');

    function startGame() {{
        currentLevel = 0;
        gameActive = true;
        startTime = Date.now();
        loadLevel(0);
        gameLoop();
    }}

    function loadLevel(idx) {{
        document.getElementById('sector-num').innerText = '0' + (idx + 1);
        levelImg.src = LEVELS[idx];
        moveGlitch();
    }}

    function moveGlitch() {{
        lastMoveTime = Date.now();
        // Random size (80-250px)
        let w = Math.floor(Math.random() * 170) + 80;
        let h = Math.floor(Math.random() * 170) + 80;
        let x = Math.floor(Math.random() * (700 - w));
        let y = Math.floor(Math.random() * (700 - h));
        glitch.style.width = w + 'px';
        glitch.style.height = h + 'px';
        glitch.style.left = x + 'px';
        glitch.style.top = y + 'px';
        glitch.style.display = 'block';
    }}

    function hitGlitch(e) {{
        if (!gameActive) return;
        e.stopPropagation();
        
        // WHITE FLASH TRANSITION
        let flash = document.createElement('div');
        flash.style.position = 'fixed'; flash.style.top = 0; flash.style.left = 0;
        flash.style.width = '100%'; flash.style.height = '100%';
        flash.style.backgroundColor = 'white'; flash.style.zIndex = 99999;
        document.body.appendChild(flash);
        setTimeout(() => flash.remove(), 50);

        currentLevel++;
        if (currentLevel < 9) {{
            loadLevel(currentLevel);
        }} else {{
            endGame();
        }}
    }}

    function endGame() {{
        gameActive = false;
        cancelAnimationFrame(animationFrameId);
        let totalTime = ((Date.now() - startTime) / 1000).toFixed(2);
        document.getElementById('time-code').innerText = totalTime;
        document.getElementById('game-over-screen').style.display = 'flex';
    }}

    function gameLoop() {{
        if (!gameActive) return;
        let elapsed = Date.now() - lastMoveTime;
        let timeLeft = {MOVE_DELAY_MS} - elapsed;
        let pct = Math.max(0, (timeLeft / {MOVE_DELAY_MS}) * 100);
        timerBar.style.width = pct + '%';

        // Color change for urgency
        if (pct < 30) timerBar.style.backgroundColor = '#f00';
        else timerBar.style.backgroundColor = '#0f0';

        if (elapsed > {MOVE_DELAY_MS}) {{
            moveGlitch(); // Auto-teleport
        }}
        animationFrameId = requestAnimationFrame(gameLoop);
    }}
    
    function selectText(node) {{
        if (document.body.createTextRange) {{
            const range = document.body.createTextRange();
            range.moveToElementText(node);
            range.select();
        }} else if (window.getSelection) {{
            const selection = window.getSelection();
            const range = document.createRange();
            range.selectNodeContents(node);
            selection.removeAllRanges();
            selection.addRange(range);
        }}
    }}

    // START
    setTimeout(startGame, 500); // Brief delay to let assets load

    // MISS PENALTY
    levelImg.onmousedown = function() {{
        if (gameActive) {{
            document.body.style.backgroundColor = '#500';
            setTimeout(() => document.body.style.backgroundColor = '#080808', 50);
            moveGlitch();
        }}
    }}
</script>
</body>
</html>
"""

# --- TITLE WITH GLITCH CSS ---
st.markdown("""
    <style>
    @keyframes glitch-title {
        0% { text-shadow: 2px 2px 0px #f00, -2px -2px 0px #0ff; }
        90% { text-shadow: 2px 2px 0px #f00, -2px -2px 0px #0ff; }
        91% { text-shadow: -5px 5px 0px #f00, 5px -5px 0px #0ff; transform: skew(5deg); }
        92% { text-shadow: 5px -5px 0px #f00, -5px 5px 0px #0ff; transform: skew(-5deg); }
        93% { text-shadow: 0px 0px 0px #f00, 0px 0px 0px #0ff; transform: none; }
        100% { text-shadow: 2px 2px 0px #f00, -2px -2px 0px #0ff; }
    }
    .glitch-title {
        font-size: 3em; font-weight: bold; color: white; text-align: center;
        animation: glitch-title 2s infinite;
    }
    </style>
    <h1 class="glitch-title">DETROIT: ANOMALY [09]</h1>
    """, unsafe_allow_html=True)

# --- GAME STATES ---
if 'game_state' not in st.session_state:
    st.session_state.game_state = 'menu'

if st.session_state.game_state == 'menu':
    col1, col2 = st.columns([2,1])
    with col1:
        tag = st.text_input("OPERATIVE TAG (3 CHARS):", max_chars=3).upper()
    with col2:
        st.write("") # Spacer
        st.write("")
        if st.button(">> INITIALIZE <<", type="primary", use_container_width=True):
            if len(tag) == 3:
                st.session_state.player_tag = tag
                st.session_state.game_state = 'playing'
                st.rerun()

if st.session_state.game_state == 'playing':
    # RENDER THE JS GAME
    components.html(GAME_HTML, height=720)
    
    st.markdown("---")
    c1, c2 = st.columns([3, 1])
    with c1:
        final_time_input = st.text_input("PASTE FINAL TIME HERE:", placeholder="e.g., 18.45")
    with c2:
        st.write("") # spacer
        st.write("")
        if st.button("SUBMIT SCORE", type="primary", use_container_width=True):
            try:
                time_val = float(final_time_input)
                # --- SAVE TO SHEETS ---
                conn = st.connection("gsheets", type=GSheetsConnection)
                conn.update(worksheet="Scores", data=pd.DataFrame([{"Tag": st.session_state.player_tag, "Time": time_val}]))
                st.success("UPLOAD COMPLETE.")
                time.sleep(2)
                st.session_state.game_state = 'menu'
                st.rerun()
            except:
                st.error("ERROR: INVALID TIME OR CONNECTION FAILED.")

# LEADERBOARD ALWAYS VISIBLE
try:
    conn = st.connection("gsheets", type=GSheetsConnection)
    df = conn.read(worksheet="Scores", ttl=5).dropna()
    df['Time'] = pd.to_numeric(df['Time'])
    st.markdown("### GLOBAL OPERATIVES")
    st.dataframe(df.sort_values('Time').head(10).reset_index(drop=True), use_container_width=True)
except: pass