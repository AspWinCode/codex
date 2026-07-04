import { useEffect, useState } from 'react';
import { Link } from 'react-router-dom';
import { contestsApi } from '../api';

export default function ContestsPage() {
  const [contests, setContests] = useState<any[]>([]);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    contestsApi.list().then(({ data }) => setContests(data)).finally(() => setLoading(false));
  }, []);

  if (loading) return <div className="text-center py-20 text-surface-300">Загрузка...</div>;

  const now = new Date();
  const upcoming = contests.filter((c) => new Date(c.start_at) > now);
  const active = contests.filter((c) => new Date(c.start_at) <= now && new Date(c.end_at) > now);
  const finished = contests.filter((c) => new Date(c.end_at) <= now);

  const Section = ({ title, items, color }: { title: string; items: any[]; color: string }) => (
    items.length > 0 ? (
      <div className="mb-8">
        <h2 className="text-lg font-semibold mb-3">{title}</h2>
        <div className="space-y-3">
          {items.map((c) => (
            <Link key={c.id} to={`/contest/${c.id}`} className="card flex items-center justify-between hover:shadow-md transition-shadow">
              <div>
                <h3 className="font-semibold">{c.title}</h3>
                <p className="text-sm text-surface-300 mt-1">
                  {new Date(c.start_at).toLocaleString('ru')} — {new Date(c.end_at).toLocaleString('ru')}
                </p>
              </div>
              <span className={`badge-${color}`}>{c.status}</span>
            </Link>
          ))}
        </div>
      </div>
    ) : null
  );

  return (
    <div>
      <h1 className="text-2xl font-bold mb-6">Соревнования</h1>
      <Section title="Активные" items={active} color="green" />
      <Section title="Предстоящие" items={upcoming} color="blue" />
      <Section title="Завершённые" items={finished} color="gray" />
      {contests.length === 0 && <div className="card text-center py-12 text-surface-300">Соревнований пока нет</div>}
    </div>
  );
}
