# voice_live.py
# NATIVE 2.0 — Voice Live pipeline
# Replaces: transcriber.py, agent_conversational.py, tts.py

import asyncio
import base64
import queue
import pyaudio
from azure.core.credentials import AzureKeyCredential
from azure.ai.voicelive.aio import connect
from azure.ai.voicelive.models import (
    AudioEchoCancellation,
    AudioNoiseReduction,
    AzureStandardVoice,
    InputAudioFormat,
    OutputAudioFormat,
    Modality,
    RequestSession,
    ServerEventType,
    ServerVad,
)
from config import AZURE_VOICELIVE_ENDPOINT, AZURE_VOICELIVE_API_KEY, AZURE_VOICELIVE_MODEL
from context_builder import build_user_context
from level_detector import get_user_level, get_level_instructions
from pedagogy import should_inject, build_injection, build_pronunciation_injection

# Available voices
VOICES = {
    "Ava":    "en-US-Ava:DragonHDLatestNeural",
    "Emma":   "en-US-Emma:DragonHDLatestNeural",
    "Andrew": "en-US-Andrew:DragonHDLatestNeural",
}

# Character personalities
PERSONALITIES = {
    "Ava": """You are Ava, 26, American, warm and expressive. You love art and travel.
You are NOT a teacher — you are a native English speaking friend having a real conversation.
The user is learning English. Help them naturally — never academically.
When the user makes a grammar error that changes meaning, echo the correct version naturally in your response.
Example: User says 'Yesterday I go to the park' → You say 'Oh you went to the park? What did you do?'
Never say 'you should say', 'the correct form is', or 'instead of'.
Emotional expressions like 'Helloooo' or 'Yeahhh' are NEVER errors — ignore them completely.
If the user is rude: set a boundary calmly once, then move on.
If the user is flirty: be friendly but redirect naturally.
If the user is shy: ask simple questions to bring them out.
When the user interrupts to correct a word, do NOT just swap the word and continue.
First, reinterpret the entire meaning of what the user said with the corrected word.
If your previous response still makes sense with the correct word, acknowledge and continue.
If your previous response no longer makes sense, acknowledge the misunderstanding naturally:
'Oh cats! That completely changes what I said — I thought you meant something else entirely. 
So you have cats? Tell me about them.'
Never continue a line of thought that becomes wrong or absurd after a correction.
Always prioritize meaning over continuity.
Keep responses to 1-3 sentences. Natural conversational English only.""",

    "Emma": """You are Emma, 30, American, direct and witty. You work in tech.
You are NOT a teacher — you are a native English speaking friend having a real conversation.
The user is learning English. Help them naturally — never academically.
When the user makes a grammar error that changes meaning, echo the correct version naturally in your response.
Example: User says 'I am boring at the party' → You say 'Bored? Yeah boring parties are rough. What happened?'
Never say 'you should say', 'the correct form is', or 'instead of'.
Emotional expressions like 'Helloooo' or 'Yeahhh' are NEVER errors — ignore them completely.
If the user is rude: call it out once briefly then move on.
If the user is sarcastic: match the energy and enjoy the banter.
If the user is nervous: lighten the mood with humor.
When the user interrupts to correct a word, do NOT just swap the word and continue.
First, reinterpret the entire meaning of what the user said with the corrected word.
If your previous response still makes sense with the correct word, acknowledge and continue.
If your previous response no longer makes sense, acknowledge the misunderstanding naturally:
'Oh cats! That completely changes what I said — I thought you meant something else entirely. 
So you have cats? Tell me about them.'
Never continue a line of thought that becomes wrong or absurd after a correction.
Always prioritize meaning over continuity.
Keep responses to 1-3 sentences. Natural conversational English only.""",

    "Andrew": """You are Andrew, 32, American, confident and direct. You are a sports journalist.
You are NOT a teacher — you are a native English speaking friend having a real conversation.
The user is learning English. Help them naturally — never academically.
When the user makes a grammar error that changes meaning, echo the correct version naturally in your response.
Example: User says 'He don't know' → You say 'He doesn't know? Yeah that's rough.'
Never say 'you should say', 'the correct form is', or 'instead of'.
Emotional expressions like 'Helloooo' or 'Yeahhh' are NEVER errors — ignore them completely.
If the user is aggressive: stay calm but firm.
If the user is shy: ask direct questions to get them talking.
If the user is funny: build on it and enjoy it.
When the user interrupts to correct a word, do NOT just swap the word and continue.
First, reinterpret the entire meaning of what the user said with the corrected word.
If your previous response still makes sense with the correct word, acknowledge and continue.
If your previous response no longer makes sense, acknowledge the misunderstanding naturally:
'Oh cats! That completely changes what I said — I thought you meant something else entirely. 
So you have cats? Tell me about them.'
Never continue a line of thought that becomes wrong or absurd after a correction.
Always prioritize meaning over continuity.
Keep responses to 1-3 sentences. Natural conversational English only.""",
}


