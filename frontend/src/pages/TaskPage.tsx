import { useEffect, useRef, useState } from 'react';
import { Link, useParams } from 'react-router-dom';
import Editor, { OnMount } from '@monaco-editor/react';
import { tasksApi, gamificationApi } from '../api';
import type { TaskCourseContext, GamificationMe } from '../api';
import type { Verdict, SubmissionTestResult } from '../types';
import Markdown from '../components/Markdown';
import { useSubmissionWatcher } from '../features/task/hooks/useSubmissionWatcher';
import { useTaskData } from '../features/task/hooks/useTaskData';
import { useAuthStore } from '../store/auth';
import './LabPage.css';

// ── Verdict metadata ────────────────────────────────────────

const VERDICT_MAP: Record<Verdict, { label: string; color: string; short: string }> = {
  AC:  { label: 'Улика принята',           color: '#00E4AE', short: 'ПРИНЯТО'      },
  WA:  { label: 'Версия не подтвердилась', color: '#FF5454', short: 'ОПРОВЕРГНУТО' },
  RE:  { label: 'Ошибка исполнения',       color: '#FF5454', short: 'СБОЙ'         },
  TLE: { label: 'Лимит времени',           color: '#D8A53A', short: 'ТАЙМ-АУТ'    },
  MLE: { label: 'Лимит памяти',            color: '#D8A53A', short: 'ПАМЯТИ НЕТ'  },
  CE:  { label: 'Ошибка компиляции',       color: '#FF8C42', short: 'КОД: ОШИБКА' },
  PE:  { label: 'Формат вывода',           color: '#FF8C42', short: 'ФОРМАТ'       },
  IE:  { label: 'Внутренняя ошибка',       color: '#8AA39F', short: 'СИСТЕМНАЯ'    },
};

const ANNA_MESSAGES: Record<Verdict, string> = {
  AC:  'Данные верифицированы. Улика добавлена в досье дела.',
  WA:  'Версия не подтверждается. Пересмотри алгоритм.',
  RE:  'Программа завершилась аварийно. Проверь граничные случаи.',
  TLE: 'Слишком долго. Ищи более эффективный подход.',
  MLE: 'Превышен лимит памяти. Оптимизируй структуры данных.',
  CE:  'Код не компилируется. Проверь синтаксис.',
  PE:  'Неверный формат вывода. Проверь пробелы и переносы строк.',
  IE:  'Системная ошибка. Попробуй ещё раз.',
};

const ANNA_IDLE = 'Анализирую задание... Запусти тест, когда будешь готов.';

const RITA_MESSAGES = [
  'Помни — каждая деталь может оказаться ключевой уликой.',
  'Сначала разберись с простыми случаями, потом — с граничными.',
  'Если алгоритм кажется сложным, попробуй упростить модель.',
  'Хороший следователь проверяет свою теорию с разных сторон.',
  'Иногда правильное решение — это самое очевидное.',
];

function getRitaMsg(taskId?: string) {
  const idx = parseInt(taskId ?? '0', 10) % RITA_MESSAGES.length;
  return RITA_MESSAGES[isNaN(idx) ? 0 : idx];
}

// ── Timer hook ──────────────────────────────────────────────

function useTimer() {
  const [seconds, setSeconds] = useState(0);
  useEffect(() => {
    const id = setInterval(() => setSeconds((s) => s + 1), 1000);
    return () => clearInterval(id);
  }, []);
  const h = Math.floor(seconds / 3600);
  const m = Math.floor((seconds % 3600) / 60);
  const s = seconds % 60;
  return h > 0
    ? `${h}:${String(m).padStart(2, '0')}:${String(s).padStart(2, '0')}`
    : `${String(m).padStart(2, '0')}:${String(s).padStart(2, '0')}`;
}

// ── Kodex Monaco theme ──────────────────────────────────────

