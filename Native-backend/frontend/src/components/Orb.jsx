import { useRef, useMemo } from "react"
import { useFrame } from "@react-three/fiber"
import * as THREE from "three"

export default function Orb({ speaking = false, listening = false }) {
  const meshRef = useRef()
  const pointsRef = useRef()

  // Generate particle sphere
  const particles = useMemo(() => {
    const count = 2000
    const positions = new Float32Array(count * 3)

    for (let i = 0; i < count; i++) {
      const phi = Math.acos(-1 + (2 * i) / count)
      const theta = Math.sqrt(count * Math.PI) * phi

      positions[i * 3] = Math.cos(theta) * Math.sin(phi)
      positions[i * 3 + 1] = Math.sin(theta) * Math.sin(phi)
      positions[i * 3 + 2] = Math.cos(phi)
    }

    return positions
  }, [])

  // Animate the orb
  useFrame((state) => {
    if (!pointsRef.current) return

    const time = state.clock.elapsedTime

    // Rotate slowly
    pointsRef.current.rotation.y = time * 0.2
    pointsRef.current.rotation.x = time * 0.1

    // Pulse when speaking
    const scale = speaking
      ? 1 + Math.sin(time * 8) * 0.08
      : listening
      ? 1 + Math.sin(time * 3) * 0.03
      : 1 + Math.sin(time * 1.5) * 0.01

    pointsRef.current.scale.setScalar(scale)

    // Color shift
    const color = speaking
      ? new THREE.Color(0.3, 0.8, 1.0)   // blue when speaking
      : listening
      ? new THREE.Color(0.5, 1.0, 0.7)   // green when listening
      : new THREE.Color(0.6, 0.6, 0.8)   // default purple-gray

    pointsRef.current.material.color = color
  })

  return (
    <points ref={pointsRef}>
      <bufferGeometry>
        <bufferAttribute
          attach="attributes-position"
          args={[particles, 3]}
        />
      </bufferGeometry>
      <pointsMaterial
        size={0.015}
        color={new THREE.Color(0.6, 0.6, 0.8)}
        transparent
        opacity={0.8}
        sizeAttenuation
      />
    </points>
  )
}