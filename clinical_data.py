"""
clinical_data.py
-----------------
Evidence-based clinical content for SpeakAgain.

Sources used to ground this module:
- Kim et al., 2025 (VoiceAdapt RCT, JMIR mHealth) — naming therapy protocol
- Braley et al., 2021 (Frontiers in Neurology) — Constant Therapy digital therapeutic
- Upton et al., 2024 — iTalkBetter (only app with proven spontaneous-speech transfer)
- Ericson et al., 2025 systematic review — 39 studies on self-administered computer therapy
- WAB-R (Western Aphasia Battery) — severity classification standard
- Brady et al., Cochrane Review 2016 — intensity matters most
- Breitenstein et al., 2017 (Lancet) — 10+ hours/week intensive SLT improves outcomes

Key evidence-based design choices:
1. High intensity > sophistication (Cochrane, 2016)
2. Picture-naming with graded cueing is the most-validated single technique
3. Semantic + phonological cueing stacked works better than either alone
4. Generalisation is the hard problem — we address it with "complexity-based" items
5. Spaced repetition improves retention vs massed practice
"""

from datetime import datetime
from typing import Optional


# ------------------------------------------------------------------
# APHASIA TYPES — simplified WAB-R classification
# Based on fluency, comprehension, repetition, naming dimensions
# ------------------------------------------------------------------
APHASIA_TYPES = {
    "broca": {
        "name": "Broca's aphasia (non-fluent)",
        "description": "You know what you want to say but struggle to produce words. Short, effortful speech. Comprehension is usually good.",
        "recovery_focus": "Word retrieval and sentence building",
        "color": "#2B6CB0",
    },
    "wernicke": {
        "name": "Wernicke's aphasia (fluent)",
        "description": "Speech flows but words may be wrong or made up. Understanding others is harder.",
        "recovery_focus": "Comprehension and word-meaning matching",
        "color": "#D4537E",
    },
    "anomic": {
        "name": "Anomic aphasia (word-finding)",
        "description": "Mostly fluent speech but frequent word-finding pauses. The word is 'on the tip of the tongue'.",
        "recovery_focus": "Naming and semantic retrieval",
        "color": "#639922",
    },
    "global": {
        "name": "Global aphasia",
        "description": "Significant difficulty with both producing and understanding speech. Requires the most structured, patient approach.",
        "recovery_focus": "Core vocabulary, yes/no reliability, functional phrases",
        "color": "#BA7517",
    },
    "conduction": {
        "name": "Conduction aphasia",
        "description": "Fluent speech and good comprehension, but repetition is hard. Aware of errors and frustrated by them.",
        "recovery_focus": "Repetition practice, self-monitoring",
        "color": "#534AB7",
    },
    "mild": {
        "name": "Mild aphasia",
        "description": "Speech is mostly intact with occasional word-finding difficulties. Recovery focus is on complex language.",
        "recovery_focus": "Complex sentences, reading, writing",
        "color": "#0F6E56",
    },
}


