import streamlit as st
import time
import pandas as pd
import random
import os
import base64
from PIL import Image, ImageOps, ImageEnhance
from streamlit_gsheets import GSheetsConnection
from streamlit_image_coordinates import streamlit_image_coordinates
import re 

# --- CONFIGURATION ---
st.set_page_config(page_title="DETROIT: Anomaly [09]", layout="centered", initial_sidebar_state="collapsed")

GAME_WIDTH = 700
HIT_TOLERANCE = 100

# MODIFIED: Reduced to 4 levels
LEVEL_FILES = [
    "assets/level1.png", "assets/level2.png", "assets/level3.png",
    "assets/level4.png"
]

# MODIFIED: 4 levels with a total of 22 real glitches (3+5+7+7)
GLITCHES_PER_LEVEL = [3, 5, 7, 7] 

# --- HELPER FUNCTIONS ---

def get_base64(bin_file):
    """Encodes a local file to base64 for use in HTML/CSS."""
    try:
        with open(bin_file, 'rb') as f:
            return base64.b64encode(f.read()).decode()
    except:
        return None

def inject_css():
    """Injects CSS for dark theme, film grain, and global glitch effect."""
    st.markdown("""
        <style>
            /* --- BASE STYLES & FILM GRAIN --- */
            .stApp { 
                background-color: #080808; 
                color: #d0d0d0; 
                font-family: 'Courier New', monospace; 
            }
            #MainMenu, footer, header {visibility: hidden;}
            .block-container { 
                justify-content: center; 
                align-items: center; 
                display: flex; 
                flex-direction: column; 
            }
            /* Film Grain Effect (Applied to the whole background) */
            .stApp::after {
                content: " "; 
                position: fixed; 
                inset: 0;
                background:
                    linear-gradient(rgba(18,16,16,0) 50%, rgba(0,0,0,0.25) 50%),
                    linear-gradient(90deg, rgba(255,0,0,0.06), rgba(0,255,0,0.02), rgba(0,0,255,0.06));
                background-size: 100% 3px, 3px 100%;
                pointer-events: none; 
                opacity: 0.15; 
                z-index: 999;
            }
            
            /* --- GLOBAL GLITCH EFFECT --- */
            h1, h2, h3, h4, p, .stMarkdown, .stText, 
            .stButton > button, .stTextInput > div > div > input, 
            .stDataFrame, .stProgress > div > div, 
            .stTextInput > label, .stMarkdown > div { 
                animation: glitch-text 500ms infinite; 
                white-space: nowrap; 
            }
            
            /* Keyframe definition for the text shadow glitch */
            @keyframes glitch-text {
                0%,14% { text-shadow: 0.05em 0 0 #f44, -0.05em -0.025em 0 #2f2, 0.025em 0.05em 0 #34f; }
                15%,49% { text-shadow: -0.05em -0.025em 0 #f44, 0.025em 0.025em 0 #2f2, -0.05em -0.05em 0 #34f; }
                50%,99% { text-shadow: 0.025em 0.05em 0 #f44, 0.05em 0 0 #2f2, 0 -0.05em 0 #34f; }
                100% { text-shadow: -0.025em 0 0 #f44, -0.025em -0.025em 0 #2f2, -0.025em -0.05em 0 #34f; }
            }
        </style>
    """, unsafe_allow_html=True)

def trigger_static_transition():
    """Creates a brief static/glitch visual and sound effect."""
    st.markdown('<audio src="https://www.myinstants.com/media/sounds/static-noise.mp3" autoplay style="display:none;"></audio>', unsafe_allow_html=True)
    placeholder = st.empty()
    with placeholder.container():
        st.markdown('<div style="position:fixed;top:0;left:0;width:100%;height:100%;background-color:#111;z-index:10000;"></div>', unsafe_allow_html=True)
        time.sleep(0.1)
        # Fallback GIF URL if local assets fails
        g_url = "https://media.giphy.com/media/oEI9uBYSzLpBK/giphy.gif"
        st.markdown(f'<div style="position:fixed;top:0;left:0;width:100%;height:100%;background:url({g_url});background-size:cover;z-index:10001;opacity:0.8;mix-blend-mode:hard-light;"></div>', unsafe_allow_html=True)
        time.sleep(0.4)
    placeholder.empty()

