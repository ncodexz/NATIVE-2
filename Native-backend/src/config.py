# config.py
# Central configuration — loads all environment variables

import os
from dotenv import load_dotenv

load_dotenv()

# Provider
PROVIDER = os.getenv("PROVIDER", "local")

# Azure Speech — STT, TTS, MAI models, Pronunciation Assessment
AZURE_SPEECH_KEY = os.getenv("AZURE_SPEECH_KEY")
AZURE_SPEECH_REGION = os.getenv("AZURE_SPEECH_REGION")

# Azure AI Foundry — Grok 4.3
AZURE_GROK_ENDPOINT = os.getenv("AZURE_GROK_ENDPOINT")
AZURE_GROK_API_KEY = os.getenv("AZURE_GROK_API_KEY")
AZURE_GROK_DEPLOYMENT_NAME = os.getenv("AZURE_GROK_DEPLOYMENT_NAME")

# Learning config
LEARNING_LANGUAGE = "en-US"
NATIVE_LANGUAGE = "es-ES"

# Azure Voice Live
AZURE_VOICELIVE_ENDPOINT = os.getenv("AZURE_VOICELIVE_ENDPOINT")
AZURE_VOICELIVE_API_KEY = os.getenv("AZURE_VOICELIVE_API_KEY")
AZURE_VOICELIVE_MODEL = os.getenv("AZURE_VOICELIVE_MODEL", "gpt-4o-mini")
# Azure Translator
AZURE_TRANSLATOR_ENDPOINT = os.getenv("AZURE_TRANSLATOR_ENDPOINT")
AZURE_TRANSLATOR_KEY = os.getenv("AZURE_TRANSLATOR_KEY")

# Azure AI Search - Foundry IQ
AZURE_SEARCH_ENDPOINT = os.getenv("AZURE_SEARCH_ENDPOINT")
AZURE_SEARCH_KEY = os.getenv("AZURE_SEARCH_KEY")
AZURE_SEARCH_INDEX = os.getenv("AZURE_SEARCH_INDEX", "native-knowledge")