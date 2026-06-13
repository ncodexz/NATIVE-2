# text_analyzer.py
# Analyzes English text and returns words with grammatical types
# Used for color coding in the frontend

import nltk
from nltk import pos_tag, word_tokenize

# NLTK POS tag to our word types
POS_MAP = {
    'PRP':  'pronoun',
    'PRP$': 'pronoun',
    'WP':   'pronoun',
    'VB':   'verb',
    'VBD':  'verb',
    'VBG':  'verb',
    'VBN':  'verb',
    'VBP':  'verb',
    'VBZ':  'verb',
    'MD':   'verb',
    'NN':   'noun',
    'NNS':  'noun',
    'NNP':  'noun',
    'NNPS': 'noun',
    'JJ':   'adjective',
    'JJR':  'adjective',
    'JJS':  'adjective',
    'RB':   'adverb',
    'RBR':  'adverb',
    'RBS':  'adverb',
    'DT':   'article',
    'IN':   'preposition',
    'CC':   'conjunction',
}

def analyze_grammar(text: str) -> list:
    """Returns list of words with their grammatical types using NLTK."""
    if not text.strip():
        return []
    try:
        tokens = word_tokenize(text)
        tagged = pos_tag(tokens)
        return [
            {"word": word, "type": POS_MAP.get(tag, "other")}
            for word, tag in tagged
            if word.isalpha()
        ]
    except Exception:
        return []

def analyze_grammar_bilingual(english: str, spanish: str) -> dict:
    from config import AZURE_GROK_ENDPOINT, AZURE_GROK_API_KEY, AZURE_GROK_DEPLOYMENT_NAME
    """Analyzes both English and Spanish with meaning-based color matching using Grok."""
    if not english.strip():
        return {"english": [], "spanish": []}

    import requests
    import json

    prompt = f"""Match these English and Spanish words by meaning and assign grammatical types.

    English: "{english}"
    Spanish: "{spanish}"

    Return ONLY this JSON, no explanation:
    {{
    "english": [
        {{"word": "I", "type": "pronoun"}},
        {{"word": "went", "type": "verb"}},
        {{"word": "to", "type": "preposition"}},
        {{"word": "the", "type": "article"}},
        {{"word": "store", "type": "noun"}},
        {{"word": "yesterday", "type": "adverb"}}
    ],
    "spanish": [
        {{"word": "Yo", "type": "pronoun"}},
        {{"word": "fui", "type": "verb"}},
        {{"word": "a", "type": "preposition"}},
        {{"word": "la", "type": "article"}},
        {{"word": "tienda", "type": "noun"}},
        {{"word": "ayer", "type": "adverb"}}
    ]
    }}

    Rules:
    - Match words by MEANING not position
    - "store" and "tienda" must have the same type (noun)
    - "went" and "fui" must have the same type (verb)
    - Types: pronoun, verb, noun, adjective, adverb, article, preposition, conjunction, other"""

    headers = {
        "Authorization": f"Bearer {AZURE_GROK_API_KEY}",
        "Content-Type": "application/json"
    }

    payload = {
        "model": AZURE_GROK_DEPLOYMENT_NAME,
        "messages": [
            {"role": "system", "content": "Return ONLY valid JSON. No markdown, no explanation."},
            {"role": "user", "content": prompt}
        ],
        "max_tokens": 800,
        "temperature": 0
    }

    try:
        response = requests.post(
            f"{AZURE_GROK_ENDPOINT}/chat/completions",
            headers=headers,
            json=payload
        )
        if response.status_code == 200:
            content = response.json()["choices"][0]["message"]["content"]
            content = content.strip().replace("```json", "").replace("```", "")
            data = json.loads(content)

            return {
                "english": [
                    {"word": w["word"], "color": get_word_color(w["type"])}
                    for w in data.get("english", [])
                ],
                "spanish": [
                    {"word": w["word"], "color": get_word_color(w["type"])}
                    for w in data.get("spanish", [])
                ]
            }
        return {"english": [], "spanish": []}
    except Exception:
        return {"english": [], "spanish": []}

def get_word_color(word_type: str) -> str:
    """Returns hex color for each word type."""
    colors = {
        "pronoun":     "#60A5FA",  # blue
        "verb":        "#34D399",  # green
        "noun":        "#F87171",  # red
        "adjective":   "#FB923C",  # orange
        "adverb":      "#FBBF24",  # yellow
        "article":     "#9CA3AF",  # gray
        "preposition": "#6B7280",  # dark gray
        "conjunction": "#A78BFA",  # purple
        "other":       "#D1D5DB",  # light gray
    }
    return colors.get(word_type, "#D1D5DB")

def get_pronunciation_color(score: float) -> str:
    """Returns hex color based on pronunciation score."""
    if score >= 90:
        return "#34D399"  # green
    elif score >= 70:
        return "#FBBF24"  # yellow
    elif score >= 50:
        return "#FB923C"  # orange
    else:
        return "#F87171"  # red