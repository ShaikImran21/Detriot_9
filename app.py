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
from google.oauth2.service_account import Credentials

# --- CONFIGURATION ---
st.set_page_config(page_title="DETROIT: ANOMALY [09]", layout="wide", initial_sidebar_state="collapsed")

GAME_WIDTH = 1200
HIT_TOLERANCE = 150

LEVEL_FILES = ["assets/level1.png", "assets/level2.png", "assets/level3.png"]
GLITCHES_PER_LEVEL = [3, 5, 7]

# --- HELPER: ASSETS ---
def get_base64(bin_file):
    try:
        with open(bin_file, 'rb') as f:
            return base64.b64encode(f.read()).decode()
    except:
        return None

# --- AUDIO FUNCTIONS ---
@st.cache_data(show_spinner=False, persist="disk")
def get_audio_base64(bin_file):
    try:
        with open(bin_file, 'rb') as f:
            return base64.b64encode(f.read()).decode()
    except:
        return None


def play_background_music(audio_file, file_type="mp3", audio_id="bg-music"):
    try:
        audio_base64 = get_audio_base64(audio_file)
        if audio_base64:
            audio_html = f"""
                <audio id="{audio_id}" autoplay loop style="display:none;">
                    <source src="data:audio/{file_type};base64,{audio_base64}" type="audio/{file_type}">
                </audio>
            """
            return audio_html
        return ""
    except Exception as e:
        print(f"Background audio error: {e}")
        return ""


def play_audio(audio_file, file_type="wav", audio_id=""):
    """
    Works with both local files and remote URLs.
    """
    try:
        if isinstance(audio_file, str) and (audio_file.startswith("http://") or audio_file.startswith("https://")):
            unique_id = f"{audio_id}_{random.randint(1000,9999)}"
            audio_html = f"""
                <audio id="{unique_id}" autoplay style="display:none;">
                    <source src="{audio_file}" type="audio/{file_type}">
                </audio>
            """
            st.markdown(audio_html, unsafe_allow_html=True)
            return

        audio_base64 = get_audio_base64(audio_file)
        if audio_base64:
            unique_id = f"{audio_id}_{random.randint(1000,9999)}"
            audio_html = f"""
                <audio id="{unique_id}" autoplay style="display:none;">
                    <source src="data:audio/{file_type};base64,{audio_base64}" type="audio/{file_type}">
                </audio>
            """
            st.markdown(audio_html, unsafe_allow_html=True)
    except Exception as e:
        print(f"Audio error: {e}")
        pass


# --- CSS / VIDEO / GLITCH ---
def inject_css(video_file_path):
    video_base64 = get_base64(video_file_path)
    if video_base64:
        video_html = f"""
        <video id="video-bg" autoplay loop muted>
            <source src="data:video/mp4;base64,{video_base64}" type="video/mp4">
        </video>
        """
        st.markdown(video_html, unsafe_allow_html=True)

    st.markdown(f"""
        <style>
            #video-bg {{
                position: fixed;
                right: 0;
                bottom: 0;
                min-width: 100%;
                min-height: 100%;
                width: auto;
                height: auto;
                z-index: -100;
                object-fit: cover;
                opacity: 1.0;
                display: none;
            }}
            .stApp {{ 
                background-color: #080808;
                color: #d0d0d0; 
                font-family: 'Courier New', monospace; 
            }}
            #MainMenu, footer, header {{visibility: hidden;}}
            .block-container {{overflow-x: auto !important;}}
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
                75% {{ transform: translate3d(-5px, 5px, 0); opacity: 0.25; }}
            }}
            h1,h2,h3,h4,h5,h6,p,label,span,div,button,a,input {{
                animation: glitch-text 500ms infinite !important; color: #d0d0d0 !important;
            }}
            @keyframes glitch-text {{
                0% {{ text-shadow: 0.05em 0 0 rgba(255,0,0,0.75), -0.025em -0.05em 0 rgba(0,255,0,0.75); }}
                50% {{ text-shadow: -0.05em -0.025em 0 rgba(255,0,0,0.75), 0.05em 0.025em 0 rgba(0,255,0,0.75); }}
                100% {{ text-shadow: 0.025em 0.05em 0 rgba(255,0,0,0.75), 0.05em 0 0 rgba(0,255,0,0.75); }}
            }}
        </style>
    """, unsafe_allow_html=True)


