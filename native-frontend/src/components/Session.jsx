import { useState, useEffect, useRef } from "react"
import { Canvas } from "@react-three/fiber"
import Orb from "./Orb"
import axios from "axios"

const API = "http://localhost:8000"
const WS = "ws://localhost:8000"

const CHARACTERS = [
  { name: "Ava", description: "Warm and expressive" },
  { name: "Emma", description: "Direct and witty" },
  { name: "Andrew", description: "Confident and natural" },
]

export default function Session({ token, user, onLogout }) {
  const [character, setCharacter] = useState(null)
  const [sessionId, setSessionId] = useState(null)
  const [connected, setConnected] = useState(false)
  const [speaking, setSpeaking] = useState(false)
  const [listening, setListening] = useState(false)
  const [transcript, setTranscript] = useState("")
  const [userTranscript, setUserTranscript] = useState("")
  const [muted, setMuted] = useState(false)
  const [micPaused, setMicPaused] = useState(false)
  const [translation, setTranslation] = useState("")
  const [pronunciationWords, setPronunciationWords] = useState([])
  const [userLevel, setUserLevel] = useState("")
  const [sessionSummary, setSessionSummary] = useState("")
  const [showSummary, setShowSummary] = useState(false)
 

  const wsRef = useRef(null)
  const audioContextRef = useRef(null)
  const streamRef = useRef(null)
  const processorRef = useRef(null)
  const summaryCalledRef = useRef(false)
  const micPausedRef = useRef(false)


  async function startSession(char) {
    try {
      const res = await axios.post(
        `${API}/session/start`,
        { character: char.name },
        { headers: { Authorization: `Bearer ${token}` } }
      )
      setCharacter(char)
      setSessionId(res.data.session_id)
      setUserLevel(res.data.level)
      connectWebSocket(res.data.session_id, char.name, res.data.user_id)
    } catch (err) {
      console.error("Failed to start session", err)
    }
  }

  function connectWebSocket(sid, charName, userId) {
    const ws = new WebSocket(
      `${WS}/ws/voice/${sid}/${charName}/${user}/${userId}`
    )
    ws.binaryType = "arraybuffer"
    wsRef.current = ws

    ws.onopen = () => {
      setConnected(true)
      startMicrophone(ws)
    }

    ws.onmessage = async (event) => {
      if (event.data instanceof ArrayBuffer) {
        // Audio from assistant — play it
        if (!muted) playAudio(event.data)
      } else {
        const msg = JSON.parse(event.data)

        if (msg.type === "assistant_transcript") {
          setTranscript(prev => prev + msg.text)
          setSpeaking(true)
          setListening(false)
        }

        if (msg.type === "user_transcript") {
          setUserTranscript(msg.text)
          setTranscript("")
        }
        if (msg.type === "user_speaking") {
          setListening(true)
          setSpeaking(false)
          setUserTranscript("")
          setTranslation("")
          setPronunciationWords([])
          
        }
        if (msg.type === "assistant_done") {
          setSpeaking(false)
          setListening(false)
        }
        
        if (msg.type === "assistant_translation") {
          setTranslation(msg.text)
        }
        if (msg.type === "pronunciation_result") {
          setPronunciationWords(prev => [...prev, ...msg.words])
        }
      }
    }

    ws.onclose = () => {
      setConnected(false)
      setSpeaking(false)
      setListening(false)
    }
    ws.onopen = () => {
      console.log("WebSocket connected")  // ← añade
      setConnected(true)
      startMicrophone(ws)
    }

    ws.onclose = (event) => {
      console.log("WebSocket closed", event.code, event.reason)  // ← añade
      setConnected(false)
      setSpeaking(false)
      setListening(false)
    }

    ws.onerror = (error) => {
      console.log("WebSocket error", error)  // ← añade
    }




  }

  async function startMicrophone(ws) {
    try {
      const stream = await navigator.mediaDevices.getUserMedia({ audio: true })
      streamRef.current = stream

      const audioContext = new AudioContext({ sampleRate: 24000 })
      audioContextRef.current = audioContext

      const source = audioContext.createMediaStreamSource(stream)
      const processor = audioContext.createScriptProcessor(1024, 1, 1)
      processorRef.current = processor

      processor.onaudioprocess = (e) => {
        if (micPausedRef.current || ws.readyState !== WebSocket.OPEN) return
        const input = e.inputBuffer.getChannelData(0)
        const pcm = float32ToPCM16(input)
        ws.send(pcm)
      }

      source.connect(processor)
      processor.connect(audioContext.destination)
    } catch (err) {
      console.error("Microphone error", err)
    }
  }

  function float32ToPCM16(float32Array) {
    const buffer = new ArrayBuffer(float32Array.length * 2)
    const view = new DataView(buffer)
    for (let i = 0; i < float32Array.length; i++) {
      const s = Math.max(-1, Math.min(1, float32Array[i]))
      view.setInt16(i * 2, s < 0 ? s * 0x8000 : s * 0x7fff, true)
    }
    return buffer
  }

    const audioQueueRef = useRef([])
    const isPlayingRef = useRef(false)

    function playAudio(arrayBuffer) {
    audioQueueRef.current.push(arrayBuffer)
    if (!isPlayingRef.current) {
        playNext()
    }
    }

    function playNext() {
    if (audioQueueRef.current.length === 0) {
        isPlayingRef.current = false
        return
    }
    
    isPlayingRef.current = true
    const buffer = audioQueueRef.current.shift()
    
    const audioContext = audioContextRef.current
    if (!audioContext) return

    // PCM16 to Float32
    const int16 = new Int16Array(buffer)
    const float32 = new Float32Array(int16.length)
    for (let i = 0; i < int16.length; i++) {
        float32[i] = int16[i] / 32768.0
    }

    const audioBuffer = audioContext.createBuffer(1, float32.length, 24000)
    audioBuffer.copyToChannel(float32, 0)

    const source = audioContext.createBufferSource()
    source.buffer = audioBuffer
    source.connect(audioContext.destination)
    source.onended = playNext
    source.start()
    }

  async function endSession() {
    if (summaryCalledRef.current) return  // ← evita llamadas duplicadas
    summaryCalledRef.current = true
    
    try {
      const res = await axios.post(
        `${API}/session/${sessionId}/summary`,
        {},
        { headers: { Authorization: `Bearer ${token}` } }
      )
      setSessionSummary(res.data.summary)
      setUserLevel(res.data.level)
      setShowSummary(true)
    } catch (err) {
      console.error("Summary error", err)
    }

    if (wsRef.current) wsRef.current.close()
    if (streamRef.current) streamRef.current.getTracks().forEach(t => t.stop())
    if (audioContextRef.current) audioContextRef.current.close()
    setConnected(false)
    setTranscript("")
    setUserTranscript("")
  }

  // Character selection screen
  if (!character) {
    return (
      <div className="min-h-screen bg-black flex flex-col items-center justify-center">
        <h1 className="text-4xl font-bold text-white tracking-widest mb-2">NATIVE</h1>
        <p className="text-gray-500 text-sm mb-12">Choose your conversation partner</p>

        <div className="flex gap-6">
          {CHARACTERS.map(char => (
            <button
              key={char.name}
              onClick={() => startSession(char)}
              className="border border-gray-700 hover:border-white text-white px-8 py-6 rounded-xl transition group"
            >
              <div className="text-xl font-semibold group-hover:text-white">{char.name}</div>
              <div className="text-gray-500 text-sm mt-1">{char.description}</div>
            </button>
          ))}
        </div>

        <button
          onClick={onLogout}
          className="mt-12 text-gray-600 hover:text-gray-400 text-sm transition"
        >
          Sign out
        </button>
      </div>
    )
  }
// Summary screen
if (showSummary) {
  return (
    <div className="min-h-screen bg-black flex flex-col items-center justify-center px-6">
      <h2 className="text-white text-2xl font-semibold mb-2">Session Complete</h2>
      {userLevel && userLevel !== "unknown" && (
        <p className="text-gray-500 text-sm mb-8 tracking-widest uppercase">Level: {userLevel}</p>
      )}
      <div className="w-full max-w-lg border border-gray-800 rounded-xl p-6 mb-8">
        <p className="text-gray-400 text-xs mb-3 tracking-wider">SESSION SUMMARY</p>
        <p className="text-gray-200 text-base leading-relaxed">{sessionSummary}</p>
      </div>
      <button
        onClick={() => {
          setShowSummary(false)
          setCharacter(null)
          setSessionId(null)
          setTranscript("")
          setUserTranscript("")
          setPronunciationWords([])
          setTranslation("")
        }}
        className="border border-gray-700 text-gray-400 hover:border-white hover:text-white px-8 py-3 rounded-lg transition text-sm"
      >
        Start New Session
      </button>
    </div>
  )
}
  // Session screen
  return (
    <div className="min-h-screen bg-black flex flex-col items-center justify-between py-12 px-6">

      {/* Header */}
      <div className="text-center">
        <p className="text-gray-500 text-sm tracking-wider">Talking with</p>
        <h2 className="text-white text-2xl font-semibold">{character.name}</h2>
        {userLevel && userLevel !== "unknown" && (
          <p className="text-gray-600 text-xs mt-1 tracking-widest uppercase">{userLevel}</p>
        )}
      </div>

      {/* Orb */}
      <div className="w-64 h-64">
        <Canvas camera={{ position: [0, 0, 2.5] }}>
          <ambientLight intensity={0.5} />
          <Orb speaking={speaking} listening={listening} />
        </Canvas>
      </div>

      {/* Transcripts */}

      {/* Transcripts */}
      <div className="w-full max-w-lg space-y-3 min-h-32">
        
        {userTranscript && (
          <div className="text-center">
            <p className="text-gray-400 text-xs mb-1">You said</p>
            <div className="flex flex-wrap justify-center gap-1">
              {pronunciationWords.length > 0
                ? pronunciationWords.map((w, i) => (
                    <span key={i} style={{ color: w.color }} className="text-lg font-medium">
                      {w.word}
                    </span>
                  ))
                : <span className="text-white text-lg">{userTranscript}</span>
              }
            </div>
          </div>
        )}

        {transcript && (
          <div className="text-center">
            <p className="text-gray-500 text-xs mb-1">{character.name}</p>
            <p className="text-gray-200 text-base">{transcript}</p>
            {translation && (
              <p className="text-gray-600 text-sm mt-1 italic">{translation}</p>
            )}
          </div>
        )}

      </div>

      {/* Controls */}
      <div className="flex gap-4">
        <button
          onClick={() => {
            setMicPaused(!micPaused)
            micPausedRef.current = !micPausedRef.current
          }}
          className={`px-6 py-3 rounded-lg border transition text-sm ${
            micPaused
              ? "border-yellow-500 text-yellow-500"
              : "border-gray-700 text-gray-400 hover:border-white hover:text-white"
          }`}
        >
          {micPaused ? "🎤 Paused" : "🎤 Mic"}
        </button>

        <button
          onClick={() => setMuted(!muted)}
          className={`px-6 py-3 rounded-lg border transition text-sm ${
            muted
              ? "border-yellow-500 text-yellow-500"
              : "border-gray-700 text-gray-400 hover:border-white hover:text-white"
          }`}
        >
          {muted ? "🔇 Muted" : "🔊 Audio"}
        </button>

        <button
          onClick={endSession}
          className="px-6 py-3 rounded-lg border border-red-800 text-red-500 hover:border-red-500 transition text-sm"
        >
          ⏹ End
        </button>
      </div>

    </div>
  )
}