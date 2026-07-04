import { useEffect, useState } from 'react';
import { progressApi, tasksApi } from '../api';
import type { Progress, Task } from '../types';
import VerdictBadge from '../components/VerdictBadge';
import { Link } from 'react-router-dom';

export default function ProgressPage() {
  const [progress, setProgress] = useState<Progress[]>([]);
  const [tasks, setTasks] = useState<Task[]>([]);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    Promise.all([progressApi.get(), tasksApi.list()]).then(([pRes, tRes]) => {
      setProgress(pRes.data);
      setTasks(tRes.data);
    }).finally(() => setLoading(false));
  }, []);

  if (loading) return <div className="text-center py-20 text-surface-300">Загрузка...</div>;

  const progressMap: Record<number, Progress> = {};
  progress.forEach((p) => { progressMap[p.task_id] = p; });

  const solved = progress.filter((p) => p.best_verdict === 'AC');
  const inProgress = progress.filter((p) => p.best_verdict !== 'AC');
  const available = tasks.filter((t) => !progressMap[t.id]);
  const totalAttempts = progress.reduce((sum, p) => sum + p.attempts, 0);

  return (
    <div>
      <h1 className="text-2xl font-bold mb-6">Мой прогресс</h1>
      <div className="grid grid-cols-3 gap-4 mb-8">
        <div className="card text-center">
          <div className="text-3xl font-bold text-primary-600">{solved.length}</div>
          <div className="text-sm text-surface-300 mt-1">Решено</div>
        </div>
        <div className="card text-center">
          <div className="text-3xl font-bold text-yellow-600">{inProgress.length}</div>
          <div className="text-sm text-surface-300 mt-1">В процессе</div>
        </div>
        <div className="card text-center">
          <div className="text-3xl font-bold text-dark-700">{totalAttempts}</div>
          <div className="text-sm text-surface-300 mt-1">Всего попыток</div>
        </div>
      </div>

      {/* Решённые задачи */}
      {solved.length > 0 && (
        <div className="mb-6">
          <h2 className="text-lg font-semibold mb-3 text-green-600">✓ Решённые задачи ({solved.length})</h2>
          <div className="card overflow-hidden p-0">
            <table className="w-full text-sm">
              <thead>
                <tr className="bg-surface-50 text-left">
                  <th className="px-4 py-3 font-medium">Задача</th>
                  <th className="px-4 py-3 font-medium">Тип</th>
                  <th className="px-4 py-3 font-medium">Попытки</th>
                  <th className="px-4 py-3 font-medium">Решено</th>
                </tr>
              </thead>
              <tbody>
                {solved.map((p) => {
                  const task = tasks.find((t) => t.id === p.task_id);
                  return (
                    <tr key={p.id} className="border-t border-surface-100 hover:bg-surface-50">
                      <td className="px-4 py-3">
                        <Link to={`/task/${p.task_id}`} className="text-primary-600 hover:underline">
                          {task?.title || `Задача #${p.task_id}`}
                        </Link>
                      </td>
                      <td className="px-4 py-3"><span className="badge-blue">{task?.task_type || '—'}</span></td>
                      <td className="px-4 py-3">{p.attempts}</td>
                      <td className="px-4 py-3 text-xs text-surface-300">{p.solved_at ? new Date(p.solved_at).toLocaleString('ru') : '—'}</td>
                    </tr>
                  );
                })}
              </tbody>
            </table>
          </div>
        </div>
      )}

      {/* В процессе */}
      {inProgress.length > 0 && (
        <div className="mb-6">
          <h2 className="text-lg font-semibold mb-3 text-yellow-600">⏳ В процессе ({inProgress.length})</h2>
          <div className="card overflow-hidden p-0">
            <table className="w-full text-sm">
              <thead>
                <tr className="bg-surface-50 text-left">
                  <th className="px-4 py-3 font-medium">Задача</th>
                  <th className="px-4 py-3 font-medium">Тип</th>
                  <th className="px-4 py-3 font-medium">Попытки</th>
                  <th className="px-4 py-3 font-medium">Лучший результат</th>
                </tr>
              </thead>
              <tbody>
                {inProgress.map((p) => {
                  const task = tasks.find((t) => t.id === p.task_id);
                  return (
                    <tr key={p.id} className="border-t border-surface-100 hover:bg-surface-50">
                      <td className="px-4 py-3">
                        <Link to={`/task/${p.task_id}`} className="text-primary-600 hover:underline">
                          {task?.title || `Задача #${p.task_id}`}
                        </Link>
                      </td>
                      <td className="px-4 py-3"><span className="badge-blue">{task?.task_type || '—'}</span></td>
                      <td className="px-4 py-3">{p.attempts}</td>
                      <td className="px-4 py-3"><VerdictBadge verdict={p.best_verdict} /></td>
                    </tr>
                  );
                })}
              </tbody>
            </table>
          </div>
        </div>
      )}

      {/* Доступные задачи */}
      {available.length > 0 && (
        <div className="mb-6">
          <h2 className="text-lg font-semibold mb-3 text-surface-400">📋 Доступные задачи ({available.length})</h2>
          <div className="card overflow-hidden p-0">
            <table className="w-full text-sm">
              <thead>
                <tr className="bg-surface-50 text-left">
                  <th className="px-4 py-3 font-medium">Задача</th>
                  <th className="px-4 py-3 font-medium">Тип</th>
                </tr>
              </thead>
              <tbody>
                {available.map((task) => (
                  <tr key={task.id} className="border-t border-surface-100 hover:bg-surface-50">
                    <td className="px-4 py-3">
                      <Link to={`/task/${task.id}`} className="text-primary-600 hover:underline">
                        {task.title}
                      </Link>
                    </td>
                    <td className="px-4 py-3"><span className="badge-blue">{task.task_type}</span></td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </div>
      )}

      {progress.length === 0 && available.length === 0 && (
        <div className="card text-center py-12 text-surface-300">Нет доступных задач</div>
      )}
    </div>
  );
}
