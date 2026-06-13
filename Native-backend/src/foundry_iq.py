# foundry_iq.py
# Foundry IQ knowledge base retrieval
# Queries pedagogical knowledge base for grammar, pronunciation, vocabulary, idioms

import os
from azure.search.documents import SearchClient
from azure.search.documents.models import VectorizedQuery
from azure.core.credentials import AzureKeyCredential
from config import AZURE_SPEECH_REGION

# Foundry IQ / Azure AI Search credentials
SEARCH_ENDPOINT = os.getenv("AZURE_SEARCH_ENDPOINT")
SEARCH_KEY = os.getenv("AZURE_SEARCH_KEY")
SEARCH_INDEX = os.getenv("AZURE_SEARCH_INDEX", "native-knowledge")

def query_knowledge_base(query: str, top: int = 3) -> str:
    """
    Queries Foundry IQ knowledge base for pedagogical context.
    Returns relevant content as a string to inject into agent context.
    """
    if not SEARCH_ENDPOINT or not SEARCH_KEY:
        return ""

    try:
        client = SearchClient(
            endpoint=SEARCH_ENDPOINT,
            index_name=SEARCH_INDEX,
            credential=AzureKeyCredential(SEARCH_KEY)
        )

        results = client.search(
            search_text=query,
            top=top,
            select=["content", "title"]
        )

        context_parts = []
        for result in results:
            title = result.get("title", "")
            content = result.get("content", "")
            if content:
                context_parts.append(f"## {title}\n{content[:500]}")

        if context_parts:
            return "\n\n".join(context_parts)
        return ""

    except Exception as e:
        print(f"Foundry IQ query error: {e}")
        return ""

def get_pedagogical_context(error_type: str, original: str, correction: str) -> str:
    """
    Gets pedagogical context for a specific error to enrich agent corrections.
    """
    query = f"{error_type} {original} {correction} Spanish speakers English"
    return query_knowledge_base(query)

def get_pronunciation_context(word: str) -> str:
    """
    Gets pronunciation guidance for a specific word.
    """
    query = f"pronunciation {word} Spanish speakers"
    return query_knowledge_base(query, top=2)

def get_level_context(level: str) -> str:
    """
    Gets vocabulary and conversation guidance for a specific level.
    """
    query = f"vocabulary {level} level English Spanish speakers conversation"
    return query_knowledge_base(query, top=2)