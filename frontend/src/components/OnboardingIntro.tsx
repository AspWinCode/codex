import { useEffect, useRef, useState } from 'react';
import './OnboardingIntro.css';

const TERMINAL_LINES = [
  'encrypted connection...',
  'decoding...',
  'authentication...',
  'secure channel established.',
];

type Stage = 'terminal' | 'letter' | 'form' | 'welcome';

interface RainHandle {
  stop: () => void;
  setMuted: (m: boolean) => void;
}

function startRainAudio(): RainHandle | null {
  let audioCtx: AudioContext | null = null;
  let masterGain: GainNode | null = null;

  try {
    audioCtx = new (window.AudioContext || (window as any).webkitAudioContext)();

    const sr = audioCtx.sampleRate;
    const buf = audioCtx.createBuffer(1, sr * 3, sr);
    const data = buf.getChannelData(0);
    for (let i = 0; i < data.length; i++) data[i] = Math.random() * 2 - 1;

    const src = audioCtx.createBufferSource();
    src.buffer = buf;
    src.loop = true;

    const hp = audioCtx.createBiquadFilter();
    hp.type = 'highpass';
    hp.frequency.value = 300;
    hp.Q.value = 0.3;

    const lp = audioCtx.createBiquadFilter();
    lp.type = 'lowpass';
    lp.frequency.value = 1400;
    lp.Q.value = 0.4;

    masterGain = audioCtx.createGain();
    masterGain.gain.setValueAtTime(0, audioCtx.currentTime);
    masterGain.gain.linearRampToValueAtTime(0.22, audioCtx.currentTime + 3);

    src.connect(hp);
    hp.connect(lp);
    lp.connect(masterGain);
    masterGain.connect(audioCtx.destination);
    src.start();
  } catch {
    return null;
  }

  const g = masterGain!;
  const ctx = audioCtx!;

  return {
    stop() {
      try {
        const t = ctx.currentTime;
        g.gain.cancelScheduledValues(t);
        g.gain.setValueAtTime(g.gain.value, t);
        g.gain.linearRampToValueAtTime(0, t + 1.5);
        setTimeout(() => ctx.close().catch(() => {}), 1700);
      } catch {}
    },
    setMuted(m: boolean) {
      try {
        const t = ctx.currentTime;
        g.gain.cancelScheduledValues(t);
        g.gain.setValueAtTime(g.gain.value, t);
        g.gain.linearRampToValueAtTime(m ? 0 : 0.22, t + 0.4);
      } catch {}
    },
  };
}

