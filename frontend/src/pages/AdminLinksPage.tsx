import { useEffect, useState } from 'react';
import { personalLinksApi } from '../api';
import type { PersonalLink } from '../types';

export default function AdminLinksPage() {
  const [links, setLinks] = useState<PersonalLink[]>([]);
  const [showCreate, setShowCreate] = useState(false);
  const [form, setForm] = useState({ task_id: '', user_id: '', usage_limit: '' });
  const [loading, setLoading] = useState(true);

  const load = () => personalLinksApi.list().then(({ data }) => setLinks(data)).finally(() => setLoading(false));
  useEffect(() => { load(); }, []);

  const handleCreate = async (e: React.FormEvent) => {
    e.preventDefault();
    await personalLinksApi.create({
      task_id: parseInt(form.task_id),
      user_id: parseInt(form.user_id),
      usage_limit: form.usage_limit ? parseInt(form.usage_limit) : undefined,
    });
    setForm({ task_id: '', user_id: '', usage_limit: '' });
    setShowCreate(false);
    load();
  };

  if (loading) return <div className="text-center py-20 text-surface-300">Загрузка...</div>;

  return (
    <div>
      <div className="flex items-center justify-between mb-6">
        <h1 className="text-2xl font-bold">Персональные ссылки</h1>
        <button onClick={() => setShowCreate(!showCreate)} className="btn-primary">+ Ссылка</button>
      </div>
      {showCreate && (
        <form onSubmit={handleCreate} className="card mb-6 space-y-4">
          <div className="grid grid-cols-3 gap-4">
            <div>
              <label className="block text-sm font-medium mb-1">Task ID</label>
              <input className="input" type="number" value={form.task_id} onChange={(e) => setForm({ ...form, task_id: e.target.value })} required />
            </div>
            <div>
              <label className="block text-sm font-medium mb-1">User ID</label>
              <input className="input" type="number" value={form.user_id} onChange={(e) => setForm({ ...form, user_id: e.target.value })} required />
            </div>
            <div>
              <label className="block text-sm font-medium mb-1">Лимит использований</label>
              <input className="input" type="number" value={form.usage_limit} onChange={(e) => setForm({ ...form, usage_limit: e.target.value })} placeholder="Без лимита" />
            </div>
          </div>
          <div className="flex gap-2">
            <button type="submit" className="btn-primary btn-sm">Создать</button>
            <button type="button" onClick={() => setShowCreate(false)} className="btn-secondary btn-sm">Отмена</button>
          </div>
        </form>
      )}
      <div className="card overflow-hidden p-0">
        <table className="w-full text-sm">
          <thead>
            <tr className="bg-surface-50 text-left">
              <th className="px-4 py-3 font-medium">ID</th>
              <th className="px-4 py-3 font-medium">Задача</th>
              <th className="px-4 py-3 font-medium">Пользователь</th>
              <th className="px-4 py-3 font-medium">Ссылка</th>
              <th className="px-4 py-3 font-medium">Использований</th>
            </tr>
          </thead>
          <tbody>
            {links.map((l) => (
              <tr key={l.id} className="border-t border-surface-100">
                <td className="px-4 py-3">{l.id}</td>
                <td className="px-4 py-3">#{l.task_id}</td>
                <td className="px-4 py-3">#{l.user_id}</td>
                <td className="px-4 py-3">
                  <code className="bg-surface-100 px-2 py-0.5 rounded text-xs">{l.url}</code>
                </td>
                <td className="px-4 py-3">{l.usage_count}{l.usage_limit ? `/${l.usage_limit}` : ''}</td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </div>
  );
}