const KODEX_THEME_DATA = {
  base: 'vs-dark' as const,
  inherit: true,
  rules: [
    { token: 'comment',   foreground: '3d5a55', fontStyle: 'italic' },
    { token: 'keyword',   foreground: '1CCBFF', fontStyle: 'bold'   },
    { token: 'string',    foreground: '00E4AE'                       },
    { token: 'number',    foreground: 'D8A53A'                       },
    { token: 'type',      foreground: '1CCBFF'                       },
    { token: 'function',  foreground: 'E8F4F2'                       },
    { token: 'variable',  foreground: 'B8D8D4'                       },
    { token: 'operator',  foreground: '8AA39F'                       },
    { token: 'delimiter', foreground: '16343D'                       },
  ],
  colors: {
    'editor.background':                   '#091217',
    'editor.foreground':                   '#E8F4F2',
    'editor.lineHighlightBackground':      '#0B1820',
    'editorLineNumber.foreground':         '#213A42',
    'editorLineNumber.activeForeground':   '#00E4AE',
    'editor.selectionBackground':          '#00E4AE22',
    'editor.inactiveSelectionBackground':  '#00E4AE11',
    'editorCursor.foreground':             '#00E4AE',
    'editorIndentGuide.background1':       '#16343D',
    'editorIndentGuide.activeBackground1': '#00E4AE44',
    'scrollbarSlider.background':          '#16343D88',
    'scrollbarSlider.hoverBackground':     '#16343DBB',
    'editorGutter.background':             '#091217',
    'editor.findMatchBackground':          '#D8A53A33',
    'editor.findMatchHighlightBackground': '#D8A53A1A',
  },
};

// ── Inline lab editor ───────────────────────────────────────

interface LabEditorProps {
  value: string;
  onChange: (v: string) => void;
  language: string;
}

function LabEditor({ value, onChange, language }: LabEditorProps) {
  const handleMount: OnMount = (editor, monaco) => {
    monaco.editor.defineTheme('kodex', KODEX_THEME_DATA);
    monaco.editor.setTheme('kodex');
    editor.focus();
  };

  return (
    <Editor
      height="100%"
      language={language}
      value={value}
      onChange={(v) => onChange(v ?? '')}
      onMount={handleMount}
      options={{
        fontFamily: "'JetBrains Mono', 'Fira Code', 'Cascadia Code', monospace",
        fontSize: 13,
        lineHeight: 22,
        minimap: { enabled: false },
        scrollBeyondLastLine: false,
        renderLineHighlight: 'line',
        padding: { top: 16, bottom: 16 },
        scrollbar: { verticalScrollbarSize: 6, horizontalScrollbarSize: 6 },
        bracketPairColorization: { enabled: true },
        wordWrap: 'off',
        tabSize: 4,
        insertSpaces: true,
        smoothScrolling: true,
        cursorSmoothCaretAnimation: 'on',
        cursorBlinking: 'phase',
      }}
    />
  );
}

// ── Avatars ─────────────────────────────────────────────────

function AnnaAvatar({ size = 36 }: { size?: number }) {
  return (
    <svg width={size} height={size} viewBox="0 0 36 36" fill="none">
      <circle cx="18" cy="18" r="18" fill="#0B2030" />
      <circle cx="18" cy="14" r="6" fill="#1CCBFF" fillOpacity="0.15" stroke="#1CCBFF" strokeWidth="1.2" />
      <path d="M6 34c0-6.627 5.373-12 12-12s12 5.373 12 12" stroke="#1CCBFF" strokeWidth="1.2" strokeLinecap="round" />
      <circle cx="18" cy="14" r="3" fill="#1CCBFF" fillOpacity="0.35" />
      <rect x="14" y="4" width="8" height="4" rx="1" fill="#1CCBFF" fillOpacity="0.15" stroke="#1CCBFF" strokeWidth="1" />
    </svg>
  );
}

function AgentAvatar({ size = 44 }: { size?: number }) {
  return (
    <svg width={size} height={size} viewBox="0 0 44 44" fill="none">
      <circle cx="22" cy="22" r="22" fill="#071015" stroke="#16343D" strokeWidth="1" />
      <circle cx="22" cy="18" r="7" fill="#00E4AE" fillOpacity="0.1" stroke="#00E4AE" strokeWidth="1.2" />
      <path d="M8 42c0-7.732 6.268-14 14-14s14 6.268 14 14" stroke="#00E4AE" strokeWidth="1.2" strokeLinecap="round" />
      <circle cx="22" cy="18" r="3.5" fill="#00E4AE" fillOpacity="0.35" />
      <path d="M17 10h10M22 6v4" stroke="#00E4AE" strokeWidth="1" strokeLinecap="round" />
    </svg>
  );
}

