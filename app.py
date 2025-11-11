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

# --- Helper: Load base64 for files ---
def get_base64(bin_file):
    try:
        with open(bin_file, 'rb') as f: return base64.b64encode(f.read()).decode()
    except: return None

# --- Audio caching ---
@st.cache_data(show_spinner=False, persist="disk")
def get_audio_base64(bin_file):
    try:
        with open(bin_file, 'rb') as f: return base64.b64encode(f.read()).decode()
    except: return None

# --- Play audio function ---
def play_audio(audio_file, loop=False, file_type="wav"):
    try:
        audio_base64 = get_audio_base64(audio_file)
        if audio_base64:
            loop_attr = "loop" if loop else ""
            audio_html = f"""
                <audio autoplay {loop_attr} style="display:none;">
                    <source src="data:audio/{file_type};base64,{audio_base64}" type="audio/{file_type}">
                </audio>
            """
            container = st.empty()
            container.markdown(audio_html, unsafe_allow_html=True)
            if not loop:
                time.sleep(0.1)
                container.empty()
    except:
        pass

# --- Persistent container for menu music (keeps music playing on reruns) ---
if 'menu_audio_container' not in st.session_state:
    st.session_state.menu_audio_container = st.empty()

def play_menu_music():
    audio_file = "537256__humanfobia__letargo-sumergido.mp3"
    try:
        audio_base64 = get_audio_base64(audio_file)
        if audio_base64:
            audio_html = f"""
                <audio autoplay loop style="display:none;" id="menu-music">
                    <source src="data:audio/mp3;base64,{audio_base64}" type="audio/mp3">
                </audio>
            """
            st.session_state.menu_audio_container.markdown(audio_html, unsafe_allow_html=True)
    except:
        pass

# --- CSS and Video Background injecting function ---
def inject_css(video_file_path):
    video_base64 = get_base64(video_file_path)
    if video_base64:
        video_html = f"""
        <video id="video-bg" autoplay loop muted>
            <source src="data:video/mp4;base64,{video_base64}" type="video/mp4">
            Your browser does not support the video tag.
        </video>
        """
        st.markdown(video_html, unsafe_allow_html=True)
    st.markdown(f"""
        <style>
            /* CSS styles here as in your code */
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
                background-size: cover;
                background-repeat: no-repeat;
                background-attachment: fixed;
                background-position: center;
                color: #d0d0d0; 
                font-family: 'Courier New', monospace; 
            }}
            #MainMenu, footer, header {{visibility: hidden;}}
            .block-container {{
                overflow-x: auto !important;
            }}
            /* Other CSS omitted for brevity */
        </style>
    """, unsafe_allow_html=True)

# --- Other functions like trigger_static_transition, get_random_box, check_overlap, move_glitch, generate_mutating_frame, generate_scaled_gif, validate_usn, save_score, get_leaderboard ---
# Keep all your existing implementations as provided by you above.

inject_css("167784-837438543.mp4")

def get_num_real_targets(level_idx): return 2 if level_idx == 2 else 1

if 'game_state' not in st.session_state:
    st.session_state.update({'game_state': 'menu', 'current_level': 0, 'start_time': 0.0, 'player_tag': 'UNK', 'player_name': '', 'player_usn': '', 'final_time': 0.0, 'last_move_time': time.time(), 'glitch_seed': random.randint(1, 100000), 'real_boxes': [], 'fake_boxes': [], 'hits': 0})

st.title("DETROIT: ANOMALY [09]")

