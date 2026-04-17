"""
ai_completion.py
-----------------
AI sentence completion for aphasia patients.

Primary: Claude API (best-in-class for understanding fragment intent)
Fallback: Rule-based pattern matching — works offline with zero dependencies,
so patients in low-connectivity areas still get useful suggestions.

Evidence for this approach: Kim et al. (2025, VoiceAdapt) and Upton et al.
(2024, iTalkBetter) both found that fragment-to-sentence completion
significantly reduces communication frustration in chronic aphasia patients.
"""

import os
import json
import requests
import streamlit as st
from typing import Optional


def _get_claude_key() -> Optional[str]:
    try:
        if "ANTHROPIC_API_KEY" in st.secrets:
            return st.secrets["ANTHROPIC_API_KEY"]
    except Exception:
        pass
    return os.environ.get("ANTHROPIC_API_KEY")


# ------------------------------------------------------------------
# Rule-based fallback — patterns observed in aphasia communication
# Covers the most common patient communication themes
# ------------------------------------------------------------------
FALLBACK_PATTERNS = {
    # keywords found -> likely sentences
    ("hungry", "food", "eat"): [
        ("I am hungry and would like to eat", 0.85),
        ("Please give me some food", 0.78),
        ("When will the meal be ready?", 0.65),
    ],
    ("thirsty", "water", "drink"): [
        ("I am thirsty and would like some water", 0.88),
        ("Please bring me a drink", 0.80),
        ("Can I have a cup of water please?", 0.72),
    ],
    ("pain", "hurt", "ache"): [
        ("I am in pain and need help", 0.90),
        ("The pain is getting worse", 0.82),
        ("Please call the doctor about my pain", 0.75),
    ],
    ("tired", "sleep", "rest"): [
        ("I am tired and want to rest", 0.88),
        ("I would like to go to sleep now", 0.80),
        ("I need to lie down", 0.72),
    ],
    ("bathroom", "toilet"): [
        ("I need to use the bathroom", 0.92),
        ("Please help me to the toilet", 0.85),
        ("I need the bathroom now, it is urgent", 0.72),
    ],
    ("family", "wife", "husband", "daughter", "son"): [
        ("I would like to speak with my family", 0.80),
        ("Please call my family for me", 0.75),
        ("I miss my family", 0.68),
    ],
    ("doctor", "medicine", "hospital"): [
        ("Please call the doctor", 0.85),
        ("I need to take my medication", 0.80),
        ("When is my next doctor appointment?", 0.72),
    ],
    ("cold", "blanket", "warm"): [
        ("I am cold and need a blanket", 0.85),
        ("Please turn up the heat", 0.78),
        ("I would like another blanket please", 0.72),
    ],
    ("hot", "warm", "fan"): [
        ("I am too hot", 0.82),
        ("Please turn on the fan", 0.78),
        ("Can you open the window please?", 0.70),
    ],
    ("dinner", "wife"): [
        ("I am hungry and want to have dinner with my wife", 0.87),
        ("Please help me make dinner, I am hungry", 0.72),
        ("My wife should know I am ready for dinner", 0.65),
    ],
    ("yes", "agree"): [("Yes, I agree", 0.90), ("Yes, that is right", 0.82), ("Yes, thank you", 0.75)],
    ("no", "stop"): [("No, please stop", 0.88), ("No, I do not want that", 0.80), ("No, thank you", 0.75)],
    ("happy",): [("I am feeling happy today", 0.82), ("I am in a good mood", 0.75)],
    ("sad",): [("I am feeling sad today", 0.82), ("I am not feeling well emotionally", 0.72)],
    ("lonely", "alone"): [("I am feeling lonely", 0.85), ("I would like some company", 0.78)],
}


def _fallback_complete(fragment: str) -> list[tuple[str, float]]:
    """Rule-based completion — always works, no API required."""
    fragment_lower = fragment.lower().strip()
    if not fragment_lower:
        return []

    words = set(fragment_lower.replace(",", " ").replace(".", " ").split())

    # Score each pattern by keyword overlap
    matches = []
    for keywords, suggestions in FALLBACK_PATTERNS.items():
        overlap = sum(1 for kw in keywords if any(kw in w or w in kw for w in words))
        if overlap > 0:
            matches.append((overlap, suggestions))

    if matches:
        matches.sort(key=lambda x: -x[0])
        return matches[0][1]

    # Generic fallbacks based on fragment structure
    if len(words) == 1:
        word = list(words)[0]
        return [
            (f"I need {word}", 0.60),
            (f"I want {word}", 0.55),
            (f"Please bring me {word}", 0.50),
        ]

    # Default — construct simple sentences
    fragment_cleaned = fragment.strip()
    return [
        (f"I would like to say: {fragment_cleaned}", 0.55),
        (f"I am trying to tell you about {fragment_cleaned}", 0.48),
        (f"Please understand: {fragment_cleaned}", 0.42),
    ]


