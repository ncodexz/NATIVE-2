# tts.py
# Text to Speech — Azure Speech TTS with MAI-Voice-1 streaming

import azure.cognitiveservices.speech as speechsdk
from config import AZURE_SPEECH_KEY, AZURE_SPEECH_REGION

VOICES = {
    "Olivia": "en-US-Iris:MAI-Voice-1",
    "Harper": "en-US-Joy:MAI-Voice-1",
    "Iris":   "en-US-June:MAI-Voice-1",
    "Grant":  "en-US-Grant:MAI-Voice-1",
    "Jasper": "en-US-Jasper:MAI-Voice-1",
}

async def speak(text: str, character: str = "Olivia") -> None:
    voice = VOICES.get(character, "en-US-Iris:MAI-Voice-1")
    print(f"{character}: {text}")

    speech_config = speechsdk.SpeechConfig(
        subscription=AZURE_SPEECH_KEY,
        region=AZURE_SPEECH_REGION
    )
    speech_config.speech_synthesis_voice_name = voice
    audio_config = speechsdk.audio.AudioOutputConfig(use_default_speaker=True)
    synthesizer = speechsdk.SpeechSynthesizer(
        speech_config=speech_config,
        audio_config=audio_config
    )
    synthesizer.speak_text_async(text).get()