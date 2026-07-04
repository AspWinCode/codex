import { useState } from 'react';
import { Link, useNavigate, useSearchParams } from 'react-router-dom';
import { usersApi } from '../api';

export default function ResetPasswordPage() {
  const [params] = useSearchParams();
  const token = params.get('token') || '';
  const navigate = useNavigate();

  const [password, setPassword] = useState('');
  const [confirm, setConfirm] = useState('');
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState('');
  const [done, setDone] = useState(false);

  if (!token) {
    return (
      <div className="min-h-screen bg-surface-50 flex items-center justify-center">
        <div className="bg-white rounded-2xl shadow-md p-8 w-full max-w-sm text-center">
          <div className="text-red-600 font-medium mb-4">Ссылка недействительна</div>
          <Link to="/login" className="btn-primary w-full block">Вернуться к входу</Link>
        </div>
      </div>
    );
  }

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    if (password !== confirm) {
      setError('Пароли не совпадают');
      return;
    }
    setError('');
    setLoading(true);
    try {
      await usersApi.resetPasswordByToken(token, password);
      setDone(true);
      setTimeout(() => navigate('/login'), 2000);
    } catch (err: any) {
      setError(err.response?.data?.detail || 'Ошибка. Ссылка устарела или уже использована.');
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="min-h-screen bg-surface-50 flex items-center justify-center">
      <div className="bg-white rounded-2xl shadow-md p-8 w-full max-w-sm">
        <h1 className="text-xl font-bold mb-6 text-dark-900">Новый пароль</h1>
        {done ? (
          <div className="text-center">
            <div className="text-green-600 font-medium mb-2">Пароль изменён!</div>
            <p className="text-sm text-surface-400">Перенаправление на страницу входа...</p>
          </div>
        ) : (
          <form onSubmit={handleSubmit} className="space-y-4">
            <div>
              <label className="block text-sm font-medium mb-1">Новый пароль</label>
              <input
                className="input"
                type="password"
                value={password}
                onChange={(e) => setPassword(e.target.value)}
                required
                minLength={4}
              />
            </div>
            <div>
              <label className="block text-sm font-medium mb-1">Повторите пароль</label>
              <input
                className="input"
                type="password"
                value={confirm}
                onChange={(e) => setConfirm(e.target.value)}
                required
                minLength={4}
              />
            </div>
            {error && <div className="text-red-600 text-sm">{error}</div>}
            <button type="submit" className="btn-primary w-full" disabled={loading}>
              {loading ? 'Сохранение...' : 'Сохранить пароль'}
            </button>
          </form>
        )}
      </div>
    </div>
  );
}