# ------------------------------------------------------------------
# ASSESSMENT TASKS — 8-task simplified battery
# Adapted from WAB-R bedside version + Boston Diagnostic Aphasia Exam
# ------------------------------------------------------------------
ASSESSMENT_TASKS = [
    {
        "id": "q1",
        "dimension": "fluency",
        "prompt": "Imagine telling someone about your morning. How many words can you string together in one sentence?",
        "options": [
            ("Just one or two words", 0),
            ("Three to five words", 1),
            ("Short sentence (6-10 words)", 2),
            ("Full sentences, but slow", 3),
            ("Full sentences, natural flow", 4),
        ],
    },
    {
        "id": "q2",
        "dimension": "comprehension",
        "prompt": "When someone speaks a normal sentence to you, can you understand it?",
        "options": [
            ("Almost never", 0),
            ("Sometimes, simple sentences only", 1),
            ("Most of the time if they speak slowly", 2),
            ("Usually yes", 3),
            ("Always, at normal speed", 4),
        ],
    },
    {
        "id": "q3",
        "dimension": "naming",
        "prompt": "When you look at a common object (a cup, a phone), can you say its name?",
        "options": [
            ("Almost never", 0),
            ("Sometimes, with long pauses", 1),
            ("Usually, after some delay", 2),
            ("Almost always quickly", 3),
            ("Always immediately", 4),
        ],
    },
    {
        "id": "q4",
        "dimension": "repetition",
        "prompt": "If someone says a short sentence, can you repeat it back correctly?",
        "options": [
            ("No", 0),
            ("Single words only", 1),
            ("Short phrases (2-3 words)", 2),
            ("Most sentences", 3),
            ("Always, even long sentences", 4),
        ],
    },
    {
        "id": "q5",
        "dimension": "reading",
        "prompt": "Can you read and understand short written text (a label, a text message)?",
        "options": [
            ("No, letters don't make sense", 0),
            ("Single words only", 1),
            ("Short phrases", 2),
            ("Most short text", 3),
            ("Anything — books, news, forms", 4),
        ],
    },
    {
        "id": "q6",
        "dimension": "writing",
        "prompt": "Can you write your own name and simple words?",
        "options": [
            ("No", 0),
            ("Only my name, with difficulty", 1),
            ("Name and a few familiar words", 2),
            ("Short sentences", 3),
            ("Full sentences and paragraphs", 4),
        ],
    },
    {
        "id": "q7",
        "dimension": "word_finding",
        "prompt": "When you know what you want to say but the word won't come, how often does that happen?",
        "options": [
            ("Constantly — in almost every sentence", 0),
            ("Very often — several times per minute", 1),
            ("Often — a few times per minute", 2),
            ("Occasionally", 3),
            ("Rarely", 4),
        ],
    },
    {
        "id": "q8",
        "dimension": "self_monitoring",
        "prompt": "When you make a speech mistake, do you notice?",
        "options": [
            ("I rarely know when I make mistakes", 0),
            ("Sometimes, if someone tells me", 1),
            ("Usually, after I've said something", 2),
            ("Yes, right away", 3),
            ("Yes, and I can correct myself", 4),
        ],
    },
]


def classify_aphasia(responses: dict[str, int]) -> tuple[str, float]:
    """
    Classify aphasia type and severity from assessment responses.

    Args:
        responses: dict mapping question id -> score (0-4)

    Returns:
        (aphasia_type_key, severity_score_0_to_5)

    Logic is simplified but follows WAB-R principles:
    - Fluency dimension < Comprehension → Broca's
    - Comprehension dimension very low + fluency present → Wernicke's
    - Both fluency and comprehension very low → Global
    - Repetition specifically impaired, others OK → Conduction
    - Primarily naming issues → Anomic
    - Overall scores high → Mild
    """
    fluency = responses.get("q1", 2)
    comprehension = responses.get("q2", 2)
    naming = responses.get("q3", 2)
    repetition = responses.get("q4", 2)
    word_finding = responses.get("q7", 2)

    total = sum(responses.values())
    max_total = len(responses) * 4
    severity = (total / max_total) * 5  # 0 (severe) to 5 (normal)

    # Classification cascade
    if fluency <= 1 and comprehension <= 1:
        aph_type = "global"
    elif fluency <= 1 and comprehension >= 2:
        aph_type = "broca"
    elif fluency >= 2 and comprehension <= 1:
        aph_type = "wernicke"
    elif repetition <= 1 and fluency >= 2 and comprehension >= 2:
        aph_type = "conduction"
    elif naming <= 2 and word_finding <= 2 and fluency >= 2:
        aph_type = "anomic"
    elif severity >= 4:
        aph_type = "mild"
    else:
        aph_type = "anomic"  # most common default

    return aph_type, round(severity, 1)


