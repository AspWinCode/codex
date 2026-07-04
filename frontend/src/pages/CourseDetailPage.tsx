import { useEffect, useState } from 'react';
import { Link, useParams } from 'react-router-dom';
import { coursesApi, tasksApi } from '../api';
import type { Course, Module, Task } from '../types';

export default function CourseDetailPage() {
  const { courseId } = useParams<{ courseId: string }>();
  const [course, setCourse] = useState<Course | null>(null);
  const [modules, setModules] = useState<Module[]>([]);
  const [tasks, setTasks] = useState<Record<number, Task[]>>({});
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    if (!courseId) return;
    const id = parseInt(courseId);
    Promise.all([
      coursesApi.get(id),
      coursesApi.listModules(id),
    ]).then(async ([courseRes, modulesRes]) => {
      setCourse(courseRes.data);
      setModules(modulesRes.data);
      const taskMap: Record<number, Task[]> = {};
      for (const mod of modulesRes.data) {
        for (const sub of mod.submodules || []) {
          const { data } = await tasksApi.list({ submodule_id: sub.id });
          taskMap[sub.id] = data;
        }
      }
      setTasks(taskMap);
    }).finally(() => setLoading(false));
  }, [courseId]);

  if (loading) return <div className="text-center py-20 text-surface-300">Загрузка...</div>;
  if (!course) return <div className="text-center py-20 text-red-500">Курс не найден</div>;

  return (
    <div>
      <div className="mb-6">
        <Link to="/" className="text-sm text-primary-600 hover:underline">&larr; Все курсы</Link>
        <h1 className="text-2xl font-bold mt-2">{course.title}</h1>
        {course.description && <p className="text-surface-300 mt-1">{course.description}</p>}
      </div>
      {modules.length === 0 ? (
        <div className="card text-center py-8 text-surface-300">Модулей пока нет</div>
      ) : (
        <div className="space-y-6">
          {modules.map((mod) => (
            <div key={mod.id} className="card">
              <h2 className="text-lg font-semibold mb-4">{mod.title}</h2>
              {(mod.submodules || []).length === 0 ? (
                <p className="text-sm text-surface-300">Подмодулей нет</p>
              ) : (
                <div className="space-y-3">
                  {(mod.submodules || []).map((sub) => (
                    <div key={sub.id}>
                      <h3 className="text-sm font-medium text-dark-700 mb-2">{sub.title}</h3>
                      <div className="space-y-1 pl-4">
                        {(tasks[sub.id] || []).map((task) => (
                          <Link
                            key={task.id}
                            to={`/task/${task.id}`}
                            className="flex items-center gap-2 p-2 rounded-lg hover:bg-surface-100 transition-colors text-sm"
                          >
                            <span className="w-2 h-2 rounded-full bg-primary-500"></span>
                            <span className="flex-1">{task.title}</span>
                            <span className="text-xs text-surface-300">{task.task_type}</span>
                          </Link>
                        ))}
                        {(!tasks[sub.id] || tasks[sub.id].length === 0) && (
                          <p className="text-xs text-surface-300 pl-4">Задач нет</p>
                        )}
                      </div>
                    </div>
                  ))}
                </div>
              )}
            </div>
          ))}
        </div>
      )}
    </div>
  );
}
