import streamlit as st
import time
import pandas as pd
import random
import base64
import io
from PIL import Image, ImageOps, ImageEnhance, ImageDraw
from streamlit_gsheets import GSheetsConnection
from streamlit_image_coordinates import streamlit_image_coordinates

st.set_page_config(page_title="DETROIT: ANOMALY [09]", layout="centered", initial_sidebar_state="collapsed")

# --- SETTINGS ---
GAME_WIDTH = 700
HIT_TOLERANCE = 50
MOVE_DELAY = 5.0    # Glitch moves every 5 seconds
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
    # Only used for the border now, animation is baked into GIF
    st.markdown(f"""
    <style>
        div[data-testid="stImage"] {{ position: relative !important; display: inline-block !important; overflow: hidden !important; }}
        div[data-testid="stImage"]::before {{
            content: ""; position: absolute;
            left: {l}%; top: {t}%; width: {w}%; height: {h}%;
            z-index: 900; pointer-events: none;
            border: 1px solid rgba(0, 255, 0, 0.3);
            box-shadow: 0 0 15px rgba(0, 255, 0, 0.2) inset;
            mix-blend-mode: hard-light;
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
        gb64 = get_base64("assets/glitch.gif")
        if not gb64: gb64 = get_base64("assets/glitch.avif")
        g_url = f"data:image/gif;base64,{gb64}" if gb64 else "https://media.giphy.com/media/oEI9uBYSzLpBK/giphy.gif"
        st.markdown(f'<div style="position:fixed;top:0;left:0;width:100%;height:100%;background:url({g_url});background-size:cover;z-index:10001;opacity:0.8;mix-blend-mode:hard-light;"></div>', unsafe_allow_html=True)
        time.sleep(0.4)
    placeholder.empty()

# --- RANDOMIZERS ---
def get_new_glitch_box():
    w = random.randint(120, 250)
    h = random.randint(120, 250)
    x1 = random.randint(50, NATIVE_SIZE - w - 50)
    y1 = random.randint(50, NATIVE_SIZE - h - 50)
    return (x1, y1, x1 + w, y1 + h)

# --- DATAMOSH GENERATOR ---
def create_datamosh_frame(base_img, box):
    frame = base_img.copy()
    try:
        glitch = frame.crop(box).convert('RGB')
        gw, gh = glitch.size
        # 1. Digital Artifacts (Macroblocking)
        block = random.randint(8, 32)
        glitch = glitch.resize((max(1, gw//block), max(1, gh//block)), Image.NEAREST)
        glitch = glitch.resize((gw, gh), Image.NEAREST)
        # 2. Signal Corruption (Green/Pink tint)
        y_ch, cb, cr = glitch.convert('YCbCr').split()
        if random.random() > 0.5: cb = ImageEnhance.Brightness(cb).enhance(random.choice([0.0, 2.0]))
        else: cr = ImageEnhance.Brightness(cr).enhance(random.choice([0.0, 2.0]))
        glitch = Image.merge('YCbCr', (y_ch, cb, cr)).convert('RGB')
        frame.paste(glitch, box)
    except: pass
    return frame

@st.cache_data(show_spinner=False, persist="disk")
def generate_scaled_gif(img_path, original_box, target_width, level_idx, glitch_seed):
    try:
        random.seed(glitch_seed)
        base_img = Image.open(img_path).convert("RGB")
        scale_factor = target_width / base_img.width
        target_height = int(base_img.height * scale_factor)
        base_img = base_img.resize((target_width, target_height), Image.Resampling.LANCZOS)

        x1, y1, x2, y2 = original_box
        scaled_box = (int(x1 * scale_factor), int(y1 * scale_factor), int(x2 * scale_factor), int(y2 * scale_factor))

        frames = []
        # 15 Normal frames (~3s wait)
        for _ in range(15): frames.append(base_img.copy())
        # 8 Datamosh frames (~0.8s visible glitch)
        for _ in range(8): frames.append(create_datamosh_frame(base_img, scaled_box))
            
        temp_file = f"lvl_{level_idx}_{glitch_seed}.gif"
        # 200ms normal, 100ms chaos
        frames[0].save(temp_file, format="GIF", save_all=True, append_images=frames[1:], duration=[200]*15 + [100]*8, loop=0)
        return temp_file, scaled_box
    except: return None, None

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
        'last_move_time': time.time(), 
        'glitch_seed': random.randint(1, 100000),
        'current_box': get_new_glitch_box()
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

# --- GAME LOOP ---
st.title("DETROIT: ANOMALY [09]")

if st.session_state.game_state == 'playing':
    if time.time() - st.session_state.last_move_time > MOVE_DELAY:
        st.session_state.glitch_seed = random.randint(1, 100000)
        st.session_state.current_box = get_new_glitch_box()
        st.session_state.last_move_time = time.time()
        st.rerun()

if st.session_state.game_state == "menu":
    tag = st.text_input("OPERATIVE TAG (3 CHARS):", max_chars=3).upper()
    if st.button(">> START SIMULATION <<", type="primary"):
        if len(tag) == 3:
            st.session_state.update({
                'game_state': 'playing', 'player_tag': tag, 'start_time': time.time(), 
                'current_level': 0, 'last_move_time': time.time(), 
                'current_box': get_new_glitch_box(), 'glitch_seed': random.randint(1, 100000)
            })
            st.rerun()
    st.markdown("### TOP AGENTS")
    st.dataframe(get_leaderboard(), hide_index=True, use_container_width=True)

elif st.session_state.game_state == "playing":
    lvl_idx = st.session_state.current_level
    
    elapsed = time.time() - st.session_state.last_move_time
    time_left = max(0.0, MOVE_DELAY - elapsed)
    st.progress(time_left / MOVE_DELAY, text=f"SECTOR 0{lvl_idx + 1} // SIGNAL STABLE FOR {max(0, time_left - 1.0):.1f}s")

    # Inject subtle border for extra visibility
    l, t = (st.session_state.current_box[0] / NATIVE_SIZE) * 100, (st.session_state.current_box[1] / NATIVE_SIZE) * 100
    w = ((st.session_state.current_box[2] - st.session_state.current_box[0]) / NATIVE_SIZE) * 100
    h = ((st.session_state.current_box[3] - st.session_state.current_box[1]) / NATIVE_SIZE) * 100
    inject_glitch_css(l, t, w, h)

    gif_path, scaled_box = generate_scaled_gif(LEVEL_FILES[lvl_idx], st.session_state.current_box, GAME_WIDTH, lvl_idx, st.session_state.glitch_seed)

    if gif_path and scaled_box:
        coords = streamlit_image_coordinates(gif_path, key=f"lvl_{lvl_idx}_{st.session_state.glitch_seed}", width=GAME_WIDTH)
        if coords:
            x1, y1, x2, y2 = scaled_box
            if time.time() - st.session_state.last_move_time > MOVE_DELAY:
                 st.toast("TOO SLOW! ANOMALY SHIFTED.", icon="⚠️")
                 st.session_state.glitch_seed = random.randint(1, 100000)
                 st.session_state.current_box = get_new_glitch_box()
                 st.session_state.last_move_time = time.time()
                 time.sleep(0.5)
                 st.rerun()
            elif (x1 - HIT_TOLERANCE) <= coords['x'] <= (x2 + HIT_TOLERANCE) and \
                 (y1 - HIT_TOLERANCE) <= coords['y'] <= (y2 + HIT_TOLERANCE):
                trigger_static_transition()
                if lvl_idx < 8: 
                    st.session_state.current_level += 1
                    st.session_state.glitch_seed = random.randint(1, 100000)
                    st.session_state.current_box = get_new_glitch_box()
                    st.session_state.last_move_time = time.time()
                    st.rerun()
                else: 
                    st.session_state.final_time = time.time() - st.session_state.start_time
                    st.session_state.game_state = 'game_over'
                    st.rerun()
            else:
                 st.toast("MISS! SEQUENCE RESET.", icon="❌")
                 st.session_state.glitch_seed = random.randint(1, 100000)
                 st.session_state.current_box = get_new_glitch_box()
                 st.session_state.last_move_time = time.time()
                 time.sleep(0.5)
                 st.rerun()
    
    # Smart refresh to keep timer updated without flashing
    if time_left < 1.5: time.sleep(0.2); st.rerun()
    else: time.sleep(1.0); st.rerun()

elif st.session_state.game_state == "game_over":
    st.balloons()
    st.write(f"AGENT: {st.session_state.player_tag} | TIME: {st.session_state.final_time:.2f}s")
    if st.button("UPLOAD SCORE", type="primary"):
        if save_score(st.session_state.player_tag, st.session_state.final_time):
            st.success("DATA UPLOADED.")
        else:
            st.error("UPLOAD FAILED.")
        time.sleep(2); st.session_state.game_state = 'menu'; st.rerun()
    st.markdown("### GLOBAL RANKINGS")
    st.dataframe(get_leaderboard(), hide_index=True, use_container_width=True)