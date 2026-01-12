import streamlit as st
import pandas as pd
from gtts import gTTS
import requests
import io
import base64
import difflib

# Page Config
st.set_page_config(page_title="English Vocab Quiz", page_icon="📝")

# --- Helper Functions ---
def clean_text(text):
    return "".join([c for c in text if c.isalpha() or c.isdigit() or c.isspace()]).strip()

def is_correct(user_input, answer, threshold=0.85):
    """Checks if the answer is correct using fuzzy matching."""
    user_input = clean_text(str(user_input).lower())
    answer = clean_text(str(answer).lower())
    
    if user_input == answer:
        return True
    
    # Fuzzy match
    similarity = difflib.SequenceMatcher(None, user_input, answer).ratio()
    return similarity >= threshold

def get_audio_html(text, label="Play Audio"):
    """Generates an HTML audio player for the given text using gTTS."""
    try:
        tts = gTTS(text=text, lang='en')
        # Save to memory
        mp3_fp = io.BytesIO()
        tts.write_to_fp(mp3_fp)
        mp3_fp.seek(0)
        
        # Encode to base64
        b64 = base64.b64encode(mp3_fp.read()).decode()
        md = f"""
            <audio controls autoplay>
            <source src="data:audio/mp3;base64,{b64}" type="audio/mp3">
            </audio>
            """
        return md
    except Exception as e:
        return f"Error generating audio: {e}"

def fetch_hint(word):
    """Fetches definition from Dictionary API."""
    try:
        url = f"https://api.dictionaryapi.dev/api/v2/entries/en/{word}"
        response = requests.get(url)
        if response.status_code == 200:
            data = response.json()
            return data[0]['meanings'][0]['definitions'][0]['definition']
    except Exception:
        pass
    return "No definition found."

def load_data(file):
    try:
        df = pd.read_excel(file)
        if 'English' not in df.columns or 'Korean' not in df.columns:
            st.error("Excel must have 'English' and 'Korean' columns.")
            return None
        return df
    except Exception as e:
        st.error(f"Error loading file: {e}")
        return None

# --- Session State Initialization ---
if 'data' not in st.session_state:
    st.session_state.data = None
if 'current_index' not in st.session_state:
    st.session_state.current_index = 0
if 'score' not in st.session_state:
    st.session_state.score = 0
if 'results' not in st.session_state:
    st.session_state.results = []
if 'input_key' not in st.session_state:
    st.session_state.input_key = 0  # To reset input field

# ... (Previous code)

# --- Sidebar ---
st.sidebar.title("Navigation")

# Mode Selector
mode = st.sidebar.radio("Quiz Mode", ["Reading (Eng -> Kor)", "Dictation (Listen -> Write)"])

# File Uploader
uploaded_file = st.sidebar.file_uploader("📂 Upload Vocabulary (.xlsx)", type=['xlsx'])

if uploaded_file:
    # Load new data if changed
    if st.session_state.data is None or (hasattr(uploaded_file, 'name') and st.session_state.get('last_file') != uploaded_file.name):
        df = load_data(uploaded_file)
        if df is not None:
            st.session_state.data = df
            st.session_state.total_words = len(df)
            st.session_state.current_index = 0
            st.session_state.score = 0
            st.session_state.results = [None] * len(df)
            st.session_state.last_file = uploaded_file.name
            st.rerun()

# Default Load (if no file uploaded)
if st.session_state.data is None:
    try:
        # Try loading default
        df = load_data('vocabulary.xlsx')
        if df is not None:
            st.session_state.data = df
            st.session_state.total_words = len(df)
            st.session_state.results = [None] * len(df)
    except:
        st.info("Please upload an Excel file to start.")

