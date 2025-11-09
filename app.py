import streamlit as st
import pandas as pd
import base64
import time
import json
from streamlit_gsheets import GSheetsConnection
import streamlit.components.v1 as components

st.set_page_config(page_title="DETROIT: ANOMALY [09]", layout="centered", initial_sidebar_state="collapsed")

# --- SETTINGS ---
MOVE_DELAY_MS = 1000  # 1 second to click. Hardcore mode.

# --- ASSET LOADER ---
def get_base64(bin_file):
    try:
        with open(bin_file, 'rb') as f:
            return f"data:image/png;base64,{base64.b64encode(f.read()).decode()}"
    except: return ""

# Load Level Images
LEVEL_IMAGES = [get_base64(f"assets/level{i}.png") for i in range(1, 10)]
# Load Glitch Texture (Prefer GIF for animation, fallback to AVIF)
GLITCH_ASSET = get_base64("assets/glitch.gif")
if not GLITCH_ASSET:
    GLITCH_ASSET = get_base64("assets/glitch.avif")

# --- JAVASCRIPT GAME ENGINE ---
GAME_HTML = f"""
<!DOCTYPE html>
<html>
<head>
<style>
    /* --- GLOBAL STYLES --- */
    body {{ margin: 0; background-color: #080808; color: #0f0; font-family: 'Courier New', monospace; overflow: hidden; user-select: none; }}
    #game-container {{ position: relative; width: 700px; height: 700px; margin: 0 auto; border: 2px solid #333; overflow: hidden; }}
    #level-img {{ width: 100%; height: 100%; object-fit: cover; pointer-events: auto; cursor: crosshair; }}
    
    /* --- THE GLITCH TARGET --- */
    #glitch-target {{
        position: absolute;
        z-index: 1000;
        display: none; /* Hidden until game starts */
        border: 2px solid #0f0;
        background-size: cover !important;
        mix-blend-mode: hard-light;
        animation: violent-flash 0.15s infinite; /* CSS Animation + GIF Texture */
        cursor: crosshair;
    }}
    @keyframes violent-flash {{
        0% {{ opacity: 0.9; filter: hue-rotate(0deg) invert(0) contrast(1.2); }}
        25% {{ opacity: 0.7; filter: hue-rotate(90deg) invert(1) contrast(2); }}
        50% {{ opacity: 1.0; filter: hue-rotate(180deg) invert(0) contrast(1.5); }}
        75% {{ opacity: 0.6; filter: hue-rotate(270deg) invert(1) contrast(3); }}
        100% {{ opacity: 0.9; filter: hue-rotate(0deg) invert(0) contrast(1.2); }}
    }}

    /* --- HUD & UI --- */
    #hud {{ position: absolute; top: 10px; left: 10px; z-index: 1001; background: rgba(0,0,0,0.8); padding: 5px 15px; pointer-events: none; font-size: 24px; border-left: 4px solid #0f0; }}
    #timer-bar {{ position: absolute; top: 0; left: 0; height: 8px; background-color: #f00; width: 100%; z-index: 1002; transition: width 0.1s linear; }}
    
    /* --- CRT SCANLINE FILTER --- */
    .scanlines {{
        position: fixed; top: 0; left: 0; width: 100vw; height: 100vh; pointer-events: none; z-index: 9999;
        background: linear-gradient(rgba(18, 16, 16, 0) 50%, rgba(0, 0, 0, 0.25) 50%), linear-gradient(90deg, rgba(255, 0, 0, 0.06), rgba(0, 255, 0, 0.02), rgba(0, 0, 255, 0.06));
        background-size: 100% 4px, 3px 100%; opacity: 0.3;
    }}

    /* --- END SCREEN --- */
    #game-over-screen {{
        display: none; position: absolute; top: 0; left: 0; width: 100%; height: 100%;
        background: rgba(0,0,0,0.95); color: #0f0; z-index: 2000;
        flex-direction: column; justify-content: center; align-items: center; text-align: center;
    }}
    .copy-code {{ font-size: 48px; font-weight: bold; color: #fff; background: #000; padding: 20px 40px; border: 4px dashed #0f0; margin: 30px; cursor: pointer; transition: all 0.2s; }}
    .copy-code:active {{ background: #0f0; color: #000; transform: scale(0.95); }}
</style>
</head>
<body>
    <div class="scanlines"></div>
    <div id="game-container">
        <div id="timer-bar"></div>
        <div id="hud">SECTOR: <span id="sector-num">01</span> / 09</div>
        <img id="level-img" src="" onmousedown="missClick()">
        <div id="glitch-target" onmousedown="hitGlitch(event)"></div>
        
        <div id="game-over-screen">
            <h1>SIMULATION COMPLETE</h1>
            <p>FINAL TIME CODE:</p>
            <div class="copy-code" id="time-code" onclick="navigator.clipboard.writeText(this.innerText); let old=this.innerText; this.innerText='COPIED!'; setTimeout(()=>this.innerText=old, 1000)">0.00</div>
            <p>▲ CLICK TO COPY ▲</p>
        </div>
    </div>

<script>
    // --- INJECT PYTHON VARIABLES ---
    const LEVELS = {json.dumps(LEVEL_IMAGES)};
    const GLITCH_TEXTURE = "{GLITCH_ASSET}";
    const DELAY_MS = {MOVE_DELAY_MS};

    // --- GAME VARIABLES ---
    let currentLevel = 0;
    let startTime = 0;
    let lastMoveTime = 0;
    let gameActive = false;
    let animFrame;

    // --- DOM ELEMENTS ---
    const glitch = document.getElementById('glitch-target');
    const levelImg = document.getElementById('level-img');
    const timerBar = document.getElementById('timer-bar');
    const hudSector = document.getElementById('sector-num');

    // --- MAIN LOGIC ---
    function startGame() {{
        currentLevel = 0;
        gameActive = true;
        // APPLY THE GLITCH TEXTURE HERE
        glitch.style.backgroundImage = 'url(' + GLITCH_TEXTURE + ')';
        startTime = Date.now();
        loadLevel(0);
        gameLoop();
    }}

    function loadLevel(idx) {{
        hudSector.innerText = '0' + (idx + 1);
        levelImg.src = LEVELS[idx];
        moveGlitch();
    }}

    function moveGlitch() {{
        lastMoveTime = Date.now();
        // Random size 80px - 250px
        let w = Math.floor(Math.random() * 170) + 80;
        let h = Math.floor(Math.random() * 170) + 80;
        // Keep inside 700x700 box
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
        e.stopPropagation(); // IMPORTANT: Don't trigger a miss!

        // White flash transition
        let flash = document.createElement('div');
        flash.style.cssText = 'position:fixed;top:0;left:0;width:100%;height:100%;background:#fff;z-index:99999;pointer-events:none;';
        document.body.appendChild(flash);
        setTimeout(() => flash.remove(), 50);

        currentLevel++;
        if (currentLevel < 9) {{
            loadLevel(currentLevel);
        }} else {{
            endGame();
        }}
    }}

    function missClick() {{
        if (gameActive) {{
            // Red flash penalty
            let flash = document.createElement('div');
            flash.style.cssText = 'position:fixed;top:0;left:0;width:100%;height:100%;background:rgba(255,0,0,0.3);z-index:99998;pointer-events:none;';
            document.body.appendChild(flash);
            setTimeout(() => flash.remove(), 100);
            moveGlitch(); // Teleport immediately on miss
        }}
    }}

    function endGame() {{
        gameActive = false;
        cancelAnimationFrame(animFrame);
        let finalTimeStr = ((Date.now() - startTime) / 1000).toFixed(2);
        document.getElementById('time-code').innerText = finalTimeStr;
        document.getElementById('game-over-screen').style.display = 'flex';
    }}

    function gameLoop() {{
        if (!gameActive) return;
        let elapsed = Date.now() - lastMoveTime;
        let timeLeft = DELAY_MS - elapsed;
        let pct = Math.max(0, (timeLeft / DELAY_MS) * 100);
        
        timerBar.style.width = pct + '%';
        // Color urgency
        if (pct < 25) timerBar.style.backgroundColor = '#f00';
        else if (pct < 50) timerBar.style.backgroundColor = '#ff0';
        else timerBar.style.backgroundColor = '#0f0';

        if (elapsed > DELAY_MS) moveGlitch();
        animFrame = requestAnimationFrame(gameLoop);
    }}

    // WAIT 1s FOR ASSETS TO LOAD THEN START
    setTimeout(startGame, 1000);

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
        92% { text-shadow: -5px 5px 0px #f00, 5px -5px 0px #0ff; transform: skew(5deg); }
        94% { text-shadow: 5px -5px 0px #f00, -5px 5px 0px #0ff; transform: skew(-5deg); }
        100% { text-shadow: 2px 2px 0px #f00, -2px -2px 0px #0ff; transform: skew(0deg); }
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
    # Render the full JS game in an iframe
    components.html(GAME_HTML, height=720)

    # Render the Score Submission UI below it
    st.markdown("---")
    st.write("### 📡 SECURE UPLINK")
    st.caption("Click the green time code above to copy it, then paste it here:")
    
    c1, c2 = st.columns([3, 1])
    with c1:
        final_time_input = st.text_input("PASTE CODE HERE:", label_visibility="collapsed", placeholder="e.g., 18.45")
    with c2:
        if st.button("TRANSMIT DATA", type="primary", use_container_width=True):
            if final_time_input:
                try:
                    t_val = float(final_time_input)
                    conn = st.connection("gsheets", type=GSheetsConnection)
                    conn.update(worksheet="Scores", data=pd.DataFrame([{"Tag": st.session_state.player_tag, "Time": t_val}]))
                    st.success("UPLOAD COMPLETE.")
                    time.sleep(2)
                    st.session_state.game_state = 'menu'
                    st.rerun()
                except:
                    st.error("UPLOAD FAILED. Check connection.")
            else:
                st.warning("MISSING TIME CODE")
    
    if st.button("ABORT MISSION (RETURN TO MENU)"):
        st.session_state.game_state = 'menu'
        st.rerun()

# --- LEADERBOARD ---
try:
    conn = st.connection("gsheets", type=GSheetsConnection)
    df = conn.read(worksheet="Scores", ttl=5).dropna()
    df['Time'] = pd.to_numeric(df['Time'])
    st.markdown("### GLOBAL OPERATIVES")
    st.dataframe(df.sort_values('Time').head(10).reset_index(drop=True), use_container_width=True)
except:
    st.caption("Leaderboard offline.")