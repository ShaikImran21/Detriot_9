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
import gspread
from google.oauth2.service_account import Credentials # <-- ADDED IMPORT

# --- CONFIGURATION ---
st.set_page_config(page_title="DETROIT: ANOMALY [09]", layout="centered", initial_sidebar_state="collapsed")

GAME_WIDTH = 700
# MAXIMUM TOLERANCE: Very easy to hit now, perfect for all mobile users.
HIT_TOLERANCE = 150 

LEVEL_FILES = ["assets/level1.png", "assets/level2.png", "assets/level3.png"] # <-- MODIFIED
GLITCHES_PER_LEVEL = [3, 5, 7] # <-- MODIFIED

# --- HELPER: ASSETS ---
def get_base64(bin_file):
    try:
        with open(bin_file, 'rb') as f: return base64.b64encode(f.read()).decode()
    except: return None

# --- CSS: ULTRA GLITCH + MOBILE FIX ---
def inject_css(video_file_path): # <-- MODIFIED: Pass in the video path
    
    # 1. ENCODE THE VIDEO FILE
    video_base64 = get_base64(video_file_path)
    
    # 2. CREATE THE HTML <video> TAG
    if video_base64:
        video_html = f"""
        <video id="video-bg" autoplay loop muted>
            <source src="data:video/mp4;base64,{video_base64}" type="video/mp4">
            Your browser does not support the video tag.
        </video>
        """
        # Inject the video tag into the app
        st.markdown(video_html, unsafe_allow_html=True)

    # 3. CSS for the video + original CSS
    st.markdown(f"""
        <style>
            /* --- START: VIDEO BACKGROUND --- */
            #video-bg {{
                position: fixed;
                right: 0;
                bottom: 0;
                min-width: 100%;
                min-height: 100%;
                width: auto;
                height: auto;
                z-index: -100; /* Puts it behind all content */
                object-fit: cover; /* Fill the screen */
                opacity: 1.0; /* Dim the video so text is readable */
            }}
            /* --- END: VIDEO BACKGROUND --- */

            /* BASE THEME - MODIFIED for VIDEO */
            .stApp {{ 
                /* This is no longer a solid color.
                It's a semi-transparent overlay to darken the video
                and keep the text readable.
                */
                background-color: rgba(8, 8, 8, 0.75); /* 75% opaque dark */
                background-size: cover;
                background-repeat: no-repeat;
                background-attachment: fixed;
                background-position: center;
                color: #d0d0d0; 
                font-family: 'Courier New', monospace; 
            }}
            #MainMenu, footer, header {{visibility: hidden;}}

            /* FORCE HORIZONTAL SCROLL ON MOBILE (Prevents squishing) */
            .block-container {{
                min-width: 720px !important;
                max-width: 900px !important;
                overflow-x: auto !important;
            }}
            
            /* HARDWARE-ACCELERATED STATIC OVERLAY */
            #static-overlay {{
                position: fixed; top: -50%; left: -50%; width: 200%; height: 200%;
                background: repeating-linear-gradient(transparent 0px, rgba(0, 0, 0, 0.25) 50%, transparent 100%),
                            repeating-linear-gradient(90deg, rgba(255, 0, 0, 0.06), rgba(0, 255, 0, 0.02), rgba(0, 0, 255, 0.06));
                background-size: 100% 3px, 3px 100%; z-index: 99999; pointer-events: none; opacity: 0.2;
                animation: gpu-jitter 0.3s infinite linear alternate-reverse; mix-blend-mode: hard-light;
            }}
            @keyframes gpu-jitter {{
                0%, 100% {{ transform: translate3d(0,0,0); opacity: 0.15; }}
                25% {{ transform: translate3d(-5px, -5px, 0); opacity: 0.2; }}
                50% {{ transform: translate3d(5px, 5px, 0); opacity: 0.15; }}
                /* ... (end of @keyframes gpu-jitter) ... */
                75% {{ transform: translate3d(-5px, 5px, 0); opacity: 0.25; }}
            }}
            
            /* --- START: Glitchy Title Background --- */
            h1 {{
                position: relative !important;
                z-index: 1;
                /* Add some padding to see the background better */
                padding: 10px 5px; 
            }}

            /* REMOVED GLITCHY TITLE BACKGROUND */
            /* ... (rest of your original h1::before CSS) ... */
            
            /* GLOBAL TEXT GLITCH */
            h1, h2, h3, h4, h5, h6, p, label, span, div, button, a, input, .stDataFrame, .stMarkdown, .stExpander {{
                animation: glitch-text 500ms infinite !important; color: #d0d0d0 !important;
            }}
            img, #static-overlay {{ animation: none !important; }}
            #static-overlay {{ animation: gpu-jitter 0.3s infinite linear alternate-reverse !important; }}

            @keyframes glitch-text {{
                0% {{ text-shadow: 0.05em 0 0 rgba(255,0,0,0.75), -0.025em -0.05em 0 rgba(0,255,0,0.75), 0.025em 0.05em 0 rgba(0,0,255,0.75); }}
                14% {{ text-shadow: 0.05em 0 0 rgba(255,0,0,0.75), -0.025em -0.05em 0 rgba(0,255,0,0.75), 0.025em 0.05em 0 rgba(0,0,255,0.75); }}
                15% {{ text-shadow: -0.05em -0.025em 0 rgba(255,0,0,0.75), 0.025em 0.025em 0 rgba(0,255,0,0.75), -0.05em -0.05em 0 rgba(0,0,255,0.75); }}
                49% {{ text-shadow: -0.05em -0.025em 0 rgba(255,0,0,0.75), 0.025em 0.025em 0 rgba(0,255,0,0.75), -0.05em -0.05em 0 rgba(0,0,255,0.75); }}
                50% {{ text-shadow: 0.025em 0.05em 0 rgba(255,0,0,0.75), 0.05em 0 0 rgba(0,255,0,0.75), 0 -0.05em 0 rgba(0,0,255,0.75); }}
                99% {{ text-shadow: 0.025em 0.05em 0 rgba(255,0,0,0.75), 0.05em 0 0 rgba(0,255,0,0.75), 0 -0.05em 0 rgba(0,0,255,0.75); }}
                100% {{ text-shadow: -0.025em 0 0 rgba(255,0,0,0.75), -0.025em -0.025em 0 rgba(0,255,0,0.75), -0.025em -0.05em 0 rgba(0,0,255,0.75); }}
            }}
        </style>
    """, unsafe_allow_html=True)