export default function OnboardingIntro({ onComplete }: { onComplete: (agentName: string) => void }) {
  const [stage, setStage] = useState<Stage>('terminal');
  const [typedLines, setTypedLines] = useState<string[]>(['', '', '', '']);
  const [showCursor, setShowCursor] = useState(true);
  const [name, setName] = useState('');
  const [focused, setFocused] = useState(false);
  const [creating, setCreating] = useState(false);
  const [fading, setFading] = useState(false);
  const [muted, setMuted] = useState(false);

  const canvasRef = useRef<HTMLCanvasElement>(null);
  const sceneRef = useRef<HTMLDivElement>(null);
  const inputRef = useRef<HTMLInputElement>(null);
  const rafRef = useRef<number | null>(null);
  const rainRef = useRef<RainHandle | null>(null);

  // Canvas rain animation
  useEffect(() => {
    const canvas = canvasRef.current;
    if (!canvas) return;
    const ctx = canvas.getContext('2d');
    if (!ctx) return;

    function resize() {
      if (!canvas) return;
      canvas.width = window.innerWidth;
      canvas.height = window.innerHeight;
    }
    resize();
    window.addEventListener('resize', resize);

    function makeDrop() {
      return {
        x: Math.random() * canvas!.width,
        y: Math.random() * canvas!.height,
        len: 14 + Math.random() * 26,
        speed: 5 + Math.random() * 9,
        drift: -1.4 + Math.random() * 0.6,
        opacity: 0.06 + Math.random() * 0.16,
        hue: Math.random() > 0.7 ? '53,199,255' : '0,255,171',
      };
    }

    const drops = Array.from({ length: 160 }, makeDrop);

    function tick() {
      if (!ctx || !canvas) return;
      ctx.clearRect(0, 0, canvas.width, canvas.height);
      for (const d of drops) {
        ctx.strokeStyle = `rgba(${d.hue},${d.opacity})`;
        ctx.lineWidth = 1;
        ctx.beginPath();
        ctx.moveTo(d.x, d.y);
        ctx.lineTo(d.x + d.drift * 2, d.y + d.len);
        ctx.stroke();
        d.y += d.speed;
        d.x += d.drift;
        if (d.y > canvas.height) {
          d.y = -d.len;
          d.x = Math.random() * canvas.width;
        }
      }
      rafRef.current = requestAnimationFrame(tick);
    }
    rafRef.current = requestAnimationFrame(tick);

    return () => {
      window.removeEventListener('resize', resize);
      if (rafRef.current) cancelAnimationFrame(rafRef.current);
    };
  }, []);

  // Mouse parallax
  useEffect(() => {
    function handleMove(e: MouseEvent) {
      if (!sceneRef.current) return;
      const x = (e.clientX / window.innerWidth - 0.5) * 18;
      const y = (e.clientY / window.innerHeight - 0.5) * 12;
      sceneRef.current.style.transform = `translate(${x}px,${y}px)`;
    }
    window.addEventListener('mousemove', handleMove);
    return () => window.removeEventListener('mousemove', handleMove);
  }, []);

  // Typewriter
  useEffect(() => {
    let cancelled = false;
    let lineIndex = 0;
    let charIndex = 0;

    function typeNext() {
      if (cancelled) return;
      if (lineIndex >= TERMINAL_LINES.length) {
        setShowCursor(false);
        setTimeout(() => {
          if (!cancelled) setStage('letter');
        }, 900);
        return;
      }
      const line = TERMINAL_LINES[lineIndex];
      if (charIndex <= line.length) {
        setTypedLines((prev) => {
          const next = [...prev];
          next[lineIndex] = line.slice(0, charIndex);
          return next;
        });
        charIndex++;
        setTimeout(typeNext, 30 + Math.random() * 12);
      } else {
        lineIndex++;
        charIndex = 0;
        setTimeout(typeNext, 260);
      }
    }

    const startTimeout = setTimeout(typeNext, 900);
    return () => {
      cancelled = true;
      clearTimeout(startTimeout);
    };
  }, []);

  // Stop audio on unmount
  useEffect(() => {
    return () => { rainRef.current?.stop(); };
  }, []);

  const handleAccept = () => {
    // First user gesture — safe to start AudioContext
    if (!rainRef.current) {
      rainRef.current = startRainAudio();
    }
    setStage('form');
    setTimeout(() => inputRef.current?.focus(), 700);
  };

  const handleCreate = () => {
    const trimmed = name.trim();
    if (!trimmed) return;
    setCreating(true);
    setTimeout(() => setStage('welcome'), 1300);
  };

  const handleEnter = () => {
    setFading(true);
    rainRef.current?.stop();
    setTimeout(() => onComplete(name.trim()), 1100);
  };

  const handleToggleMute = () => {
    setMuted((prev) => {
      const next = !prev;
      rainRef.current?.setMuted(next);
      return next;
    });
  };

  return (
    <div className="kx-root">
      <canvas ref={canvasRef} className="kx-rain" />
      <div ref={sceneRef} className="kx-scene">
        <div className="kx-city" />
        <div className="kx-skyline" />
        <div className="kx-windows" />
        <div className="kx-fog" />
      </div>
      <div className="kx-grain" />
      <div className="kx-scanline" />
      <div className="kx-vignette" />

      {stage !== 'terminal' && (
        <button
          className={`kx-sound-btn ${muted ? 'kx-muted' : ''}`}
          onClick={handleToggleMute}
          title={muted ? 'Включить звук' : 'Выключить звук'}
        >
          {muted ? (
            <svg viewBox="0 0 24 24" fill="none" strokeWidth={1.8} strokeLinecap="round" strokeLinejoin="round">
              <polygon points="11 5 6 9 2 9 2 15 6 15 11 19 11 5" />
              <line x1="23" y1="9" x2="17" y2="15" />
              <line x1="17" y1="9" x2="23" y2="15" />
            </svg>
          ) : (
            <svg viewBox="0 0 24 24" fill="none" strokeWidth={1.8} strokeLinecap="round" strokeLinejoin="round">
              <polygon points="11 5 6 9 2 9 2 15 6 15 11 19 11 5" />
              <path d="M19.07 4.93a10 10 0 0 1 0 14.14" />
              <path d="M15.54 8.46a5 5 0 0 1 0 7.07" />
            </svg>
          )}
        </button>
      )}

      <div className="kx-stage">
        <div className="kx-brand">
          <div className="kx-brand-mark">
            <svg viewBox="0 0 24 24" fill="none" strokeWidth={1.6} strokeLinecap="round" strokeLinejoin="round">
              <circle cx="11" cy="11" r="7" />
              <path d="M21 21l-4.3-4.3" />
            </svg>
          </div>
          <div className="kx-brand-title">КОДЭКС</div>
          <div className="kx-brand-sub">Агентство цифровых расследований</div>
        </div>

        <div className="kx-center-column">
          <div className={`kx-panel kx-terminal ${stage === 'terminal' ? 'kx-active' : ''}`}>
            {TERMINAL_LINES.map((_, i) => (
              <div key={i} className={`kx-term-line ${typedLines[i] ? 'kx-shown' : ''}`}>
                <span className="kx-term-prefix">&gt; </span>
                <span>{typedLines[i]}</span>
                {i === TERMINAL_LINES.length - 1 && showCursor && <span className="kx-cursor" />}
              </div>
            ))}
          </div>

          <div className={`kx-panel kx-letter ${stage === 'letter' ? 'kx-active' : ''}`}>
            <div className="kx-letter-seal">В.К.</div>
            <div className="kx-letter-body">
              <p>Агент.</p>
              <p>Если ты читаешь это сообщение —</p>
              <p>значит мы нашли тебя раньше,</p>
              <p>чем это сделал Хаос.</p>
              <p>Нам нужны люди, умеющие замечать детали,</p>
              <p>искать закономерности и мыслить как следователь.</p>
              <p>Если ты готов — добро пожаловать.</p>
            </div>
            <div className="kx-letter-sign">— Виктор Кодэкс, директор агентства</div>
            <div className="kx-btn-row">
              <button className="kx-btn-primary" onClick={handleAccept}>Принять приглашение</button>
            </div>
          </div>

          <div className={`kx-panel kx-form-panel ${stage === 'form' ? 'kx-active' : ''}`}>
            <div className="kx-form-question">Как тебя зовут, агент?</div>
            <div className={`kx-input-line ${focused ? 'kx-focused' : ''}`}>
              <span>&gt;</span>
              <input
                ref={inputRef}
                type="text"
                placeholder="введи имя агента"
                autoComplete="off"
                spellCheck={false}
                value={name}
                onChange={(e) => setName(e.target.value)}
                onFocus={() => setFocused(true)}
                onBlur={() => setFocused(false)}
                onKeyDown={(e) => {
                  if (e.key === 'Enter' && name.trim()) handleCreate();
                }}
              />
            </div>
            <button className="kx-btn-primary" disabled={!name.trim() || creating} onClick={handleCreate}>
              {creating ? 'Создание досье...' : 'Создать досье'}
            </button>
          </div>

          <div className={`kx-panel kx-welcome ${stage === 'welcome' ? 'kx-active' : ''}`}>
            <div className="kx-check-mark">✓</div>
            <div className="kx-welcome-line">Досье создано.</div>
            <div className="kx-welcome-line kx-name">Добро пожаловать, агент <span className="kx-name-out">{name.trim()}</span>.</div>
            <div className="kx-welcome-line">Первое дело уже лежит на вашем столе.</div>
            <div className="kx-btn-row kx-welcome-btn">
              <button className="kx-btn-primary" onClick={handleEnter}>Открыть дело №001</button>
            </div>
          </div>
        </div>
      </div>

      <div className={`kx-fade-screen ${fading ? 'kx-active' : ''}`} />
    </div>
  );
}
