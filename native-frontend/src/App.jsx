import { useState } from "react"
import Login from "./components/Login"
import Session from "./components/Session"

export default function App() {
  const [token, setToken] = useState(null)
  const [user, setUser] = useState(null)

  return (
    <div className="relative">
      <img 
        src="/logos.png" 
        alt="ncodexz" 
        className="fixed bottom-4 right-4 w-40 h-40 opacity-50 z-50"
      />
      {!token 
        ? <Login onLogin={(t, u) => { setToken(t); setUser(u) }} />
        : <Session token={token} user={user} onLogout={() => { setToken(null); setUser(null) }} />
      }
    </div>
  )
}