# ------------------------------------------------------------------
# PHRASE LIBRARY — 200+ common patient needs
# Organized by category. Includes multilingual where relevant.
# Evidence: Communication boards are a Level 1 recommendation in
# ASHA practice guidelines for severe aphasia.
# ------------------------------------------------------------------
PHRASE_LIBRARY = {
    "Urgent needs": [
        "I am in pain",
        "I need help now",
        "Please call the doctor",
        "I cannot breathe well",
        "My chest hurts",
        "I feel dizzy",
        "I am going to fall",
        "I need to sit down",
        "Please call my family",
        "I need my medication",
    ],
    "Basic needs": [
        "I am hungry",
        "I am thirsty",
        "I need to use the bathroom",
        "I am cold",
        "I am hot",
        "I am tired",
        "I want to sleep",
        "I want to wake up",
        "I want to sit up",
        "I want to lie down",
    ],
    "Feelings": [
        "I am happy today",
        "I am sad",
        "I am frustrated",
        "I am worried",
        "I am scared",
        "I am bored",
        "I am lonely",
        "I feel better today",
        "I feel worse today",
        "I need a hug",
    ],
    "Requests": [
        "Please speak slowly",
        "Please repeat that",
        "I did not understand",
        "Please wait, I am thinking",
        "Please write it down",
        "Please show me",
        "I want to be alone",
        "I want company",
        "Please turn on the TV",
        "Please turn off the light",
    ],
    "Family and social": [
        "I love you",
        "Thank you",
        "I miss you",
        "How are you",
        "Please come and see me",
        "Please call my daughter",
        "Please call my son",
        "Please call my wife",
        "Please call my husband",
        "Please call my friend",
    ],
    "Food and drink": [
        "I want water",
        "I want tea",
        "I want juice",
        "I want rice",
        "I want bread",
        "I want fruit",
        "I do not like this food",
        "Please give me more",
        "I have had enough",
        "I cannot eat this, it is too hard",
    ],
    "Daily care": [
        "I need a bath",
        "I need to brush my teeth",
        "I need clean clothes",
        "Please help me walk",
        "Please help me stand",
        "Please help me dress",
        "My skin is itching",
        "I need a blanket",
        "My pillow is uncomfortable",
        "Please turn me over",
    ],
    "Rehabilitation": [
        "I want to practice speaking",
        "I did my exercises today",
        "I am too tired to exercise",
        "My therapy helped today",
        "I am making progress",
        "This exercise is too hard",
        "This exercise is too easy",
        "I need to rest before more therapy",
        "I can walk a little today",
        "My arm is moving better",
    ],
}


# Multilingual common phrases — Yoruba, Igbo, Hausa, Pidgin
MULTILINGUAL_PHRASES = {
    "Yoruba": {
        "I am in pain": "Mo ni irora",
        "I am hungry": "Ebi n pa mi",
        "I am thirsty": "Omi ngbẹ mi",
        "Thank you": "E ṣe",
        "Please help me": "E jọwọ ran mi lọwọ",
        "I love you": "Mo nifẹ rẹ",
        "I am tired": "Ara mi ti rẹ",
    },
    "Igbo": {
        "I am in pain": "Ahụ na-egbu m",
        "I am hungry": "Agụụ na-agụ m",
        "I am thirsty": "Akpịrị na-akpọ m nkụ",
        "Thank you": "Daalụ",
        "Please help me": "Biko nyere m aka",
        "I love you": "A hụrụ m gị n'anya",
        "I am tired": "Ike gwụrụ m",
    },
    "Hausa": {
        "I am in pain": "Ina jin zafi",
        "I am hungry": "Ina jin yunwa",
        "I am thirsty": "Ina jin kishirwa",
        "Thank you": "Na gode",
        "Please help me": "Don Allah taimake ni",
        "I love you": "Ina son ka",
        "I am tired": "Na gaji",
    },
    "Pidgin": {
        "I am in pain": "Body dey pain me",
        "I am hungry": "Hunger dey catch me",
        "I am thirsty": "Water dey thirst me",
        "Thank you": "Thank you well well",
        "Please help me": "Abeg help me",
        "I love you": "I love you",
        "I am tired": "I don tire",
    },
}


