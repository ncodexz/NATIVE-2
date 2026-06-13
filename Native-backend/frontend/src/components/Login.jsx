import { useState } from "react"
import axios from "axios"

const API = "http://localhost:8000"

export default function Login({ onLogin }) {
  const [name, setName] = useState("")
  const [password, setPassword] = useState("")
  const [isRegister, setIsRegister] = useState(false)
  const [error, setError] = useState("")
  const [loading, setLoading] = useState(false)

  async function handleSubmit(e) {
    e.preventDefault()
    setLoading(true)
    setError("")

    try {
      if (isRegister) {
        await axios.post(`${API}/register`, { name, password })
      }

      const form = new FormData()
      form.append("username", name)
      form.append("password", password)

      const res = await axios.post(`${API}/token`, form)
      onLogin(res.data.access_token, name)

    } catch (err) {
      setError(err.response?.data?.detail || "Something went wrong")
    } finally {
      setLoading(false)
    }
  }

  return (
    <div className="min-h-screen bg-black flex items-center justify-center">
      <div className="w-full max-w-md p-8">
        
        {/* Logo */}
        <div className="text-center mb-12">
          <h1 className="text-5xl font-bold text-white tracking-widest">NATIVE</h1>
          <p className="text-gray-500 mt-2 text-sm tracking-wider">English Coach — 2.0</p>
        </div>

        {/* Form */}
        <form onSubmit={handleSubmit} className="space-y-4">
          <input
            type="text"
            placeholder="Name"
            value={name}
            onChange={e => setName(e.target.value)}
            className="w-full bg-transparent border border-gray-700 text-white px-4 py-3 rounded-lg focus:outline-none focus:border-white transition"
            required
          />
          <input
            type="password"
            placeholder="Password"
            value={password}
            onChange={e => setPassword(e.target.value)}
            className="w-full bg-transparent border border-gray-700 text-white px-4 py-3 rounded-lg focus:outline-none focus:border-white transition"
            required
          />

          {error && (
            <p className="text-red-400 text-sm text-center">{error}</p>
          )}

          <button
            type="submit"
            disabled={loading}
            className="w-full bg-white text-black py-3 rounded-lg font-semibold hover:bg-gray-200 transition disabled:opacity-50"
          >
            {loading ? "..." : isRegister ? "Create Account" : "Sign In"}
          </button>
        </form>

        {/* Toggle */}
        <p className="text-center text-gray-600 mt-6 text-sm">
          {isRegister ? "Already have an account?" : "New here?"}{" "}
          <button
            onClick={() => setIsRegister(!isRegister)}
            className="text-gray-400 hover:text-white transition"
          >
            {isRegister ? "Sign In" : "Create Account"}
          </button>
        </p>

      </div>
    </div>
  )
}