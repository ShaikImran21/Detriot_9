import streamlit as st
import pandas as pd
import base64
import time
import json
from streamlit_gsheets import GSheetsConnection
import streamlit.components.v1 as components

st.set_page_config(page_title="DETROIT: ANOMALY [09]", layout="centered", initial_sidebar_state="collapsed")

# --- SETTINGS ---
MOVE_DELAY_MS = 4000  # Glitch moves every 4 seconds (in milliseconds)

# --- HELPER: ASSET LOADER ---
def get_base64(bin_file):
    try:
        with open(bin_file, 'rb') as f:
            return f"data:image/png;base64,{base64.b64encode(f.read()).decode()}"
    except: return ""

# --- LOAD ASSETS INTO MEMORY ---
# We must preload all images as base64 to pass them to JavaScript
LEVEL_IMAGES = [get_base64(f"assets/level{i}.png") for i in range(1, 10)]
# Try to load GIF, fallback to AVIF, fallback to nothing
GLITCH_ASSET = get_base64("assets/glitch.gif")
if not GLITCH_ASSET: GLITCH_ASSET = get_base64("assets/glitch.avif")

# --- JAVASCRIPT GAME ENGINE ---
# This is a complete game written in HTML/JS/CSS that will run inside an iframe
GAME_HTML = f"""
<!DOCTYPE html>
<html>
<head>
<style>
    body {{ margin: 0; background-color: #080808; color: #0f0; font-family: 'Courier New', monospace; overflow: hidden; }}
    #game-container {{ position: relative; width: 700px; height: 700px; margin: 0 auto; border: 2px solid #333; }}
    #level-img {{ width: 100%; height: 100%; object-fit: cover; }}
    #glitch-target {{
        position: absolute;
        border: 2px solid #0f0;
        background-image: url('{GLITCH_ASSET}');
        background-size: cover;
        mix-blend-mode: hard-light;
        opacity: 0.8;
        cursor: crosshair;
        display: none; /* Hidden initially */
    }}
    #hud {{ 
        position: absolute; top: 10px; left: 10px; z-index: 1001; 
        background: rgba(0,0,0,0.7); padding: 5px 10px; pointer-events: none;
    }}
    #timer-bar {{
        position: absolute; top: 0; left: 0; height: 5px; background-color: #0f0; width: 100%; z-index: 1002;
        transition: width 0.1s linear;
    }}
    /* CRT EFFECT */
    .scanlines {{
        position: fixed; top: 0; left: 0; width: 100vw; height: 100vh; pointer-events: none; z-index: 9999;
        background: linear-gradient(rgba(18, 16, 16, 0) 50%, rgba(0, 0, 0, 0.25) 50%), linear-gradient(90deg, rgba(255, 0, 0, 0.06), rgba(0, 255, 0, 0.02), rgba(0, 0, 255, 0.06));
        background-size: 100% 4px, 3px 100%; opacity: 0.3;
    }}
    #game-over-screen {{
        display: none; position: absolute; top: 0; left: 0; width: 100%; height: 100%;
        background: rgba(0,0,0,0.9); color: #0f0; z-index: 2000;
        flex-direction: column; justify-content: center; align-items: center; text-align: center;
    }}
    .copy-code {{ font-size: 24px; background: #111; padding: 10px; border: 1px dashed #0f0; margin: 20px; user-select: all; }}
</style>
</head>
<body>
    <div class="scanlines"></div>
    <div id="timer-bar"></div>
    <div id="game-container">
        <div id="hud">SECTOR: <span id="sector-num">01</span> / 09</div>
        <img id="level-img" src="">
        <div id="glitch-target" onclick="hitGlitch()"></div>
        <div id="game-over-screen">
            <h1>SIMULATION COMPLETE</h1>
            <p>FINAL TIME:</p>
            <h2 id="final-time-display">0.00s</h2>
            <p>COPY THIS TIME CODE BELOW TO SAVE YOUR SCORE:</p>
            <div class="copy-code" id="time-code"></div>
        </div>
    </div>

<script>
    // --- GAME STATE ---
    const LEVELS = {json.dumps(LEVEL_IMAGES)};
    let currentLevel = 0;
    let startTime = 0;
    let lastMoveTime = 0;
    let gameActive = false;
    let moveInterval;

    const container = document.getElementById('game-container');
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
        // Random size (50px to 200px)
        let w = Math.floor(Math.random() * 150) + 50;
        let h = Math.floor(Math.random() * 150) + 50;
        // Random position within 700x700 container
        let x = Math.floor(Math.random() * (700 - w));
        let y = Math.floor(Math.random() * (700 - h));
        
        glitch.style.width = w + 'px';
        glitch.style.height = h + 'px';
        glitch.style.left = x + 'px';
        glitch.style.top = y + 'px';
        glitch.style.display = 'block';
    }}

    function hitGlitch() {{
        if (!gameActive) return;
        
        // Flash effect
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
        let totalTime = ((Date.now() - startTime) / 1000).toFixed(2);
        document.getElementById('final-time-display').innerText = totalTime + 's';
        document.getElementById('time-code').innerText = totalTime;
        document.getElementById('game-over-screen').style.display = 'flex';
    }}

    function gameLoop() {{
        if (!gameActive) return;
        
        let elapsed = Date.now() - lastMoveTime;
        let timeLeft = {MOVE_DELAY} - elapsed;
        
        // Update timer bar width
        let pct = (timeLeft / {MOVE_DELAY}) * 100;
        timerBar.style.width = pct + '%';

        if (elapsed > {MOVE_DELAY}) {{
            moveGlitch(); // Auto-move if too slow
        }}
        requestAnimationFrame(gameLoop);
    }}

    // Start immediately when loaded
    startGame();

    // Penalty for missing click (clicking background instead of glitch)
    levelImg.onclick = function() {{
        if (gameActive) {{
            document.body.style.backgroundColor = '#500'; // Red flash for miss
            setTimeout(() => document.body.style.backgroundColor = '#080808', 50);
            moveGlitch(); // Teleport immediately on miss
        }}
    }}

</script>
</body>
</html>
"""