# ------------------------------------------------------------------
# EXERCISE BANK — 6 exercise types, difficulty-graded
# Evidence-based: picture-naming with graded cueing is the most
# replicated effective treatment for aphasia (Cochrane 2016)
# ------------------------------------------------------------------

# Words ordered roughly by frequency + concreteness — high-frequency
# concrete nouns are easiest (anchor for severe aphasia)
WORD_BANK = {
    1: ["cup", "bed", "dog", "cat", "sun", "tree", "car", "fish", "door", "key"],
    2: ["chair", "table", "phone", "shoe", "spoon", "plate", "book", "clock", "bag", "flower"],
    3: ["window", "bottle", "pillow", "blanket", "mirror", "bicycle", "umbrella", "camera", "wallet", "kitchen"],
    4: ["stethoscope", "thermometer", "wheelchair", "physiotherapist", "neighbour", "medication", "appointment", "pharmacy", "stretcher", "laboratory"],
    5: ["rehabilitation", "prescription", "consultation", "demonstration", "congratulations", "responsibility", "investigation", "pharmaceutical", "neurological", "occupational"],
}


SENTENCE_BUILDING = {
    1: [  # 2-3 word sentences
        {"jumbled": ["eat", "I"], "correct": "I eat", "hint": "Subject then verb"},
        {"jumbled": ["sleep", "want", "I"], "correct": "I want sleep", "hint": "Say what you want"},
        {"jumbled": ["hungry", "am", "I"], "correct": "I am hungry", "hint": "Describe yourself"},
    ],
    2: [  # 4-5 word sentences
        {"jumbled": ["want", "cup", "a", "I", "of"], "correct": "I want a cup of", "hint": "Requesting something"},
        {"jumbled": ["go", "to", "want", "bed", "I"], "correct": "I want to go to bed", "hint": "Stating an intention"},
        {"jumbled": ["doctor", "call", "please", "the"], "correct": "Please call the doctor", "hint": "Making a request"},
    ],
    3: [  # 6-8 word sentences
        {"jumbled": ["daughter", "I", "my", "to", "speak", "to", "want"], "correct": "I want to speak to my daughter", "hint": "Expressing a need"},
        {"jumbled": ["go", "to", "need", "I", "hospital", "the"], "correct": "I need to go to the hospital", "hint": "Explaining an action"},
        {"jumbled": ["have", "pain", "I", "chest", "in", "my"], "correct": "I have pain in my chest", "hint": "Describing a symptom"},
    ],
    4: [  # 8-12 word sentences, complex
        {"jumbled": ["exercises", "morning", "I", "my", "every", "do", "physiotherapy", "after", "breakfast"], "correct": "I do my physiotherapy exercises every morning after breakfast", "hint": "Daily routine"},
    ],
}


CLOZE_EXERCISES = {
    1: [
        {"sentence": "I brush my ___", "options": ["teeth", "floor", "door"], "answer": "teeth"},
        {"sentence": "I drink ___", "options": ["water", "chair", "window"], "answer": "water"},
        {"sentence": "I sleep in ___", "options": ["bed", "cup", "shoe"], "answer": "bed"},
    ],
    2: [
        {"sentence": "The dog is ___ in the garden", "options": ["running", "eating book", "sleeping television"], "answer": "running"},
        {"sentence": "I eat breakfast in the ___", "options": ["morning", "chair", "hospital"], "answer": "morning"},
    ],
    3: [
        {"sentence": "Before taking my medication, I must ___", "options": ["read the label", "sing loudly", "close the window"], "answer": "read the label"},
        {"sentence": "My physiotherapy appointment is scheduled for ___", "options": ["next Tuesday morning", "yellow sunshine today", "purple elephant walks"], "answer": "next Tuesday morning"},
    ],
}


