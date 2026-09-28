import { Html } from '@react-three/drei';

export function CanvasLoader() {
  return (
    <Html center>
      <div className="pointer-events-none select-none whitespace-nowrap font-mono text-xs uppercase tracking-[0.35em] text-cyan-300">
        Loading Cyber-City...
      </div>
    </Html>
  );
}
