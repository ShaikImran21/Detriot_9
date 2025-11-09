import streamlit as st
import pandas as pd
import base64
import time
import json
import random
import io
from PIL import Image, ImageEnhance, ImageOps
from streamlit_gsheets import GSheetsConnection
import streamlit.components.v1 as components

st.set_page_config(page_title="DETROIT: ANOMALY [09]", layout="centered", initial_sidebar_state="collapsed")

# --- SETTINGS ---
MOVE_DELAY_MS = 1000  # 1 SECOND per glitch.
HIT_TOLERANCE_PX = 50 # JS needs this for hit checking

# --- PYTHON ASSET GENERATOR ---
def get_base64(bin_file):
    try:
        with open(bin_file, 'rb') as f: return f"data:image/png;base64,{base64.b64encode(f.read()).decode()}"
    except: return ""

# Pre-generate a violent glitch GIF using Python PIL
@st.cache_data(ttl=3600)
def get_python_glitch_texture():
    try:
        # Try to load user's base glitch file if it exists for texture
        base = Image.open("assets/glitch.gif") if os.path.exists("assets/glitch.gif") else Image.new("RGB", (200, 200), (255, 0, 255))
        base = base.convert("RGB")
        frames = []
        # Generate 10 violently mutated frames
        for _ in range(10):
            frame = base.copy()
            # Python image violence applied here
            frame = ImageOps.invert(frame)
            frame = ImageEnhance.Contrast(frame).enhance(4.0)
            r, g, b = frame.split()
            frame = Image.merge("RGB", (random.choice([r,g,b]), random.choice([r,g,b]), random.choice([r,g,b])))
            frames.append(frame)
        
        # Save to base64 GIF string
        gif_io = io.BytesIO()
        frames[0].save(gif_io, format='GIF', save_all=True, append_images=frames[1:], duration=50, loop=0)
        return f"data:image/gif;base64,{base64.b64encode(gif_io.getvalue()).decode()}"
    except: return get_base64("assets/glitch.gif") # Fallback

# --- LOAD RESOURCES ---
LEVEL_IMAGES = [get_base64(f"assets/level{i}.png") for i in range(1, 10)]
GLITCH_TEXTURE = get_python_glitch_texture()

