import streamlit as st
import time
import pandas as pd
import random
import base64
from PIL import Image, ImageOps, ImageEnhance
from streamlit_image_coordinates import streamlit_image_coordinates

st.set_page_config(page_title="DETROIT: Anomaly [09]", layout="centered", initial_sidebar_state="collapsed")

GAME_WIDTH = 700
BASE_MOVE_DELAY = 15.0  # base seconds before glitch teleports
BASE_HIT_TOLERANCE = 100
BASE_MIN_BOX_SIZE = 60
BASE_MAX_BOX_SIZE = 250
MAX_MISSES = 3

LEVEL_IMGS = [
    "assets/level1.png", "assets/level2.png", "assets/level3.png",
    "assets/level4.png", "assets/level5.png", "assets/level6.png",
    "assets/level7.png", "assets/level8.png", "assets/level9.png"
]

def get_base64(bin_file):
    try:
        with open(bin_file, "rb") as f:
            return base64.b64encode(f.read()).decode()
    except:
        return None

def inject_css():
    st.markdown(
        """
        <style>
        .stApp { background-color: #080808; color: #d0d0d0; font-family: 'Courier New', monospace; }
        #MainMenu, footer, header {visibility:hidden;}
        .block-container {display: flex; justify-content: center; align-items: center; flex-direction: column;}
        </style>
        """, unsafe_allow_html=True)

def trigger_static_transition():
    st.markdown('<audio src="https://www.myinstants.com/media/sounds/static-noise.mp3" autoplay style="display:none;"></audio>', unsafe_allow_html=True)
    placeholder = st.empty()
    with placeholder.container():
        st.markdown('<div style="position:fixed;top:0;left:0;width:100%;height:100%;background:#111;z-index:10000;"></div>', unsafe_allow_html=True)
        time.sleep(0.1)
        gb64 = get_base64("assets/glitch.gif")
        if not gb64:
            gb64 = get_base64("assets/glitch.avif")
        g_url = f"data:image/gif;base64,{gb64}" if gb64 else "https://media.giphy.com/media/oEI9uBYSzLpBK/giphy.gif"
        st.markdown(f'<div style="position:fixed;top:0;left:0;width:100%;height:100%;background:url({g_url});background-size:cover;opacity:0.8;mix-blend-mode:hard-light;z-index:10001;"></div>', unsafe_allow_html=True)
        time.sleep(0.4)
    placeholder.empty()

def get_glitch_box(level):
    # Reduce glitch size as level increases
    min_size = max(BASE_MIN_BOX_SIZE, BASE_MAX_BOX_SIZE - level * 20)
    max_size = min(BASE_MAX_BOX_SIZE, BASE_MAX_BOX_SIZE - level * 15)
    w = random.randint(min_size, max_size)
    h = random.randint(min_size, max_size)
    x1 = random.randint(50, 1024 - w - 50)
    y1 = random.randint(50, 1024 - h - 50)
    return (x1, y1, x1 + w, y1 + h)

def generate_mutating_frame(base_img, box):
    frame = base_img.copy()
    x1, y1, x2, y2 = box
    cx, cy = (x1 + x2) // 2, (y1 + y2) // 2
    for _ in range(random.randint(4, 9)):
        w_shard = random.randint(30, 200)
        h_shard = random.randint(20, 150)
        sx = cx - w_shard // 2 + random.randint(-60, 60)
        sy = cy - h_shard // 2 + random.randint(-60, 60)
        sx = max(0, min(sx, base_img.width - w_shard))
        sy = max(0, min(sy, base_img.height - h_shard))
        shard_box = (sx, sy, sx + w_shard, sy + h_shard)
        try:
            shard = frame.crop(shard_box).convert("RGB")
            shard = ImageOps.invert(shard)
            shard = ImageEnhance.Contrast(shard).enhance(3.0)
            frame.paste(shard, shard_box)
        except: pass
    return frame

@st.cache_data(show_spinner=False, persist="disk")
def generate_scaled_gif(img_path, box, target_width, level_idx, glitch_seed):
    try:
        random.seed(glitch_seed)
        base_img = Image.open(img_path).convert("RGB")
        scale_factor = target_width / base_img.width
        base_img = base_img.resize((target_width, int(base_img.height * scale_factor)), Image.Resampling.LANCZOS)

        x1, y1, x2, y2 = box
        scaled_box = (int(x1 * scale_factor), int(y1 * scale_factor), int(x2 * scale_factor), int(y2 * scale_factor))

        frames = []
        for _ in range(8): frames.append(base_img.copy())
        for _ in range(6): frames.append(generate_mutating_frame(base_img, scaled_box))

        temp_file = f"/tmp/lvl_{level_idx}_{glitch_seed}.gif"
        frames[0].save(temp_file, format="GIF", save_all=True, append_images=frames[1:], duration=[200]*8 + [80]*6, loop=0)
        return temp_file, scaled_box
    except:
        return None, None

