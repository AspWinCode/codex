import { useEffect, useRef, useState } from 'react';
import './CaseIntro.css';

type Stage = 'access' | 'folder' | 'spread' | 'rita' | 'cctv' | 'anna' | 'cta';

const ACCESS_LINES = [
  'KODEX AGENCY // SECURE TERMINAL v4.1',
  'ИДЕНТИФИКАЦИЯ АГЕНТА...',
  'УРОВЕНЬ ДОСТУПА: ▓▓ СТАЖЁР',
  'ПОДКЛЮЧЕНИЕ К БАЗЕ ДЕЛ...',
];

const RITA_LINES = [
  'Агент.',
  'Сегодня утром поступило сообщение о крупной недостаче.',
  'Камеры ничего не показали.',
  'Но система учёта ведёт себя странно.',
  'Виктор считает — это не обычная кража.',
];

const ANNA_LINES = [
  'Я уже просмотрела журнал операций.',
  'Проблема не в товарах.',
  'Проблема в данных.',
  'Кто-то изменил записи.',
  'Нам нужно восстановить исходную информацию.',
  'Без анализа данных мы не сможем продолжить расследование.',
];

function sleep(ms: number): Promise<void> {
  return new Promise((r) => setTimeout(r, ms));
}

function useTypewriter(lines: string[], active: boolean) {
  const [idx, setIdx] = useState(0);
  const [chars, setChars] = useState(0);
  const [displayed, setDisplayed] = useState<string[]>([]);

  useEffect(() => {
    if (!active) {
      setIdx(0);
      setChars(0);
      setDisplayed([]);
    }
  }, [active]);

  useEffect(() => {
    if (!active || idx >= lines.length) return;
    const line = lines[idx];
    if (chars <= line.length) {
      const t = setTimeout(() => {
        setDisplayed((prev) => {
          const next = [...prev];
          next[idx] = line.slice(0, chars);
          return next;
        });
        setChars((c) => c + 1);
      }, 26 + Math.random() * 12);
      return () => clearTimeout(t);
    } else {
      const t = setTimeout(() => {
        setIdx((i) => i + 1);
        setChars(0);
      }, 320);
      return () => clearTimeout(t);
    }
  }, [active, idx, chars, lines]);

  return { displayed, done: idx >= lines.length };
}

