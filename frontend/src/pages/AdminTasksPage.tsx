import { useEffect, useState } from 'react';
import { tasksApi } from '../api';
import type { Task } from '../types';
import { Link } from 'react-router-dom';

type TaskForm = {
  title: string;
  description: string;
  task_type: string;
  runner_type: string;
  submodule_id: string;
  sql_schema: string;
  sql_seed: string;
  tests: { test_type: string; input_data: string; expected_output: string }[];
  hints: { hint_level: number; unlock_attempts: number; content: string }[];
};

const defaultForm: TaskForm = {
  title: '', description: '', task_type: 'python_io', runner_type: 'stdin_runner',
  submodule_id: '', sql_schema: '', sql_seed: '',
  tests: [{ test_type: 'public', input_data: '', expected_output: '' }],
  hints: [],
};

const RUNNER_MAP: Record<string, string> = {
  python_io: 'stdin_runner',
  python_oop: 'pytest_runner',
  python_numpy: 'pytest_runner',
  sql_query: 'sql_runner',
  cpp_io: 'cpp_runner',
  js_io: 'js_runner',
};

export default function AdminTasksPage() {
  const [tasks, setTasks] = useState<Task[]>([]);
  const [showCreate, setShowCreate] = useState(false);
  const [form, setForm] = useState<TaskForm>({ ...defaultForm });
  const [loading, setLoading] = useState(true);

  const load = () => tasksApi.list().then(({ data }) => setTasks(data)).finally(() => setLoading(false));
  useEffect(() => { load(); }, []);

  const handleCreate = async (e: React.FormEvent) => {
    e.preventDefault();
    await tasksApi.create({
      title: form.title,
      description: form.description || null,
      task_type: form.task_type,
      runner_type: form.runner_type,
      submodule_id: form.submodule_id ? parseInt(form.submodule_id) : null,
      sql_schema: form.sql_schema || null,
      sql_seed: form.sql_seed || null,
      tests: form.tests.filter((t) => t.expected_output),
      hints: form.hints.filter((h) => h.content),
    });
    setForm({ ...defaultForm });
    setShowCreate(false);
    load();
  };

  const handleDelete = async (id: number) => {
    if (!confirm('Удалить задачу?')) return;
    await tasksApi.delete(id);
    load();
  };

  const addTest = () => setForm({ ...form, tests: [...form.tests, { test_type: 'public', input_data: '', expected_output: '' }] });
  const addHint = () => setForm({ ...form, hints: [...form.hints, { hint_level: form.hints.length + 1, unlock_attempts: (form.hints.length + 1) * 2, content: '' }] });

  const updateTaskType = (tt: string) => setForm({ ...form, task_type: tt, runner_type: RUNNER_MAP[tt] || 'stdin_runner' });

  if (loading) return <div className="text-center py-20 text-surface-300">Загрузка...</div>;

  return (
    <div>
      <div className="flex items-center justify-between mb-6">
        <h1 className="text-2xl font-bold">Управление задачами</h1>
        <button onClick={() => setShowCreate(!showCreate)} className="btn-primary">+ Задача</button>
      </div>
      {showCreate && (
        <form onSubmit={handleCreate} className="card mb-6 space-y-4">
          <div className="grid grid-cols-2 gap-4">
            <div>
              <label className="block text-sm font-medium mb-1">Название</label>
              <input className="input" value={form.title} onChange={(e) => setForm({ ...form, title: e.target.value })} required />
            </div>
            <div>
              <label className="block text-sm font-medium mb-1">Тип задачи</label>
              <select className="input" value={form.task_type} onChange={(e) => updateTaskType(e.target.value)}>
                <option value="python_io">Python IO</option>
                <option value="python_oop">Python OOP</option>
                <option value="python_numpy">Python NumPy</option>
                <option value="sql_query">SQL Query</option>
                <option value="cpp_io">C++ IO</option>
                <option value="js_io">JavaScript IO</option>
              </select>
            </div>
          </div>
          <div>
            <label className="block text-sm font-medium mb-1">Описание</label>
            <textarea className="input" rows={3} value={form.description} onChange={(e) => setForm({ ...form, description: e.target.value })} />
          </div>
          <div className="grid grid-cols-2 gap-4">
            <div>
              <label className="block text-sm font-medium mb-1">ID подмодуля (необязательно)</label>
              <input className="input" type="number" value={form.submodule_id} onChange={(e) => setForm({ ...form, submodule_id: e.target.value })} />
            </div>
            <div>
              <label className="block text-sm font-medium mb-1">Runner</label>
              <input className="input bg-surface-50" value={form.runner_type} readOnly />
            </div>
          </div>
          {form.task_type === 'sql_query' && (
            <div className="grid grid-cols-2 gap-4">
              <div>
                <label className="block text-sm font-medium mb-1">SQL Schema</label>
                <textarea className="input font-mono text-sm" rows={4} value={form.sql_schema} onChange={(e) => setForm({ ...form, sql_schema: e.target.value })} />
              </div>
              <div>
                <label className="block text-sm font-medium mb-1">SQL Seed</label>
                <textarea className="input font-mono text-sm" rows={4} value={form.sql_seed} onChange={(e) => setForm({ ...form, sql_seed: e.target.value })} />
              </div>
            </div>
          )}
          <div>
            <div className="flex items-center justify-between mb-2">
              <label className="text-sm font-medium">Тесты</label>
              <button type="button" onClick={addTest} className="text-xs text-primary-600 hover:underline">+ Тест</button>
            </div>
            {form.tests.map((t, i) => (
              <div key={i} className="grid grid-cols-3 gap-2 mb-2">
                <select className="input text-sm" value={t.test_type} onChange={(e) => { const tests = [...form.tests]; tests[i] = { ...t, test_type: e.target.value }; setForm({ ...form, tests }); }}>
                  <option value="public">Public</option>
                  <option value="hidden">Hidden</option>
                </select>
                <textarea className="input text-sm font-mono" rows={2} placeholder="Input" value={t.input_data} onChange={(e) => { const tests = [...form.tests]; tests[i] = { ...t, input_data: e.target.value }; setForm({ ...form, tests }); }} />
                <textarea className="input text-sm font-mono" rows={2} placeholder="Expected output" value={t.expected_output} onChange={(e) => { const tests = [...form.tests]; tests[i] = { ...t, expected_output: e.target.value }; setForm({ ...form, tests }); }} />
              </div>
            ))}
          </div>
          <div>
            <div className="flex items-center justify-between mb-2">
              <label className="text-sm font-medium">Подсказки</label>
              <button type="button" onClick={addHint} className="text-xs text-primary-600 hover:underline">+ Подсказка</button>
            </div>
            {form.hints.map((h, i) => (
              <div key={i} className="grid grid-cols-3 gap-2 mb-2">
                <input className="input text-sm" type="number" placeholder="Уровень" value={h.hint_level} onChange={(e) => { const hints = [...form.hints]; hints[i] = { ...h, hint_level: parseInt(e.target.value) || 1 }; setForm({ ...form, hints }); }} />
                <input className="input text-sm" type="number" placeholder="После N попыток" value={h.unlock_attempts} onChange={(e) => { const hints = [...form.hints]; hints[i] = { ...h, unlock_attempts: parseInt(e.target.value) || 0 }; setForm({ ...form, hints }); }} />
                <textarea className="input text-sm" rows={2} placeholder="Текст подсказки" value={h.content} onChange={(e) => { const hints = [...form.hints]; hints[i] = { ...h, content: e.target.value }; setForm({ ...form, hints }); }} />
              </div>
            ))}
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
              <th className="px-4 py-3 font-medium">Название</th>
              <th className="px-4 py-3 font-medium">Тип</th>
              <th className="px-4 py-3 font-medium">Статус</th>
              <th className="px-4 py-3 font-medium">Действия</th>
            </tr>
          </thead>
          <tbody>
            {tasks.map((t) => (
              <tr key={t.id} className="border-t border-surface-100">
                <td className="px-4 py-3">{t.id}</td>
                <td className="px-4 py-3 font-medium">
                  <Link to={`/task/${t.id}`} className="text-primary-600 hover:underline">{t.title}</Link>
                </td>
                <td className="px-4 py-3"><span className="badge-blue">{t.task_type}</span></td>
                <td className="px-4 py-3"><span className={t.status === 'published' ? 'badge-green' : 'badge-yellow'}>{t.status}</span></td>
                <td className="px-4 py-3">
                  <button onClick={() => handleDelete(t.id)} className="text-xs text-red-600 hover:underline">Удалить</button>
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </div>
  );
}