def trigger_static_transition():
    play_audio("https://www.myinstants.com/media/sounds/static-noise.mp3", file_type="mp3", audio_id="static")
    placeholder = st.empty()
    with placeholder.container():
        st.markdown('<div style="position:fixed;top:0;left:0;width:100%;height:100%;background-color:#111;z-index:10000;"></div>', unsafe_allow_html=True)
        time.sleep(0.1)
        g_url = "https://media.giphy.com/media/oEI9uBYSzLpBK/giphy.gif"
        st.markdown(f'<div style="position:fixed;top:0;left:0;width:100%;height:100%;background:url({g_url});background-size:cover;z-index:10001;opacity:0.8;mix-blend-mode:hard-light;"></div>', unsafe_allow_html=True)
        time.sleep(0.4)
    placeholder.empty()


# --- GLITCH GENERATION ---
def check_overlap(box1, box2, buffer=20):
    b1_x1, b1_y1, b1_x2, b1_y2 = box1
    b2_x1, b2_y1, b2_x2, b2_y2 = box2
    if (b1_x2 + buffer < b2_x1) or (b2_x2 + buffer < b1_x1) or (b1_y2 + buffer < b2_y1) or (b2_y2 + buffer < b1_y1):
        return False
    return True


def get_random_box_for_image(img_w, img_h, level, is_fake=False):
    base_min = max(int(min(img_w, img_h) * 0.04), 20)
    base_max = max(int(min(img_w, img_h) * 0.18), base_min + 10)
    if is_fake:
        max_s = max(base_max - level * 6, base_min + 10)
        min_s = max(base_min - level * 2, 12)
    else:
        max_s = max(base_max - level * 10, base_min + 5)
        min_s = max(base_min - level * 5, 10)
    w = random.randint(min_s, min(max_s, img_w - 40))
    h = random.randint(min_s, min(max_s, img_h - 40))
    x = random.randint(20, max(20, img_w - w - 20))
    y = random.randint(20, max(20, img_h - h - 20))
    return (x, y, w, h)


def move_glitch(num_real=1):
    lvl = st.session_state.current_level
    img_path = LEVEL_FILES[lvl]
    try:
        img = Image.open(img_path)
        img_w, img_h = img.size
        img.close()
    except Exception:
        img_w, img_h = 1024, 1024

    st.session_state.glitch_seed = random.randint(1, 100000)
    real_temp, fake_temp = [], []
    for _ in range(num_real):
        for _ in range(200):
            nb = get_random_box_for_image(img_w, img_h, lvl, False)
            rect = (nb[0], nb[1], nb[0]+nb[2], nb[1]+nb[3])
            if not any(check_overlap(rect, b) for b in real_temp):
                real_temp.append(rect)
                break
    for _ in range(lvl + 1):
        for _ in range(200):
            nb = get_random_box_for_image(img_w, img_h, lvl, True)
            rect = (nb[0], nb[1], nb[0]+nb[2], nb[1]+nb[3])
            if not any(check_overlap(rect, b) for b in real_temp + fake_temp):
                fake_temp.append(rect)
                break
    st.session_state.real_boxes = real_temp
    st.session_state.fake_boxes = fake_temp
    st.session_state.last_move_time = time.time()


def generate_mutating_frame(base_img, boxes, is_fake=False):
    frame = base_img.copy()
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
            except:
                pass
    return frame


@st.cache_data(show_spinner=False, persist="disk")
def generate_scaled_gif(img_path, real_boxes_orig, fake_boxes_orig, target_width, level_idx, glitch_seed):
    try:
        random.seed(glitch_seed)
        base_img = Image.open(img_path).convert("RGB")
        orig_w, orig_h = base_img.size
        target_height = int(target_width * (9 / 16))
        sf_w, sf_h = target_width / orig_w, target_height / orig_h
        base_resized = base_img.resize((target_width, target_height), Image.Resampling.LANCZOS)
        scaled_real = [(int(x1*sf_w), int(y1*sf_h), int(x2*sf_w), int(y2*sf_h)) for x1,y1,x2,y2 in real_boxes_orig]
        scaled_fake = [(int(x1*sf_w), int(y1*sf_h), int(x2*sf_h), int(y2*sf_h)) for x1,y1,x2,y2 in fake_boxes_orig]
        frames = [base_resized.copy() for _ in range(15)]
        for _ in range(8):
            f = generate_mutating_frame(base_resized.copy(), scaled_real, is_fake=False)
            f = generate_mutating_frame(f, scaled_fake, is_fake=True)
            frames.append(f)
        temp_file = f"/tmp/lvl_{level_idx}_{glitch_seed}.gif"
        durations = [200]*15 + [70]*8
        frames[0].save(temp_file, format="GIF", save_all=True, append_images=frames[1:], duration=durations, loop=0)
        return temp_file, scaled_real, scaled_fake
    except Exception as e:
        print("generate_scaled_gif error:", e)
        return None, [], []


