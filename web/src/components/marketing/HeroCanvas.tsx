"use client";

/**
 * HeroCanvas — a subtle, premium 3D data-orb for the landing hero (docs/07 §0, §8).
 *
 * Evidence-led, not hype: a slow, calm rotating icosahedron ("the market as structure")
 * with a wireframe shell and an orbiting particle field, in the brand indigo + AI violet.
 * No spinning logos, no urgency. Loaded client-only (ssr:false) and only when motion is
 * allowed — the caller renders a static gradient fallback for `prefers-reduced-motion`.
 */

import { Canvas, useFrame } from "@react-three/fiber";
import { Float, Icosahedron, MeshDistortMaterial, PointMaterial, Points } from "@react-three/drei";
import { useMemo, useRef } from "react";
import type { Mesh, Points as ThreePoints } from "three";

function DataOrb() {
  const core = useRef<Mesh>(null);
  useFrame((_, dt) => {
    if (core.current) core.current.rotation.y += dt * 0.12;
  });
  return (
    <Float speed={1.1} rotationIntensity={0.35} floatIntensity={0.5}>
      <Icosahedron ref={core} args={[1.55, 5]}>
        <MeshDistortMaterial
          color="#5B8DEF"
          emissive="#2b4a8f"
          emissiveIntensity={0.35}
          roughness={0.32}
          metalness={0.55}
          distort={0.26}
          speed={1.3}
        />
      </Icosahedron>
      {/* Wireframe shell — the "evidence lattice" */}
      <Icosahedron args={[1.62, 2]}>
        <meshBasicMaterial color="#9A7BFF" wireframe transparent opacity={0.18} />
      </Icosahedron>
    </Float>
  );
}

function ParticleField() {
  const positions = useMemo(() => {
    const count = 900;
    const arr = new Float32Array(count * 3);
    for (let i = 0; i < count; i++) {
      const r = 3.2 + Math.random() * 3.2;
      const theta = Math.random() * Math.PI * 2;
      const phi = Math.acos(2 * Math.random() - 1);
      arr[i * 3] = r * Math.sin(phi) * Math.cos(theta);
      arr[i * 3 + 1] = r * Math.sin(phi) * Math.sin(theta);
      arr[i * 3 + 2] = r * Math.cos(phi);
    }
    return arr;
  }, []);
  const ref = useRef<ThreePoints>(null);
  useFrame((_, dt) => {
    if (ref.current) ref.current.rotation.y -= dt * 0.025;
  });
  return (
    <Points ref={ref} positions={positions} stride={3} frustumCulled={false}>
      <PointMaterial
        color="#5B8DEF"
        size={0.02}
        sizeAttenuation
        transparent
        opacity={0.55}
        depthWrite={false}
      />
    </Points>
  );
}

export default function HeroCanvas() {
  return (
    <Canvas
      camera={{ position: [0, 0, 5], fov: 45 }}
      dpr={[1, 1.5]}
      gl={{ antialias: true, alpha: true }}
      style={{ pointerEvents: "none" }}
    >
      <ambientLight intensity={0.55} />
      <directionalLight position={[3, 3, 3]} intensity={1.1} />
      <pointLight position={[-3, -2, -2]} intensity={2.2} color="#9A7BFF" />
      <DataOrb />
      <ParticleField />
    </Canvas>
  );
}