class NativeVoiceLive:
    def __init__(self, character: str, user_name: str, user_id: int, user_context: str = "", session_id: int = 0):
        self.character = character
        self.user_name = user_name
        self.user_id = user_id
        self.user_context = user_context
        self.session_id = session_id  # ← añade
        self.connection = None
        self._active_response = False
        self._response_api_done = False
        self.turn_count = 0
        self.session_scores = []

    def _build_instructions(self) -> str:
        base = PERSONALITIES.get(self.character, PERSONALITIES["Ava"])
    
        # Get user level and adapt character behavior
        user_level = get_user_level(self.user_id)
        level_instructions = get_level_instructions(user_level)
        
        # Build personalized context from user history
        from context_builder import build_user_context
        user_context = build_user_context(self.user_id, self.user_name)
        
        context = f"\n\nUSER LEVEL:\n{level_instructions}"
        context += f"\n\nUSER CONTEXT:\n{user_context}"
        context += f"\n\nUser's name is {self.user_name}."
        
        if self.user_context:
            context += f"\n\n{self.user_context}"
        
        context += "\nStart with a natural, warm greeting."
    
        return base + context
    async def start(self):
        credential = AzureKeyCredential(AZURE_VOICELIVE_API_KEY)
        voice_name = VOICES.get(self.character, "en-US-Ava:DragonHDLatestNeural")

        try:
            async with connect(
                endpoint=AZURE_VOICELIVE_ENDPOINT,
                credential=credential,
                model=AZURE_VOICELIVE_MODEL,
            ) as connection:
                self.connection = connection
                ap = _AudioProcessor(connection)

                await connection.session.update(session=RequestSession(
                    modalities=[Modality.TEXT, Modality.AUDIO],
                    instructions=self._build_instructions(),
                    voice=AzureStandardVoice(name=voice_name),
                    input_audio_transcription={"model": "azure-speech"},
                    input_audio_format=InputAudioFormat.PCM16,
                    output_audio_format=OutputAudioFormat.PCM16,
                    turn_detection=ServerVad(
                        threshold=0.8,
                        prefix_padding_ms=300,
                        silence_duration_ms=800,
                    ),
                    input_audio_echo_cancellation=AudioEchoCancellation(),
                    input_audio_noise_reduction=AudioNoiseReduction(
                        type="azure_deep_noise_suppression"
                    ),
                ))

                ap.start_playback()

                print(f"\n{'='*40}")
                print(f"   NATIVE 2.0 — Talking with {self.character}")
                print(f"   Press Ctrl+C to end session")
                print(f"{'='*40}\n")

                async for event in connection:
                    await self._handle_event(event, ap)

        except KeyboardInterrupt:
            print(f"\n\nSession ended. Great work {self.user_name}!")
        finally:
            if 'ap' in locals():
                ap.shutdown()

    async def _handle_event(self, event, ap):
        if event.type == ServerEventType.SESSION_UPDATED:
            ap.start_capture()

        elif event.type == ServerEventType.INPUT_AUDIO_BUFFER_SPEECH_STARTED:
            print("🎤 Listening...")
            ap.skip_pending_audio()
            if self._active_response and not self._response_api_done:
                try:
                    await self.connection.response.cancel()
                except Exception:
                    pass
        elif event.type == ServerEventType.CONVERSATION_ITEM_INPUT_AUDIO_TRANSCRIPTION_COMPLETED:
            print(f"\n📝 You said: {event.transcript}\n")

        elif event.type == ServerEventType.INPUT_AUDIO_BUFFER_SPEECH_STOPPED:
            print("💭 Processing...")

        elif event.type == ServerEventType.RESPONSE_CREATED:
            self._active_response = True
            self._response_api_done = False

        elif event.type == ServerEventType.RESPONSE_AUDIO_DELTA:
            ap.queue_audio(event.delta)

        elif event.type == ServerEventType.RESPONSE_AUDIO_TRANSCRIPT_DELTA:
            print(event.delta, end="", flush=True)

        elif event.type == ServerEventType.RESPONSE_AUDIO_TRANSCRIPT_DONE:
            print(f"TRANSCRIPT DONE: {event.transcript}")
            from translator import translate_to_spanish
            from text_analyzer import analyze_grammar_bilingual
            
            translation = translate_to_spanish(event.transcript)
            analysis = analyze_grammar_bilingual(event.transcript, translation)
            
            await websocket.send_json({
                "type": "assistant_analysis",
                "analysis": analysis
            })

        elif event.type == ServerEventType.RESPONSE_DONE:
            self._active_response = False
            self._response_api_done = True
            print("\n🎤 Your turn...\n")

        elif event.type == ServerEventType.ERROR:
            print(f"❌ Error: {event.error.message}")
    

    async def _update_session_context(self, scores: dict):
        """Updates session context and injects pedagogy when needed."""
        self.turn_count += 1
        self.session_scores.append(scores)

        injections = []

        # Check pronunciation issues
        pronunciation_injection = build_pronunciation_injection(scores, self.user_id)
        if pronunciation_injection:
            injections.append(pronunciation_injection)

        # Check if pedagogical injection needed
        if should_inject(self.turn_count, self.user_id):
            correction_injection = build_injection(self.user_id)
            if correction_injection:
                injections.append(correction_injection)

        # If there are injections, update the session
        if injections and self.connection:
            combined = "\n\n".join(injections)
            try:
                from azure.ai.voicelive.models import RequestSession
                await self.connection.session.update(
                    session=RequestSession(instructions=combined)
                )
            except Exception:
                pass
    async def start_websocket(self, websocket):
            """Voice Live session via WebSocket for frontend."""
            import base64
            from azure.core.credentials import AzureKeyCredential
            from azure.ai.voicelive.aio import connect
            from azure.ai.voicelive.models import (
                RequestSession, AzureStandardVoice, Modality,
                InputAudioFormat, OutputAudioFormat, ServerVad,
                AudioEchoCancellation, AudioNoiseReduction
            )

            print("start_websocket called")
            credential = AzureKeyCredential(AZURE_VOICELIVE_API_KEY)
            voice_name = VOICES.get(self.character, "en-US-Ava:DragonHDLatestNeural")
            audio_buffer = bytearray()
            is_user_speaking = False
            user_transcript_ref = ""
            _user_id = self.user_id        
            _session_id = self.session_id
            turn_count = 0

            try:
                async with connect(
                    endpoint=AZURE_VOICELIVE_ENDPOINT,
                    credential=credential,
                    model=AZURE_VOICELIVE_MODEL,
                ) as connection:
                    print("Voice Live connected")
                    self.connection = connection

                    await connection.session.update(session=RequestSession(
                        modalities=[Modality.TEXT, Modality.AUDIO],
                        instructions=self._build_instructions(),
                        voice=AzureStandardVoice(name=voice_name),
                        input_audio_format=InputAudioFormat.PCM16,
                        output_audio_format=OutputAudioFormat.PCM16,
                        input_audio_transcription={"model": "azure-speech"},
                        turn_detection=ServerVad(
                            threshold=0.5,
                            prefix_padding_ms=300,
                            silence_duration_ms=600,
                        ),
                        input_audio_echo_cancellation=AudioEchoCancellation(),
                        input_audio_noise_reduction=AudioNoiseReduction(
                            type="azure_deep_noise_suppression"
                        ),
                    ))
                    print("Session configured")
                    async def run_pronunciation_assessment(audio_data: bytes, ws, reference_text: str = "", user_id: int = 0, session_id: int = 0):
                        try:
                            loop = asyncio.get_event_loop()
                            from pronunciation import assess_pronunciation
                            from database import save_progress
                            words = await loop.run_in_executor(None, assess_pronunciation, audio_data, reference_text)
                            if words:
                                # Calculate average scores
                                avg_accuracy = sum(w["accuracy"] for w in words) / len(words)
                                
                                # Save to database
                                save_progress(_user_id, _session_id, {
                                    "accuracy": avg_accuracy,
                                    "fluency": avg_accuracy * 0.9,
                                    "prosody": avg_accuracy * 0.85,
                                    "grammar": 0,
                                    "vocabulary": 0
                                })
                                
                                await ws.send_json({
                                    "type": "pronunciation_result",
                                    "words": words
                                })
                        except Exception as e:
                            print(f"Pronunciation task error: {e}")
                    async def receive_from_client():
                        nonlocal audio_buffer, is_user_speaking
                        try:
                            while True:
                                data = await websocket.receive_bytes()
                                audio_b64 = base64.b64encode(data).decode("utf-8")
                                await connection.input_audio_buffer.append(audio=audio_b64)
                                audio_buffer.extend(data)
                        except Exception as e:
                            print(f"receive_from_client error: {e}")
                            
                    async def send_to_client():
                        try:
                            async for event in connection:
                                print(f"EVENT: {event.type}")
                                if event.type == ServerEventType.RESPONSE_AUDIO_DELTA:
                                    await websocket.send_bytes(event.delta)
                                    
                                elif event.type == ServerEventType.RESPONSE_AUDIO_TRANSCRIPT_DELTA:
                                    await websocket.send_json({
                                        "type": "assistant_transcript",
                                        "text": event.delta
                                    })
                                    
                                elif event.type == ServerEventType.RESPONSE_AUDIO_TRANSCRIPT_DONE:
                                    from translator import translate_to_spanish
                                    translation = translate_to_spanish(event.transcript)
                                    await websocket.send_json({
                                        "type": "assistant_translation",
                                        "text": translation
                                    })   
                                elif event.type == ServerEventType.CONVERSATION_ITEM_INPUT_AUDIO_TRANSCRIPTION_COMPLETED:
                                    nonlocal user_transcript_ref
                                    print(f"USER TRANSCRIPT: '{event.transcript}'")
                                    user_transcript_ref += " " + event.transcript if user_transcript_ref else event.transcript
                                    await websocket.send_json({
                                        "type": "user_transcript",
                                        "text": user_transcript_ref
                                    })
                               
                                elif event.type == ServerEventType.RESPONSE_DONE:
                                    nonlocal turn_count
                                    await websocket.send_json({"type": "assistant_done"})
                                    turn_count += 1
                                    
                                    if turn_count % 5 == 0:
                                        from pedagogy import should_inject, build_injection
                                        if should_inject(turn_count, _user_id):
                                            injection = build_injection(_user_id)
                                            if injection:
                                                try:
                                                    from azure.ai.voicelive.models import RequestSession
                                                    await connection.session.update(
                                                        session=RequestSession(instructions=injection)
                                                    )
                                                    print(f"Pedagogy injected at turn {turn_count}")
                                                except Exception as e:
                                                    print(f"Pedagogy injection error: {e}")
                                    
                                elif event.type == ServerEventType.INPUT_AUDIO_BUFFER_SPEECH_STARTED:
                                    await websocket.send_json({"type": "user_speaking"})
                                    audio_buffer.clear()
                                    is_user_speaking = True
                                    user_transcript_ref = ""

                                elif event.type == ServerEventType.INPUT_AUDIO_BUFFER_SPEECH_STOPPED:
                                    is_user_speaking = False
                                    # Run pronunciation assessment in background
                                    if len(audio_buffer) > 0:
                                        audio_copy = bytes(audio_buffer)
                                        audio_buffer.clear()
                                        asyncio.create_task(
                                            run_pronunciation_assessment(audio_copy, websocket, user_transcript_ref, _user_id, _session_id)
                                        )  
                                    
                        except Exception as e:
                            print(f"send_to_client error: {e}")

                    await asyncio.gather(
                        receive_from_client(),
                        send_to_client()
                    )

            except Exception as e:
                import traceback
                print(f"Voice Live error: {e}")
                print(traceback.format_exc())
                await websocket.close()
    

                
        
