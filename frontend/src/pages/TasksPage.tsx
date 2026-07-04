import { useEffect, useState } from 'react';
import { Link } from 'react-router-dom';
import { tasksApi } from '../api';
import type { TaskCourseContext } from '../api';
import type { Task } from '../types';

export default function TasksPage() {
  const [tasks, setTasks] = useState<Task[]>([]);
  const [contextMap, setContextMap] = useState<Record<number, TaskCourseContext[]>>({});
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    tasksApi.list().then(async ({ data }) => {
      setTasks(data);
      // Загружаем контекст курсов для каждой задачи параллельно
      const results = await Promise.allSettled(
        data.map((t) =>
          tasksApi.getCourseContext(t.id).then((r) => ({ id: t.id, ctx: r.data }))
        )
      );
      const map: Record<number, TaskCourseContext[]> = {};
      results.forEach((r) => {
        if (r.status === 'fulfilled') map[r.value.id] = r.value.ctx;
      });
      setContextMap(map);
    }).finally(() => setLoading(false));
  }, []);

  if (loading) return <div className="text-center py-20 text-surface-300">Загрузка...</div>;

  return (
    <div>
      <h1 className="text-2xl font-bold mb-6">Задачи</h1>
      {tasks.length === 0 ? (
        <div className="card text-center py-12 text-surface-300">Задач пока нет</div>
      ) : (
        <div className="grid gap-3">
          {tasks.map((task) => {
            const ctx = contextMap[task.id] ?? [];
            // Если задача привязана к курсу — ссылка ведёт в курс
            const primaryCtx = ctx[0];
            const href = primaryCtx
              ? `/course/${primaryCtx.course_id}?task=${task.id}`
              : `/task/${task.id}`;
            return (
              <Link
                key={task.id}
                to={href}
                className="card flex items-center justify-between hover:shadow-md transition-shadow group"
              >
                <div className="min-w-0 flex-1">
                  <div className="font-medium text-dark-900 group-hover:text-primary-600">{task.title}</div>
                  <div className="flex items-center gap-2 mt-1 flex-wrap">
                    <span className="text-xs text-surface-400">{task.task_type}</span>
                    {ctx.map((c) => (
                      <span key={c.course_id} className="text-xs text-primary-500 flex items-center gap-1">
                        <span>📚</span>{c.course_title}
                        {c.node_title && <span className="text-surface-300">› {c.node_title}</span>}
                      </span>
                    ))}
                  </div>
                </div>
                <span className="text-surface-400 group-hover:text-primary-600 ml-4 shrink-0">→</span>
              </Link>
            );
          })}
        </div>
      )}
    </div>
  );
}
