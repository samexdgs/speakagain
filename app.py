"""
SpeakAgain — AI-powered Aphasia Communication & Rehabilitation Aid
Project #6 of 10 — Neurological Rehabilitation AI Series
Samuel Oluwakoya · Lagos, Nigeria · Samuel@bloomgatelaw.com

Run locally:
    pip install -r requirements.txt
    streamlit run app.py

Deploy on Streamlit Community Cloud:
    1. Push this folder to GitHub
    2. Connect GitHub to streamlit.io
    3. Add secrets in app settings:
        BREVO_API_KEY = "xkeysib-..."
        ANTHROPIC_API_KEY = "sk-ant-..." (optional — app works without it)
"""
import streamlit as st
import pandas as pd
import numpy as np
from datetime import datetime, timedelta
import random
import json
import io
import base64
from pathlib import Path

import plotly.graph_objects as go
import plotly.express as px

from clinical_data import (
    APHASIA_TYPES, ASSESSMENT_TASKS, classify_aphasia,
    PHRASE_LIBRARY, MULTILINGUAL_PHRASES,
    WORD_BANK, SENTENCE_BUILDING, CLOZE_EXERCISES, READING_PASSAGES,
    get_exercise_difficulty, detect_crisis, EMOTIONS,
)
from ai_completion import complete_sentence, predict_next_words
from brevo_mailer import (
    send_daily_summary, send_milestone_email, send_concern_alert, send_welcome_email,
)

# Try gTTS — graceful if not available
try:
    from gtts import gTTS
    TTS_AVAILABLE = True
except Exception:
    TTS_AVAILABLE = False


# ==================================================================
# STREAMLIT CONFIG
# ==================================================================
st.set_page_config(
    page_title="SpeakAgain — Aphasia AI Aid",
    page_icon="💬",
    layout="wide",
    initial_sidebar_state="expanded",
)


# ==================================================================
# STYLES — patient-friendly UI: large text, high contrast, calm colors
# ==================================================================
def inject_css():
    st.markdown("""
    <style>
    /* Base fonts larger for readability */
    html, body, [class*="css"] {
        font-size: 16px !important;
    }
    .big-button {
        background: #2B6CB0;
        color: white;
        padding: 16px 24px;
        border-radius: 10px;
        font-size: 18px;
        font-weight: 500;
        border: none;
        width: 100%;
        cursor: pointer;
        margin: 6px 0;
    }
    .phrase-card {
        background: #EBF4FF;
        border: 1px solid #B5D4F4;
        border-radius: 10px;
        padding: 14px 18px;
        margin: 8px 0;
        font-size: 18px;
        color: #1A3A5C;
    }
    .suggestion {
        background: #FFFFFF;
        border: 1px solid #D3D1C7;
        border-radius: 10px;
        padding: 16px;
        margin: 10px 0;
        font-size: 18px;
        line-height: 1.5;
    }
    .suggestion-top {
        border-color: #639922;
        background: #EAF3DE;
    }
    .confidence-high { color: #27500A; font-weight: 500; }
    .confidence-med { color: #854F0B; font-weight: 500; }
    .confidence-low { color: #5F5E5A; font-weight: 500; }
    .metric-big {
        font-size: 42px;
        font-weight: 500;
        color: #1A3A5C;
    }
    .metric-label {
        font-size: 14px;
        color: #5F5E5A;
    }
    .pill {
        display: inline-block;
        padding: 4px 12px;
        border-radius: 20px;
        font-size: 13px;
        margin-right: 6px;
    }
    .pill-info { background: #E6F1FB; color: #0C447C; }
    .pill-success { background: #EAF3DE; color: #27500A; }
    .pill-warning { background: #FAEEDA; color: #854F0B; }
    .pill-alert { background: #FCEBEB; color: #791F1F; }
    .hero {
        background: linear-gradient(135deg, #1A3A5C, #2B6CB0);
        color: white;
        padding: 24px 28px;
        border-radius: 14px;
        margin-bottom: 20px;
    }
    .hero h1 { color: white; margin: 0; font-size: 26px; font-weight: 500; }
    .hero p { color: #B5D4F4; margin-top: 6px; font-size: 15px; }
    </style>
    """, unsafe_allow_html=True)

inject_css()


# ==================================================================
# SESSION STATE — keeps data during the session
# (In production, this moves to Supabase)
# ==================================================================
def init_state():
    defaults = {
        "profile": None,             # {name, email, caregiver_email, caregiver_name, language}
        "assessment_complete": False,
        "aphasia_type": None,
        "severity": None,
        "severity_history": [],      # [(date, score)]
        "context_history": [],       # recent communications for AI context
        "communicated_today": [],    # sentences sent today
        "exercise_log": [],          # [{date, type, correct, total}]
        "emotion_log": [],           # [{date, emoji, label}]
        "recovered_words": set(),
        "streak_days": 0,
        "last_session_date": None,
        "daily_target": 5,           # exercises per day
        "last_suggestions": [],
        "current_exercise": None,
        "exercise_answer_given": False,
        "text_size": "normal",       # normal / large / x-large
        "high_contrast": False,
        "hand_preference": "right",
    }
    for k, v in defaults.items():
        if k not in st.session_state:
            st.session_state[k] = v