# --- VALIDATION ---
def validate_usn(usn):
    return re.match(r"^\d[A-Z]{2}\d{2}[A-Z]{2}\d{3}$", usn)


# --- GOOGLE SHEETS ---
conn = None
try:
    conn = st.connection("gsheets", type=GSheetsConnection)
except:
    pass

def save_score(tag, name, usn, time_val):
    try:
        scopes = [
            "https://spreadsheets.google.com/feeds",
            "https://www.googleapis.com/auth/drive"
        ]
        creds_dict = st.secrets["connections"]["gsheets"]
        creds = Credentials.from_service_account_info(creds_dict, scopes=scopes)
        client = gspread.authorize(creds)
        spreadsheet_url = creds_dict["spreadsheet"]
        sh = client.open_by_url(spreadsheet_url)
        try:
            worksheet = sh.worksheet("Scores")
        except gspread.exceptions.WorksheetNotFound:
            worksheet = sh.add_worksheet(title="Scores", rows=100, cols=4)
            worksheet.append_row(["Tag", "Name", "USN", "Time"])
        worksheet.append_row([str(tag), str(name), str(usn), f"{time_val:.2f}"])
        return True
    except Exception as e:
        print(f"GSheets Write Error: {e}")
        return False

def get_leaderboard():
    if conn:
        try:
            df = conn.read(worksheet="Scores", ttl=0, dtype=str)
            df.columns = df.columns.str.strip()
            if not all(c in df.columns for c in ['Tag', 'Name', 'USN', 'Time']):
                return pd.DataFrame(columns=["Rank", "Name", "USN", "Time"])
            df['Time'] = pd.to_numeric(df['Time'].astype(str).str.replace(',', ''), errors='coerce')
            df.dropna(subset=['Time', 'USN'], inplace=True)
            if df.empty:
                return pd.DataFrame(columns=["Rank", "Name", "USN", "Time"])
            df.sort_values(by='Time', ascending=True, inplace=True)
            df['Rank'] = range(1, len(df)+1)
            df['Time'] = df['Time'].apply(lambda x: f"{x:.2f}s")
            return df[['Rank', 'Name', 'USN', 'Time']].head(10).reset_index(drop=True)
        except Exception:
            pass
    return pd.DataFrame(columns=["Rank", "Name", "USN", "Time"])


# --- MAIN INIT ---
inject_css("167784-837438543.mp4")
def get_num_real_targets(level_idx): return 2 if level_idx == 2 else 1

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
        'real_boxes': [], 
        'fake_boxes': [], 
        'hits': 0,
        'menu_music_playing': False,
        'gameplay_music_playing': False,
        'menu_music_placeholder': st.empty(),
        'game_music_placeholder': st.empty()
    })

st.title("DETROIT: ANOMALY [09]")

# --- MENU STATE ---
if st.session_state.game_state == "menu":
    st.markdown("<style>#video-bg { display:block!important; }</style>", unsafe_allow_html=True)

    if 'audio_enabled' not in st.session_state:
        st.session_state.audio_enabled = False
    if not st.session_state.audio_enabled:
        st.warning("🔊 Audio disabled. Click to enable.")
        if st.button("🎵 ENABLE AUDIO"):
            st.session_state.audio_enabled = True
            play_audio("541987__rob_marion__gasp_ui_clicks_5.wav")
            time.sleep(0.1)
            st.rerun()

    if st.session_state.audio_enabled:
        audio_html = play_background_music("537256__humanfobia__letargo-sumergido.mp3")
        st.session_state.menu_music_placeholder.markdown(audio_html, unsafe_allow_html=True)

    st.markdown("### OPERATIVE DATA INPUT")
    tag = st.text_input(">> AGENT TAG (3 CHARS):", max_chars=3, value=st.session_state.player_tag if st.session_state.player_tag != 'UNK' else '').upper()
    name = st.text_input(">> FULL NAME:", value=st.session_state.player_name)
    usn = st.text_input(">> USN (e.g., 1MS22AI000):", value=st.session_state.player_us)
