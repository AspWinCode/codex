import { useEffect, useState } from 'react';
import { useParams } from 'react-router-dom';
import { personalLinksApi } from '../api';
import type { Task } from '../types';

export default function PersonalTaskPage() {
  const { token } = useParams<{ token: string }>();
  const [task, setTask] = useState<Task | null>(null);
  const [error, setError] = useState('');
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    if (!token) return;
    personalLinksApi.resolve(token)
      .then(({ data }) => setTask(data))
      .catch((err) => setError(err.response?.data?.detail || 'Ссылка недействительна'))
      .finally(() => setLoading(false));
  }, [token]);

  if (loading) return <div className="min-h-screen flex items-center justify-center text-surface-300">Загрузка...</div>;
  if (error) return <div className="min-h-screen flex items-center justify-center text-red-500">{error}</div>;
  if (!task) return null;

  return (
    <div className="max-w-3xl mx-auto p-8">
      <h1 className="text-2xl font-bold mb-4">{task.title}</h1>
      <span className="badge-blue">{task.task_type}</span>
      {task.description && (
        <div className="card mt-6">
          <div className="prose prose-sm whitespace-pre-wrap">{task.description}</div>
        </div>
      )}
      <div className="card mt-4 text-center text-sm text-surface-300">
        Для отправки решения войдите в систему
      </div>
    </div>
  );
}