# --- JAVASCRIPT ENGINE (THE NO-RELOAD ZONE) ---
GAME_HTML = f"""
<!DOCTYPE html>
<html>
<head>
<style>
    /* --- GLOBAL STYLES --- */
    body {{ margin: 0; background: #080808; overflow: hidden; user-select: none; font-family: monospace; }}
    #game-container {{ width: 700px; height: 700px; margin: 0 auto; position: relative; border: 2px solid #333; }}
    #level-img {{ width: 100%; height: 100%; object-fit: cover; pointer-events: auto; }}
    
    /* --- THE GLITCH (PYTHON TEXTURE + CSS VIOLENCE) --- */
    #glitch-target {{
        position: absolute; display: none; z-index: 1000;
        background-image: url('{GLITCH_TEXTURE}');
        background-size: cover;
        mix-blend-mode: hard-light;
        border: 2px solid #0f0;
        box-shadow: 0 0 15px rgba(0,255,0,0.5);
        animation: css-violence 0.1s infinite;
        cursor: crosshair;
    }}
    @keyframes css-violence {{
        0% {{ filter: hue-rotate(0deg) invert(0); transform: translate(0,0) skew(0deg); }}
        25% {{ filter: hue-rotate(90deg) invert(1); transform: translate(-2px,2px) skew(2deg); }}
        50% {{ filter: hue-rotate(180deg) invert(0); transform: translate(2px,-2px) skew(-2deg); }}
        75% {{ filter: hue-rotate(270deg) invert(1); transform: translate(-2px,-2px) skew(1deg); }}
        100% {{ filter: hue-rotate(360deg) invert(0); transform: translate(0,0) skew(0deg); }}
    }}

    /* --- UI --- */
    #hud {{ position: absolute; top: 10px; left: 10px; color: #0f0; background: rgba(0,0,0,0.8); padding: 5px 15px; font-size: 24px; border-left: 4px solid #0f0; z-index: 1001; }}
    #timer-bar {{ position: absolute; top: 0; left: 0; height: 8px; background: #f00; width: 100%; z-index: 1002; }}
    .scanlines {{ position: fixed; top: 0; left: 0; width: 100vw; height: 100vh; pointer-events: none; z-index: 9999; background: linear-gradient(rgba(18, 16, 16, 0) 50%, rgba(0, 0, 0, 0.25) 50%), linear-gradient(90deg, rgba(255, 0, 0, 0.06), rgba(0, 255, 0, 0.02), rgba(0, 0, 255, 0.06)); background-size: 100% 4px, 3px 100%; opacity: 0.3; }}
    
    /* --- END SCREEN --- */
    #game-over {{ display: none; position: absolute; top: 0; left: 0; width: 100%; height: 100%; background: rgba(0,0,0,0.95); color: #fff; flex-direction: column; justify-content: center; align-items: center; z-index: 2000; }}
    .copy-code {{ font-size: 48px; color: #0f0; border: 4px dashed #0f0; padding: 20px; margin: 30px; cursor: pointer; }}
</style>
</head>
<body>
    <div class="scanlines"></div>
    <div id="game-container">
        <div id="timer-bar"></div>
        <div id="hud">SECTOR: <span id="sector">01</span> / 09</div>
        <img id="level-img" src="">
        <div id="glitch-target"></div>
        <div id="game-over">
            <h1>SIMULATION COMPLETE</h1>
            <p>FINAL TIME CODE:</p>
            <div class="copy-code" id="time-code" onclick="navigator.clipboard.writeText(this.innerText); this.style.color='#fff'">0.00</div>
            <p>▲ CLICK TO COPY ▲</p>
        </div>
    </div>

<script>
    const LEVELS = {json.dumps(LEVEL_IMAGES)};
    const MOVE_DELAY = {MOVE_DELAY_MS};
    let level = 0, start = 0, lastMove = 0, active = false, anim;

    const el = (id) => document.getElementById(id);
    const glitch = el('glitch-target');

    function init() {{
        level = 0; active = true; start = Date.now();
        loadLevel(0); loop();
    }}

    function loadLevel(idx) {{
        el('sector').innerText = '0' + (idx + 1);
        el('level-img').src = LEVELS[idx];
        moveGlitch();
    }}

    function moveGlitch() {{
        lastMove = Date.now();
        let w = Math.floor(Math.random() * 150) + 100;
        let h = Math.floor(Math.random() * 150) + 100;
        glitch.style.width = w + 'px'; glitch.style.height = h + 'px';
        glitch.style.left = Math.floor(Math.random() * (700 - w)) + 'px';
        glitch.style.top = Math.floor(Math.random() * (700 - h)) + 'px';
        glitch.style.display = 'block';
    }}

    glitch.onmousedown = (e) => {{
        if (!active) return;
        e.stopPropagation();
        // Flash
        let f = document.createElement('div');
        f.style.cssText = 'position:fixed;top:0;left:0;width:100%;height:100%;background:#fff;z-index:99999';
        document.body.appendChild(f); setTimeout(() => f.remove(), 50);
        
        level++;
        if (level < 9) loadLevel(level);
        else endGame();
    }};

    el('level-img').onmousedown = () => {{
        if (active) {{
            let f = document.createElement('div');
            f.style.cssText = 'position:fixed;top:0;left:0;width:100%;height:100%;background:rgba(255,0,0,0.5);z-index:99998';
            document.body.appendChild(f); setTimeout(() => f.remove(), 50);
            moveGlitch();
        }}
    }};

    function endGame() {{
        active = false; cancelAnimationFrame(anim);
        el('time-code').innerText = ((Date.now() - start) / 1000).toFixed(2);
        el('game-over').style.display = 'flex';
    }}

    function loop() {{
        if (!active) return;
        let elapsed = Date.now() - lastMove;
        el('timer-bar').style.width = Math.max(0, ((MOVE_DELAY - elapsed) / MOVE_DELAY) * 100) + '%';
        if (elapsed > MOVE_DELAY) moveGlitch();
        anim = requestAnimationFrame(loop);
    }}

    setTimeout(init, 1000);
</script>
</body>
</html>
"""

# --- PYTHON INTERFACE ---
st.markdown("""
    <style>
    .main-title { font-size: 3em; font-weight: 800; color: #fff; text-align: center; animation: title-glitch 1s infinite; }
    @keyframes title-glitch {
        0% { text-shadow: 2px 2px #f00, -2px -2px #0ff; }
        50% { text-shadow: -2px -2px #f00, 2px 2px #0ff; transform: skew(2deg); }
        100% { text-shadow: 2px 2px #f00, -2px -2px #0ff; }
    }
    </style>
    <div class="main-title">DETROIT: ANOMALY [09]</div>
    """, unsafe_allow_html=True)

if 'game_state' not in st.session_state: st.session_state.game_state = 'menu'

if st.session_state.game_state == 'menu':
    c1, c2 = st.columns([2,1])
    with c1: tag = st.text_input("TAG:", max_chars=3).upper()
    with c2:
        st.write(""); st.write("")
        if st.button("INITIALIZE", use_container_width=True) and len(tag)==3:
            st.session_state.player_tag = tag
            st.session_state.game_state = 'playing'
            st.rerun()

if st.session_state.game_state == 'playing':
    components.html(GAME_HTML, height=720)
    st.caption("Paste the final time code here to save:")
    c1, c2 = st.columns([3,1])
    with c1: t_code = st.text_input("TIME CODE:", label_visibility="collapsed")
    with c2:
        if st.button("SUBMIT", use_container_width=True):
            try:
                conn = st.connection("gsheets", type=GSheetsConnection)
                conn.update(worksheet="Scores", data=pd.DataFrame([{"Tag": st.session_state.player_tag, "Time": float(t_code)}]))
                st.success("SAVED!"); time.sleep(2); st.session_state.game_state = 'menu'; st.rerun()
            except: st.error("ERROR")
    if st.button("ABORT"): st.session_state.game_state = 'menu'; st.rerun()

try:
    conn = st.connection("gsheets", type=GSheetsConnection)
    st.dataframe(conn.read(worksheet="Scores", ttl=5).sort_values('Time').head(10), use_container_width=True)
except: pass