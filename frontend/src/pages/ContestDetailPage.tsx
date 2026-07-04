import { useEffect, useState } from 'react';
import { useParams, Link } from 'react-router-dom';
import { contestsApi } from '../api';

export default function ContestDetailPage() {
  const { contestId } = useParams<{ contestId: string }>();
  const [contest, setContest] = useState<any>(null);
  const [leaderboard, setLeaderboard] = useState<any[]>([]);
  const [timeLeft, setTimeLeft] = useState('');
  const [loading, setLoading] = useState(true);
  const [joining, setJoining] = useState(false);

  useEffect(() => {
    if (!contestId) return;
    const id = parseInt(contestId);
    Promise.all([contestsApi.get(id), contestsApi.leaderboard(id)])
      .then(([c, lb]) => { setContest(c.data); setLeaderboard(lb.data); })
      .finally(() => setLoading(false));
  }, [contestId]);

  useEffect(() => {
    if (!contest) return;
    const interval = setInterval(() => {
      const now = new Date().getTime();
      const end = new Date(contest.end_at).getTime();
      const start = new Date(contest.start_at).getTime();
      if (now < start) {
        const diff = start - now;
        setTimeLeft(`До начала: ${formatTime(diff)}`);
      } else if (now < end) {
        const diff = end - now;
        setTimeLeft(`Осталось: ${formatTime(diff)}`);
      } else {
        setTimeLeft('Завершено');
        clearInterval(interval);
      }
    }, 1000);
    return () => clearInterval(interval);
  }, [contest]);

  const formatTime = (ms: number) => {
    const h = Math.floor(ms / 3600000);
    const m = Math.floor((ms % 3600000) / 60000);
    const s = Math.floor((ms % 60000) / 1000);
    return `${h}ч ${m}м ${s}с`;
  };

  const handleJoin = async () => {
    if (!contestId) return;
    setJoining(true);
    try {
      await contestsApi.join(parseInt(contestId));
      const { data } = await contestsApi.leaderboard(parseInt(contestId));
      setLeaderboard(data);
    } catch (e: any) {
      alert(e.response?.data?.detail || 'Ошибка');
    } finally {
      setJoining(false);
    }
  };

  if (loading) return <div className="text-center py-20 text-surface-300">Загрузка...</div>;
  if (!contest) return <div className="text-center py-20 text-red-500">Соревнование не найдено</div>;

  return (
    <div>
      <Link to="/contests" className="text-sm text-primary-600 hover:underline">&larr; Все соревнования</Link>
      <div className="flex items-start justify-between mt-3 mb-6">
        <div>
          <h1 className="text-2xl font-bold">{contest.title}</h1>
          {contest.description && <p className="text-surface-300 mt-1">{contest.description}</p>}
        </div>
        <div className="text-right">
          <div className="text-lg font-mono font-bold text-primary-600">{timeLeft}</div>
          <button onClick={handleJoin} disabled={joining} className="btn-primary btn-sm mt-2">
            {joining ? '...' : 'Участвовать'}
          </button>
        </div>
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
        <div className="card">
          <h2 className="text-sm font-semibold text-dark-700 mb-3">Задачи</h2>
          <div className="space-y-2">
            {(contest.contest_tasks || []).map((ct: any, i: number) => (
              <Link key={ct.id} to={`/task/${ct.task_id}`} className="flex items-center justify-between p-2 rounded-lg hover:bg-surface-100 text-sm">
                <span>{String.fromCharCode(65 + i)}. {ct.task_title || `Task #${ct.task_id}`}</span>
                <span className="text-xs text-surface-300">{ct.max_score} pts</span>
              </Link>
            ))}
          </div>
        </div>

        <div className="card">
          <h2 className="text-sm font-semibold text-dark-700 mb-3">Таблица лидеров</h2>
          {leaderboard.length === 0 ? (
            <p className="text-sm text-surface-300">Пока нет участников</p>
          ) : (
            <table className="w-full text-sm">
              <thead>
                <tr className="text-left text-surface-300">
                  <th className="pb-2">#</th>
                  <th className="pb-2">Участник</th>
                  <th className="pb-2">Решено</th>
                  <th className="pb-2">Очки</th>
                </tr>
              </thead>
              <tbody>
                {leaderboard.map((e, i) => (
                  <tr key={e.user_id} className="border-t border-surface-100">
                    <td className="py-2 font-bold text-primary-600">{i + 1}</td>
                    <td className="py-2">{e.login}</td>
                    <td className="py-2">{e.solved_count}</td>
                    <td className="py-2 font-semibold">{e.score}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          )}
        </div>
      </div>
    </div>
  );
}