init_state()


# ==================================================================
# HELPERS
# ==================================================================
def text_to_speech_html(text: str) -> str:
    """Generate TTS audio and return HTML audio player."""
    if not TTS_AVAILABLE:
        return ""
    try:
        tts = gTTS(text=text, lang="en", slow=False)
        buf = io.BytesIO()
        tts.write_to_fp(buf)
        buf.seek(0)
        audio_b64 = base64.b64encode(buf.read()).decode()
        return f"""<audio autoplay controls style="width:100%;margin-top:8px;">
        <source src="data:audio/mpeg;base64,{audio_b64}" type="audio/mpeg">
        </audio>"""
    except Exception:
        return ""


def update_streak():
    today = datetime.now().date()
    last = st.session_state.last_session_date
    if last is None:
        st.session_state.streak_days = 1
    elif last == today:
        pass  # same day, no change
    elif last == today - timedelta(days=1):
        st.session_state.streak_days += 1
    else:
        st.session_state.streak_days = 1
    st.session_state.last_session_date = today


def register_exercise_result(exercise_type: str, correct: bool, word: str = None):
    st.session_state.exercise_log.append({
        "date": datetime.now().isoformat(),
        "type": exercise_type,
        "correct": correct,
        "word": word,
    })
    if correct and word:
        st.session_state.recovered_words.add(word.lower())
    update_streak()


def get_today_stats():
    today = datetime.now().date().isoformat()[:10]
    today_exercises = [
        e for e in st.session_state.exercise_log
        if e["date"][:10] == today
    ]
    completed = len(today_exercises)
    correct = sum(1 for e in today_exercises if e["correct"])
    return completed, correct, len(today_exercises)


# ==================================================================
# ONBOARDING / PROFILE SETUP
# ==================================================================
def render_onboarding():
    st.markdown("""
    <div class="hero">
      <h1>Welcome to SpeakAgain</h1>
      <p>An AI communication and rehabilitation aid built for stroke survivors with aphasia.<br>
      By Samuel Oluwakoya · Project #6 of 10 in the Neurological Rehabilitation AI Series.</p>
    </div>
    """, unsafe_allow_html=True)

    col1, col2 = st.columns([3, 2])
    with col1:
        st.markdown("### Let's set up your profile")
        st.caption("This takes one minute. All data stays in your session.")

        with st.form("profile_setup"):
            name = st.text_input("Your name", placeholder="e.g. Samuel")
            email = st.text_input("Your email (optional)", placeholder="for progress reports")
            st.markdown("---")
            st.markdown("**Caregiver or family member** (receives daily updates)")
            caregiver_name = st.text_input("Caregiver name", placeholder="e.g. Ngozi")
            caregiver_email = st.text_input("Caregiver email", placeholder="for alerts & daily summaries")

            language = st.selectbox(
                "Preferred language for phrases",
                ["English", "Yoruba", "Igbo", "Hausa", "Pidgin"],
            )
            hand = st.radio("Which hand do you use?", ["Right", "Left"], horizontal=True)

            submitted = st.form_submit_button("Start SpeakAgain", use_container_width=True, type="primary")

            if submitted:
                if not name.strip():
                    st.error("Please enter your name.")
                else:
                    st.session_state.profile = {
                        "name": name.strip(),
                        "email": email.strip(),
                        "caregiver_email": caregiver_email.strip(),
                        "caregiver_name": caregiver_name.strip() or "Caregiver",
                        "language": language,
                    }
                    st.session_state.hand_preference = hand.lower()

                    # Try welcome email (silent if no API key)
                    if email.strip():
                        ok, _ = send_welcome_email(email.strip(), name.strip(), "patient")
                    st.rerun()

    with col2:
        st.markdown("### What you can do here")
        st.markdown("""
        <div class="phrase-card">
        <strong>Communication mode</strong><br>
        Type a few words. The AI builds the full sentence and reads it aloud.
        </div>
        <div class="phrase-card">
        <strong>Daily exercises</strong><br>
        Short speech therapy tailored to your aphasia type and severity.
        </div>
        <div class="phrase-card">
        <strong>Caregiver connection</strong><br>
        Family gets daily updates and alerts when you need support.
        </div>
        <div class="phrase-card">
        <strong>Progress tracking</strong><br>
        See your word recovery, exercise streaks, and severity improvements.
        </div>
        """, unsafe_allow_html=True)


