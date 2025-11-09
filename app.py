import streamlit as st
import pandas as pd
import base64
import time
import json
from streamlit_gsheets import GSheetsConnection
import streamlit.components.v1 as components

st.set_page_config(page_title="DETROIT: ANOMALY [09]", layout="centered", initial_sidebar_state="collapsed")

# --- SETTINGS ---
MOVE_DELAY_MS = 4000  # Glitch moves every 4 seconds (4000 ms)

# --- HELPER: ASSET LOADER ---
def get_base64(bin_file):
    try:
        with open(bin_file, 'rb') as f:
            return f"data:image/png;base64,{base64.b64encode(f.read()).decode()}"
    except: return ""

# --- LOAD ASSETS ---
LEVEL_IMAGES = [get_base64(f"assets/level{i}.png") for i in range(1, 10)]
GLITCH_ASSET = get_base64("assets/glitch.gif")
if not GLITCH_ASSET: GLITCH_ASSET = get_base64("assets/glitch.avif")

# --- JAVASCRIPT GAME ENGINE ---
GAME_HTML = f"""
<!DOCTYPE html>
<html>
<head>
<style>
    body {{ margin: 0; background-color: #080808; color: #0f0; font-family: 'Courier New', monospace; overflow: hidden; }}
    #game-container {{ position: relative; width: 700px; height: 700px; margin: 0 auto; border: 2px solid #333; }}
    #level-img {{ width: 100%; height: 100%; object-fit: cover; pointer-events: auto; }}
    #glitch-target {{
        position: absolute;
        z-index: 1000; /* Ensure it's on top */
        border: 2px solid #0f0;
        background-image: url('{GLITCH_ASSET}');
        background-size: cover;
        mix-blend-mode: hard-light;
        opacity: 0.8;
        cursor: crosshair;
        display: none;
    }}
    #hud {{ 
        position: absolute; top: 10px; left: 10px; z-index: 1001; 
        background: rgba(0,0,0,0.7); padding: 5px 10px; pointer-events: none;
    }}
    #timer-bar {{
        position: absolute; top: 0; left: 0; height: 5px; background-color: #0f0; width: 100%; z-index: 1002;
    }}
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
    .copy-code {{ font-size: 32px; font-weight: bold; color: #fff; background: #000; padding: 15px; border: 2px dashed #0f0; margin: 20px; user-select: all; }}
</style>
</head>
<body>
    <div class="scanlines"></div>
    <div id="game-container">
        <div id="timer-bar"></div>
        <div id="hud">SECTOR: <span id="sector-num">01</span> / 09</div>
        <img id="level-img" src="">
        <div id="glitch-target" onclick="hitGlitch(event)"></div>
        
        <div id="game-over-screen">
            <h1>SIMULATION COMPLETE</h1>
            <p>FINAL TIME:</p>
            <h2 id="final-time-display" style="font-size: 48px; margin: 10px 0;">0.00s</h2>
            <p>▼ COPY THIS CODE TO SAVE ▼</p>
            <div class="copy-code" id="time-code"></div>
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
        let w = Math.floor(Math.random() * 150) + 80;
        let h = Math.floor(Math.random() * 150) + 80;
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
        e.stopPropagation(); // Prevent double-clicking background
        
        // Flash white on hit
        document.body.style.backgroundColor = '#fff';
        setTimeout(() => document.body.style.backgroundColor = '#080808', 50);

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
        document.getElementById('final-time-display').innerText = totalTime + 's';
        document.getElementById('time-code').innerText = totalTime;
        document.getElementById('game-over-screen').style.display = 'flex';
    }}

    function gameLoop() {{
        if (!gameActive) return;
        let elapsed = Date.now() - lastMoveTime;
        let timeLeft = {MOVE_DELAY_MS} - elapsed;
        let pct = Math.max(0, (timeLeft / {MOVE_DELAY_MS}) * 100);
        timerBar.style.width = pct + '%';

        if (elapsed > {MOVE_DELAY_MS}) {{
            moveGlitch();
        }}
        animationFrameId = requestAnimationFrame(gameLoop);
    }}

    // Start game immediately
    startGame();

    // Miss penalty
    levelImg.onclick = function() {{
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

# --- STREAMLIT PYTHON SIDE ---
st.markdown("## DETROIT: ANOMALY [09]")

if 'game_state' not in st.session_state:
    st.session_state.game_state = 'menu'

if st.session_state.game_state == 'menu':
    tag = st.text_input("OPERATIVE TAG (3 CHARS):", max_chars=3).upper()
    if st.button("START SIMULATION", type="primary", use_container_width=True):
        if len(tag) == 3:
            st.session_state.player_tag = tag
            st.session_state.game_state = 'playing'
            st.rerun()

if st.session_state.game_state == 'playing':
    # RENDER JS GAME
    components.html(GAME_HTML, height=720)
    
    st.markdown("---")
    st.write("### 📡 DATA UPLINK")
    st.caption("Copy the GREEN time code from the game screen above and paste it here.")
    
    c1, c2 = st.columns([3, 1])
    with c1:
        final_time_input = st.text_input("PASTE CODE HERE:", label_visibility="collapsed", placeholder="e.g., 24.53")
    with c2:
        if st.button("SUBMIT", type="primary", use_container_width=True):
            try:
                time_val = float(final_time_input)
                conn = st.connection("gsheets", type=GSheetsConnection)
                conn.update(worksheet="Scores", data=pd.DataFrame([{"Tag": st.session_state.player_tag, "Time": time_val}]))
                st.success("✅ SAVED!")
                time.sleep(2)
                st.session_state.game_state = 'menu'
                st.rerun()
            except Exception as e:
                st.error("INVALID CODE OR CONNECTION FAILED.")

# Always show leaderboard
try:
    conn = st.connection("gsheets", type=GSheetsConnection)
    df = conn.read(worksheet="Scores", ttl=5).dropna()
    df['Time'] = pd.to_numeric(df['Time'])
    st.markdown("### TOP AGENTS")
    st.dataframe(df.sort_values('Time').head(10).reset_index(drop=True), use_container_width=True)
except: pass