# ------------------------------------------------------------------
# Claude API completion — primary path
# ------------------------------------------------------------------
def _claude_complete(
    fragment: str,
    aphasia_type: str = "anomic",
    context_history: Optional[list[str]] = None,
) -> Optional[list[tuple[str, float]]]:
    """
    Use Claude API to complete fragments into natural sentences.
    Returns None on failure — caller should use fallback.
    """
    api_key = _get_claude_key()
    if not api_key:
        return None

    context_str = ""
    if context_history:
        recent = context_history[-3:]  # last 3 exchanges
        context_str = f"\n\nRecent conversation context:\n" + "\n".join(f"- {c}" for c in recent)

    prompt = f"""A stroke survivor with {aphasia_type} aphasia has typed these fragments: "{fragment}"

They know what they want to say but struggle to produce complete sentences. Generate 3 likely complete sentences they might mean.{context_str}

Guidelines:
- Use simple, natural everyday language
- Keep each sentence under 15 words
- Make them distinctly different interpretations
- Score each with confidence 0.0–1.0

Return ONLY valid JSON in this exact format:
{{"suggestions": [
  {{"sentence": "...", "confidence": 0.87}},
  {{"sentence": "...", "confidence": 0.72}},
  {{"sentence": "...", "confidence": 0.61}}
]}}"""

    try:
        response = requests.post(
            "https://api.anthropic.com/v1/messages",
            headers={
                "x-api-key": api_key,
                "anthropic-version": "2023-06-01",
                "content-type": "application/json",
            },
            json={
                "model": "claude-sonnet-4-6",
                "max_tokens": 500,
                "messages": [{"role": "user", "content": prompt}],
            },
            timeout=15,
        )

        if response.status_code != 200:
            return None

        data = response.json()
        text = data["content"][0]["text"]

        # Extract JSON from response (strip any markdown fencing)
        text = text.strip()
        if text.startswith("```"):
            text = text.split("```")[1]
            if text.startswith("json"):
                text = text[4:]
        text = text.strip()

        parsed = json.loads(text)
        return [(s["sentence"], float(s["confidence"])) for s in parsed["suggestions"]]

    except Exception:
        return None


def complete_sentence(
    fragment: str,
    aphasia_type: str = "anomic",
    context_history: Optional[list[str]] = None,
) -> tuple[list[tuple[str, float]], str]:
    """
    Main entry point — tries Claude, falls back to rules.

    Returns: (suggestions, source) where source is 'ai' or 'offline'
    """
    if not fragment or not fragment.strip():
        return [], "none"

    # Try Claude first
    ai_result = _claude_complete(fragment, aphasia_type, context_history)
    if ai_result and len(ai_result) > 0:
        return ai_result, "ai"

    # Fall back to rules
    return _fallback_complete(fragment), "offline"


# ------------------------------------------------------------------
# Predictive word suggestions — as the patient types
# ------------------------------------------------------------------
COMMON_WORDS_BY_PREFIX = {
    "a": ["and", "am", "at", "after", "ask", "ache", "able"],
    "b": ["bed", "be", "bathroom", "because", "bring", "blanket", "better"],
    "c": ["can", "call", "come", "cold", "cup", "chair", "child", "care"],
    "d": ["doctor", "day", "drink", "do", "daughter", "down", "dinner"],
    "e": ["eat", "end", "every", "eye", "energy", "empty"],
    "f": ["family", "food", "feel", "friend", "for", "father", "fine"],
    "g": ["go", "get", "good", "give", "grandson", "granddaughter"],
    "h": ["help", "hungry", "home", "house", "hot", "hurt", "hospital", "husband"],
    "i": ["I", "in", "is", "it", "if", "inside", "itch"],
    "j": ["just", "juice"],
    "k": ["know", "keep", "kitchen"],
    "l": ["like", "lunch", "little", "long", "listen"],
    "m": ["my", "more", "medicine", "morning", "mother", "man"],
    "n": ["no", "not", "now", "need", "never", "noise", "nurse"],
    "o": ["of", "on", "or", "okay", "often", "out", "open"],
    "p": ["please", "pain", "phone", "painful", "pillow", "picture"],
    "q": ["quiet", "question"],
    "r": ["rest", "right", "room", "remember", "read"],
    "s": ["sleep", "sit", "stop", "sad", "some", "see", "son", "sick"],
    "t": ["the", "thank", "tired", "to", "today", "together", "television", "toilet"],
    "u": ["up", "under", "understand", "use"],
    "v": ["very", "view", "voice"],
    "w": ["want", "water", "wife", "warm", "why", "what", "when", "where"],
    "y": ["yes", "you", "your", "yesterday"],
    "z": ["zero"],
}


def predict_next_words(partial: str, limit: int = 6) -> list[str]:
    """Return predicted word completions for what the patient is typing."""
    if not partial:
        return ["I", "please", "help", "want", "need", "thank"][:limit]

    partial_lower = partial.lower().strip()
    if not partial_lower:
        return []

    first_char = partial_lower[0]
    candidates = COMMON_WORDS_BY_PREFIX.get(first_char, [])

    matches = [w for w in candidates if w.lower().startswith(partial_lower)]

    # If only one char typed, return all starting with it
    if len(partial_lower) == 1:
        return matches[:limit]

    return matches[:limit]