# ==================================================================
# ASSESSMENT — classifies aphasia type and severity
# ==================================================================
def render_assessment():
    st.markdown("## Quick aphasia assessment")
    st.caption("8 questions. Takes 5 minutes. Helps us personalise everything else.")

    st.info("Answer based on how you are right now. Your caregiver can help if needed.")

    with st.form("assessment_form"):
        responses = {}
        for task in ASSESSMENT_TASKS:
            st.markdown(f"**{task['prompt']}**")
            option_labels = [opt[0] for opt in task["options"]]
            choice = st.radio(
                "Select one:",
                option_labels,
                key=f"ass_{task['id']}",
                label_visibility="collapsed",
            )
            score = next(opt[1] for opt in task["options"] if opt[0] == choice)
            responses[task["id"]] = score
            st.markdown("---")

        submit = st.form_submit_button("See my results", use_container_width=True, type="primary")

        if submit:
            aph_type, severity = classify_aphasia(responses)
            st.session_state.aphasia_type = aph_type
            st.session_state.severity = severity
            st.session_state.severity_history.append(
                (datetime.now().isoformat(), severity)
            )
            st.session_state.assessment_complete = True
            st.rerun()


def render_assessment_result():
    aph = APHASIA_TYPES[st.session_state.aphasia_type]
    sev = st.session_state.severity

    st.markdown(f"""
    <div class="hero" style="background: linear-gradient(135deg, {aph['color']}, #1A3A5C);">
      <h1>Your result: {aph['name']}</h1>
      <p>Severity score: <strong>{sev} / 5</strong></p>
    </div>
    """, unsafe_allow_html=True)

    st.markdown(f"### What this means")
    st.markdown(aph["description"])
    st.markdown(f"**Recovery focus for you:** {aph['recovery_focus']}")

    col1, col2, col3 = st.columns(3)
    with col1:
        st.metric("Severity score", f"{sev} / 5")
    with col2:
        st.metric("Exercise difficulty", f"Level {get_exercise_difficulty(sev)}")
    with col3:
        st.metric("Aphasia type", aph["name"].split(" (")[0])

    st.info("You can now use Communication Mode and Daily Exercises. Your progress will be tracked, and we'll reassess monthly to see improvement.")

    if st.button("Continue to main app →", use_container_width=True, type="primary"):
        st.rerun()


# ==================================================================
# COMMUNICATION MODE — fragment to sentence
# ==================================================================
def render_communication():
    st.markdown("## 💬 Communication mode")
    st.caption("Type what you can. Even just one or two words. I'll build the sentence.")

    profile = st.session_state.profile

    # Input area
    col1, col2 = st.columns([4, 1])
    with col1:
        fragment = st.text_input(
            "What do you want to say?",
            placeholder="e.g. hungry, or 'hungry dinner wife'",
            key="comm_fragment",
            label_visibility="collapsed",
        )
    with col2:
        go_clicked = st.button("Complete →", use_container_width=True, type="primary")

    # Predictive typing suggestions — note: we DON'T try to write back into
    # the same key Streamlit is using for the input widget (that causes
    # StreamlitAPIException). Instead, when a suggestion is clicked we
    # append it to a separate "extra" field that the user can combine.
    if fragment:
        last_word = fragment.split()[-1] if fragment.split() else ""
        predictions = predict_next_words(last_word, limit=6)
        if predictions and last_word:
            st.caption("Tap a word to hear it spoken — then type it in above:")
            cols = st.columns(len(predictions))
            for i, word in enumerate(predictions):
                with cols[i]:
                    if st.button(word, key=f"pred_{i}_{word}", use_container_width=True):
                        # Speak the predicted word in the patient's language
                        lang_code = get_tts_lang_code(
                            st.session_state.profile.get("language", "English")
                            if st.session_state.profile else "English"
                        )
                        audio = text_to_speech_html(word, lang=lang_code)
                        if audio:
                            st.markdown(audio, unsafe_allow_html=True)

    # Generate suggestions
    if go_clicked and fragment.strip():
        with st.spinner("Building sentences..."):
            suggestions, source = complete_sentence(
                fragment,
                aphasia_type=st.session_state.aphasia_type or "anomic",
                context_history=st.session_state.context_history[-5:],
            )
            st.session_state.last_suggestions = suggestions
            st.session_state.last_source = source

    # Show suggestions
    if st.session_state.last_suggestions:
        source = getattr(st.session_state, "last_source", "offline")
        if source == "ai":
            st.caption("✨ AI-generated suggestions")
        else:
            st.caption("📚 Offline suggestions (AI unavailable)")

        for i, (sentence, confidence) in enumerate(st.session_state.last_suggestions[:3]):
            is_top = i == 0
            conf_class = (
                "confidence-high" if confidence >= 0.8 else
                "confidence-med" if confidence >= 0.65 else
                "confidence-low"
            )
            css_class = "suggestion suggestion-top" if is_top else "suggestion"

            c1, c2 = st.columns([4, 1])
            with c1:
                st.markdown(f"""
                <div class="{css_class}">
                <strong>"{sentence}"</strong><br>
                <span class="{conf_class}">Confidence: {int(confidence * 100)}%</span>
                </div>
                """, unsafe_allow_html=True)
            with c2:
                if st.button("🔊 Speak", key=f"speak_{i}", use_container_width=True):
                    # TTS
                    if TTS_AVAILABLE:
                        audio_html = text_to_speech_html(sentence)
                        if audio_html:
                            st.markdown(audio_html, unsafe_allow_html=True)
                    # Log it
                    st.session_state.communicated_today.append({
                        "date": datetime.now().isoformat(),
                        "sentence": sentence,
                    })
                    st.session_state.context_history.append(sentence)

                    # Crisis check — if keywords, alert caregiver
                    concern = detect_crisis(sentence)
                    if concern and profile and profile.get("caregiver_email"):
                        ok, msg = send_concern_alert(
                            profile["caregiver_email"],
                            profile["caregiver_name"],
                            profile["name"],
                            concern,
                        )
                        if ok:
                            st.warning(f"⚠️ Alert sent to {profile['caregiver_name']}")

    # Quick phrase library
    st.markdown("---")
    st.markdown("### Quick phrases — tap to speak")

    language = profile.get("language", "English") if profile else "English"

    tabs = st.tabs(list(PHRASE_LIBRARY.keys()))
    for tab, (category, phrases) in zip(tabs, PHRASE_LIBRARY.items()):
        with tab:
            for i, phrase in enumerate(phrases):
                # Translate if non-English selected
                display_phrase = phrase
                if language != "English" and language in MULTILINGUAL_PHRASES:
                    translation = MULTILINGUAL_PHRASES[language].get(phrase)
                    if translation:
                        display_phrase = f"{phrase} — {translation}"

                c1, c2 = st.columns([5, 1])
                with c1:
                    st.markdown(f'<div class="phrase-card">{display_phrase}</div>', unsafe_allow_html=True)
                with c2:
                    if st.button("🔊", key=f"phrase_{category}_{i}", use_container_width=True):
                        if TTS_AVAILABLE:
                            audio = text_to_speech_html(phrase)
                            if audio:
                                st.markdown(audio, unsafe_allow_html=True)
                        st.session_state.communicated_today.append({
                            "date": datetime.now().isoformat(),
                            "sentence": phrase,
                        })

                        concern = detect_crisis(phrase)
                        if concern and profile and profile.get("caregiver_email"):
                            ok, msg = send_concern_alert(
                                profile["caregiver_email"],
                                profile["caregiver_name"],
                                profile["name"],
                                concern,
                            )


