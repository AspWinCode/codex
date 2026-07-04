import { useState } from 'react';
import { Link } from 'react-router-dom';
import { usersApi } from '../api';

export default function ForgotPasswordPage() {
  const [email, setEmail] = useState('');
  const [sent, setSent] = useState(false);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState('');

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setError('');
    setLoading(true);
    try {
      await usersApi.forgotPassword(email);
      setSent(true);
    } catch {
      setError('Ошибка. Попробуйте позже.');
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="min-h-screen bg-surface-50 flex items-center justify-center">
      <div className="bg-white rounded-2xl shadow-md p-8 w-full max-w-sm">
        <h1 className="text-xl font-bold mb-6 text-dark-900">Восстановление пароля</h1>
        {sent ? (
          <div className="text-center space-y-4">
            <div className="text-green-600 font-medium">Письмо отправлено!</div>
            <p className="text-sm text-surface-400">
              Если указанный email зарегистрирован, на него придёт ссылка для сброса пароля.
            </p>
            <Link to="/login" className="btn-primary w-full block text-center mt-4">Вернуться к входу</Link>
          </div>
        ) : (
          <form onSubmit={handleSubmit} className="space-y-4">
            <div>
              <label className="block text-sm font-medium mb-1">Email</label>
              <input
                className="input"
                type="email"
                value={email}
                onChange={(e) => setEmail(e.target.value)}
                required
                placeholder="your@email.com"
              />
            </div>
            {error && <div className="text-red-600 text-sm">{error}</div>}
            <button type="submit" className="btn-primary w-full" disabled={loading}>
              {loading ? 'Отправка...' : 'Отправить ссылку'}
            </button>
            <div className="text-center">
              <Link to="/login" className="text-sm text-primary-600 hover:underline">Вернуться к входу</Link>
            </div>
          </form>
        )}
      </div>
    </div>
  );
}