// ── Clue overlay (AC first-time success) ─────────────────────

interface ClueOverlayProps {
  taskTitle: string;
  rewardCoins: number;
  onDismiss: () => void;
}

function ClueOverlay({ taskTitle, rewardCoins, onDismiss }: ClueOverlayProps) {
  return (
    <div className="lp-clue-overlay" onClick={onDismiss}>
      <div className="lp-clue-card" onClick={(e) => e.stopPropagation()}>
        <div className="lp-clue-header">
          <div className="lp-clue-line" />
          <span className="lp-clue-title">НОВАЯ УЛИКА</span>
          <div className="lp-clue-line" />
        </div>

        <div className="lp-clue-icon">
          <svg viewBox="0 0 24 24" fill="none" strokeWidth={1.6} strokeLinecap="round" strokeLinejoin="round">
            <path d="M9 12l2 2 4-4" />
            <circle cx="12" cy="12" r="10" />
          </svg>
        </div>

        <div className="lp-clue-name">{taskTitle}</div>
        <div className="lp-clue-desc">
          Улика верифицирована и добавлена в досье дела.<br />
          Анализ подтверждён системой экспертизы КОДЭКС.
        </div>

        <div className="lp-clue-anna">
          <div className="lp-clue-anna-avatar"><AnnaAvatar size={36} /></div>
          <div>
            <div className="lp-clue-anna-name">АННА ЛОГ · АНАЛИТИК</div>
            <div className="lp-clue-anna-text">
              <p>Данные верифицированы. Улика добавлена в досье дела. Продолжай работу, агент.</p>
            </div>
          </div>
        </div>

        <div className="lp-clue-rewards">
          {rewardCoins > 0 && (
            <div className="lp-reward">
              <span className="lp-reward-val">+{rewardCoins}</span>
              <span className="lp-reward-key">монет</span>
            </div>
          )}
          <div className="lp-reward">
            <span className="lp-reward-val lp-reward-blue">AC</span>
            <span className="lp-reward-key">верифицировано</span>
          </div>
        </div>

        <button className="lp-clue-btn" onClick={onDismiss}>
          Продолжить расследование
        </button>
      </div>
    </div>
  );
}

// ── Main page ────────────────────────────────────────────────

