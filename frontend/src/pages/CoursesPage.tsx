import { useEffect, useState } from 'react';
import { Link } from 'react-router-dom';
import { courseStudentApi, coursesApi } from '../api';
import type { CourseProgressStats } from '../api';
import type { Course } from '../types';

export default function CoursesPage() {
  const [courses, setCourses] = useState<Course[]>([]);
  const [progressMap, setProgressMap] = useState<Record<number, CourseProgressStats>>({});
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    coursesApi.list()
      .then(async ({ data }) => {
        setCourses(data);
        // Загружаем прогресс по каждому курсу параллельно
        const results = await Promise.allSettled(
          data.map((c) => courseStudentApi.getProgress(c.id).then((r) => ({ id: c.id, p: r.data })))
        );
        const map: Record<number, CourseProgressStats> = {};
        results.forEach((r) => {
          if (r.status === 'fulfilled') map[r.value.id] = r.value.p;
        });
        setProgressMap(map);
      })
      .finally(() => setLoading(false));
  }, []);

  if (loading) return <div className="text-center py-20 text-surface-300">Загрузка...</div>;

  return (
    <div>
      <h1 className="text-2xl font-bold mb-6">Курсы</h1>
      {courses.length === 0 ? (
        <div className="card text-center py-12 text-surface-300">Курсы пока не добавлены</div>
      ) : (
        <div className="grid gap-4 md:grid-cols-2 lg:grid-cols-3">
          {courses.map((c) => {
            const p = progressMap[c.id];
            const total = p?.total_tasks_count ?? 0;
            const done = p?.completed_tasks_count ?? 0;
            const pct = total > 0 ? Math.round((done / total) * 100) : 0;
            return (
              <Link key={c.id} to={`/course/${c.id}`} className="card hover:shadow-md transition-shadow group flex flex-col gap-3">
                <div className="flex items-start justify-between">
                  <h2 className="text-lg font-semibold group-hover:text-primary-600 transition-colors">{c.title}</h2>
                  <span className={`badge-${c.status === 'published' ? 'green' : c.status === 'draft' ? 'yellow' : 'gray'} shrink-0`}>
                    {c.status}
                  </span>
                </div>
                {c.description && <p className="text-sm text-surface-300 line-clamp-2">{c.description}</p>}
                {total > 0 && (
                  <div>
                    <div className="flex items-center justify-between text-xs text-surface-400 mb-1">
                      <span>Прогресс</span>
                      <span className="font-medium text-dark-700">{done}/{total} задач</span>
                    </div>
                    <div className="w-full bg-surface-200 rounded-full h-1.5 overflow-hidden">
                      <div
                        className={`h-full rounded-full transition-all ${pct === 100 ? 'bg-accent-500' : 'bg-primary-500'}`}
                        style={{ width: `${pct}%` }}
                      />
                    </div>
                    {pct === 100 && (
                      <div className="text-xs text-accent-600 font-medium mt-1">✓ Курс завершён</div>
                    )}
                  </div>
                )}
              </Link>
            );
          })}
        </div>
      )}
    </div>
  );
}
