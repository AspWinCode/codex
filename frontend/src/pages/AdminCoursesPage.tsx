import { useEffect, useState } from 'react';
import { useNavigate } from 'react-router-dom';
import { adminCoursesApi, type AdminCourse } from '../api';

export default function AdminCoursesPage() {
  const [courses, setCourses] = useState<AdminCourse[]>([]);
  const [loading, setLoading] = useState(true);
  const [showCreate, setShowCreate] = useState(false);
  const [createForm, setCreateForm] = useState<{
    title: string;
    description: string;
    short_description: string;
    status: AdminCourse['status'];
  }>({ title: '', description: '', short_description: '', status: 'draft' });
  const [editingId, setEditingId] = useState<number | null>(null);
  const [editForm, setEditForm] = useState<{
    title: string;
    description: string;
    short_description: string;
    status: AdminCourse['status'];
  }>({ title: '', description: '', short_description: '', status: 'draft' });
  const [submitting, setSubmitting] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const navigate = useNavigate();

  const load = () => {
    setError(null);
    adminCoursesApi.list()
      .then(({ data }) => setCourses(data))
      .catch((e) => setError(e.response?.data?.detail || e.message || 'Ошибка загрузки'))
      .finally(() => setLoading(false));
  };

  useEffect(() => { load(); }, []);

  const handleCreateCourse = async (e: React.FormEvent) => {
    e.preventDefault();
    setSubmitting(true);
    try {
      await adminCoursesApi.create({
        title: createForm.title,
        description: createForm.description || undefined,
        short_description: createForm.short_description || undefined,
        status: createForm.status,
      });
      setCreateForm({ title: '', description: '', short_description: '', status: 'draft' });
      setShowCreate(false);
      load();
    } catch (e: any) {
      const d = e.response?.data?.detail;
      setError(
        typeof d === 'string' ? d
          : Array.isArray(d) ? d.map((x: any) => x.msg || x.loc?.join('.')).join('; ')
          : d && typeof d === 'object' ? JSON.stringify(d) : e.message || 'Ошибка создания'
      );
    } finally {
      setSubmitting(false);
    }
  };

  const handleUpdateCourse = async (e: React.FormEvent) => {
    e.preventDefault();
    if (editingId == null) return;
    setSubmitting(true);
    try {
      await adminCoursesApi.update(editingId, {
        title: editForm.title,
        description: editForm.description || undefined,
        short_description: editForm.short_description || undefined,
        status: editForm.status,
      });
      setEditingId(null);
      load();
    } catch (e: any) {
      setError(e.response?.data?.detail || e.message || 'Ошибка сохранения');
    } finally {
      setSubmitting(false);
    }
  };

  const handlePublish = async (c: AdminCourse) => {
    setSubmitting(true);
    try {
      await adminCoursesApi.update(c.id, { status: 'published' });
      load();
    } catch (e: any) {
      setError(e.response?.data?.detail || e.message || 'Ошибка');
    } finally {
      setSubmitting(false);
    }
  };

  const handleUnpublish = async (c: AdminCourse) => {
    setSubmitting(true);
    try {
      await adminCoursesApi.update(c.id, { status: 'draft' });
      load();
    } catch (e: any) {
      setError(e.response?.data?.detail || e.message || 'Ошибка');
    } finally {
      setSubmitting(false);
    }
  };

  const handleDeleteCourse = async (id: number) => {
    if (!confirm('Удалить курс? Это действие нельзя отменить.')) return;
    setSubmitting(true);
    try {
      await adminCoursesApi.delete(id);
      load();
    } catch (e: any) {
      setError(e.response?.data?.detail || e.message || 'Ошибка удаления');
    } finally {
      setSubmitting(false);
    }
  };

  if (loading) return <div className="text-center py-20 text-surface-300">Загрузка...</div>;

  return (
    <div>
      <div className="flex items-center justify-between mb-6">
        <h1 className="text-2xl font-bold">Управление курсами</h1>
        <button
          type="button"
          onClick={() => setShowCreate(!showCreate)}
          className="btn-primary"
        >
          + Курс
        </button>
      </div>

      {error && (
        <div className="card mb-4 bg-red-50 text-red-700 border border-red-200">
          {error}
          <button type="button" onClick={() => setError(null)} className="ml-2 underline">Закрыть</button>
        </div>
      )}

      {showCreate && (
        <form onSubmit={handleCreateCourse} className="card mb-6 space-y-4">
          <h2 className="font-semibold">Новый курс</h2>
          <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
            <div>
              <label className="block text-sm font-medium mb-1">Название</label>
              <input
                className="input w-full"
                value={createForm.title}
                onChange={(e) => setCreateForm({ ...createForm, title: e.target.value })}
                required
              />
            </div>
            <div>
              <label className="block text-sm font-medium mb-1">Статус</label>
              <select
                className="input w-full"
                value={createForm.status}
                onChange={(e) => setCreateForm({ ...createForm, status: e.target.value as AdminCourse['status'] })}
              >
                <option value="draft">Черновик</option>
                <option value="published">Опубликован</option>
              </select>
            </div>
          </div>
          <div>
            <label className="block text-sm font-medium mb-1">Описание</label>
            <textarea
              className="input w-full"
              rows={2}
              value={createForm.description}
              onChange={(e) => setCreateForm({ ...createForm, description: e.target.value })}
            />
          </div>
          <div className="flex gap-2">
            <button type="submit" className="btn-primary btn-sm" disabled={submitting}>Создать</button>
            <button type="button" onClick={() => setShowCreate(false)} className="btn-secondary btn-sm">Отмена</button>
          </div>
        </form>
      )}

      <div className="space-y-4">
        {courses.map((c) => (
          <div key={c.id} className="card">
            <div className="flex items-center justify-between flex-wrap gap-2">
              <div className="flex items-center gap-2 flex-wrap">
                <div className="text-lg font-semibold">
                  {c.title}
                </div>
                <span className={`badge-${c.status === 'published' ? 'green' : 'yellow'}`}>
                  {c.status === 'published' ? 'Опубликован' : 'Черновик'}
                </span>
                {c.status === 'archived' && <span className="badge-gray">Архив</span>}
              </div>
              <div className="flex gap-2 flex-wrap">
                {editingId === c.id ? null : (
                  <>
                    {c.status === 'draft' && (
                      <button type="button" onClick={() => handlePublish(c)} className="btn-primary btn-sm" disabled={submitting}>
                        Опубликовать
                      </button>
                    )}
                    {c.status === 'published' && (
                      <button type="button" onClick={() => handleUnpublish(c)} className="btn-secondary btn-sm" disabled={submitting}>
                        Снять с публикации
                      </button>
                    )}
                    <button
                      type="button"
                      onClick={() => {
                        setEditingId(c.id);
                        setEditForm({
                          title: c.title,
                          description: c.description || '',
                          short_description: c.short_description || '',
                          status: c.status,
                        });
                      }}
                      className="btn-secondary btn-sm"
                    >
                      Редактировать
                    </button>
                    <button
                      type="button"
                      onClick={() => navigate(`/admin/courses/${c.id}`)}
                      className="btn-secondary btn-sm"
                    >
                      Редактор структуры
                    </button>
                    <button
                      type="button"
                      onClick={() => handleDeleteCourse(c.id)}
                      className="btn-danger btn-sm"
                      disabled={submitting}
                    >
                      Удалить
                    </button>
                  </>
                )}
              </div>
            </div>

            {editingId === c.id && (
              <form onSubmit={handleUpdateCourse} className="mt-4 p-4 bg-surface-50 rounded-lg space-y-4">
                <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                  <div>
                    <label className="block text-sm font-medium mb-1">Название</label>
                    <input
                      className="input w-full"
                      value={editForm.title}
                      onChange={(e) => setEditForm({ ...editForm, title: e.target.value })}
                      required
                    />
                  </div>
                  <div>
                    <label className="block text-sm font-medium mb-1">Статус</label>
                    <select
                      className="input w-full"
                      value={editForm.status}
                      onChange={(e) => setEditForm({ ...editForm, status: e.target.value as AdminCourse['status'] })}
                    >
                      <option value="draft">Черновик</option>
                      <option value="published">Опубликован</option>
                    </select>
                  </div>
                </div>
                <div>
                  <label className="block text-sm font-medium mb-1">Описание</label>
                  <textarea
                    className="input w-full"
                    rows={2}
                    value={editForm.description}
                    onChange={(e) => setEditForm({ ...editForm, description: e.target.value })}
                  />
                </div>
                <div className="flex gap-2">
                  <button type="submit" className="btn-primary btn-sm" disabled={submitting}>Сохранить</button>
                  <button type="button" onClick={() => setEditingId(null)} className="btn-secondary btn-sm">Отмена</button>
                </div>
              </form>
            )}

            {/* Структура и задачи редактируются на отдельной странице AdminCourseEditorPage */}
          </div>
        ))}
      </div>
    </div>
  );
}