inject_css()

if "game_state" not in st.session_state:
    st.session_state.update({
        "game_state": "menu",
        "current_level": 0,
        "start_time": 0,
        "player_tag": "",
        "final_time": 0,
        "last_move_time": time.time(),
        "glitch_seed": random.randint(1, 100000),
        "current_box": get_glitch_box(0),
        "misses": 0,
    })

st.title("DETROIT: ANOMALY [09]")

if st.session_state.game_state == "menu":
    tag = st.text_input("OPERATIVE TAG (3 CHARS):", max_chars=3).upper()
    if st.button(">> START SIMULATION <<") and len(tag) == 3:
        st.session_state.update({
            "game_state": "playing",
            "player_tag": tag,
            "start_time": time.time(),
            "current_level": 0,
            "last_move_time": time.time(),
            "glitch_seed": random.randint(1, 100000),
            "current_box": get_glitch_box(0),
            "misses": 0,
        })
        st.rerun()

elif st.session_state.game_state == "playing":
    lvl_idx = st.session_state.current_level
    move_delay = max(3.0, BASE_MOVE_DELAY - lvl_idx * 2)
    hit_tolerance = max(15, BASE_HIT_TOLERANCE - lvl_idx * 10)

    elapsed = time.time() - st.session_state.last_move_time
    time_left = max(0, move_delay - elapsed)
    st.progress(time_left / move_delay, text=f"SECTOR 0{lvl_idx + 1} // SHIFT IN {time_left:.1f}s")
    
    # Prepare glitch and decoy box
    real_box = st.session_state.current_box
    decoy_box = get_glitch_box(lvl_idx) if lvl_idx >= 3 else None

    gif_path, scaled_real_box = generate_scaled_gif(LEVEL_IMGS[lvl_idx], real_box, GAME_WIDTH, lvl_idx, st.session_state.glitch_seed)
    gif_path_decoy, scaled_decoy_box = None, None
    if decoy_box is not None:
        # Different seed for decoy GIF
        decoy_seed = st.session_state.glitch_seed + 1
        gif_path_decoy, scaled_decoy_box = generate_scaled_gif(LEVEL_IMGS[lvl_idx], decoy_box, GAME_WIDTH, lvl_idx, decoy_seed)

    # Display real glitch and decoy side by side
    col1, col2 = st.columns(2)
    with col1:
        coords = streamlit_image_coordinates(gif_path, key=f"real_{lvl_idx}_{st.session_state.glitch_seed}", width=GAME_WIDTH)
    with col2:
        if gif_path_decoy:
            _ = st.image(gif_path_decoy, width=GAME_WIDTH)
            
    if coords:
        cx, cy = coords['x'], coords['y']

        if (scaled_real_box[0] - hit_tolerance) <= cx <= (scaled_real_box[2] + hit_tolerance) and (scaled_real_box[1] - hit_tolerance) <= cy <= (scaled_real_box[3] + hit_tolerance):
            trigger_static_transition()
            st.session_state.current_level += 1
            st.session_state.glitch_seed = random.randint(1, 100000)
            st.session_state.current_box = get_glitch_box(st.session_state.current_level)
            st.session_state.last_move_time = time.time()
            st.session_state.misses = 0
            st.experimental_rerun()
        else:
            st.session_state.misses += 1
            st.warning(f"MISS! {MAX_MISSES - st.session_state.misses} guesses left.")
            if st.session_state.misses >= MAX_MISSES:
                st.session_state.game_state = "game_over"
                st.experimental_rerun()

    if elapsed > move_delay:
        st.session_state.glitch_seed = random.randint(1, 100000)
        st.session_state.current_box = get_glitch_box(st.session_state.current_level)
        st.session_state.last_move_time = time.time()
        st.experimental_rerun()

elif st.session_state.game_state == "game_over":
    st.balloons()
    st.write(f"AGENT: {st.session_state.player_tag} | TIME: {st.session_state.final_time:.2f}s")
    if st.button("UPLOAD SCORE", type="primary"):
        # Upload logic here if connected
        st.success("DATA UPLOADED.")
        st.session_state.game_state = "menu"
        st.experimental_rerun()
