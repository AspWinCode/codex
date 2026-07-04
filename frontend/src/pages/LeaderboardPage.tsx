import { useEffect, useState } from 'react';
import { Link } from 'react-router-dom';
import { ratingsApi } from '../api';

export default function LeaderboardPage() {
  const [entries, setEntries] = useState<any[]>([]);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    ratingsApi.leaderboard(100).then(({ data }) => setEntries(data)).finally(() => setLoading(false));
  }, []);

  if (loading) return <div className="text-center py-20 text-surface-300">Загрузка...</div>;

  const getRankColor = (i: number) => {
    if (i === 0) return 'text-yellow-500';
    if (i === 1) return 'text-gray-400';
    if (i === 2) return 'text-amber-700';
    return 'text-dark-700';
  };

  return (
    <div>
      <h1 className="text-2xl font-bold mb-6">Рейтинг</h1>
      {entries.length === 0 ? (
        <div className="card text-center py-12 text-surface-300">Пока нет данных</div>
      ) : (
        <div className="card overflow-hidden p-0">
          <table className="w-full text-sm">
            <thead>
              <tr className="bg-surface-50 text-left">
                <th className="px-4 py-3 font-medium w-16">#</th>
                <th className="px-4 py-3 font-medium">Пользователь</th>
                <th className="px-4 py-3 font-medium">Рейтинг</th>
                <th className="px-4 py-3 font-medium">Решено</th>
                <th className="px-4 py-3 font-medium">Соревнований</th>
              </tr>
            </thead>
            <tbody>
              {entries.map((e, i) => (
                <tr key={e.user_id} className="border-t border-surface-100 hover:bg-surface-50">
                  <td className={`px-4 py-3 font-bold ${getRankColor(i)}`}>{i + 1}</td>
                  <td className="px-4 py-3">
                    <Link to={`/profile/${e.user_id}`} className="text-primary-600 hover:underline font-medium">{e.login}</Link>
                  </td>
                  <td className="px-4 py-3 font-semibold">{e.rating}</td>
                  <td className="px-4 py-3">{e.solved_total}</td>
                  <td className="px-4 py-3">{e.contests_participated}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}
    </div>
  );
}