if st.session_state.game_state == "menu":
    st.markdown("""
        <style>
        #video-bg { display: block !important; }
        .stApp { background-color: rgba(8, 8, 8, 0.75) !important; }
        </style>
        """, unsafe_allow_html=True)
    play_menu_music()  # <-- Play persistent menu music here
    
    st.markdown("### OPERATIVE DATA INPUT")
    tag = st.text_input(">> AGENT TAG (3 CHARS):", max_chars=3, value=st.session_state.player_tag if st.session_state.player_tag != 'UNK' else '').upper()
    name = st.text_input(">> FULL NAME:", value=st.session_state.player_name)
    usn = st.text_input(">> USN (e.g., 1MS22AI000):", value=st.session_state.player_usn).upper()

    if st.button(">> START SIMULATION <<", type="primary", disabled=(len(tag)!=3 or not name or not validate_usn(usn))):
        play_audio("541987__rob_marion__gasp_ui_clicks_5.wav", file_type="wav")
        time.sleep(0.1)
        st.session_state.update({'game_state': 'playing', 'player_tag': tag, 'player_name': name, 'player_usn': usn, 'start_time': time.time(), 'current_level': 0, 'hits': 0})
        move_glitch(get_num_real_targets(0))
        st.rerun()

    with st.expander("MISSION BRIEFING // RULES"):
        st.markdown("""
        OBJECTIVE: NEUTRALIZE ALL ACTIVE ANOMALIES IN MINIMUM TIME.
        PROTOCOLS:
        1. IDENTIFY: Real anomalies are BRIGHT and heavily inverted. Decoys are darker.
        2. ENGAGE: Tap precisely on the real anomaly.
        3. ADVANCE: Clear 3 Sectors.
        4. CAUTION: Sector 3 contains MULTIPLE simultaneous targets.
        """, unsafe_allow_html=True)

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
    play_audio("615546__projecteur__cosmic-dark-synthwave.mp3", loop=True, file_type="mp3")

    lvl = st.session_state.current_level
    needed, targets = GLITCHES_PER_LEVEL[lvl], get_num_real_targets(lvl)
    c1, c2, c3 = st.columns(3)
    c1.markdown(f"AGENT: {st.session_state.player_tag}")
    c2.markdown(f"TIME: {time.time()-st.session_state.start_time:.1f}s")
    c3.markdown(f"LVL: {lvl+1}/3")
    st.progress(st.session_state.hits/needed, text=f"Neutralized: {st.session_state.hits}/{needed}")
    
    gif, scaled_real, scaled_fake = generate_scaled_gif(LEVEL_FILES[lvl], st.session_state.real_boxes, st.session_state.fake_boxes, GAME_WIDTH, lvl, st.session_state.glitch_seed)
    if gif:
        coords = streamlit_image_coordinates(gif, key=f"lvl_{lvl}_{st.session_state.glitch_seed}", width=GAME_WIDTH)
        if coords:
            cx, cy = coords['x'], coords['y']
            hit = any((x1-HIT_TOLERANCE) <= cx <= (x2+HIT_TOLERANCE) and (y1-HIT_TOLERANCE) <= cy <= (y2+HIT_TOLERANCE) for x1,y1,x2,y2 in scaled_real)
            fake_hit = any((x1-HIT_TOLERANCE) <= cx <= (x2+HIT_TOLERANCE) and (y1-HIT_TOLERANCE) <= cy <= (y2+HIT_TOLERANCE) for x1,y1,x2,y2 in scaled_fake)
            
            if hit:
                play_audio("828680__jw_audio__uimisc_digital-interface-message-selection-confirmation-alert_10_jw-audio_user-interface.wav", file_type="wav")
                trigger_static_transition()
                st.session_state.hits += 1
                if st.session_state.hits >= needed:
                    if lvl < 2:
                        st.session_state.current_level += 1
                        st.session_state.hits = 0
                        move_glitch(get_num_real_targets(st.session_state.current_level))
                    else:
                        st.session_state.final_time = time.time() - st.session_state.start_time
                        st.session_state.game_state = 'game_over'
                else:
                    move_glitch(targets)
                st.rerun()
                
            elif fake_hit:
                play_audio("713179__vein_adams__user-interface-beep-error-404-glitch.wav", file_type="wav")
                st.toast("DECOY NEUTRALIZED.", icon="⚠")
                move_glitch(targets)
                st.rerun()
            
            else:
                play_audio("541987__rob_marion__gasp_ui_clicks_5.wav", file_type="wav")
                st.toast("MISS! RELOCATING...", icon="❌")
                move_glitch(targets)
                st.rerun()

elif st.session_state.game_state == "game_over":
    st.balloons()
    st.markdown(f"## MISSION COMPLETE\n*OPERATIVE:* {st.session_state.player_name}\n*TIME:* {st.session_state.final_time:.2f}s")
    if st.button(">> UPLOAD SCORE <<", type="primary"):
        with st.spinner("UPLOADING..."):
            if save_score(st.session_state.player_tag, st.session_state.player_name, st.session_state.player_usn, st.session_state.final_time):
                st.success("UPLOAD SUCCESSFUL.")
            else:
                st.error("UPLOAD FAILED.")
        time.sleep(1.5)
        st.session_state.game_state = 'menu'
        st.rerun()
