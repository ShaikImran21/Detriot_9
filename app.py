import streamlit as st
import time
import pandas as pd
import random
import os
import base64
from PIL import Image, ImageOps, ImageEnhance
from streamlit_gsheets import GSheetsConnection
from streamlit_image_coordinates import streamlit_image_coordinates


st.set_page_config(page_title="DETROIT: Anomaly [09]", layout="centered", initial_sidebar_state="collapsed")


# --- SETTINGS ---
GAME_WIDTH = 700
HIT_TOLERANCE = 0  # Set to zero to match exact glitch box size
MOVE_DELAY = 15  # seconds before glitch teleports


# --- LEVEL IMAGES ---
LEVEL_IMGS = [
    "assets/level1.png", "assets/level2.png", "assets/level3.png",
    "assets/level4.png", "assets/level5.png", "assets/level6.png",
    "assets/level7.png", "assets/level8.png", "assets/level9.png"
]


# --- HELPER: ASSET LOADER ---
def get_base64(bin_file):
    try:
        with open(bin_file, 'rb') as f:
            return base64.b64encode(f.read()).decode()
    except:
        return None


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


# --- TRANSITION ---
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


# --- RANDOM LOCATION GENERATOR ---
def get_new_glitch_box():
    w = random.randint(80, 180)
    h = random.randint(80, 180)
    x1 = random.randint(50, 1024 - w - 50)
    y1 = random.randint(50, 1024 - h - 50)
    return (x1, y1, x1 + w, y1 + h)


# --- CHAOS GENERATOR ---
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
        target_height = int(base_img.height * scale_factor)
        base_img = base_img.resize((target_width, target_height), Image.Resampling.LANCZOS)


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


if 'game_state' not in st.session_state:
    st.session_state.update({
        'game_state': 'menu',
        'current_level': 0,
        'start_time': 0.0,
        'player_tag': 'UNK',
        'final_time': 0.0,
        'last_move_time': time.time(),
        'glitch_seed': random.randint(1, 100000),
    })


st.title("DETROIT: ANOMALY [09]")


if st.session_state.game_state == 'playing':
    if time.time() - st.session_state.last_move_time > MOVE_DELAY:
        st.session_state.glitch_seed = random.randint(1, 100000)
        st.session_state.last_move_time = time.time()
        st.rerun()


if st.session_state.game_state == "menu":
    tag = st.text_input("OPERATIVE TAG (3 CHARS):", max_chars=3).upper()
    if st.button(">> START SIMULATION <<", type="primary"):
        if len(tag) == 3:
            st.session_state.update({
                'game_state': 'playing',
                'player_tag': tag,
                'start_time': time.time(),
                'current_level': 0,
                'last_move_time': time.time(),
            })
            st.rerun()
    st.markdown("### TOP AGENTS")
    # Leaderboard omitted for brevity


elif st.session_state.game_state == "playing":
    lvl_idx = st.session_state.current_level


    if 'current_box' not in st.session_state or st.session_state.get('stored_seed') != st.session_state.glitch_seed:
        random.seed(st.session_state.glitch_seed)
        st.session_state.current_box = get_new_glitch_box()
        st.session_state.stored_seed = st.session_state.glitch_seed


    gif_path, scaled_box = generate_scaled_gif(LEVEL_IMGS[lvl_idx], st.session_state.current_box, GAME_WIDTH, lvl_idx, st.session_state.glitch_seed)


    progress = MOVE_DELAY - (time.time() - st.session_state.last_move_time)
    if progress > 0:
        st.progress(progress / MOVE_DELAY, text=f"SECTOR 0{lvl_idx + 1} // ANOMALY SHIFT IN {progress:.1f}s")


    if gif_path and scaled_box:
        coords = streamlit_image_coordinates(gif_path, key=f"lvl_{lvl_idx}_{st.session_state.glitch_seed}", width=GAME_WIDTH)
        if coords:
            x1, y1, x2, y2 = scaled_box
            if x1 <= coords['x'] <= x2 and y1 <= coords['y'] <= y2:  # exact glitch box, no tolerance
                trigger_static_transition()
                if lvl_idx < 8:
                    st.session_state.current_level += 1
                    st.session_state.last_move_time = time.time()
                    st.session_state.glitch_seed = random.randint(1, 100000)
                    st.rerun()
                else:
                    st.session_state.final_time = time.time() - st.session_state.start_time
                    st.session_state.game_state = 'game_over'
                    st.rerun()
            else:
                st.session_state.glitch_seed = random.randint(1, 100000)
                st.session_state.last_move_time = time.time()
                st.rerun()


    time.sleep(0.1)
    st.rerun()


elif st.session_state.game_state == "game_over":
    st.balloons()
    st.write(f"AGENT: {st.session_state.player_tag} | TIME: {st.session_state.final_time:.2f}s")
    if st.button("UPLOAD SCORE", type="primary"):
        # Implement score upload if desired
        st.success("DATA UPLOADED.")  # or st.error("UPLOAD FAILED.")
        time.sleep(2)
        st.session_state.game_state = 'menu'
        st.rerun()
    st.markdown("### GLOBAL RANKINGS")
    # Leaderboard display omitted for brevity
