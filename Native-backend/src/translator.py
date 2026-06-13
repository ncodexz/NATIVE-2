# translator.py
# Azure Translator — translates English to Spanish for subtitles

import requests
from config import AZURE_TRANSLATOR_ENDPOINT, AZURE_TRANSLATOR_KEY

def translate_to_spanish(text: str) -> str:
    """Translates English text to Spanish."""
    if not text.strip():
        return ""

    url = f"{AZURE_TRANSLATOR_ENDPOINT}/translate?api-version=2026-06-06"
    
    headers = {
        "Ocp-Apim-Subscription-Key": AZURE_TRANSLATOR_KEY,
        "Content-Type": "application/json"
    }
    
    body = {
        "inputs": [
            {
                "Text": text,
                "language": "en",
                "targets": [{"language": "es"}]
            }
        ]
    }

    try:
        response = requests.post(url, headers=headers, json=body)
        if response.status_code == 200:
            return response.json()["value"][0]["translations"][0]["text"]
        return ""
    except Exception:
        return ""