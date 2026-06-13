# agent_analytical.py
# Analytical agent — detects errors, tone, and builds learning map

import requests
import json
from config import AZURE_GROK_ENDPOINT, AZURE_GROK_API_KEY, AZURE_GROK_DEPLOYMENT_NAME

SYSTEM_PROMPT = """You are an English language analysis assistant for a conversational learning app.
Your job is to analyze what a Spanish speaker said in English.

PHILOSOPHY:
- Conversation flows naturally. Errors are part of learning.
- Only flag errors that genuinely impact communication or appear repeatedly.
- Emotional expressions like "Helloooo!", "Yeahhh", "Omg" are NEVER errors.
- Informal but understood phrases are NEVER errors.

PRONUNCIATION RULES:
- Score > 80: acceptable, do not flag
- Score 60-80: flag only if it changes meaning
- Score < 60: flag as pronunciation issue, suggest practice

ERROR CLASSIFICATION:
1. "structural" — grammar error that blocks communication: "I no understand"
2. "vocabulary" — wrong word that changes meaning: "I am boring" instead of "I am bored"  
3. "pronunciation" — spoken differently than written, changes meaning: "can't" as "cant"
4. "expression" — informal/emotional expression → NEVER flag these

CORRECTION STYLE:
- NEVER use "instead of X say Y" format
- NEVER interrupt conversation for minor errors
- The character should integrate corrections naturally in their response
- For pronunciation: suggest brief practice only if score < 60 or error is repeated

Always respond ONLY with valid JSON, no extra text.

{
    "errors": [
        {
            "type": "structural|vocabulary|pronunciation",
            "original": "what the user said incorrectly",
            "correction": "correct version",
            "context": "brief explanation in Spanish",
            "severity": "low|medium|high"
        }
    ],
    "emotional_tone": "neutral|friendly|sarcastic|rude|flirty|frustrated|shy|excited",
    "intensity": "low|medium|high",
    "should_correct_now": true or false,
    "pronunciation_needs_practice": true or false,
    "summary": "one line in Spanish"
}

should_correct_now = true ONLY when:
- Error severely blocks communication
- Same error appears 3+ times in session
- Pronunciation score < 60 AND meaning is unclear

should_correct_now = false in ALL other cases."""

def analyze(user_input: str, pronunciation_scores: dict) -> dict:
    if not user_input.strip():
        return {
            "errors": [],
            "emotional_tone": "neutral",
            "intensity": "low",
            "should_correct_now": False,
            "summary": "No input detected"
        }

    prompt = f"""Analyze this English sentence from a Spanish speaker:
    
Sentence: "{user_input}"

Pronunciation scores:
- Accuracy: {pronunciation_scores.get('accuracy', 0):.1f}/100
- Fluency: {pronunciation_scores.get('fluency', 0):.1f}/100
- Prosody: {pronunciation_scores.get('prosody', 0):.1f}/100

Return JSON analysis."""

    headers = {
        "Authorization": f"Bearer {AZURE_GROK_API_KEY}",
        "Content-Type": "application/json"
    }

    payload = {
        "model": AZURE_GROK_DEPLOYMENT_NAME,
        "messages": [
            {"role": "system", "content": SYSTEM_PROMPT},
            {"role": "user", "content": prompt}
        ],
        "max_tokens": 300,
        "temperature": 0.3
    }

    response = requests.post(
        f"{AZURE_GROK_ENDPOINT}/chat/completions",
        headers=headers,
        json=payload
    )

    if response.status_code == 200:
        content = response.json()["choices"][0]["message"]["content"]
        try:
            return json.loads(content)
        except json.JSONDecodeError:
            return {
                "errors": [],
                "emotional_tone": "neutral",
                "intensity": "low",
                "should_correct_now": False,
                "summary": "Analysis failed"
            }
    else:
        return {
            "errors": [],
            "emotional_tone": "neutral", 
            "intensity": "low",
            "should_correct_now": False,
            "summary": "Service unavailable"
        }