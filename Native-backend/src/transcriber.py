# transcriber.py
# Speech to Text — Azure Speech STT + Pronunciation Assessment

import azure.cognitiveservices.speech as speechsdk
from config import AZURE_SPEECH_KEY, AZURE_SPEECH_REGION, LEARNING_LANGUAGE

def transcribe() -> tuple:
    # Speech config
    speech_config = speechsdk.SpeechConfig(
        subscription=AZURE_SPEECH_KEY,
        region=AZURE_SPEECH_REGION
    )
    speech_config.speech_recognition_language = LEARNING_LANGUAGE
    
    # Reduce silence timeout for faster response
    speech_config.set_property(
        speechsdk.PropertyId.SpeechServiceConnection_EndSilenceTimeoutMs, "900"
    )
    speech_config.set_property(
        speechsdk.PropertyId.SpeechServiceConnection_InitialSilenceTimeoutMs, "5000"
    )

    # Pronunciation Assessment config
    pronunciation_config = speechsdk.PronunciationAssessmentConfig(
        grading_system=speechsdk.PronunciationAssessmentGradingSystem.HundredMark,
        granularity=speechsdk.PronunciationAssessmentGranularity.Word,
        enable_miscue=True
    )
    pronunciation_config.enable_prosody_assessment()

    # Audio from microphone
    audio_config = speechsdk.audio.AudioConfig(use_default_microphone=True)

    # Recognizer
    recognizer = speechsdk.SpeechRecognizer(
        speech_config=speech_config,
        audio_config=audio_config
    )

    # Attach pronunciation assessment
    pronunciation_config.apply_to(recognizer)

    print("Recording with Azure... speak now")
    result = recognizer.recognize_once()

    if result.reason == speechsdk.ResultReason.RecognizedSpeech:
        # Get pronunciation scores
        pronunciation_result = speechsdk.PronunciationAssessmentResult(result)
        scores = {
            "accuracy": pronunciation_result.accuracy_score,
            "fluency": pronunciation_result.fluency_score,
            "prosody": pronunciation_result.prosody_score,
            "completeness": pronunciation_result.completeness_score
        }
        return result.text, scores

    else:
        return "", {"accuracy": 0, "fluency": 0, "prosody": 0, "completeness": 0}