def get_new_glitch_box(level=0):
    """Generates aggressively smaller glitch boxes for increased difficulty per level."""
    max_size = max(150 - level * 20, 30) 
    min_size = max(50 - level * 10, 15) 
    min_size = min(min_size, max_size) 
    
    w = random.randint(min_size, max_size)
    h = random.randint(min_size, max_size)
    
    x1 = random.randint(50, 1024 - w - 50)
    y1 = random.randint(50, 1024 - h - 50)
    
    return (x1, y1, x1 + w, y1 + h)

def generate_fake_glitch_box(level=0):
    """Generates a slightly larger, non-target glitch box (decoy)."""
    max_size = max(180 - level * 15, 60) 
    min_size = max(70 - level * 5, 40) 
    
    w = random.randint(min_size, max_size)
    h = random.randint(min_size, max_size)
    
    x1 = random.randint(50, 1024 - w - 50)
    y1 = random.randint(50, 1024 - h - 50)
    return (x1, y1, x1 + w, y1 + h)


def generate_mutating_frame(base_img, boxes, is_fake=False):
    """Creates a visual difference between real (high contrast) and fake (low contrast) glitches."""
    frame = base_img.copy()
    
    if not isinstance(boxes, list):
        boxes = [boxes]
        
    contrast_level = 1.0 if is_fake else 3.0 
    
    for box in boxes:
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
                
                shard = ImageEnhance.Contrast(shard).enhance(contrast_level)
                frame.paste(shard, shard_box)
            except:
                pass
    return frame

@st.cache_data(show_spinner=False, persist="disk")
def generate_scaled_gif(img_path, original_boxes, target_width, level_idx, glitch_seed):
    """Generates and caches the pulsating glitch GIF, including fakes."""
    try:
        random.seed(glitch_seed)
        base_img = Image.open(img_path).convert("RGB")
        scale_factor = target_width / base_img.width
        target_height = int(base_img.height * scale_factor)
        base_img = base_img.resize((target_width, target_height), Image.Resampling.LANCZOS)
        
        scaled_real_boxes = []
        for x1, y1, x2, y2 in original_boxes:
             scaled_real_boxes.append((int(x1 * scale_factor), int(y1 * scale_factor), int(x2 * scale_factor), int(y2 * scale_factor)))

        num_fakes = level_idx + 1 
        
        scaled_fake_boxes = []
        for _ in range(num_fakes):
            fake_box = generate_fake_glitch_box(level_idx)
            x1, y1, x2, y2 = fake_box
            scaled_fake_boxes.append((int(x1 * scale_factor), int(y1 * scale_factor), int(x2 * scale_factor), int(y2 * scale_factor)))


        frames = []
        for _ in range(15):
            frames.append(base_img.copy())
        
        for _ in range(8):
            mutated_frame = generate_mutating_frame(base_img, original_boxes, is_fake=False)
            mutated_frame = generate_mutating_frame(mutated_frame, scaled_fake_boxes, is_fake=True)
            frames.append(mutated_frame)

        temp_file = f"/tmp/lvl_{level_idx}_{glitch_seed}.gif"
        frames[0].save(temp_file, format="GIF", save_all=True, append_images=frames[1:], duration=[200]*15 + [70]*8, loop=0)

        return temp_file, scaled_real_boxes, scaled_fake_boxes
    except:
        return None, [], []


def validate_usn(usn):
    """Basic validation for a typical USN format (e.g., 1MS22AI000)."""
    return re.match(r"^\d[A-Z]{2}\d{2}[A-Z]{2}\d{3}$", usn)

# --- GOOGLE SHEETS FUNCTIONS ---

conn = None
try:
    conn = st.connection("gsheets", type=GSheetsConnection)
except Exception:
    pass 

def save_score(tag, name, usn, time_val):
    """Saves the score, name, and USN to the Google Sheet."""
    if conn:
        try:
            df = pd.DataFrame([{"Tag": tag, "Name": name, "USN": usn, "Time": time_val}])
            conn.write(worksheet="Scores", data=df, append=True)
            return True
        except Exception:
            return False
    return False

