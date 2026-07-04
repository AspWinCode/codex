import { useCallback, useEffect, useState } from 'react';
import { hintsApi, progressApi, submissionsApi, tasksApi } from '../../../api';
import type { Submission, Task, TaskHint } from '../../../types';

const DEFAULT_PLACEHOLDERS: Record<string, string> = {
  sql_query: '-- Ваш SQL запрос\nSELECT ',
  cpp_io: '#include <iostream>\nusing namespace std;\n\nint main() {\n    \n    return 0;\n}\n',
  js_io: '// Ваше решение\nconst readline = require("readline");\nconst rl = readline.createInterface({ input: process.stdin });\n\nrl.on("line", (line) => {\n    \n});\n',
};

function resolveInitialCode(taskType: string): string {
  return DEFAULT_PLACEHOLDERS[taskType] || '# Ваше решение\n';
}

function storageKey(taskId: number) {
  return `code_task_${taskId}`;
}

export function useTaskData(taskId?: string) {
  const [task, setTask] = useState<Task | null>(null);
  const [code, setCode] = useState('');
  const [history, setHistory] = useState<Submission[]>([]);
  const [hints, setHints] = useState<TaskHint[]>([]);
  const [loading, setLoading] = useState(true);
  const [showHints, setShowHints] = useState(false);
  const [draftSavedAt, setDraftSavedAt] = useState<Date | null>(null);

  const refreshHistory = useCallback((tid: number) => {
    submissionsApi.list(tid).then(({ data }) => setHistory(data));
  }, []);

  const refreshHints = useCallback((tid: number) => {
    progressApi.getHints(tid).then(({ data }) => {
      setHints((prev) => {
        // Автоматически показываем подсказки если появились новые
        if (data.length > prev.length && data.length > 0) {
          setShowHints(true);
        }
        return data;
      });
    }).catch(() => {});
  }, []);

  const [unlockingHintId, setUnlockingHintId] = useState<number | null>(null);
  const [hintError, setHintError] = useState<string | null>(null);

  const unlockHint = useCallback(async (hintId: number) => {
    setUnlockingHintId(hintId);
    setHintError(null);
    try {
      const { data } = await hintsApi.unlock(hintId);
      setHints((prev) => prev.map((h) => (h.id === hintId ? data : h)));
    } catch (err: any) {
      setHintError(err.response?.data?.detail || 'Не удалось купить подсказку');
    } finally {
      setUnlockingHintId(null);
    }
  }, []);

  const handleSetCode = useCallback((newCode: string) => {
    setCode(newCode);
    if (taskId) {
      try {
        localStorage.setItem(storageKey(Number(taskId)), newCode);
        setDraftSavedAt(new Date());
      } catch {}
    }
  }, [taskId]);

  const clearDraft = useCallback(() => {
    if (taskId) {
      try { localStorage.removeItem(storageKey(Number(taskId))); } catch {}
      if (task) setCode(resolveInitialCode(task.task_type));
      setDraftSavedAt(null);
    }
  }, [taskId, task]);

  const hasDraft = useCallback(() => {
    if (!taskId) return false;
    try { return localStorage.getItem(storageKey(Number(taskId))) !== null; } catch { return false; }
  }, [taskId]);

  useEffect(() => {
    if (!taskId) {
      setLoading(false);
      return;
    }

    const id = Number(taskId);
    if (Number.isNaN(id)) {
      setLoading(false);
      return;
    }

    setLoading(true);

    tasksApi.get(id)
      .then(({ data }) => {
        setTask(data);
        try {
          const saved = localStorage.getItem(storageKey(id));
          setCode(saved ?? resolveInitialCode(data.task_type));
        } catch {
          setCode(resolveInitialCode(data.task_type));
        }
      })
      .finally(() => setLoading(false));

    refreshHistory(id);
    refreshHints(id);
  }, [taskId, refreshHistory, refreshHints]);

  return {
    task,
    code,
    setCode: handleSetCode,
    history,
    hints,
    loading,
    showHints,
    setShowHints,
    refreshHistory,
    refreshHints,
    draftSavedAt,
    clearDraft,
    hasDraft,
    unlockHint,
    unlockingHintId,
    hintError,
  };
}
