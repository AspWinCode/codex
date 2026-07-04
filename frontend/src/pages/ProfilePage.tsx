import { useEffect, useState } from 'react';
import { useParams } from 'react-router-dom';
import { achievementsApi, authApi } from '../api';
import { useAuthStore } from '../store/auth';

const iconMap: Record<string, string> = {
  trophy: 'M5 3v4M3 5h4M6 17v4m-2-2h4m5-16l2.286 6.857L21 12l-5.714 2.143L13 21l-2.286-6.857L5 12l5.714-2.143L13 3z',
  fire: 'M17.657 18.657A8 8 0 016.343 7.343S7 9 9 10c0-2 .5-5 2.986-7C14 5 16.09 5.777 17.656 7.343A7.975 7.975 0 0120 13a7.975 7.975 0 01-2.343 5.657z',
  rocket: 'M15.59 14.37a6 6 0 01-5.84 7.38v-4.8m5.84-2.58a14.98 14.98 0 006.16-12.12A14.98 14.98 0 009.631 8.41m5.96 5.96a14.926 14.926 0 01-5.841 2.58m-.119-8.54a6 6 0 00-7.381 5.84h4.8m2.58-5.84a14.927 14.927 0 00-2.58 5.84m2.699 2.7c-.103.021-.207.041-.311.06a15.09 15.09 0 01-2.448-2.448 14.9 14.9 0 01.06-.312m-2.24 2.39a4.493 4.493 0 00-1.757 4.306 4.493 4.493 0 004.306-1.758M16.5 9a1.5 1.5 0 11-3 0 1.5 1.5 0 013 0z',
  crown: 'M4.5 12.75l6 6 9-13.5',
  star: 'M11.48 3.499a.562.562 0 011.04 0l2.125 5.111a.563.563 0 00.475.345l5.518.442c.499.04.701.663.321.988l-4.204 3.602a.563.563 0 00-.182.557l1.285 5.385a.562.562 0 01-.84.61l-4.725-2.885a.563.563 0 00-.586 0L6.982 20.54a.562.562 0 01-.84-.61l1.285-5.386a.562.562 0 00-.182-.557l-4.204-3.602a.563.563 0 01.321-.988l5.518-.442a.563.563 0 00.475-.345L11.48 3.5z',
  globe: 'M12 21a9.004 9.004 0 008.716-6.747M12 21a9.004 9.004 0 01-8.716-6.747M12 21c2.485 0 4.5-4.03 4.5-9S14.485 3 12 3m0 18c-2.485 0-4.5-4.03-4.5-9S9.515 3 12 3m0 0a8.997 8.997 0 017.843 4.582M12 3a8.997 8.997 0 00-7.843 4.582m15.686 0A11.953 11.953 0 0112 10.5c-2.998 0-5.74-1.1-7.843-2.918m15.686 0A8.959 8.959 0 0121 12c0 .778-.099 1.533-.284 2.253m0 0A17.919 17.919 0 0112 16.5c-3.162 0-6.133-.815-8.716-2.247m0 0A9.015 9.015 0 013 12c0-1.605.42-3.113 1.157-4.418',
  bolt: 'M3.75 13.5l10.5-11.25L12 10.5h8.25L9.75 21.75 12 13.5H3.75z',
  flame: 'M15.362 5.214A8.252 8.252 0 0112 21 8.25 8.25 0 016.038 7.048 8.287 8.287 0 009 9.6a8.983 8.983 0 013.361-6.867 8.21 8.21 0 003 2.48z',
  flag: 'M3 3v1.5M3 21v-6m0 0l2.77-.693a9 9 0 016.208.682l.108.054a9 9 0 006.086.71l3.114-.732a48.524 48.524 0 01-.005-10.499l-3.11.732a9 9 0 01-6.085-.711l-.108-.054a9 9 0 00-6.208-.682L3 4.5M3 15V4.5',
  medal: 'M16.5 18.75h-9m9 0a3 3 0 013 3h-15a3 3 0 013-3m9 0v-3.375c0-.621-.503-1.125-1.125-1.125h-.871M7.5 18.75v-3.375c0-.621.504-1.125 1.125-1.125h.872m5.007 0H9.497m5.007 0a7.454 7.454 0 01-.982-3.172M9.497 14.25a7.454 7.454 0 00.981-3.172M5.25 4.236c-.982.143-1.954.317-2.916.52A6.003 6.003 0 007.73 9.728M5.25 4.236V4.5c0 2.108.966 3.99 2.48 5.228M5.25 4.236V2.721C7.456 2.41 9.71 2.25 12 2.25c2.291 0 4.545.16 6.75.47v1.516M18.75 4.236c.982.143 1.954.317 2.916.52A6.003 6.003 0 0116.27 9.728M18.75 4.236V4.5c0 2.108-.966 3.99-2.48 5.228m0 0a6.003 6.003 0 01-2.905 1.058',
};