# ==================================================================
# DAILY EXERCISES
# ==================================================================
def render_exercises():
    st.markdown("## 🧠 Daily exercises")

    severity = st.session_state.severity or 2.5
    difficulty = get_exercise_difficulty(severity)

    completed, correct, total = get_today_stats()
    target = st.session_state.daily_target

    # Progress ring
    col1, col2, col3, col4 = st.columns(4)
    col1.metric("Today", f"{completed}/{target}")
    col2.metric("Correct", f"{correct}/{completed}" if completed else "0/0")
    col3.metric("Streak", f"{st.session_state.streak_days} days")
    col4.metric("Difficulty", f"Level {difficulty}")

    st.markdown("---")

    exercise_type = st.selectbox(
        "Choose an exercise",
        ["Word retrieval (picture naming)", "Sentence building", "Cloze completion",
         "Reading comprehension", "Repetition"],
    )

    if "Word retrieval" in exercise_type:
        render_word_retrieval(difficulty)
    elif "Sentence building" in exercise_type:
        render_sentence_building(difficulty)
    elif "Cloze" in exercise_type:
        render_cloze(difficulty)
    elif "Reading" in exercise_type:
        render_reading(difficulty)
    elif "Repetition" in exercise_type:
        render_repetition(difficulty)


def render_word_retrieval(difficulty: int):
    st.markdown("### Word retrieval (picture naming)")
    st.caption("You'll be given a hint describing an object. Type what it is.")

    # Generate current word
    if st.session_state.current_exercise is None or st.session_state.current_exercise.get("type") != "word_retrieval":
        word = random.choice(WORD_BANK[difficulty])
        # Description hints (we don't have real pictures, so use clear descriptions)
        descriptions = {
            "cup": "You drink tea or water from this", "bed": "You sleep in this",
            "dog": "A common four-legged pet that barks", "cat": "A small furry pet that meows",
            "sun": "Bright object in the sky during the day", "tree": "Has leaves and grows tall",
            "car": "A vehicle with four wheels", "fish": "Lives in water",
            "door": "You open it to enter a room", "key": "Opens a lock",
            "chair": "You sit on this", "table": "You put plates on this when eating",
            "phone": "You use this to call people", "shoe": "You wear these on your feet",
            "spoon": "You eat soup with this", "plate": "Food is served on this",
            "book": "Has pages with words", "clock": "Tells the time",
            "bag": "You carry things in this", "flower": "Grows in a garden, often colourful",
        }
        description = descriptions.get(word, f"Think about something you use every day related to '{word[0]}'")
        st.session_state.current_exercise = {
            "type": "word_retrieval",
            "word": word,
            "description": description,
            "hint_level": 0,
        }
        st.session_state.exercise_answer_given = False

    exercise = st.session_state.current_exercise
    word = exercise["word"]

    st.markdown(f"#### Hint: {exercise['description']}")

    # Progressive hints
    if exercise["hint_level"] >= 1:
        st.info(f"First letter: **{word[0]}**")
    if exercise["hint_level"] >= 2:
        mid = word[:len(word)//2] + "_" * (len(word) - len(word)//2)
        st.info(f"Starts with: **{mid}**")
    if exercise["hint_level"] >= 3:
        st.info(f"The word is: **{word}**")

    answer = st.text_input("What is it?", key=f"wr_{exercise['word']}")

    col1, col2, col3 = st.columns(3)
    with col1:
        if st.button("Check", use_container_width=True, type="primary"):
            if answer.strip().lower() == word.lower():
                st.success(f"🎉 Correct! The word is **{word}**.")
                register_exercise_result("word_retrieval", correct=True, word=word)
                if TTS_AVAILABLE:
                    st.markdown(text_to_speech_html(f"Correct. The word is {word}."), unsafe_allow_html=True)
                st.session_state.exercise_answer_given = True
            else:
                st.error(f"Not quite. Try again — or get a hint.")
    with col2:
        if st.button("Hint", use_container_width=True):
            if exercise["hint_level"] < 3:
                exercise["hint_level"] += 1
                st.rerun()
    with col3:
        if st.button("Next word", use_container_width=True):
            if not st.session_state.exercise_answer_given:
                register_exercise_result("word_retrieval", correct=False, word=word)
            st.session_state.current_exercise = None
            st.rerun()


def render_sentence_building(difficulty: int):
    st.markdown("### Sentence building")
    st.caption("Arrange the words to form a correct sentence.")

    if st.session_state.current_exercise is None or st.session_state.current_exercise.get("type") != "sentence_building":
        options = SENTENCE_BUILDING.get(difficulty, SENTENCE_BUILDING[1])
        chosen = random.choice(options)
        st.session_state.current_exercise = {"type": "sentence_building", **chosen}
        st.session_state.exercise_answer_given = False

    ex = st.session_state.current_exercise

    st.markdown(f"**Words (in random order):** {', '.join(ex['jumbled'])}")
    st.caption(f"Hint: {ex['hint']}")

    answer = st.text_input("Write the sentence in the correct order:", key=f"sb_{ex['correct']}")

    c1, c2 = st.columns(2)
    with c1:
        if st.button("Check", use_container_width=True, type="primary"):
            # Lenient check — lowercase, strip punctuation
            clean_ans = answer.strip().lower().rstrip(".!?")
            clean_correct = ex["correct"].lower().rstrip(".!?")
            if clean_ans == clean_correct:
                st.success(f"🎉 Correct: **{ex['correct']}**")
                register_exercise_result("sentence_building", correct=True)
                if TTS_AVAILABLE:
                    st.markdown(text_to_speech_html(ex["correct"]), unsafe_allow_html=True)
                st.session_state.exercise_answer_given = True
            else:
                st.warning(f"Almost! The correct sentence is: **{ex['correct']}**")
                register_exercise_result("sentence_building", correct=False)
                st.session_state.exercise_answer_given = True
    with c2:
        if st.button("Next", use_container_width=True):
            st.session_state.current_exercise = None
            st.rerun()


def render_cloze(difficulty: int):
    st.markdown("### Fill in the blank")
    st.caption("Choose the word that best completes the sentence.")

    if st.session_state.current_exercise is None or st.session_state.current_exercise.get("type") != "cloze":
        options = CLOZE_EXERCISES.get(difficulty, CLOZE_EXERCISES[1])
        chosen = random.choice(options)
        st.session_state.current_exercise = {"type": "cloze", **chosen}
        st.session_state.exercise_answer_given = False

    ex = st.session_state.current_exercise
    st.markdown(f"### _{ex['sentence']}_")

    choice = st.radio("Which word fits?", ex["options"], key=f"cz_{ex['sentence']}")

    c1, c2 = st.columns(2)
    with c1:
        if st.button("Check", use_container_width=True, type="primary"):
            if choice == ex["answer"]:
                st.success(f"🎉 Correct!")
                register_exercise_result("cloze", correct=True)
                filled = ex["sentence"].replace("___", choice)
                if TTS_AVAILABLE:
                    st.markdown(text_to_speech_html(filled), unsafe_allow_html=True)
            else:
                st.error(f"The answer is **{ex['answer']}**")
                register_exercise_result("cloze", correct=False)
            st.session_state.exercise_answer_given = True
    with c2:
        if st.button("Next", use_container_width=True):
            st.session_state.current_exercise = None
            st.rerun()


def render_reading(difficulty: int):
    st.markdown("### Reading comprehension")

    if st.session_state.current_exercise is None or st.session_state.current_exercise.get("type") != "reading":
        passages = READING_PASSAGES.get(difficulty, READING_PASSAGES[1])
        chosen = random.choice(passages)
        st.session_state.current_exercise = {"type": "reading", **chosen, "answers_given": {}}

    ex = st.session_state.current_exercise

    st.markdown(f"""
    <div class="phrase-card" style="font-size:18px;">
    {ex['text']}
    </div>
    """, unsafe_allow_html=True)

    if TTS_AVAILABLE and st.button("🔊 Read aloud", use_container_width=False):
        st.markdown(text_to_speech_html(ex["text"]), unsafe_allow_html=True)

    all_correct = True
    for i, q in enumerate(ex["questions"]):
        st.markdown(f"**{q['q']}**")
        user_answer = st.radio("Your answer:", q["options"], key=f"rd_{ex['text'][:20]}_{i}", label_visibility="collapsed")
        ex["answers_given"][i] = user_answer
        if user_answer != q["answer"]:
            all_correct = False

    c1, c2 = st.columns(2)
    with c1:
        if st.button("Submit all answers", use_container_width=True, type="primary"):
            if all_correct:
                st.success("🎉 All correct!")
                register_exercise_result("reading", correct=True)
            else:
                for i, q in enumerate(ex["questions"]):
                    given = ex["answers_given"].get(i)
                    if given == q["answer"]:
                        st.success(f"Q{i+1}: Correct")
                    else:
                        st.error(f"Q{i+1}: The answer is **{q['answer']}**")
                register_exercise_result("reading", correct=False)
    with c2:
        if st.button("New passage", use_container_width=True):
            st.session_state.current_exercise = None
            st.rerun()


def render_repetition(difficulty: int):
    st.markdown("### Repetition exercise")
    st.caption("Listen to the word or phrase, then type what you heard.")

    if st.session_state.current_exercise is None or st.session_state.current_exercise.get("type") != "repetition":
        word = random.choice(WORD_BANK[difficulty])
        st.session_state.current_exercise = {"type": "repetition", "word": word}
        st.session_state.exercise_answer_given = False

    ex = st.session_state.current_exercise
    word = ex["word"]

    if TTS_AVAILABLE:
        if st.button("🔊 Play word", use_container_width=True, type="primary"):
            st.markdown(text_to_speech_html(word), unsafe_allow_html=True)
    else:
        st.info(f"TTS not available. The word is: **{word}**")

    answer = st.text_input("Type what you heard:", key=f"rep_{word}")

    c1, c2 = st.columns(2)
    with c1:
        if st.button("Check", use_container_width=True):
            if answer.strip().lower() == word.lower():
                st.success(f"🎉 Correct: **{word}**")
                register_exercise_result("repetition", correct=True, word=word)
            else:
                st.warning(f"You typed '{answer}'. The word was **{word}**.")
                register_exercise_result("repetition", correct=False, word=word)
            st.session_state.exercise_answer_given = True
    with c2:
        if st.button("Next word", use_container_width=True):
            st.session_state.current_exercise = None
            st.rerun()


# ==================================================================
# PROGRESS DASHBOARD
# ==================================================================
def render_progress():
    st.markdown("## 📊 Your progress")

    # High-level stats
    completed_today, correct_today, _ = get_today_stats()
    total_sessions = len(st.session_state.exercise_log)
    total_correct = sum(1 for e in st.session_state.exercise_log if e["correct"])
    accuracy = (total_correct / total_sessions * 100) if total_sessions else 0

    c1, c2, c3, c4 = st.columns(4)
    with c1:
        st.metric("Total exercises", total_sessions)
    with c2:
        st.metric("Accuracy", f"{accuracy:.0f}%")
    with c3:
        st.metric("Day streak", f"{st.session_state.streak_days}")
    with c4:
        st.metric("Words recovered", len(st.session_state.recovered_words))

    st.markdown("---")

    # Severity history chart
    if len(st.session_state.severity_history) >= 1:
        st.markdown("### Aphasia severity over time")
        df = pd.DataFrame(st.session_state.severity_history, columns=["date", "score"])
        df["date"] = pd.to_datetime(df["date"])
        fig = px.line(df, x="date", y="score", markers=True,
                      title="Severity score — higher is better",
                      range_y=[0, 5])
        fig.update_traces(line_color="#2B6CB0", marker=dict(size=12))
        fig.update_layout(height=350, plot_bgcolor="white", paper_bgcolor="white")
        st.plotly_chart(fig, use_container_width=True)

    # Exercise type breakdown
    if st.session_state.exercise_log:
        st.markdown("### Exercise breakdown (last 30 days)")
        df = pd.DataFrame(st.session_state.exercise_log)
        by_type = df.groupby("type").size().reset_index(name="count")
        fig = px.bar(by_type, x="type", y="count", color="type",
                     color_discrete_sequence=px.colors.qualitative.Pastel)
        fig.update_layout(height=300, showlegend=False, plot_bgcolor="white")
        st.plotly_chart(fig, use_container_width=True)

    # Recovered words
    if st.session_state.recovered_words:
        st.markdown("### Words you've mastered")
        words_list = sorted(st.session_state.recovered_words)
        st.markdown(" · ".join(f"**{w}**" for w in words_list))

    # Streak calendar
    st.markdown("### Daily practice calendar")
    render_streak_calendar()


def render_streak_calendar():
    """GitHub-style calendar of daily exercise completion."""
    if not st.session_state.exercise_log:
        st.caption("Your practice calendar will appear here once you start exercises.")
        return

    df = pd.DataFrame(st.session_state.exercise_log)
    df["day"] = pd.to_datetime(df["date"]).dt.date
    daily = df.groupby("day").size().reset_index(name="count")

    # Last 30 days
    today = datetime.now().date()
    start = today - timedelta(days=29)
    full_range = pd.DataFrame({"day": pd.date_range(start, today).date})
    merged = full_range.merge(daily, on="day", how="left").fillna(0)

    # Plotly heatmap
    merged["week"] = [(d - start).days // 7 for d in merged["day"]]
    merged["weekday"] = [d.weekday() for d in merged["day"]]

    fig = go.Figure(data=go.Heatmap(
        x=merged["week"],
        y=merged["weekday"],
        z=merged["count"],
        colorscale=[[0, "#F1EFE8"], [0.3, "#C0DD97"], [1, "#27500A"]],
        showscale=False,
        hovertemplate="%{customdata}<br>Exercises: %{z}<extra></extra>",
        customdata=merged["day"].astype(str),
    ))
    fig.update_layout(
        height=220,
        yaxis=dict(
            tickvals=[0, 1, 2, 3, 4, 5, 6],
            ticktext=["Mon", "Tue", "Wed", "Thu", "Fri", "Sat", "Sun"],
        ),
        xaxis=dict(title="Week", showticklabels=False),
        plot_bgcolor="white",
        paper_bgcolor="white",
        margin=dict(l=30, r=10, t=20, b=30),
    )
    st.plotly_chart(fig, use_container_width=True)


# ==================================================================
# CAREGIVER TOOLS
# ==================================================================
def render_caregiver():
    st.markdown("## 👨‍👩‍👧 Caregiver tools")

    profile = st.session_state.profile

    if not profile or not profile.get("caregiver_email"):
        st.warning("No caregiver email set. Update your profile in the sidebar.")
        return

    st.info(f"Connected caregiver: **{profile['caregiver_name']}** ({profile['caregiver_email']})")

    st.markdown("---")

    # Emotion check-in
    st.markdown("### How are you feeling right now?")
    cols = st.columns(len(EMOTIONS))
    for i, emotion in enumerate(EMOTIONS):
        with cols[i]:
            if st.button(f"{emotion['emoji']}\n{emotion['label']}",
                        key=f"emo_{i}", use_container_width=True):
                st.session_state.emotion_log.append({
                    "date": datetime.now().isoformat(),
                    "emoji": emotion["emoji"],
                    "label": emotion["label"],
                    "score": emotion["score"],
                })
                st.success(f"Logged: {emotion['emoji']} {emotion['label']}")

                # If flagged emotion, alert caregiver
                if emotion["flag"]:
                    ok, msg = send_concern_alert(
                        profile["caregiver_email"],
                        profile["caregiver_name"],
                        profile["name"],
                        f"{profile['name']} indicated they are '{emotion['label']}'",
                    )
                    if ok:
                        st.warning(f"Caregiver notified: {msg}")

    st.markdown("---")

    # Manual send daily summary
    st.markdown("### Send daily summary now")
    st.caption("Automatically sends every evening. You can also send manually.")

    if st.button("📧 Send today's summary to caregiver", use_container_width=True, type="primary"):
        completed, correct, _ = get_today_stats()
        communicated = len(st.session_state.communicated_today)

        # Recent emotions
        today_emotions = [
            e for e in st.session_state.emotion_log
            if e["date"][:10] == datetime.now().date().isoformat()[:10]
        ]
        if today_emotions:
            avg_score = sum(e["score"] for e in today_emotions) / len(today_emotions)
            emotion_text = f"Average mood: {avg_score:.1f}/5 ({today_emotions[-1]['label']} most recently)"
        else:
            emotion_text = "Not logged today"

        # Concerning flags
        flags = []
        for msg in st.session_state.communicated_today:
            concern = detect_crisis(msg["sentence"])
            if concern:
                flags.append(concern)

        ok, result = send_daily_summary(
            caregiver_email=profile["caregiver_email"],
            caregiver_name=profile["caregiver_name"],
            patient_name=profile["name"],
            phrases_communicated=communicated,
            exercises_completed=completed,
            exercises_total=st.session_state.daily_target,
            streak_days=st.session_state.streak_days,
            emotion_trend=emotion_text,
            concerning_flags=flags,
        )
        if ok:
            st.success(f"✅ {result}")
        else:
            st.error(f"Email failed: {result}")
            st.caption("Make sure BREVO_API_KEY is set in Streamlit secrets.")

    st.markdown("---")

    # Custom phrase library
    st.markdown("### Add family phrases")
    st.caption("Phrases the patient uses often — like family member names.")

    if "custom_phrases" not in st.session_state:
        st.session_state.custom_phrases = []

    new_phrase = st.text_input("Add a phrase", placeholder="e.g. Call my daughter Ngozi")
    if st.button("Add phrase") and new_phrase.strip():
        st.session_state.custom_phrases.append(new_phrase.strip())
        st.rerun()

    if st.session_state.custom_phrases:
        for i, p in enumerate(st.session_state.custom_phrases):
            c1, c2, c3 = st.columns([4, 1, 1])
            with c1:
                st.markdown(f'<div class="phrase-card">{p}</div>', unsafe_allow_html=True)
            with c2:
                if st.button("🔊", key=f"custom_speak_{i}", use_container_width=True):
                    if TTS_AVAILABLE:
                        st.markdown(text_to_speech_html(p), unsafe_allow_html=True)
            with c3:
                if st.button("✕", key=f"custom_del_{i}", use_container_width=True):
                    st.session_state.custom_phrases.pop(i)
                    st.rerun()


# ==================================================================
# SETTINGS
# ==================================================================
def render_settings():
    st.markdown("## ⚙️ Settings")

    profile = st.session_state.profile

    st.markdown("### Your profile")
    if profile:
        for k, v in profile.items():
            st.markdown(f"**{k.replace('_', ' ').title()}:** {v or '—'}")

        if st.button("Edit profile"):
            st.session_state.profile = None
            st.rerun()

    st.markdown("---")
    st.markdown("### Accessibility")

    st.session_state.text_size = st.radio(
        "Text size",
        ["normal", "large", "x-large"],
        horizontal=True,
    )

    st.session_state.daily_target = st.slider(
        "Daily exercise target",
        min_value=1, max_value=20,
        value=st.session_state.daily_target,
    )

    st.markdown("---")
    st.markdown("### Reassess aphasia severity")
    st.caption("Reassessing monthly shows improvement over time.")

    if st.button("Start reassessment"):
        st.session_state.assessment_complete = False
        st.rerun()

    st.markdown("---")
    st.markdown("### About SpeakAgain")
    st.markdown("""
    **SpeakAgain** is Project #6 of 10 in the Neurological Rehabilitation AI Series
    by **Samuel Oluwakoya** — computer science graduate, foot drop patient, and
    independent AI health researcher based in Lagos, Nigeria.

    **Contact:** Samuel@bloomgatelaw.com · soluwakoyat@gmail.com
    **GitHub:** github.com/samexdgs
    **Live apps:** fdmapp.streamlit.app

    This tool is grounded in evidence from:
    - Kim et al., 2025 — VoiceAdapt RCT (JMIR mHealth)
    - Braley et al., 2021 — digital therapeutic RCT (Frontiers in Neurology)
    - Ericson et al., 2025 — systematic review of 39 computer-therapy studies
    - Brady et al., Cochrane Review 2016 — therapy intensity evidence

    *Not a medical device. Does not replace professional speech therapy.*
    """)


# ==================================================================
# MAIN ROUTER
# ==================================================================
def main():
    # Sidebar
    with st.sidebar:
        st.markdown("# 💬 SpeakAgain")
        st.caption("Project #6 of 10 — AI Rehabilitation Series")

        if st.session_state.profile:
            profile = st.session_state.profile
            st.markdown(f"### Hello, {profile['name']}")
            if st.session_state.aphasia_type:
                aph = APHASIA_TYPES[st.session_state.aphasia_type]
                st.markdown(f'<span class="pill pill-info">{aph["name"].split(" (")[0]}</span>', unsafe_allow_html=True)
                st.markdown(f"Severity: **{st.session_state.severity}/5**")

            st.markdown("---")
            page = st.radio(
                "Navigate",
                ["Communication", "Daily exercises", "Progress", "Caregiver", "Settings"],
                label_visibility="collapsed",
            )
        else:
            page = None

        st.markdown("---")
        st.caption("Built by Samuel Oluwakoya\nSamuel@bloomgatelaw.com\nLagos, Nigeria")

    # Routing
    if not st.session_state.profile:
        render_onboarding()
    elif not st.session_state.assessment_complete:
        render_assessment()
    elif st.session_state.assessment_complete and st.session_state.severity is not None and page is None:
        render_assessment_result()
    else:
        if page == "Communication":
            render_communication()
        elif page == "Daily exercises":
            render_exercises()
        elif page == "Progress":
            render_progress()
        elif page == "Caregiver":
            render_caregiver()
        elif page == "Settings":
            render_settings()


if __name__ == "__main__":
    main()