export default function CaseIntro({
  agentName,
  onComplete,
}: {
  agentName: string;
  onComplete: () => void;
}) {
  const [stage, setStage] = useState<Stage>('access');

  // ACCESS state
  const [accessLines, setAccessLines] = useState<string[]>([]);
  const [barPct, setBarPct] = useState(0);
  const [accessGranted, setAccessGranted] = useState(false);

  // Spread state
  const [docsVisible, setDocsVisible] = useState(false);

  // CCTV
  const [cctvLines, setCctvLines] = useState<string[]>([]);
  const cctvRef = useRef<HTMLCanvasElement>(null);
  const cctvRafRef = useRef<number | null>(null);

  // Character typewriters
  const { displayed: ritaText, done: ritaDone } = useTypewriter(RITA_LINES, stage === 'rita');
  const { displayed: annaText, done: annaDone } = useTypewriter(ANNA_LINES, stage === 'anna');

  const [fading, setFading] = useState(false);

  // ── ACCESS animation ──────────────────────────────────────────────────────
  useEffect(() => {
    if (stage !== 'access') return;
    let cancelled = false;

    async function run() {
      for (let i = 0; i < ACCESS_LINES.length; i++) {
        if (cancelled) return;
        await sleep(500 + i * 420);
        setAccessLines((p) => [...p, ACCESS_LINES[i]]);
      }
      if (cancelled) return;
      await sleep(700);
      for (let p = 0; p <= 20; p++) {
        if (cancelled) return;
        setBarPct(p);
        await sleep(60);
      }
      if (cancelled) return;
      await sleep(500);
      setAccessGranted(true);
      await sleep(1800);
      if (!cancelled) setStage('folder');
    }

    run();
    return () => { cancelled = true; };
  }, [stage]);

  // ── SPREAD → RITA auto-advance ─────────────────────────────────────────────
  useEffect(() => {
    if (stage !== 'spread') return;
    const t1 = setTimeout(() => setDocsVisible(true), 80);
    const t2 = setTimeout(() => setStage('rita'), 2800);
    return () => { clearTimeout(t1); clearTimeout(t2); };
  }, [stage]);

  // ── CCTV canvas ───────────────────────────────────────────────────────────
  useEffect(() => {
    if (stage !== 'cctv') return;
    const canvas = cctvRef.current;
    if (!canvas) return;
    const ctx = canvas.getContext('2d');
    if (!ctx) return;

    const rect = canvas.getBoundingClientRect();
    canvas.width = rect.width || 340;
    canvas.height = rect.height || 220;

    let frame = 0;
    function draw() {
      const w = canvas!.width;
      const h = canvas!.height;
      frame++;

      const img = ctx!.createImageData(w, h);
      const d = img.data;
      for (let i = 0; i < d.length; i += 4) {
        const v = Math.random() > 0.93 ? Math.random() * 180 : Math.random() * 20;
        d[i] = v; d[i + 1] = v; d[i + 2] = v * 0.78; d[i + 3] = 255;
      }
      ctx!.putImageData(img, 0, 0);

      // Scanlines
      ctx!.fillStyle = 'rgba(0,0,0,0.28)';
      for (let y = 0; y < h; y += 3) ctx!.fillRect(0, y, w, 1);

      // Horizontal glitch
      if (frame % 42 < 3) {
        const gy = Math.random() * h;
        const gh = 3 + Math.random() * 12;
        const gx = (Math.random() - 0.5) * 32;
        ctx!.drawImage(canvas!, 0, gy, w, gh, gx, gy, w, gh);
      }

      // Vignette
      const grad = ctx!.createRadialGradient(w / 2, h / 2, h * 0.12, w / 2, h / 2, h * 0.78);
      grad.addColorStop(0, 'rgba(0,0,0,0)');
      grad.addColorStop(1, 'rgba(0,0,0,0.7)');
      ctx!.fillStyle = grad;
      ctx!.fillRect(0, 0, w, h);

      cctvRafRef.current = requestAnimationFrame(draw);
    }
    cctvRafRef.current = requestAnimationFrame(draw);
    return () => { if (cctvRafRef.current) cancelAnimationFrame(cctvRafRef.current); };
  }, [stage]);

  // ── CCTV text → ANNA ──────────────────────────────────────────────────────
  useEffect(() => {
    if (stage !== 'cctv') return;
    let cancelled = false;
    const lines = [
      'CAM 03  ·  СКЛАД А  ·  07:18',
      '● REC',
      'SIGNAL LOST',
      'ERROR 0x4F2A — FRAME MISSING',
      'LOG FILE CORRUPTED',
    ];
    async function run() {
      for (const line of lines) {
        if (cancelled) return;
        await sleep(750);
        setCctvLines((p) => [...p, line]);
      }
      if (cancelled) return;
      await sleep(1500);
      setStage('anna');
    }
    run();
    return () => { cancelled = true; };
  }, [stage]);

  const name = (agentName || 'НЕИЗВЕСТЕН').toUpperCase();

  const handleOpenFolder = () => setStage('spread');
  const handleRitaContinue = () => { setCctvLines([]); setStage('cctv'); };
  const handleAnnaNext = () => setStage('cta');
  const handleComplete = () => {
    setFading(true);
    setTimeout(() => onComplete(), 1300);
  };

  const showDocs = ['spread', 'rita', 'cctv', 'anna', 'cta'].includes(stage);

  return (
    <div className="ci-root">

      {/* ── 1. ACCESS LEVEL SCREEN ── */}
      <div className={`ci-access ${stage !== 'access' ? 'ci-access-exit' : ''}`}>
        <div className="ci-access-inner">
          <div className="ci-access-logo">
            <svg viewBox="0 0 24 24" fill="none" strokeWidth={1.4} strokeLinecap="round" strokeLinejoin="round">
              <circle cx="11" cy="11" r="7" />
              <path d="M21 21l-4.3-4.3" />
            </svg>
          </div>
          <div className="ci-access-lines">
            {accessLines.map((l, i) => (
              <div key={i} className="ci-access-line">{l}</div>
            ))}
          </div>
          {accessLines.length === ACCESS_LINES.length && (
            <div className="ci-bar-row">
              <div className="ci-bar">
                {Array.from({ length: 20 }, (_, i) => (
                  <span key={i} className={i < barPct ? 'ci-bar-on' : 'ci-bar-off'}>
                    {i < barPct ? '█' : '░'}
                  </span>
                ))}
              </div>
              <span className="ci-bar-pct">{Math.round(barPct * 5)}%</span>
            </div>
          )}
          {accessGranted && <div className="ci-granted">✓&nbsp;&nbsp;ACCESS GRANTED</div>}
        </div>
      </div>

      {/* ── DESK (stages 2–7) ── */}
      {stage !== 'access' && (
        <div className="ci-desk">

          {/* Scattered documents */}
          <div className={`ci-docs ${showDocs && docsVisible ? 'ci-docs-in' : ''}`}>
            <div className="ci-doc ci-doc-photo">
              <div className="ci-photo-inner">
                <svg viewBox="0 0 24 24" fill="none" strokeWidth={1.1} strokeLinecap="round" strokeLinejoin="round">
                  <rect x="2" y="3" width="20" height="14" rx="2" />
                  <circle cx="8.5" cy="9.5" r="1.5" />
                  <path d="M21 17l-5-5L7 21" />
                </svg>
                <span>СКЛАД А · CAM 03 · 07:17</span>
                <span className="ci-photo-tag">SIGNAL LOST</span>
              </div>
            </div>

            <div className="ci-doc ci-doc-report">
              <div className="ci-doc-head">СЛУЖЕБНЫЙ РАПОРТ</div>
              <div className="ci-doc-body">
                <p>Дата: <b>14.06.2026</b></p>
                <p>Недостача: <b>847 позиций</b></p>
                <p>Сумма: <b>1&nbsp;243&nbsp;800 ₽</b></p>
                <p>Обнаружил: <b>Петров И.А.</b></p>
                <p>Статус: <span className="ci-red">НЕ ОБЪЯСНЕНО</span></p>
              </div>
            </div>

            <div className="ci-doc ci-doc-map">
              <div className="ci-doc-head">ПЛАН — СКЛАД А</div>
              <div className="ci-map-grid">
                {Array.from({ length: 15 }, (_, i) => (
                  <div key={i} className={`ci-shelf ${[3, 7, 11].includes(i) ? 'ci-shelf-hot' : ''}`} />
                ))}
              </div>
              <div className="ci-map-note">▲ A3, B7, C11 — аномалия</div>
            </div>

            <div className="ci-doc ci-doc-receipt">
              <div className="ci-doc-head">НАКЛАДНАЯ №4891</div>
              <div className="ci-doc-body">
                <div className="ci-row"><span>Паллета P-2241</span><span>✓</span></div>
                <div className="ci-row"><span>Паллета P-2242</span><span>—</span></div>
                <div className="ci-row"><span>Короб K-5571</span><span>✓</span></div>
                <div className="ci-row ci-red"><span>Короб K-5572</span><span>???</span></div>
                <div className="ci-row ci-red"><span>Короб K-5573</span><span>???</span></div>
              </div>
            </div>

            <div className="ci-doc ci-doc-log">
              <div className="ci-doc-head">SYSTEM LOG · 2026-06-14</div>
              <div className="ci-doc-body ci-mono-sm">
                <p>07:12 · сотр. 0441 · ВХОД</p>
                <p>07:14 · скан. P-2241 · OK</p>
                <p className="ci-red">07:16 · ЗАПИСЬ ИЗМЕНЕНА</p>
                <p className="ci-red">07:18 · CAM03 · ERR</p>
                <p>07:24 · сотр. 0441 · ВЫХОД</p>
              </div>
            </div>
          </div>

          {/* ── 2. FOLDER ── */}
          {stage === 'folder' && (
            <div className="ci-folder-wrap">
              <div className="ci-folder" onClick={handleOpenFolder}>
                <div className="ci-folder-tab" />
                <div className="ci-folder-body">
                  <div className="ci-stamp-red">КОНФИДЕН-<br />ЦИАЛЬНО</div>
                  <div className="ci-case-num">ДЕЛО №001</div>
                  <div className="ci-case-title">ОГРАБЛЕНИЕ<br />СКЛАДА</div>
                  <div className="ci-wax-seal"><span>КОДЭКС</span></div>
                  <div className="ci-folder-meta">
                    <div className="ci-meta-row"><span>Статус</span><span>Не расследовано</span></div>
                    <div className="ci-meta-row ci-meta-hi"><span>Приоритет</span><span>⚡ Высокий</span></div>
                    <div className="ci-meta-row"><span>Агент</span><span>{name}</span></div>
                  </div>
                  <div className="ci-folder-hint">↑ нажмите, чтобы открыть</div>
                </div>
              </div>
            </div>
          )}

          {/* ── 5. CCTV ── */}
          {stage === 'cctv' && (
            <div className="ci-cctv">
              <canvas ref={cctvRef} className="ci-cctv-canvas" />
              <div className="ci-cctv-scanlines" />
              <div className="ci-cctv-overlay">
                {cctvLines.map((l, i) => (
                  <div key={i} className={`ci-cctv-line ${l.includes('ERROR') || l.includes('CORRUPTED') || l.includes('LOST') ? 'ci-cctv-err' : ''}`}>
                    {l}
                  </div>
                ))}
              </div>
            </div>
          )}

          {/* ── 4. RITA ── */}
          {stage === 'rita' && (
            <div className="ci-card ci-card-right ci-card-in">
              <div className="ci-card-head">
                <div className="ci-avatar ci-avatar-green">
                  <svg viewBox="0 0 48 48" fill="none">
                    <circle cx="24" cy="17" r="10" fill="rgba(0,255,171,0.1)" stroke="rgba(0,255,171,0.4)" strokeWidth="1.5" />
                    <path d="M6 47c0-9.9 8.1-18 18-18s18 8.1 18 18" fill="rgba(0,255,171,0.07)" stroke="rgba(0,255,171,0.35)" strokeWidth="1.5" />
                  </svg>
                </div>
                <div>
                  <div className="ci-char-name">РИТА</div>
                  <div className="ci-char-role">Оперативник агентства</div>
                </div>
              </div>
              <div className="ci-speech">
                {ritaText.map((line, i) => line !== undefined && <p key={i}>{line}</p>)}
                {ritaDone && (
                  <button className="ci-speech-btn" onClick={handleRitaContinue}>
                    Продолжить →
                  </button>
                )}
              </div>
            </div>
          )}

          {/* ── 6. ANNA ── */}
          {(stage === 'anna' || stage === 'cta') && (
            <div className="ci-card ci-card-left ci-card-in">
              <div className="ci-card-head">
                <div className="ci-avatar ci-avatar-cyan">
                  <svg viewBox="0 0 48 48" fill="none">
                    <circle cx="24" cy="17" r="10" fill="rgba(53,199,255,0.1)" stroke="rgba(53,199,255,0.4)" strokeWidth="1.5" />
                    <path d="M6 47c0-9.9 8.1-18 18-18s18 8.1 18 18" fill="rgba(53,199,255,0.07)" stroke="rgba(53,199,255,0.35)" strokeWidth="1.5" />
                  </svg>
                </div>
                <div>
                  <div className="ci-char-name ci-anna-name">АННА ЛОГ</div>
                  <div className="ci-char-role ci-anna-role">Старший аналитик данных</div>
                </div>
              </div>
              {stage === 'anna' && (
                <div className="ci-speech">
                  {annaText.map((line, i) => line !== undefined && <p key={i}>{line}</p>)}
                  {annaDone && (
                    <button className="ci-speech-btn ci-anna-btn" onClick={handleAnnaNext}>
                      Понял →
                    </button>
                  )}
                </div>
              )}
            </div>
          )}

          {/* ── 7. CTA ── */}
          {stage === 'cta' && (
            <div className="ci-cta">
              <button className="ci-cta-btn" onClick={handleComplete}>
                <svg viewBox="0 0 24 24" fill="none" strokeWidth={1.6} strokeLinecap="round" strokeLinejoin="round">
                  <path d="M14 2H6a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V8z" />
                  <path d="M14 2v6h6" />
                  <line x1="16" y1="13" x2="8" y2="13" />
                  <line x1="16" y1="17" x2="8" y2="17" />
                </svg>
                Открыть материалы аналитика
              </button>
            </div>
          )}
        </div>
      )}

      {fading && <div className="ci-fade" />}
    </div>
  );
}