export default function ProfilePage() {
  const { userId } = useParams<{ userId: string }>();
  const { user } = useAuthStore();
  const [profile, setProfile] = useState<any>(null);
  const [loading, setLoading] = useState(true);

  // Смена пароля
  const [oldPwd, setOldPwd] = useState('');
  const [newPwd, setNewPwd] = useState('');
  const [confirmPwd, setConfirmPwd] = useState('');
  const [pwdMsg, setPwdMsg] = useState<{ type: 'ok' | 'err'; text: string } | null>(null);
  const [pwdSaving, setPwdSaving] = useState(false);

  const isOwnProfile = user?.id === Number(userId);

  const handleChangePassword = async (e: React.FormEvent) => {
    e.preventDefault();
    setPwdMsg(null);
    if (newPwd.length < 4) { setPwdMsg({ type: 'err', text: 'Минимум 4 символа' }); return; }
    if (newPwd !== confirmPwd) { setPwdMsg({ type: 'err', text: 'Пароли не совпадают' }); return; }
    setPwdSaving(true);
    try {
      await authApi.changePassword(oldPwd, newPwd);
      setPwdMsg({ type: 'ok', text: 'Пароль успешно изменён' });
      setOldPwd(''); setNewPwd(''); setConfirmPwd('');
    } catch (err: any) {
      setPwdMsg({ type: 'err', text: err.response?.data?.detail || 'Ошибка смены пароля' });
    } finally {
      setPwdSaving(false);
    }
  };

  useEffect(() => {
    if (!userId) return;
    achievementsApi.profile(parseInt(userId)).then(({ data }) => setProfile(data)).finally(() => setLoading(false));
  }, [userId]);

  if (loading) return <div className="text-center py-20 text-surface-300">Загрузка...</div>;
  if (!profile) return <div className="text-center py-20 text-red-500">Профиль не найден</div>;

  return (
    <div>
      <h1 className="text-2xl font-bold mb-6">{profile.login}</h1>

      <div className="grid grid-cols-2 md:grid-cols-4 gap-4 mb-8">
        <div className="card text-center">
          <div className="text-3xl font-bold text-primary-600">{profile.rating}</div>
          <div className="text-sm text-surface-300 mt-1">Рейтинг</div>
        </div>
        <div className="card text-center">
          <div className="text-3xl font-bold text-green-600">{profile.solved_total}</div>
          <div className="text-sm text-surface-300 mt-1">Решено</div>
        </div>
        <div className="card text-center">
          <div className="text-3xl font-bold text-yellow-600">{profile.achievements_count}</div>
          <div className="text-sm text-surface-300 mt-1">Ачивки</div>
        </div>
        <div className="card text-center">
          <div className="text-3xl font-bold text-purple-600">{profile.total_points}</div>
          <div className="text-sm text-surface-300 mt-1">Очки</div>
        </div>
      </div>

      <div className="card">
        <h2 className="text-lg font-semibold mb-4">Достижения</h2>
        {profile.achievements.length === 0 ? (
          <p className="text-sm text-surface-300">Пока нет достижений</p>
        ) : (
          <div className="grid grid-cols-2 md:grid-cols-3 lg:grid-cols-4 gap-3">
            {profile.achievements.map((a: any, i: number) => (
              <div key={i} className="flex items-center gap-3 bg-surface-50 rounded-lg p-3">
                <div className="w-10 h-10 rounded-full bg-primary-100 flex items-center justify-center flex-shrink-0">
                  <svg className="w-5 h-5 text-primary-600" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={1.5}>
                    <path strokeLinecap="round" strokeLinejoin="round" d={iconMap[a.icon] || iconMap.star} />
                  </svg>
                </div>
                <div>
                  <div className="text-sm font-medium">{a.title}</div>
                  <div className="text-xs text-surface-300">{new Date(a.earned_at).toLocaleDateString('ru')}</div>
                </div>
              </div>
            ))}
          </div>
        )}
      </div>

      {/* Смена пароля — только для своего профиля */}
      {isOwnProfile && (
        <div className="card mt-6">
          <h2 className="text-lg font-semibold mb-4">Сменить пароль</h2>
          <form onSubmit={handleChangePassword} className="space-y-3 max-w-sm">
            <div>
              <label className="block text-sm font-medium mb-1">Текущий пароль</label>
              <input
                type="password"
                className="input w-full"
                value={oldPwd}
                onChange={(e) => setOldPwd(e.target.value)}
                required
              />
            </div>
            <div>
              <label className="block text-sm font-medium mb-1">Новый пароль</label>
              <input
                type="password"
                className="input w-full"
                value={newPwd}
                onChange={(e) => setNewPwd(e.target.value)}
                required
                minLength={4}
              />
            </div>
            <div>
              <label className="block text-sm font-medium mb-1">Подтвердите пароль</label>
              <input
                type="password"
                className="input w-full"
                value={confirmPwd}
                onChange={(e) => setConfirmPwd(e.target.value)}
                required
                minLength={4}
              />
            </div>
            {pwdMsg && (
              <div className={`text-sm p-2 rounded ${pwdMsg.type === 'ok' ? 'bg-green-50 text-green-700' : 'bg-red-50 text-red-700'}`}>
                {pwdMsg.text}
              </div>
            )}
            <button type="submit" className="btn-primary" disabled={pwdSaving}>
              {pwdSaving ? 'Сохранение...' : 'Изменить пароль'}
            </button>
          </form>
        </div>
      )}
    </div>
  );
}
