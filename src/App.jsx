import { Scene } from './components/canvas/Scene';

function App() {
  return (
    <div className="relative h-screen w-screen overflow-hidden bg-[#010204] text-cyan-300">
      <div className="pointer-events-auto h-screen w-full">
        <Scene />
      </div>

      <div className="pointer-events-none absolute left-4 top-4 z-10 rounded border border-cyan-400/40 bg-slate-950/30 px-4 py-2 shadow-[0_0_25px_rgba(0,240,255,0.25)] backdrop-blur-sm">
        <div className="font-mono text-[10px] uppercase tracking-[0.45em] text-cyan-300/80">
          CYBER_PORTFOLIO v1.0 // SYSTEM ONLINE
        </div>
      </div>
    </div>
  );
}

export default App;