def trigger_static_transition():
    st.markdown('<audio src="https://www.myinstants.com/media/sounds/static-noise.mp3" autoplay style="display:none;"></audio>', unsafe_allow_html=True)
    placeholder = st.empty()
    with placeholder.container():
        st.markdown('<div style="position:fixed;top:0;left:0;width:100%;height:100%;background-color:#111;z-index:10000;"></div>', unsafe_allow_html=True)
        time.sleep(0.1)
        g_url = "https://media.giphy.com/media/oEI9uBYSzLpBK/giphy.gif"
        st.markdown(f'<div style="position:fixed;top:0;left:0;width:100%;height:100%;background:url({g_url});background-size:cover;z-index:10001;opacity:0.8;mix-blend-mode:hard-light;"></div>', unsafe_allow_html=True)
        time.sleep(0.4)
    placeholder.empty()

# --- SMART GLITCH GENERATION ---
def get_random_box(level, is_fake=False):
    if is_fake: max_s, min_s = max(180 - level*15, 60), max(70 - level*5, 40)
    else: max_s, min_s = max(150 - level*20, 30), min(max(50 - level*10, 15), max(150 - level*20, 30))
    w, h = random.randint(min_s, max_s), random.randint(min_s, max_s)
    return (random.randint(50, 1024-w-50), random.randint(50, 1024-h-50), w, h)

def check_overlap(box1, box2, buffer=20):
    b1_x1, b1_y1, b1_x2, b1_y2 = box1[0], box1[1], box1[0]+box1[2], box1[1]+box1[3]
    b2_x1, b2_y1, b2_x2, b2_y2 = box2[0], box2[1], box2[0]+box2[2], box2[1]+box2[3]
    if (b1_x2 + buffer < b2_x1) or (b2_x2 + buffer < b1_x1) or (b1_y2 + buffer < b2_y1) or (b2_y2 + buffer < b1_y1): return False
    return True