class _AudioProcessor:
    class _Packet:
        def __init__(self, seq: int, data):
            self.seq_num = seq
            self.data = data

    def __init__(self, connection):
        self.connection = connection
        self.audio = pyaudio.PyAudio()
        self.format = pyaudio.paInt16
        self.channels = 1
        self.rate = 24000
        self.chunk = 1200
        self.input_stream = None
        self.output_stream = None
        self.playback_queue = queue.Queue()
        self.playback_base = 0
        self.next_seq = 0
        self.loop = None

    def start_capture(self):
        self.loop = asyncio.get_event_loop()

        def callback(in_data, _fc, _ti, _sf):
            audio_b64 = base64.b64encode(in_data).decode("utf-8")
            asyncio.run_coroutine_threadsafe(
                self.connection.input_audio_buffer.append(audio=audio_b64),
                self.loop
            )
            return (None, pyaudio.paContinue)

        self.input_stream = self.audio.open(
            format=self.format,
            channels=self.channels,
            rate=self.rate,
            input=True,
            frames_per_buffer=self.chunk,
            stream_callback=callback
        )

    def start_playback(self):
        remaining = bytes()

        def callback(_id, frame_count, _ti, _sf):
            nonlocal remaining
            frame_count *= pyaudio.get_sample_size(pyaudio.paInt16)
            out = remaining[:frame_count]
            remaining = remaining[frame_count:]

            while len(out) < frame_count:
                try:
                    packet = self.playback_queue.get_nowait()
                except queue.Empty:
                    out += bytes(frame_count - len(out))
                    continue
                if not packet or not packet.data:
                    break
                if packet.seq_num < self.playback_base:
                    remaining = bytes()
                    continue
                need = frame_count - len(out)
                out += packet.data[:need]
                remaining = packet.data[need:]

            return (out, pyaudio.paContinue) if len(out) >= frame_count else (out, pyaudio.paComplete)

        self.output_stream = self.audio.open(
            format=self.format,
            channels=self.channels,
            rate=self.rate,
            output=True,
            frames_per_buffer=self.chunk,
            stream_callback=callback
        )

    def queue_audio(self, data):
        seq = self.next_seq
        self.next_seq += 1
        self.playback_queue.put(self._Packet(seq, data))

    def skip_pending_audio(self):
        self.playback_base = self.next_seq
        self.next_seq += 1

    def shutdown(self):
        if self.input_stream:
            self.input_stream.stop_stream()
            self.input_stream.close()
        if self.output_stream:
            self.skip_pending_audio()
            self.queue_audio(None)
            self.output_stream.stop_stream()
            self.output_stream.close()
        if self.audio:
            self.audio.terminate()