def get_leaderboard():
    """
    MODIFIED: Fetches, cleans, and sorts the leaderboard data, 
    with explicit column reading and dtype for robust operation.
    """
    if conn:
        try:
            # Force string types for text columns and float for Time column
            # This is the final fix to bypass data type reading errors from Google Sheets
            DTYPE_MAP = {
                'Tag': str, 
                'Name': str, 
                'USN': str, 
                'Time': float
            }
            
            df = conn.read(
                worksheet="Scores", 
                ttl=0, 
                usecols=['Tag', 'Name', 'USN', 'Time'],
                dtype=DTYPE_MAP
            ).dropna(subset=['Time']).copy()
            
            # Remove any rows where Time is NaN (if conversion failed silently)
            df.dropna(subset=['Time'], inplace=True)
            
            if df.empty:
                return pd.DataFrame(columns=["Rank", "Name", "USN", "Time"])

            df.sort_values(by='Time', ascending=True, inplace=True)
            df['Rank'] = range(1, len(df) + 1)
            df['Time'] = df['Time'].apply(lambda x: f"{x:.2f}s")
            
            return df[['Rank', 'Name', 'USN', 'Time']].head(10).reset_index(drop=True)
        except Exception as e:
            # You can see the error in the console by uncommenting the line below
            # st.error(f"DEBUG: Read Error: {e}") 
            pass 
    return pd.DataFrame(columns=["Rank", "Name", "USN", "Time"])


def move_glitch(num_glitches=1):
    """Generates 1 or 2 new target glitch boxes."""
    lvl = st.session_state.current_level
    st.session_state.glitch_seed = random.randint(1, 100000)
    
    real_boxes = [get_new_glitch_box(level=lvl) for _ in range(num_glitches)]
    st.session_state.current_boxes = real_boxes
    st.session_state.last_move_time = time.time()

# --- INITIALIZATION & MAIN APP LOGIC ---

inject_css()

def get_num_real_targets(level_idx):
    if level_idx in [2, 3]: 
        return 2
    return 1

if 'game_state' not in st.session_state:
    st.session_state.update({
        'game_state': 'menu',
        'current_level': 0,
        'start_time': 0.0,
        'player_tag': 'UNK',
        'player_name': '', 
        'player_usn': '',  
        'final_time': 0.0,
        'last_move_time': time.time(),
        'glitch_seed': random.randint(1, 100000),
        'current_boxes': [get_new_glitch_box()], 
        'hits': 0,
    })

st.title("DETROIT: ANOMALY [09]")

if st.session_state.game_state == "menu":
    
    st.markdown("### OPERATIVE DATA INPUT")
    tag = st.text_input(">> AGENT TAG (3 CHARS):", value=st.session_state.player_tag if st.session_state.player_tag != 'UNK' else '', max_chars=3).upper()
    name = st.text_input(">> FULL NAME:", value=st.session_state.player_name)
    usn = st.text_input(">> USN (e.g., 1MS22AI000):", value=st.session_state.player_usn).upper()
    is_valid_usn = validate_usn(usn)
    
    start_button = st.button(">> START SIMULATION <<", type="primary", disabled=(len(tag) != 3 or not name or not is_valid_usn))
    
    if len(tag) != 3 and tag: st.warning("Tag must be exactly 3 characters.")
    if usn and not is_valid_usn: st.warning("Invalid USN format. Please check.")
        
    if start_button:
        num_targets = get_num_real_targets(0)
        move_glitch(num_targets) 
        st.session_state.update({
            'game_state': 'playing', 'player_tag': tag, 'player_name': name, 
            'player_usn': usn, 'start_time': time.time(), 'current_level': 0, 'hits': 0
        })
        st.rerun()
        
    st.markdown("---")
    st.markdown("### GLOBAL RANKINGS")
    
    leaderboard_df = get_leaderboard()
    
    if conn and not leaderboard_df.empty:
        st.success("✅ Online Leaderboard (Scores Sheet Connection OK)")
        leaderboard_df.columns = ["Rank", "Name", "USN", "Time"]
        st.dataframe(leaderboard_df, hide_index=True, use_container_width=True)
    elif conn and leaderboard_df.empty:
         st.warning("⚠️ Online Connection OK, but Leaderboard is empty or Read Failed.")
         st.info("Ensure the **Scores** sheet has the headers: **Tag, Name, USN, Time** in row 1, and manually add one score to start.")
    else:
        st.error("❌ Leaderboard Connection Failed. (Check secrets.toml/sharing permissions)")
        st.dataframe(leaderboard_df, hide_index=True, use_container_width=True) 