# Navigation Buttons
if st.session_state.data is not None:
    st.sidebar.subheader("Questions")
    
    # Grid layout for buttons
    cols = st.sidebar.columns(5)
    for i in range(st.session_state.total_words):
        status = st.session_state.results[i]
        label = f"{i+1}"
        
        # Color logic
        if status is True:
            emoji = "✅"
            kind = "primary"
        elif status is False:
            emoji = "❌"
            kind = "secondary"
        else:
            emoji = ""
            kind = "secondary"
            
        btn_label = f"{label} {emoji}" if emoji else label
        
        if cols[i%5].button(btn_label, key=f"nav_{i}", help=f"Go to Question {i+1}", use_container_width=True):
            st.session_state.current_index = i
            st.session_state.input_key += 1 # Reset input
            st.rerun()

    if st.sidebar.button("↻ Reset Quiz", use_container_width=True):
        st.session_state.current_index = 0
        st.session_state.score = 0
        st.session_state.results = [None] * st.session_state.total_words
        st.session_state.input_key += 1
        st.rerun()

# --- Main App ---
st.title("English Vocabulary Quiz")

if st.session_state.data is not None:
    idx = st.session_state.current_index
    row = st.session_state.data.iloc[idx]
    english_word = row['English']
    korean_meaning = row['Korean']

    # Progress
    st.progress((idx + 1) / st.session_state.total_words)
    st.write(f"**Question {idx + 1} / {st.session_state.total_words}** | **Score: {st.session_state.score}**")

    st.markdown("---")
    
    # Word Display Area
    is_dictation = mode == "Dictation (Listen -> Write)"
    
    if is_dictation:
        # Hide word, show placeholder
        display_text = "❓ ❓ ❓"
    else:
        display_text = english_word
        
    st.markdown(f"<h1 style='text-align: center; color: #333;'>{display_text}</h1>", unsafe_allow_html=True)
    
    # Audio Controls
    c1, c2 = st.columns(2)
    with c1:
        # In Dictation, audio is crucial, so we might want to autoplay or highlight it
        label = "🔊 Play Word" + (" (Listen!)" if is_dictation else "")
        if st.button(label, key=f"audio_{idx}", use_container_width=True):
            st.markdown(get_audio_html(english_word), unsafe_allow_html=True)
            
    with c2:
        if st.button("💡 Hint", key=f"hint_{idx}", use_container_width=True):
            with st.spinner("Fetching definition..."):
                definition = fetch_hint(english_word)
                st.info(f"Hint: {definition}")
                st.markdown(get_audio_html(definition), unsafe_allow_html=True)

    st.markdown("---")

    # Input Form
    with st.form(key=f"quiz_form_{idx}_{st.session_state.input_key}"):
        
        if is_dictation:
            col_spelling, col_meaning = st.columns(2)
            with col_spelling:
                user_spelling = st.text_input("English Spelling:", autocomplete="off")
            with col_meaning:
                user_meaning = st.text_input("Korean Meaning:", autocomplete="off")
        else:
            user_meaning = st.text_input("Meaning (Korean):", autocomplete="off")
            user_spelling = None # Not used

        submitted = st.form_submit_button("Submit", use_container_width=True)

        if submitted:
            # Check logic
            correct_meaning = is_correct(user_meaning, korean_meaning)
            
            if is_dictation:
                correct_spelling = is_correct(user_spelling, english_word)
                is_right = correct_meaning and correct_spelling
                
                if is_right:
                    st.success("Perfect! 🎉")
                else:
                    msg = []
                    if not correct_spelling: msg.append(f"Spelling: {english_word}")
                    if not correct_meaning: msg.append(f"Meaning: {korean_meaning}")
                    st.error(f"Incorrect. ({', '.join(msg)})")
            else:
                is_right = correct_meaning
                if is_right:
                    st.success("Correct! 🎉")
                else:
                    st.error(f"Incorrect. Answer: {korean_meaning}")

            # Grading
            if is_right:
                if st.session_state.results[idx] is not True: 
                    st.session_state.score += 1
                st.session_state.results[idx] = True
            else:
                st.session_state.results[idx] = False
            
            # Show Next Button outside form (to avoid nested form issues, Streamlit quirks)
            st.session_state.show_next = True

    # Next Navigation (Simple 'Next' button below form)
    if st.button("Next Question ➡️"):
        if st.session_state.current_index < st.session_state.total_words - 1:
            st.session_state.current_index += 1
            st.session_state.input_key += 1
            st.rerun()
        else:
            st.balloons()
            st.success(f"Quiz Finished! Final Score: {st.session_state.score} / {st.session_state.total_words}")

else:
    st.warning("No vocabulary data loaded. Please upload a file.")