def move_glitch(num_real=1):
    lvl = st.session_state.current_level
    st.session_state.glitch_seed = random.randint(1, 100000)
    real_temp, fake_temp = [], []
    for _ in range(num_real):
        while True:
            nb = get_random_box(lvl, False)
            if not any(check_overlap(nb, b) for b in real_temp): real_temp.append(nb); break
    for _ in range(lvl + 1):
        at = 0
        while at < 50:
            nb = get_random_box(lvl, True)
            if not any(check_overlap(nb, b) for b in real_temp + fake_temp): fake_temp.append(nb); break
            at += 1
    st.session_state.real_boxes = [(x,y,x+w,y+h) for x,y,w,h in real_temp]
    st.session_state.fake_boxes = [(x,y,x+w,y+h) for x,y,w,h in fake_temp]
    st.session_state.last_move_time = time.time()

def generate_mutating_frame(base_img, boxes, is_fake=False):
    frame = base_img.copy()
    if not isinstance(boxes, list): boxes = [boxes]
    contrast_level = 1.0 if is_fake else 3.0 
    for box in boxes:
        x1, y1, x2, y2 = box
        cx, cy = (x1 + x2) // 2, (y1 + y2) // 2
        for _ in range(random.randint(4, 9)):
            w_shard, h_shard = random.randint(30, 200), random.randint(20, 150)
            sx = max(0, min(cx - w_shard // 2 + random.randint(-60, 60), base_img.width - w_shard))
            sy = max(0, min(cy - h_shard // 2 + random.randint(-60, 60), base_img.height - h_shard))
            try:
                shard = ImageEnhance.Contrast(ImageOps.invert(frame.crop((sx, sy, sx+w_shard, sy+h_shard)).convert("RGB"))).enhance(contrast_level)
                frame.paste(shard, (sx, sy, sx+w_shard, sy+h_shard))
            except: pass
    return frame

@st.cache_data(show_spinner=False, persist="disk")
def generate_scaled_gif(img_path, real_boxes_orig, fake_boxes_orig, target_width, level_idx, glitch_seed):
    try:
        random.seed(glitch_seed)
        base_img = Image.open(img_path).convert("RGB")
        sf = target_width / base_img.width
        base_img = base_img.resize((target_width, int(base_img.height * sf)), Image.Resampling.LANCZOS)
        scaled_real = [(int(x1*sf), int(y1*sf), int(x2*sf), int(y2*sf)) for x1,y1,x2,y2 in real_boxes_orig]
        scaled_fake = [(int(x1*sf), int(y1*sf), int(x2*sf), int(y2*sf)) for x1,y1,x2,y2 in fake_boxes_orig]
        frames = [base_img.copy() for _ in range(15)]
        for _ in range(8):
            frames.append(generate_mutating_frame(generate_mutating_frame(base_img, real_boxes_orig, False), fake_boxes_orig, True))
        temp_file = f"/tmp/lvl_{level_idx}_{glitch_seed}.gif"
        frames[0].save(temp_file, format="GIF", save_all=True, append_images=frames[1:], duration=[200]*15+[70]*8, loop=0)
        return temp_file, scaled_real, scaled_fake
    except: return None, [], []

def validate_usn(usn): return re.match(r"^\d[A-Z]{2}\d{2}[A-Z]{2}\d{3}$", usn)

# --- GOOGLE SHEETS ---
conn = None
try: conn = st.connection("gsheets", type=GSheetsConnection)
except: pass

def save_score(tag, name, usn, time_val):
    # We can't use the 'conn' object for writing, as it's unreliable.
    # We will build a new, direct gspread connection for writing.
    try:
        # --- FINAL, ROBUST FIX ---
        # Use gspread directly, bypassing the st.connection object for writes.
        
        # 1. Define scopes and get credentials from Streamlit secrets
        scopes = [
            "https://spreadsheets.google.com/feeds",
            "https://www.googleapis.com/auth/drive"
        ]
        
        # st.connection automatically looks in "connections.gsheets", so we do the same
        # This assumes your secrets.toml has [connections.gsheets]
        creds_dict = st.secrets["connections"]["gsheets"]
        creds = Credentials.from_service_account_info(creds_dict, scopes=scopes)
        
        # 2. Authorize gspread
        client = gspread.authorize(creds)
        
        # 3. Open the spreadsheet by its ID (also from secrets)
        if "spreadsheet" not in creds_dict:
            st.error("GSheets Error: 'spreadsheet' (URL) not found in secrets.")
            return False
            
        spreadsheet_url = creds_dict["spreadsheet"]
        sh = client.open_by_url(spreadsheet_url)

        try:
            # 4. Try to get the worksheet
            worksheet = sh.worksheet("Scores")
        except gspread.exceptions.WorksheetNotFound:
            # 5. If not found, create it and add headers
            print("Worksheet 'Scores' not found, creating it.")
            worksheet = sh.add_worksheet(title="Scores", rows=100, cols=4)
            worksheet.append_row(["Tag", "Name", "USN", "Time"])
            print("Worksheet 'Scores' created with headers.")

        # 6. Append the new score data
        worksheet.append_row([
            str(tag), 
            str(name), 
            str(usn), 
            str(f"{time_val:.2f}") # Format time as string
        ])
        # --- END NEW FIX ---
        return True
    except Exception as e:
        # MODIFICATION: Print the actual error to the console and show it in Streamlit
        print(f"GSheets Write Error: {e}")
        st.error(f"GSheets Write Error: {e}")
        return False

def get_leaderboard():
    if conn:
        try:
            df = conn.read(worksheet="Scores", ttl=0, dtype=str)
            df.columns = df.columns.str.strip()
            if not all(c in df.columns for c in ['Tag', 'Name', 'USN', 'Time']): return pd.DataFrame(columns=["Rank", "Name", "USN", "Time"])
            df['Time'] = pd.to_numeric(df['Time'].astype(str).str.replace(',', ''), errors='coerce')
            df.dropna(subset=['Time', 'USN'], inplace=True)
            if df.empty: return pd.DataFrame(columns=["Rank", "Name", "USN", "Time"])
            df.sort_values(by='Time', ascending=True, inplace=True)
            df['Rank'] = range(1, len(df) + 1)
            df['Time'] = df['Time'].apply(lambda x: f"{x:.2f}s")
            return df[['Rank', 'Name', 'USN', 'Time']].head(10).reset_index(drop=True)
        except Exception: pass
    return pd.DataFrame(columns=["Rank", "Name", "USN", "Time"])

# --- MAIN INIT ---
# Assumes the video "167784-837438543.mp4" is in the same folder as your .py file
inject_css("167784-837438543.mp4") # <-- MODIFIED

def get_num_real_targets(level_idx): return 2 if level_idx == 2 else 1 # <-- MODIFIED

if 'game_state' not in st.session_state:
    st.session_state.update({'game_state': 'menu', 'current_level': 0, 'start_time': 0.0, 'player_tag': 'UNK', 'player_name': '', 'player_usn': '', 'final_time': 0.0, 'last_move_time': time.time(), 'glitch_seed': random.randint(1, 100000), 'real_boxes': [], 'fake_boxes': [], 'hits': 0})

st.title("DETROIT: ANOMALY [09]")

if st.session_state.game_state == "menu":
    st.markdown("### OPERATIVE DATA INPUT")
    tag = st.text_input(">> AGENT TAG (3 CHARS):", max_chars=3, value=st.session_state.player_tag if st.session_state.player_tag != 'UNK' else '').upper()
    name = st.text_input(">> FULL NAME:", value=st.session_state.player_name)
    usn = st.text_input(">> USN (e.g., 1MS22AI000):", value=st.session_state.player_usn).upper()
    
    if st.button(">> START SIMULATION <<", type="primary", disabled=(len(tag)!=3 or not name or not validate_usn(usn))):
        st.session_state.update({'game_state': 'playing', 'player_tag': tag, 'player_name': name, 'player_usn': usn, 'start_time': time.time(), 'current_level': 0, 'hits': 0})
        move_glitch(get_num_real_targets(0)); st.rerun()

    # --- TEST BUTTON REMOVED ---

    with st.expander("MISSION BRIEFING // RULES"):
        st.markdown("""
        OBJECTIVE: NEUTRALIZE ALL ACTIVE ANOMALIES IN MINIMUM TIME.
        PROTOCOLS:
        1. IDENTIFY: Real anomalies are BRIGHT and heavily inverted. Decoys are darker.
        2. ENGAGE: Tap precisely on the real anomaly.
        3. ADVANCE: Clear 3 Sectors.
        4. CAUTION: Sector 3 contains MULTIPLE simultaneous targets.
        """, unsafe_allow_html=True) # <-- MODIFIED
        
    with st.expander("CREDITS // SYSTEM INFO"):
        st.markdown("""
        DETROIT: ANOMALY [09]
        * Developed by:
        * Ace
        * BoBBY
        """)

    st.markdown("---")
    st.markdown("### GLOBAL RANKINGS")
    lb = get_leaderboard()
    if conn and not lb.empty: st.dataframe(lb, hide_index=True, use_container_width=True)
    elif conn: st.warning("WAITING FOR DATA LINK...")
    else: st.error("CONNECTION SEVERED.")

elif st.session_state.game_state == "playing":
    lvl = st.session_state.current_level
    needed, targets = GLITCHES_PER_LEVEL[lvl], get_num_real_targets(lvl)
    c1, c2, c3 = st.columns(3)
    c1.markdown(f"AGENT: {st.session_state.player_tag}"); c2.markdown(f"TIME: {time.time()-st.session_state.start_time:.1f}s"); c3.markdown(f"LVL: {lvl+1}/3") # <-- MODIFIED
    st.progress(st.session_state.hits/needed, text=f"Neutralized: {st.session_state.hits}/{needed}")
    
    gif, scaled_real, scaled_fake = generate_scaled_gif(LEVEL_FILES[lvl], st.session_state.real_boxes, st.session_state.fake_boxes, GAME_WIDTH, lvl, st.session_state.glitch_seed)
    if gif:
        coords = streamlit_image_coordinates(gif, key=f"lvl_{lvl}_{st.session_state.glitch_seed}", width=GAME_WIDTH)
        if coords:
            cx, cy = coords['x'], coords['y']
            hit = any((x1-HIT_TOLERANCE) <= cx <= (x2+HIT_TOLERANCE) and (y1-HIT_TOLERANCE) <= cy <= (y2+HIT_TOLERANCE) for x1,y1,x2,y2 in scaled_real)
            fake_hit = any((x1-HIT_TOLERANCE) <= cx <= (x2+HIT_TOLERANCE) and (y1-HIT_TOLERANCE) <= cy <= (y2+HIT_TOLERANCE) for x1,y1,x2,y2 in scaled_fake)
            if hit:
                trigger_static_transition(); st.session_state.hits += 1
                if st.session_state.hits >= needed:
                    if lvl < 2: st.session_state.current_level += 1; st.session_state.hits = 0; move_glitch(get_num_real_targets(st.session_state.current_level)) # <-- MODIFIED
                    else: st.session_state.final_time = time.time() - st.session_state.start_time; st.session_state.game_state = 'game_over'
                else: move_glitch(targets)
                st.rerun()
            elif fake_hit: st.toast("DECOY NEUTRALIZED.", icon="⚠"); move_glitch(targets); st.rerun()
            else: st.toast("MISS! RELOCATING...", icon="❌"); move_glitch(targets); st.rerun()

elif st.session_state.game_state == "game_over":
    st.balloons()
    st.markdown(f"## MISSION COMPLETE\n*OPERATIVE:* {st.session_state.player_name}\n*TIME:* {st.session_state.final_time:.2f}s")
    if st.button(">> UPLOAD SCORE <<", type="primary"):
        with st.spinner("UPLOADING..."):
            if save_score(st.session_state.player_tag, st.session_state.player_name, st.session_state.player_usn, st.session_state.final_time): st.success("UPLOAD SUCCESSFUL.")
            else: st.error("UPLOAD FAILED.")
        time.sleep(1.5); st.session_state.game_state = 'menu'; st.rerun()