READING_PASSAGES = {
    1: [
        {
            "text": "James ate lunch.",
            "questions": [
                {"q": "Did James eat lunch?", "options": ["Yes", "No"], "answer": "Yes"},
            ],
        },
        {
            "text": "The cat is on the mat. The cat is black.",
            "questions": [
                {"q": "Where is the cat?", "options": ["On the mat", "On the chair", "On the bed"], "answer": "On the mat"},
                {"q": "What colour is the cat?", "options": ["Black", "White", "Brown"], "answer": "Black"},
            ],
        },
    ],
    2: [
        {
            "text": "Mary went to the market on Tuesday morning. She bought bread, milk, and fruit. Then she came home and made breakfast for her children.",
            "questions": [
                {"q": "When did Mary go to the market?", "options": ["Tuesday morning", "Sunday evening", "Monday afternoon"], "answer": "Tuesday morning"},
                {"q": "What did she buy?", "options": ["Bread, milk, and fruit", "Meat and rice", "Clothes and shoes"], "answer": "Bread, milk, and fruit"},
                {"q": "Who did she make breakfast for?", "options": ["Her children", "Her friends", "Her neighbours"], "answer": "Her children"},
            ],
        },
    ],
    3: [
        {
            "text": "Stroke recovery requires patience and daily practice. Small steps add up to big changes over months. Many people continue to improve years after their stroke, especially when they practice speaking every day.",
            "questions": [
                {"q": "What does stroke recovery require?", "options": ["Patience and daily practice", "Expensive equipment", "Eight hours of sleep"], "answer": "Patience and daily practice"},
                {"q": "When can people improve?", "options": ["Years after the stroke", "Only in the first week", "Only in hospital"], "answer": "Years after the stroke"},
            ],
        },
    ],
}


# ------------------------------------------------------------------
# Evidence-based severity-to-exercise mapping
# ------------------------------------------------------------------
def get_exercise_difficulty(severity: float) -> int:
    """Map severity score (0-5) to exercise difficulty level (1-4)."""
    if severity < 1.5:
        return 1  # Severe — one-word tasks only
    elif severity < 2.5:
        return 1
    elif severity < 3.5:
        return 2
    elif severity < 4.5:
        return 3
    else:
        return 4


# ------------------------------------------------------------------
# CRISIS KEYWORD DETECTION
# Phrases that should trigger an alert email to caregiver
# ------------------------------------------------------------------
CRISIS_KEYWORDS = {
    "pain": "Patient reported being in pain",
    "hurt": "Patient reported pain or injury",
    "fall": "Patient mentioned falling or fall risk",
    "dizzy": "Patient reported dizziness",
    "cannot breathe": "Patient reported breathing difficulty",
    "chest": "Patient mentioned chest discomfort",
    "emergency": "Patient used the word 'emergency'",
    "help now": "Patient requested urgent help",
    "scared": "Patient expressed feeling scared",
    "alone": "Patient expressed feeling alone",
}


def detect_crisis(text: str) -> Optional[str]:
    """Return a concern description if crisis keywords detected, else None."""
    text_lower = text.lower()
    for keyword, description in CRISIS_KEYWORDS.items():
        if keyword in text_lower:
            return description
    return None


# ------------------------------------------------------------------
# EMOTION OPTIONS
# ------------------------------------------------------------------
EMOTIONS = [
    {"emoji": "😰", "label": "In pain", "score": 1, "flag": True},
    {"emoji": "😢", "label": "Sad", "score": 2, "flag": False},
    {"emoji": "😐", "label": "Okay", "score": 3, "flag": False},
    {"emoji": "🙂", "label": "Good", "score": 4, "flag": False},
    {"emoji": "😊", "label": "Great", "score": 5, "flag": False},
]