export default function TaskPage() {
  const { taskId } = useParams<{ taskId: string }>();
  const { user } = useAuthStore();

  const [courseContext, setCourseContext] = useState<TaskCourseContext[]>([]);
  const [gamification, setGamification] = useState<GamificationMe | null>(null);
  const [showClue, setShowClue] = useState(false);
  const [bottomOpen, setBottomOpen] = useState(false);

  const prevVerdictRef = useRef<Verdict | null>(null);
  const timer = useTimer();

  const {
    task, code, setCode, history, hints,
    loading, showHints, setShowHints,
    refreshHistory, refreshHints,
    draftSavedAt, clearDraft, hasDraft,
    unlockHint, unlockingHintId, hintError,
  } = useTaskData(taskId);

  const { submission, submitting, submitSolution } = useSubmissionWatcher({
    refreshHistory,
    refreshHints,
  });

  useEffect(() => {
    if (!taskId) return;
    tasksApi.getCourseContext(Number(taskId))
      .then(({ data }) => setCourseContext(data))
      .catch(() => {});
  }, [taskId]);

  useEffect(() => {
    gamificationApi.me().then(({ data }) => setGamification(data)).catch(() => {});
  }, []);

  useEffect(() => {
    if (!submission) return;
    if (submission.status === 'finished') {
      if (submission.verdict === 'AC' && prevVerdictRef.current !== 'AC') {
        setShowClue(true);
        gamificationApi.me().then(({ data }) => setGamification(data)).catch(() => {});
      }
      prevVerdictRef.current = submission.verdict;
      setBottomOpen(true);
    }
  }, [submission]);

  if (loading || !task) {
    return (
      <div className="lp-loading">
        <div className="lp-loading-spinner" />
        <div className="lp-loading-text">ЗАГРУЗКА МАТЕРИАЛОВ ДЕЛА...</div>
      </div>
    );
  }

  const langMap: Record<string, string> = {
    sql_query: 'sql',
    cpp_io: 'cpp',
    js_io: 'javascript',
    py_io: 'python',
  };
  const lang = langMap[task.task_type] ?? 'python';
  const caseNum = String(taskId ?? '001').padStart(3, '0');
  const publicTests = task.tests?.filter((t) => t.test_type === 'public') ?? [];

  const currentVerdict = submission?.status === 'finished' ? submission.verdict : null;
  const isRunning = submitting || submission?.status === 'queued' || submission?.status === 'running';
  const verdictMeta = currentVerdict ? VERDICT_MAP[currentVerdict] : null;
  const annaMsg = currentVerdict ? ANNA_MESSAGES[currentVerdict] : ANNA_IDLE;

  let dotClass = 'lp-dot-pulse';
  if (isRunning)                 dotClass = 'lp-dot-run';
  else if (currentVerdict === 'AC') dotClass = 'lp-dot-ac';
  else if (currentVerdict)          dotClass = 'lp-dot-wa';

  const firstCourse = courseContext[0];

  return (
    <div className="lp-root">

      {/* ── TOP BAR ── */}
      <div className="lp-topbar">
        <Link to="/tasks" className="lp-back">
          <svg viewBox="0 0 24 24" fill="none" strokeWidth={2} strokeLinecap="round" strokeLinejoin="round">
            <path d="M19 12H5M12 5l-7 7 7 7" />
          </svg>
          Дела
        </Link>
        <div className="lp-topbar-sep" />
        <div className="lp-topbar-title">
          <span className="lp-case-badge">ДЕЛО-{caseNum}</span>
          <span className="lp-topbar-name">{task.title}</span>
          {firstCourse && (
            <>
              <div className="lp-topbar-sep" />
              <Link to={`/course/${firstCourse.course_id}`} className="lp-course-link">
                {firstCourse.course_title}
                {firstCourse.node_title && ` › ${firstCourse.node_title}`}
              </Link>
            </>
          )}
        </div>
        <div className="lp-topbar-spacer" />
        <div className="lp-topbar-status">
          <span className={`lp-status-dot ${dotClass}`} />
        </div>
      </div>

      {/* ── BODY ── */}
      <div className="lp-body">

        {/* LEFT — ДОСЬЕ ДЕЛА */}
        <div className="lp-left">
          <div className="lp-left-header">
            <span className="lp-left-label">ДОСЬЕ ДЕЛА</span>
            <div className="lp-left-meta">
              <span className="lp-badge-muted">{task.task_type.toUpperCase()}</span>
            </div>
          </div>

          {/* Description */}
          {task.description && (
            <div className="lp-section">
              <div className="lp-section-title">
                <svg viewBox="0 0 24 24" fill="none" strokeWidth={1.8} strokeLinecap="round" strokeLinejoin="round">
                  <path d="M14 2H6a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V8z" />
                  <polyline points="14 2 14 8 20 8" />
                  <line x1="16" y1="13" x2="8" y2="13" />
                  <line x1="16" y1="17" x2="8" y2="17" />
                </svg>
                Описание
              </div>
              <div className="lp-markdown">
                <Markdown content={task.description} />
              </div>
            </div>
          )}

          {/* Public test examples */}
          {publicTests.length > 0 && (
            <div className="lp-section">
              <div className="lp-section-title">
                <svg viewBox="0 0 24 24" fill="none" strokeWidth={1.8} strokeLinecap="round" strokeLinejoin="round">
                  <rect x="3" y="3" width="7" height="7" />
                  <rect x="14" y="3" width="7" height="7" />
                  <rect x="14" y="14" width="7" height="7" />
                  <rect x="3" y="14" width="7" height="7" />
                </svg>
                Тестовые данные
              </div>
              {publicTests.map((ex, i) => (
                <div key={ex.id} className="lp-sample">
                  <div className="lp-sample-title">ТЕСТ #{i + 1}</div>
                  {ex.input_data != null && (
                    <div className="lp-sample-row">
                      <span className="lp-sample-label">ВХОДНЫЕ ДАННЫЕ</span>
                      <code className="lp-sample-code">{ex.input_data}</code>
                    </div>
                  )}
                  {ex.expected_output != null && (
                    <div className="lp-sample-row">
                      <span className="lp-sample-label">ОЖИДАЕМЫЙ ВЫВОД</span>
                      <code className="lp-sample-code">{ex.expected_output}</code>
                    </div>
                  )}
                </div>
              ))}
            </div>
          )}

          {/* SQL schema if applicable */}
          {task.sql_schema && (
            <div className="lp-section">
              <div className="lp-section-title">
                <svg viewBox="0 0 24 24" fill="none" strokeWidth={1.8} strokeLinecap="round" strokeLinejoin="round">
                  <ellipse cx="12" cy="5" rx="9" ry="3" />
                  <path d="M21 12c0 1.66-4 3-9 3s-9-1.34-9-3" />
                  <path d="M3 5v14c0 1.66 4 3 9 3s9-1.34 9-3V5" />
                </svg>
                Схема базы данных
              </div>
              <pre className="lp-code-pre">{task.sql_schema}</pre>
            </div>
          )}

          {/* Hints */}
          {hints && hints.length > 0 && (
            <div className="lp-section">
              <button
                className="lp-hints-toggle"
                onClick={() => { setShowHints(!showHints); if (!showHints) refreshHints(Number(taskId)); }}
              >
                <svg viewBox="0 0 24 24" fill="none" strokeWidth={1.8} strokeLinecap="round" strokeLinejoin="round">
                  <circle cx="12" cy="12" r="10" />
                  <line x1="12" y1="16" x2="12" y2="12" />
                  <line x1="12" y1="8" x2="12.01" y2="8" />
                </svg>
                Запросить зацепку
                <span className="lp-hints-count">
                  {hints.filter((h) => h.is_unlocked).length}/{hints.length}
                </span>
                <svg className={`lp-chevron ${showHints ? 'lp-chevron-open' : ''}`} viewBox="0 0 24 24" fill="none" strokeWidth={2} strokeLinecap="round" strokeLinejoin="round">
                  <polyline points="6 9 12 15 18 9" />
                </svg>
              </button>

              {showHints && (
                <div className="lp-hints">
                  {hintError && <div className="lp-hint-error">{hintError}</div>}
                  {hints.map((hint, i) => (
                    <div key={hint.id} className={`lp-hint ${hint.is_unlocked ? 'lp-hint-open' : ''}`}>
                      <div className="lp-hint-level">ЗАЦЕПКА {i + 1}</div>
                      {hint.is_unlocked ? (
                        <div className="lp-hint-content">{hint.content}</div>
                      ) : (
                        <button
                          className="lp-hint-buy"
                          disabled={unlockingHintId === hint.id}
                          onClick={() => unlockHint(hint.id)}
                        >
                          {unlockingHintId === hint.id
                            ? 'Разблокировка...'
                            : `Разблокировать (${hint.coin_cost} монет)`}
                        </button>
                      )}
                    </div>
                  ))}
                </div>
              )}
            </div>
          )}
        </div>

        {/* CENTER — ЛАБОРАТОРИЯ */}
        <div className="lp-center">

          {/* Anna Log banner */}
          <div className="lp-anna">
            <div className="lp-anna-left">
              <div className="lp-anna-avatar"><AnnaAvatar size={36} /></div>
              <div className="lp-anna-info">
                <div className="lp-anna-name">АННА ЛОГ</div>
                <div className="lp-anna-role">АНАЛИТИК · КОДЭКС</div>
              </div>
            </div>
            <div className="lp-anna-msg">{annaMsg}</div>
            {hints && hints.some((h) => !h.is_unlocked) && (
              <button
                className="lp-anna-hint"
                onClick={() => { setShowHints(true); refreshHints(Number(taskId)); }}
              >
                Зацепка
              </button>
            )}
          </div>

          {/* Editor toolbar */}
          <div className="lp-editor-toolbar">
            <div className="lp-editor-lang">
              <span className="lp-lang-dot" />
              {lang.toUpperCase()}
            </div>

            {draftSavedAt && (
              <div className="lp-draft-saved">
                <svg viewBox="0 0 24 24" fill="none" strokeWidth={2} strokeLinecap="round" strokeLinejoin="round">
                  <path d="M9 12l2 2 4-4" />
                  <circle cx="12" cy="12" r="10" />
                </svg>
                Черновик сохранён
              </div>
            )}

            <div className="lp-editor-actions">
              {hasDraft() && (
                <button className="lp-btn-ghost" onClick={clearDraft}>
                  Сбросить
                </button>
              )}
            </div>
          </div>

          {/* Editor */}
          <div className="lp-editor-wrap">
            <div className="lp-editor-inner">
              <LabEditor value={code} onChange={setCode} language={lang} />
            </div>
          </div>

          {/* Action bar */}
          <div className="lp-actionbar">
            <div className="lp-actionbar-left">
              {submission?.runtime != null && (
                <span className="lp-runtime">
                  {submission.runtime}ms
                  {submission.memory != null && ` · ${Math.round(submission.memory / 1024)}KB`}
                </span>
              )}
              {verdictMeta && !isRunning && (
                <span
                  className="lp-verdict-tag"
                  style={{
                    color: verdictMeta.color,
                    borderColor: verdictMeta.color + '44',
                    background: verdictMeta.color + '11',
                  }}
                >
                  {verdictMeta.short}
                </span>
              )}
              {isRunning && (
                <span className="lp-verdict-tag" style={{ color: '#1CCBFF', borderColor: '#1CCBFF44', background: '#1CCBFF11' }}>
                  <span className="lp-spin lp-spin-sm" style={{ marginRight: 5 }} />
                  АНАЛИЗ...
                </span>
              )}
            </div>

            <div className="lp-actionbar-right">
              <button
                className={`lp-btn-submit ${isRunning ? 'lp-btn-loading' : ''}`}
                disabled={isRunning}
                onClick={() => submitSolution(task.id, code)}
              >
                {isRunning ? (
                  <>
                    <span className="lp-spin" />
                    Анализирую улику...
                  </>
                ) : (
                  <>
                    <svg viewBox="0 0 24 24" fill="none" strokeWidth={2} strokeLinecap="round" strokeLinejoin="round">
                      <path d="M22 2L11 13" />
                      <polygon points="22 2 15 22 11 13 2 9 22 2" />
                    </svg>
                    Передать экспертизу
                  </>
                )}
              </button>
            </div>
          </div>

          {/* Bottom — ЖУРНАЛ ЭКСПЕРТИЗЫ */}
          {(bottomOpen || isRunning) && (
            <div className="lp-bottom">
              <div
                className="lp-bottom-header"
                onClick={() => setBottomOpen((v) => !v)}
              >
                <svg style={{ width: 13, height: 13, stroke: 'currentColor' }} viewBox="0 0 24 24" fill="none" strokeWidth={2} strokeLinecap="round" strokeLinejoin="round">
                  <path d="M14 2H6a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V8z" />
                  <polyline points="14 2 14 8 20 8" />
                </svg>
                ЖУРНАЛ ЭКСПЕРТИЗЫ

                {isRunning && (
                  <span className="lp-analyzing">
                    <span className="lp-spin lp-spin-sm" />
                    Анализирую...
                  </span>
                )}
                {verdictMeta && !isRunning && (
                  <span style={{ color: verdictMeta.color, fontWeight: 700, fontSize: '0.7rem', letterSpacing: '0.1em' }}>
                    {verdictMeta.label}
                  </span>
                )}
              </div>

              {/* Test results */}
              {submission?.test_results && submission.test_results.length > 0 && (
                <div className="lp-tests">
                  {submission.test_results.map((test: SubmissionTestResult, i: number) => {
                    const isAc = test.verdict === 'AC';
                    const isPending = !test.verdict;
                    const cls = isPending
                      ? 'lp-test lp-test-pending'
                      : isAc
                      ? 'lp-test lp-test-ac'
                      : 'lp-test lp-test-wa';
                    const vm = test.verdict ? VERDICT_MAP[test.verdict] : null;
                    return (
                      <div key={test.id ?? i} className={cls}>
                        <span className="lp-test-icon">
                          {isPending ? '○' : isAc ? '✓' : '✗'}
                        </span>
                        <span className="lp-test-label">
                          Проверка журнала #{String(i + 1).padStart(2, '0')}
                          {test.test_type === 'hidden' && (
                            <span className="lp-test-hidden">СКРЫТЫЙ</span>
                          )}
                        </span>
                        <div className="lp-test-right">
                          {test.runtime != null && (
                            <span className="lp-test-time">{test.runtime}ms</span>
                          )}
                          {vm && (
                            <span className="lp-test-verdict">{vm.short}</span>
                          )}
                        </div>
                      </div>
                    );
                  })}
                </div>
              )}

              {/* Error output / stderr */}
              {submission?.status === 'finished' && submission.error_output && (
                <div className="lp-terminal">
                  <div className="lp-terminal-hdr">
                    <div className="lp-terminal-dots">
                      <span style={{ background: '#FF5454' }} />
                      <span style={{ background: '#D8A53A' }} />
                      <span style={{ background: '#00E4AE' }} />
                    </div>
                    ВЫВОД СИСТЕМЫ
                  </div>
                  <pre className="lp-terminal-body">{submission.error_output}</pre>
                </div>
              )}
            </div>
          )}
        </div>

        {/* RIGHT — АНАЛИТИК */}
        <div className="lp-right">

          {/* Agent card */}
          <div className="lp-agent">
            <div className="lp-agent-avatar"><AgentAvatar size={44} /></div>
            <div>
              <div className="lp-agent-codename">
                {user?.full_name || user?.login || 'АГЕНТ'}
              </div>
              <div className="lp-agent-rank">
                {gamification?.rank ?? 'Стажёр'} · КОДЭКС
              </div>
            </div>
          </div>

          {/* Stats */}
          <div className="lp-stats">
            <div className="lp-stat">
              <span className="lp-stat-val lp-stat-gold">{gamification?.balance ?? 0}</span>
              <span className="lp-stat-key">МОНЕТ</span>
            </div>
            <div className="lp-stat">
              <span className="lp-stat-val">{gamification?.solved_count ?? 0}</span>
              <span className="lp-stat-key">ДЕЛО ЗАКРЫТО</span>
            </div>
            <div className="lp-stat">
              <span className="lp-stat-val lp-stat-fire">{gamification?.current_streak_days ?? 0}</span>
              <span className="lp-stat-key">СЕРИЯ ДНЕЙ</span>
            </div>
            <div className="lp-stat">
              <span className="lp-stat-val">{timer}</span>
              <span className="lp-stat-key">ВРЕМЯ</span>
            </div>
          </div>

          {/* Rita message */}
          <div className="lp-right-section">
            <div className="lp-right-label">СООБЩЕНИЕ ОТ РИТЫ</div>
            <div className="lp-rita-msg">
              <div className="lp-rita-name">РИТА · НАПАРНИК</div>
              <p>{getRitaMsg(taskId)}</p>
            </div>
          </div>

          {/* Submission history */}
          {history && history.length > 0 && (
            <div className="lp-right-section">
              <div className="lp-right-label">ИСТОРИЯ ЭКСПЕРТИЗ</div>
              <div className="lp-history">
                {history.slice(0, 8).map((sub: any, i: number) => {
                  const vm = sub.verdict ? VERDICT_MAP[sub.verdict as Verdict] : null;
                  const ts = sub.created_at
                    ? new Date(sub.created_at).toLocaleTimeString('ru', { hour: '2-digit', minute: '2-digit' })
                    : '';
                  return (
                    <div key={sub.id ?? i} className="lp-history-row">
                      <span className="lp-history-id">#{history.length - i}</span>
                      <span
                        className="lp-history-verdict"
                        style={{ color: vm?.color ?? 'var(--lp-muted)' }}
                      >
                        {vm?.short ?? (sub.status === 'queued' ? 'В ОЧЕРЕДИ' : sub.status?.toUpperCase())}
                      </span>
                      <span className="lp-history-time">{ts}</span>
                    </div>
                  );
                })}
              </div>
            </div>
          )}
        </div>
      </div>

      {/* Success overlay */}
      {showClue && (
        <ClueOverlay
          taskTitle={task.title}
          rewardCoins={task.reward_coins}
          onDismiss={() => setShowClue(false)}
        />
      )}
    </div>
  );
}