elif st.session_state.game_state == "playing":
    lvl_idx = st.session_state.current_level
    if lvl_idx >= len(GLITCHES_PER_LEVEL):
        lvl_idx = len(GLITCHES_PER_LEVEL) - 1
        
    glitches_needed = GLITCHES_PER_LEVEL[lvl_idx]
    targets_on_screen = get_num_real_targets(lvl_idx)

    col1, col2, col3 = st.columns(3)
    with col1:
        st.markdown(f"**AGENT: {st.session_state.player_tag}**")
    with col2:
        elapsed_game_time = time.time() - st.session_state.start_time
        st.markdown(f"**TIME: {elapsed_game_time:.1f}s**")
    with col3:
        st.markdown(f"**LEVEL: {lvl_idx + 1}/{len(GLITCHES_PER_LEVEL)} | TARGETS: {targets_on_screen}**") 

    hits = st.session_state.hits
    progress_frac = hits / glitches_needed if glitches_needed > 0 else 0
    st.progress(progress_frac, text=f"Glitches Neutralized: {hits} / {glitches_needed}")

    gif_path, scaled_real_boxes, scaled_fake_boxes = generate_scaled_gif(
        LEVEL_FILES[lvl_idx], st.session_state.current_boxes, GAME_WIDTH, lvl_idx, st.session_state.glitch_seed
    )

    if gif_path and scaled_real_boxes:
        coords = streamlit_image_coordinates(gif_path, key=f"lvl_{lvl_idx}_{st.session_state.glitch_seed}", width=GAME_WIDTH)

        if coords:
            cx, cy = coords['x'], coords['y']
            hit_made = False
            
            # 1. Check if the click hits any REAL glitch box
            for x1, y1, x2, y2 in scaled_real_boxes:
                if (x1 - HIT_TOLERANCE) <= cx <= (x2 + HIT_TOLERANCE) and \
                   (y1 - HIT_TOLERANCE) <= cy <= (y2 + HIT_TOLERANCE):
                    hit_made = True
                    break

            # 2. Check if the click hits any FAKE glitch box
            is_fake_hit = False
            for x1, y1, x2, y2 in scaled_fake_boxes:
                if (x1 - HIT_TOLERANCE) <= cx <= (x2 + HIT_TOLERANCE) and \
                   (y1 - HIT_TOLERANCE) <= cy <= (y2 + HIT_TOLERANCE):
                    is_fake_hit = True
                    break

            if hit_made:
                trigger_static_transition()
                st.session_state.hits += 1
                
                if st.session_state.hits >= glitches_needed:
                    if lvl_idx < len(GLITCHES_PER_LEVEL) - 1:
                        st.session_state.current_level += 1
                        st.session_state.hits = 0
                        next_targets = get_num_real_targets(st.session_state.current_level)
                        move_glitch(next_targets) 
                    else:
                        st.session_state.final_time = time.time() - st.session_state.start_time
                        st.session_state.game_state = 'game_over'
                else:
                    move_glitch(targets_on_screen) 
                st.rerun()
            elif is_fake_hit:
                st.toast("DECOY NEUTRALIZED. REAL ANOMALY REMAINS.", icon="⚠️")
                move_glitch(targets_on_screen)
                st.rerun()
            else:
                st.toast("MISS! RELOCATING...", icon="❌")
                move_glitch(targets_on_screen)
                st.rerun()
    else:
        st.error(f"Error loading level file: {LEVEL_FILES[lvl_idx]}")


elif st.session_state.game_state == "game_over":
    st.balloons()
    st.markdown("## SIMULATION COMPLETE!")
    st.write(f"**OPERATIVE:** {st.session_state.player_name}")
    st.write(f"**USN:** {st.session_state.player_usn}")
    st.write(f"**FINAL TIME:** {st.session_state.final_time:.2f}s")
    
    if st.button(">> UPLOAD SCORE <<", type="primary"):
        with st.spinner("TRANSMITTING DATA..."):
            upload_success = save_score(st.session_state.player_tag, st.session_state.player_name, st.session_state.player_usn, st.session_state.final_time)

            if upload_success:
                st.success("DATA UPLOADED. MISSION SUCCESSFUL.")
            else:
                st.error("UPLOAD FAILED. CONNECTION ERROR. (Check connection status on menu screen.)")
        time.sleep(1.5)
        st.session_state.game_state = 'menu'
        st.rerun()
        
    st.markdown("---")
    st.markdown("### GLOBAL RANKINGS")
    
    leaderboard_df = get_leaderboard()
    if not leaderboard_df.empty:
        leaderboard_df.columns = ["Rank", "Name", "USN", "Time"]
        st.dataframe(leaderboard_df, hide_index=True, use_container_width=True)
    else:
        st.info("Leaderboard is empty or connection failed.")
    
    if st.button("RETURN TO MENU"):
        st.session_state.game_state = 'menu'
        st.rerun()