# --- STREAMLIT PYTHON SIDE ---
st.markdown("## DETROIT: ANOMALY [09]")

# If not playing, show menu
if 'game_state' not in st.session_state:
    st.session_state.game_state = 'menu'

if st.session_state.game_state == 'menu':
    tag = st.text_input("OPERATIVE TAG (3 CHARS):", max_chars=3).upper()
    if st.button("START SIMULATION", type="primary", use_container_width=True):
        if len(tag) == 3:
            st.session_state.player_tag = tag
            st.session_state.game_state = 'playing'
            st.rerun()

# If playing, show the JS game iframe
if st.session_state.game_state == 'playing':
    # Render the JS game. It runs independently of Python now.
    components.html(GAME_HTML, height=750)
    
    st.markdown("---")
    st.write("### 📡 DATA UPLINK")
    st.caption("When the simulation ends, copy the GREEN time code above and paste it here to save your score.")
    
    col1, col2 = st.columns([3, 1])
    with col1:
        final_time_input = st.text_input("PASTE TIME CODE HERE:", key="time_input")
    with col2:
        st.write("") # spacer
        st.write("") # spacer
        if st.button("SUBMIT SCORE", type="primary"):
            try:
                # Validate it's a real number
                time_val = float(final_time_input)
                # Save to sheets
                try:
                    conn = st.connection("gsheets", type=GSheetsConnection)
                    conn.update(worksheet="Scores", data=pd.DataFrame([{"Tag": st.session_state.player_tag, "Time": time_val}]))
                    st.success("✅ SCORE SAVED!")
                    time.sleep(2)
                    st.session_state.game_state = 'menu'
                    st.rerun()
                except Exception as e:
                    st.error(f"Database Error: {e}")
            except:
                st.error("Invalid Time Code.")

    if st.button("ABORT / RESTART"):
        st.session_state.game_state = 'menu'
        st.rerun()

# Always show leaderboard below
try:
    conn = st.connection("gsheets", type=GSheetsConnection)
    df = conn.read(worksheet="Scores", ttl=5).dropna()
    df['Time'] = pd.to_numeric(df['Time'])
    st.markdown("### TOP AGENTS")
    st.dataframe(df.sort_values('Time').head(10).reset_index(drop=True), use_container_width=True)
except:
    st.info("Leaderboard currently offline.")