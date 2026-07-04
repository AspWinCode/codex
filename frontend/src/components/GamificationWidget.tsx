import { useEffect, useState } from 'react';
import { gamificationApi, GamificationMe } from '../api';

export default function GamificationWidget() {
  const [data, setData] = useState<GamificationMe | null>(null);

  useEffect(() => {
    let cancelled = false;
    gamificationApi
      .me()
      .then(({ data }) => { if (!cancelled) setData(data); })
      .catch(() => {});
    return () => { cancelled = true; };
  }, []);

  if (!data) return null;

  return (
    <div className="px-4 py-3 mx-2 mb-2 rounded-lg bg-dark-800 border border-dark-700">
      <div className="flex items-center justify-between mb-1.5">
        <span className="text-xs font-semibold text-surface-300 uppercase tracking-wide">{data.rank}</span>
        <span className="flex items-center gap-1 text-sm font-bold text-amber-400">
          🪙 {data.balance}
        </span>
      </div>
      <div className="flex items-center justify-between text-xs text-surface-400">
        <span>Решено задач: {data.solved_count}</span>
        {data.current_streak_days > 0 && (
          <span className="flex items-center gap-1 text-orange-400">
            🔥 {data.current_streak_days}
          </span>
        )}
      </div>
    </div>
  );
}
