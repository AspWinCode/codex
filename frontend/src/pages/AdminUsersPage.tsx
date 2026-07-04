import { useEffect, useState } from 'react';
import { coursesApi, usersApi } from '../api';
import type { CourseEnrollment } from '../api';
import type { Course, User } from '../types';

interface StudentStats {
  user_id: number;
  total_attempts: number;
  solved_tasks: number;
  in_progress_tasks: number;
}

export default function AdminUsersPage() {
  const [users, setUsers] = useState<User[]>([]);
  const [allCourses, setAllCourses] = useState<Course[]>([]);
  const [search, setSearch] = useState('');
  const [showCreate, setShowCreate] = useState(false);
  const [form, setForm] = useState({ login: '', password: '', role: 'student', email: '', full_name: '' });
  const [error, setError] = useState('');
  const [loading, setLoading] = useState(true);
  const [createdCredentials, setCreatedCredentials] = useState<{ login: string; password: string } | null>(null);

  const [resetUserId, setResetUserId] = useState<number | null>(null);
  const [resetPassword, setResetPassword] = useState('');
  const [resetError, setResetError] = useState('');

  const [enrollUserId, setEnrollUserId] = useState<number | null>(null);
  const [enrollments, setEnrollments] = useState<CourseEnrollment[]>([]);
  const [enrollLoading, setEnrollLoading] = useState(false);

  const [statsUserId, setStatsUserId] = useState<number | null>(null);
  const [stats, setStats] = useState<StudentStats | null>(null);
  const [statsLoading, setStatsLoading] = useState(false);

  const load = () => usersApi.list().then(({ data }) => setUsers(data)).finally(() => setLoading(false));

  useEffect(() => {
    load();
    coursesApi.list().then(({ data }) => setAllCourses(data)).catch(() => {});
  }, []);

  const handleCreate = async (e: React.FormEvent) => {
    e.preventDefault();
    setError('');
    try {
      await usersApi.create({
        login: form.login,
        password: form.password,
        role: form.role,
        email: form.email || undefined,
        full_name: form.full_name || undefined,
      });
      setCreatedCredentials({ login: form.login, password: form.password });
      setForm({ login: '', password: '', role: 'student', email: '', full_name: '' });
      setShowCreate(false);
      load();
    } catch (err: any) {
      setError(err.response?.data?.detail || 'Ошибка');
    }
  };

  const toggleStatus = async (user: User) => {
    const newStatus = user.status === 'active' ? 'blocked' : 'active';
    await usersApi.update(user.id, { status: newStatus } as any);
    load();
  };

  const handleResetPassword = async (e: React.FormEvent) => {
    e.preventDefault();
    setResetError('');
    if (!resetUserId) return;
    try {
      await usersApi.resetPassword(resetUserId, resetPassword);
      setResetUserId(null);
      setResetPassword('');
    } catch (err: any) {
      setResetError(err.response?.data?.detail || 'Ошибка');
    }
  };

  const openEnrollments = async (userId: number) => {
    setEnrollUserId(userId);
    setEnrollLoading(true);
    try {
      const { data } = await usersApi.getEnrollments(userId);
      setEnrollments(data);
    } catch {
      setEnrollments([]);
    } finally {
      setEnrollLoading(false);
    }
  };

  const openStats = async (userId: number) => {
    setStatsUserId(userId);
    setStatsLoading(true);
    setStats(null);
    try {
      const { data } = await usersApi.getStats(userId);
      setStats(data);
    } catch {
      setStats(null);
    } finally {
      setStatsLoading(false);
    }
  };

  const handleEnroll = async (courseId: number) => {
    if (!enrollUserId) return;
    await usersApi.enroll(enrollUserId, courseId);
    const { data } = await usersApi.getEnrollments(enrollUserId);
    setEnrollments(data);
  };

  const handleUnenroll = async (courseId: number) => {
    if (!enrollUserId) return;
    await usersApi.unenroll(enrollUserId, courseId);
    const { data } = await usersApi.getEnrollments(enrollUserId);
    setEnrollments(data);
  };

  const filteredUsers = users.filter((u) => {
    const q = search.toLowerCase();
    return (
      u.login.toLowerCase().includes(q) ||
      (u.email ?? '').toLowerCase().includes(q) ||
      (u.full_name ?? '').toLowerCase().includes(q)
    );
  });

  const enrolledIds = new Set(enrollments.map((e) => e.course_id));
  const enrollUser = users.find((u) => u.id === enrollUserId);
  const statsUser = users.find((u) => u.id === statsUserId);

  if (loading) return <div className="text-center py-20 text-surface-300">Загрузка...</div>;

  return (
    <div>
      <div className="flex items-center justify-between mb-6">
        <h1 className="text-2xl font-bold">Пользователи</h1>
        <button onClick={() => { setShowCreate(!showCreate); setCreatedCredentials(null); }} className="btn-primary">+ Добавить</button>
      </div>

      {showCreate && (
        <form onSubmit={handleCreate} className="card mb-6 space-y-4">
          <div className="grid grid-cols-2 gap-4">
            <div>
              <label className="block text-sm font-medium mb-1">Логин *</label>
              <input className="input" value={form.login} onChange={(e) => setForm({ ...form, login: e.target.value })} required />
            </div>
            <div>
              <label className="block text-sm font-medium mb-1">Пароль *</label>
              <input className="input" type="text" value={form.password} onChange={(e) => setForm({ ...form, password: e.target.value })} required placeholder="Введите пароль" />
            </div>
            <div>
              <label className="block text-sm font-medium mb-1">Email</label>
              <input className="input" type="email" value={form.email} onChange={(e) => setForm({ ...form, email: e.target.value })} placeholder="student@example.com" />
              <p className="text-xs text-surface-400 mt-0.5">Если указан — логин/пароль отправятся на почту автоматически</p>
            </div>
            <div>
              <label className="block text-sm font-medium mb-1">Имя</label>
              <input className="input" value={form.full_name} onChange={(e) => setForm({ ...form, full_name: e.target.value })} placeholder="Иван Иванов" />
            </div>
            <div>
              <label className="block text-sm font-medium mb-1">Роль</label>
              <select className="input" value={form.role} onChange={(e) => setForm({ ...form, role: e.target.value })}>
                <option value="student">Студент</option>
                <option value="admin">Администратор</option>
              </select>
            </div>
          </div>
          {error && <div className="text-red-600 text-sm">{error}</div>}
          <div className="flex gap-2">
            <button type="submit" className="btn-primary btn-sm">Создать</button>
            <button type="button" onClick={() => setShowCreate(false)} className="btn-secondary btn-sm">Отмена</button>
          </div>
        </form>
      )}

      {createdCredentials && (
        <div className="card mb-6 bg-green-50 border border-green-200">
          <div className="flex items-start justify-between">
            <div>
              <div className="font-semibold text-green-800 mb-2">✅ Пользователь создан — передайте данные для входа:</div>
              <div className="space-y-1 text-sm">
                <div><span className="text-surface-400">Логин:</span> <code className="bg-white px-2 py-0.5 rounded border border-green-200 font-mono select-all">{createdCredentials.login}</code></div>
                <div><span className="text-surface-400">Пароль:</span> <code className="bg-white px-2 py-0.5 rounded border border-green-200 font-mono select-all">{createdCredentials.password}</code></div>
              </div>
            </div>
            <button onClick={() => setCreatedCredentials(null)} className="text-surface-400 hover:text-dark-900 text-lg leading-none">×</button>
          </div>
        </div>
      )}

      <div className="mb-4">
        <input
          className="input max-w-sm"
          placeholder="Поиск по логину, email или имени..."
          value={search}
          onChange={(e) => setSearch(e.target.value)}
        />
      </div>

      <div className="card overflow-hidden p-0">
        <table className="w-full text-sm">
          <thead>
            <tr className="bg-surface-50 text-left">
              <th className="px-4 py-3 font-medium">ID</th>
              <th className="px-4 py-3 font-medium">Логин / Имя</th>
              <th className="px-4 py-3 font-medium">Email</th>
              <th className="px-4 py-3 font-medium">Роль</th>
              <th className="px-4 py-3 font-medium">Статус</th>
              <th className="px-4 py-3 font-medium">Действия</th>
            </tr>
          </thead>
          <tbody>
            {filteredUsers.length === 0 ? (
              <tr>
                <td colSpan={6} className="px-4 py-8 text-center text-surface-300">
                  {search ? 'Пользователи не найдены' : 'Нет пользователей'}
                </td>
              </tr>
            ) : filteredUsers.map((u) => (
              <tr key={u.id} className="border-t border-surface-100">
                <td className="px-4 py-3 text-surface-400">{u.id}</td>
                <td className="px-4 py-3">
                  <div className="font-medium">{u.login}</div>
                  {u.full_name && <div className="text-xs text-surface-400">{u.full_name}</div>}
                </td>
                <td className="px-4 py-3 text-surface-400 text-xs">{u.email || <span className="text-surface-200">—</span>}</td>
                <td className="px-4 py-3"><span className={u.role === 'admin' ? 'badge-blue' : 'badge-gray'}>{u.role}</span></td>
                <td className="px-4 py-3"><span className={u.status === 'active' ? 'badge-green' : 'badge-red'}>{u.status}</span></td>
                <td className="px-4 py-3">
                  <div className="flex gap-3 flex-wrap">
                    <button onClick={() => toggleStatus(u)} className="text-xs text-primary-600 hover:underline">
                      {u.status === 'active' ? 'Заблокировать' : 'Разблокировать'}
                    </button>
                    <button onClick={() => { setResetUserId(u.id); setResetPassword(''); setResetError(''); }} className="text-xs text-orange-600 hover:underline">
                      Сбросить пароль
                    </button>
                    {u.role === 'student' && (
                      <>
                        <button onClick={() => openEnrollments(u.id)} className="text-xs text-purple-600 hover:underline">
                          Доступ к курсам
                        </button>
                        <button onClick={() => openStats(u.id)} className="text-xs text-teal-600 hover:underline">
                          Статистика
                        </button>
                      </>
                    )}
                  </div>
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>

      {/* Модал сброса пароля */}
      {resetUserId !== null && (
        <div className="fixed inset-0 bg-black/40 flex items-center justify-center z-50">
          <div className="bg-white rounded-2xl shadow-xl p-6 w-full max-w-sm">
            <h2 className="text-lg font-bold mb-4">Сбросить пароль</h2>
            <p className="text-sm text-surface-400 mb-4">
              Пользователь: <span className="font-medium text-dark-900">{users.find(u => u.id === resetUserId)?.login}</span>
            </p>
            <form onSubmit={handleResetPassword} className="space-y-3">
              <div>
                <label className="block text-sm font-medium mb-1">Новый пароль</label>
                <input className="input" type="text" value={resetPassword} onChange={(e) => setResetPassword(e.target.value)} required placeholder="Введите новый пароль" />
              </div>
              {resetError && <div className="text-red-600 text-sm">{resetError}</div>}
              <div className="flex gap-2 pt-2">
                <button type="submit" className="btn-primary btn-sm flex-1">Сохранить</button>
                <button type="button" onClick={() => setResetUserId(null)} className="btn-secondary btn-sm flex-1">Отмена</button>
              </div>
            </form>
          </div>
        </div>
      )}

      {/* Модал управления курсами */}
      {enrollUserId !== null && (
        <div className="fixed inset-0 bg-black/40 flex items-center justify-center z-50">
          <div className="bg-white rounded-2xl shadow-xl p-6 w-full max-w-md">
            <div className="flex items-center justify-between mb-4">
              <h2 className="text-lg font-bold">Доступ к курсам</h2>
              <button onClick={() => setEnrollUserId(null)} className="text-surface-400 hover:text-dark-900 text-xl leading-none">×</button>
            </div>
            <p className="text-sm text-surface-400 mb-3">
              Пользователь: <span className="font-medium text-dark-900">{enrollUser?.login}</span>
              {enrollUser?.full_name && <span className="text-surface-300"> ({enrollUser.full_name})</span>}
            </p>
            <p className="text-xs text-amber-600 bg-amber-50 border border-amber-200 rounded-lg px-3 py-2 mb-4">
              ⚠️ Студент видит только назначенные курсы. Без доступа — курсов не видно.
            </p>
            {enrollLoading ? (
              <div className="text-center py-4 text-surface-300">Загрузка...</div>
            ) : (
              <div className="space-y-2 max-h-72 overflow-y-auto">
                {allCourses.filter(c => c.status === 'published').map((c) => {
                  const enrolled = enrolledIds.has(c.id);
                  return (
                    <div key={c.id} className="flex items-center justify-between p-3 rounded-xl border border-surface-100 hover:bg-surface-50">
                      <span className="text-sm font-medium">{c.title}</span>
                      <button
                        onClick={() => enrolled ? handleUnenroll(c.id) : handleEnroll(c.id)}
                        className={`btn-sm ${enrolled ? 'btn-secondary text-red-600' : 'btn-primary'}`}
                      >
                        {enrolled ? 'Убрать доступ' : 'Дать доступ'}
                      </button>
                    </div>
                  );
                })}
                {allCourses.filter(c => c.status === 'published').length === 0 && (
                  <div className="text-center py-4 text-surface-300">Нет опубликованных курсов</div>
                )}
              </div>
            )}
            <div className="mt-4 pt-4 border-t border-surface-100">
              <button onClick={() => setEnrollUserId(null)} className="btn-secondary btn-sm w-full">Закрыть</button>
            </div>
          </div>
        </div>
      )}

      {/* Модал статистики студента */}
      {statsUserId !== null && (
        <div className="fixed inset-0 bg-black/40 flex items-center justify-center z-50">
          <div className="bg-white rounded-2xl shadow-xl p-6 w-full max-w-sm">
            <div className="flex items-center justify-between mb-4">
              <h2 className="text-lg font-bold">Статистика студента</h2>
              <button onClick={() => setStatsUserId(null)} className="text-surface-400 hover:text-dark-900 text-xl leading-none">×</button>
            </div>
            <p className="text-sm text-surface-400 mb-4">
              {statsUser?.full_name
                ? <><span className="font-medium text-dark-900">{statsUser.full_name}</span> <span className="text-surface-300">({statsUser.login})</span></>
                : <span className="font-medium text-dark-900">{statsUser?.login}</span>
              }
            </p>
            {statsLoading ? (
              <div className="text-center py-4 text-surface-300">Загрузка...</div>
            ) : stats ? (
              <div className="grid grid-cols-3 gap-3">
                <div className="text-center p-3 bg-green-50 rounded-xl border border-green-100">
                  <div className="text-2xl font-bold text-green-700">{stats.solved_tasks}</div>
                  <div className="text-xs text-green-600 mt-1">Решено задач</div>
                </div>
                <div className="text-center p-3 bg-yellow-50 rounded-xl border border-yellow-100">
                  <div className="text-2xl font-bold text-yellow-700">{stats.in_progress_tasks}</div>
                  <div className="text-xs text-yellow-600 mt-1">В процессе</div>
                </div>
                <div className="text-center p-3 bg-surface-50 rounded-xl border border-surface-100">
                  <div className="text-2xl font-bold text-dark-700">{stats.total_attempts}</div>
                  <div className="text-xs text-surface-400 mt-1">Всего попыток</div>
                </div>
              </div>
            ) : (
              <div className="text-center py-4 text-surface-300">Нет данных</div>
            )}
            <div className="mt-4 pt-4 border-t border-surface-100">
              <button onClick={() => setStatsUserId(null)} className="btn-secondary btn-sm w-full">Закрыть</button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}
