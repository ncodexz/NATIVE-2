# pronunciation.py
# Pronunciation Assessment via Azure Speech SDK
# Runs in parallel with Voice Live

import azure.cognitiveservices.speech as speechsdk
import asyncio
from config import AZURE_SPEECH_KEY, AZURE_SPEECH_REGION

def assess_pronunciation(audio_data: bytes, text: str = None) -> list:
    """
    Analyzes pronunciation of audio data.
    Returns list of words with pronunciation scores.
    audio_data: raw PCM16 audio bytes at 24000Hz mono
    text: reference text (optional, improves accuracy)
    """
    try:
        # Configure speech
        speech_config = speechsdk.SpeechConfig(
            subscription=AZURE_SPEECH_KEY,
            region=AZURE_SPEECH_REGION
        )
        speech_config.speech_recognition_language = "en-US"

        # Configure pronunciation assessment
        pronunciation_config = speechsdk.PronunciationAssessmentConfig(
            grading_system=speechsdk.PronunciationAssessmentGradingSystem.HundredMark,
            granularity=speechsdk.PronunciationAssessmentGranularity.Word,
            enable_miscue=False
        )

        # Create audio from bytes
        audio_format = speechsdk.audio.AudioStreamFormat(
            samples_per_second=24000,
            bits_per_sample=16,
            channels=1
        )
        stream = speechsdk.audio.PushAudioInputStream(stream_format=audio_format)
        audio_config = speechsdk.audio.AudioConfig(stream=stream)

        # Push audio data
        stream.write(audio_data)
        stream.close()

        # Create recognizer
        recognizer = speechsdk.SpeechRecognizer(
            speech_config=speech_config,
            audio_config=audio_config
        )
        pronunciation_config.apply_to(recognizer)

        # Recognize
        result = recognizer.recognize_once()

        if result.reason == speechsdk.ResultReason.RecognizedSpeech:
            pa_result = speechsdk.PronunciationAssessmentResult(result)
            words = []
            for word in pa_result.words:
                words.append({
                    "word": word.word,
                    "accuracy": word.accuracy_score,
                    "color": get_pronunciation_color(word.accuracy_score)
                })
            return words
        return []

    except Exception as e:
        print(f"Pronunciation assessment error: {e}")
        return []

def get_pronunciation_color(score: float) -> str:
    """Returns hex color based on pronunciation score."""
    if score >= 90:
        return "#34D399"  # green - perfect
    elif score >= 70:
        return "#FBBF24"  # yellow - acceptable
    elif score >= 50:
        return "#FB923C"  # orange - needs work
    else:
        return "#F87171"  # red - incorrect