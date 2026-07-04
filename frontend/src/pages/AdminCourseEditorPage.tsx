import { useEffect, useState } from 'react';
import { useNavigate, useParams, Link } from 'react-router-dom';
import {
  adminCoursesApi,
  adminNodeContentApi,
  type AdminCourse,
  type CourseNodeContent,
  type CourseNodeDetails,
  type CourseNodeStatus,
  type CourseNodeTask,
  type CourseNodeTree,
  type CourseNodeType,
} from '../api';

const NODE_TYPE_LABELS: Record<CourseNodeType, string> = {
  module: 'Модуль',
  submodule: 'Подмодуль',
  topic: 'Тема',
  subtopic: 'Подтема',
};

const NODE_ICONS: Record<CourseNodeType, string> = {
  module: '📁',
  submodule: '📂',
  topic: '📄',
  subtopic: '📃',
};

// Все допустимые дочерние типы для каждого родителя (гибкая иерархия)
const ALLOWED_CHILD_TYPES: Record<CourseNodeType, CourseNodeType[]> = {
  module:    ['submodule', 'topic', 'subtopic'],
  submodule: ['topic', 'subtopic'],
  topic:     ['subtopic'],
  subtopic:  [],
};

interface CreateNodeForm {
  parentId: number | null;
  parentType: CourseNodeType | null;
  type: CourseNodeType;
  title: string;
}

export default function AdminCourseEditorPage() {
  const { courseId } = useParams<{ courseId: string }>();
  const navigate = useNavigate();
  const [course, setCourse] = useState<AdminCourse | null>(null);
  const [tree, setTree] = useState<CourseNodeTree[]>([]);
  const [selectedNodeId, setSelectedNodeId] = useState<number | null>(null);
  const [selectedNode, setSelectedNode] = useState<CourseNodeDetails | null>(null);
  const [nodeTasks, setNodeTasks] = useState<CourseNodeTask[]>([]);
  const [nodeContent, setNodeContent] = useState<CourseNodeContent[]>([]);
  const [loading, setLoading] = useState(true);
  const [saving, setSaving] = useState(false);
  const [error, setError] = useState<string | null>(null);

  // Форма создания/редактирования лекции
  const [contentForm, setContentForm] = useState<{ title: string; content: string } | null>(null);
  const [editingContentId, setEditingContentId] = useState<number | null>(null);

  // Форма создания узла
  const [createForm, setCreateForm] = useState<CreateNodeForm | null>(null);
  const [createTitle, setCreateTitle] = useState('');
  const [creating, setCreating] = useState(false);

  const loadCourse = async () => {
    if (!courseId) return;
    setError(null);
    try {
      const [courseRes, treeRes] = await Promise.all([
        adminCoursesApi.get(Number(courseId)),
        adminCoursesApi.getTree(Number(courseId)),
      ]);
      setCourse(courseRes.data);
      setTree(treeRes.data);
    } catch (e: any) {
      setError(e.response?.data?.detail || e.message || 'Ошибка загрузки курса');
    } finally {
      setLoading(false);
    }
  };

  const loadNode = async (nodeId: number) => {
    try {
      const [nodeRes, tasksRes, contentRes] = await Promise.all([
        adminCoursesApi.getNode(nodeId),
        adminCoursesApi.getNodeTasks(nodeId),
        adminNodeContentApi.list(nodeId),
      ]);
      setSelectedNode(nodeRes.data);
      setNodeTasks(tasksRes.data);
      setNodeContent(contentRes.data);
    } catch (e: any) {
      setError(e.response?.data?.detail || e.message || 'Ошибка загрузки узла');
    }
  };

  useEffect(() => {
    void loadCourse();
  }, [courseId]);

  useEffect(() => {
    if (selectedNodeId != null) {
      void loadNode(selectedNodeId);
    } else {
      setSelectedNode(null);
      setNodeTasks([]);
    }
  }, [selectedNodeId]);

  // ── Сохранить узел ──────────────────────────────────────────────────────────
  const handleUpdateNode = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!selectedNode) return;
    setSaving(true);
    try {
      await adminCoursesApi.updateNode(selectedNode.id, {
        title: selectedNode.title,
        description: selectedNode.description || undefined,
        sort_order: selectedNode.sort_order,
        status: selectedNode.status,
      });
      await loadCourse();
      await loadNode(selectedNode.id);
    } catch (e: any) {
      setError(e.response?.data?.detail || e.message || 'Ошибка сохранения узла');
    } finally {
      setSaving(false);
    }
  };

  // ── Удалить узел ────────────────────────────────────────────────────────────
  const handleDeleteNode = async (nodeId: number, title: string) => {
    if (!confirm(`Удалить «${title}» и все вложенные элементы?`)) return;
    setSaving(true);
    try {
      await adminCoursesApi.deleteNode(nodeId);
      if (selectedNodeId === nodeId) {
        setSelectedNodeId(null);
      }
      await loadCourse();
    } catch (e: any) {
      setError(e.response?.data?.detail || e.message || 'Ошибка удаления узла');
    } finally {
      setSaving(false);
    }
  };

  // ── Архивировать / разархивировать ──────────────────────────────────────────
  const handleArchiveNode = async () => {
    if (!selectedNode) return;
    setSaving(true);
    try {
      if (selectedNode.status === 'archived') {
        await adminCoursesApi.unarchiveNode(selectedNode.id);
      } else {
        await adminCoursesApi.archiveNode(selectedNode.id);
      }
      await loadCourse();
      await loadNode(selectedNode.id);
    } catch (e: any) {
      setError(e.response?.data?.detail || e.message || 'Ошибка архивирования');
    } finally {
      setSaving(false);
    }
  };

  // ── Открыть форму создания ──────────────────────────────────────────────────
  const openCreateForm = (parentId: number | null, parentType: CourseNodeType | null) => {
    const allowedTypes = parentType === null
      ? (['module', 'submodule', 'topic', 'subtopic'] as CourseNodeType[])
      : ALLOWED_CHILD_TYPES[parentType];
    const defaultType = allowedTypes[0] ?? 'module';
    setCreateForm({ parentId, parentType, type: defaultType, title: '' });
    setCreateTitle('');
  };

  // ── Создать узел ────────────────────────────────────────────────────────────
  const handleCreateNode = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!createForm || !courseId || !createTitle.trim()) return;
    setCreating(true);
    try {
      const res = await adminCoursesApi.createNode(Number(courseId), {
        parent_id: createForm.parentId ?? undefined,
        type: createForm.type,
        title: createTitle.trim(),
        status: 'published',
      });
      setCreateForm(null);
      setCreateTitle('');
      await loadCourse();
      setSelectedNodeId(res.data.id);
    } catch (e: any) {
      setError(e.response?.data?.detail || e.message || 'Ошибка создания узла');
    } finally {
      setCreating(false);
    }
  };

  // ── Задачи ──────────────────────────────────────────────────────────────────
  const handleAttachTask = async (e: React.FormEvent<HTMLFormElement>) => {
    e.preventDefault();
    if (!selectedNode) return;
    const form = e.currentTarget; // сохраняем до await, иначе после него currentTarget = null
    const formData = new FormData(form);
    const title = String(formData.get('title') || '').trim();
    if (!title) return;
    setSaving(true);
    try {
      const res = await adminCoursesApi.attachTaskToNode(selectedNode.id, {
        create_new_task: true,
        task_title: title,
      });
      form.reset();
      await loadNode(selectedNode.id);
      await loadCourse();
      // Открываем редактор новой задачи чтобы заполнить тесты, описание, тип
      const taskId = res.data.task_id;
      const backUrl = `/admin/courses/${courseId}`;
      navigate(`/admin/tasks/${taskId}?back=${encodeURIComponent(backUrl)}`);
    } catch (e: any) {
      setError(e.response?.data?.detail || e.message || 'Ошибка добавления задачи');
    } finally {
      setSaving(false);
    }
  };

  const handleDetachTask = async (nodeTaskId: number) => {
    if (!selectedNode) return;
    if (!confirm('Удалить задачу из узла?')) return;
    setSaving(true);
    try {
      await adminCoursesApi.detachTaskFromNode(selectedNode.id, nodeTaskId);
      await loadNode(selectedNode.id);
      await loadCourse();
    } catch (e: any) {
      setError(e.response?.data?.detail || e.message || 'Ошибка удаления задачи');
    } finally {
      setSaving(false);
    }
  };

  // ── Лекционные материалы ────────────────────────────────────────────────────
  const handleSaveContent = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!selectedNode || !contentForm) return;
    setSaving(true);
    try {
      if (editingContentId != null) {
        await adminNodeContentApi.update(selectedNode.id, editingContentId, contentForm);
      } else {
        await adminNodeContentApi.create(selectedNode.id, {
          ...contentForm,
          sort_order: nodeContent.length,
        });
      }
      setContentForm(null);
      setEditingContentId(null);
      await loadNode(selectedNode.id);
    } catch (e: any) {
      setError(e.response?.data?.detail || e.message || 'Ошибка сохранения лекции');
    } finally {
      setSaving(false);
    }
  };

  const handleDeleteContent = async (contentId: number) => {
    if (!selectedNode || !confirm('Удалить лекционный материал?')) return;
    setSaving(true);
    try {
      await adminNodeContentApi.delete(selectedNode.id, contentId);
      await loadNode(selectedNode.id);
    } catch (e: any) {
      setError(e.response?.data?.detail || e.message || 'Ошибка удаления');
    } finally {
      setSaving(false);
    }
  };

  // ── Переместить узел вверх/вниз ─────────────────────────────────────────────
  const handleMoveNode = async (siblings: CourseNodeTree[], index: number, direction: 'up' | 'down') => {
    const targetIdx = direction === 'up' ? index - 1 : index + 1;
    if (targetIdx < 0 || targetIdx >= siblings.length) return;
    const nodeA = siblings[index];
    const nodeB = siblings[targetIdx];
    setSaving(true);
    try {
      // Меняем sort_order местами
      const orderA = nodeA.sort_order;
      const orderB = nodeB.sort_order;
      // Если sort_order одинаковые, используем индексы
      const newOrderA = orderA === orderB ? targetIdx : orderB;
      const newOrderB = orderA === orderB ? index : orderA;
      await Promise.all([
        adminCoursesApi.updateNode(nodeA.id, { sort_order: newOrderA }),
        adminCoursesApi.updateNode(nodeB.id, { sort_order: newOrderB }),
      ]);
      await loadCourse();
    } catch (e: any) {
      setError(e.response?.data?.detail || e.message || 'Ошибка перемещения');
    } finally {
      setSaving(false);
    }
  };

  // ── Дерево ──────────────────────────────────────────────────────────────────
  const renderTree = (nodes: CourseNodeTree[], depth = 0) => (
    <div className={depth > 0 ? 'ml-3 border-l border-surface-200 pl-3' : ''}>
      {nodes.map((node, idx) => {
        const allowedChildren = ALLOWED_CHILD_TYPES[node.type];
        const canAddChild = allowedChildren.length > 0;
        return (
          <div key={node.id} className="mb-1">
            <div className="flex items-center gap-1 group">
              {/* Кнопки перемещения вверх/вниз */}
              <div className="flex flex-col shrink-0 opacity-0 group-hover:opacity-100 transition-opacity">
                <button
                  type="button"
                  title="Переместить вверх"
                  onClick={() => handleMoveNode(nodes, idx, 'up')}
                  disabled={saving || idx === 0}
                  className="text-[10px] leading-none px-0.5 text-surface-400 hover:text-primary-600 disabled:opacity-20 disabled:cursor-default"
                >
                  ▲
                </button>
                <button
                  type="button"
                  title="Переместить вниз"
                  onClick={() => handleMoveNode(nodes, idx, 'down')}
                  disabled={saving || idx === nodes.length - 1}
                  className="text-[10px] leading-none px-0.5 text-surface-400 hover:text-primary-600 disabled:opacity-20 disabled:cursor-default"
                >
                  ▼
                </button>
              </div>

              {/* Кнопка выбора узла */}
              <button
                type="button"
                onClick={() => setSelectedNodeId(node.id)}
                className={`flex items-center gap-1 flex-1 text-left text-sm px-2 py-1 rounded truncate ${
                  selectedNodeId === node.id
                    ? 'bg-primary-50 text-primary-700 font-medium'
                    : 'hover:bg-surface-50'
                }`}
              >
                <span className="shrink-0">{NODE_ICONS[node.type]}</span>
                <span className="truncate">{node.title}</span>
                <span className="text-xs text-surface-400 ml-auto shrink-0 pl-1">
                  {node.task_count > 0 ? `${node.task_count} зад.` : ''}
                </span>
              </button>

              {/* Кнопка «+ дочерний» */}
              {canAddChild && (
                <button
                  type="button"
                  title="Добавить вложенный узел"
                  onClick={() => openCreateForm(node.id, node.type)}
                  className="shrink-0 text-xs px-1.5 py-0.5 rounded text-primary-600 hover:bg-primary-50 opacity-0 group-hover:opacity-100 transition-opacity"
                >
                  +
                </button>
              )}

              {/* Кнопка удаления */}
              <button
                type="button"
                title="Удалить"
                onClick={() => handleDeleteNode(node.id, node.title)}
                disabled={saving}
                className="shrink-0 text-xs px-1 py-0.5 rounded text-red-400 hover:text-red-600 hover:bg-red-50 opacity-0 group-hover:opacity-100 transition-opacity"
              >
                🗑
              </button>
            </div>

            {/* Встроенная форма создания дочернего узла */}
            {createForm && createForm.parentId === node.id && (
              <div className="ml-3 mt-1 mb-2 border-l-2 border-primary-200 pl-3">
                <form onSubmit={handleCreateNode} className="flex gap-2 items-center flex-wrap">
                  <select
                    className="input text-sm py-0.5"
                    value={createForm.type}
                    onChange={(e) =>
                      setCreateForm({ ...createForm, type: e.target.value as CourseNodeType })
                    }
                  >
                    {ALLOWED_CHILD_TYPES[node.type].map((t) => (
                      <option key={t} value={t}>
                        {NODE_ICONS[t]} {NODE_TYPE_LABELS[t]}
                      </option>
                    ))}
                  </select>
                  <input
                    autoFocus
                    className="input text-sm flex-1 min-w-[140px] py-0.5"
                    placeholder="Название"
                    value={createTitle}
                    onChange={(e) => setCreateTitle(e.target.value)}
                    required
                  />
                  <button type="submit" className="btn-primary btn-sm" disabled={creating}>
                    Создать
                  </button>
                  <button
                    type="button"
                    className="btn-secondary btn-sm"
                    onClick={() => setCreateForm(null)}
                  >
                    Отмена
                  </button>
                </form>
              </div>
            )}

            {node.children.length > 0 && renderTree(node.children, depth + 1)}
          </div>
        );
      })}
    </div>
  );

  if (loading) {
    return <div className="p-6 text-surface-400">Загрузка редактора курса...</div>;
  }

  if (!course) {
    return (
      <div className="p-6">
        <button type="button" className="btn-secondary mb-4" onClick={() => navigate('/admin/courses')}>
          ← Назад к списку курсов
        </button>
        <div className="text-red-600">Курс не найден.</div>
      </div>
    );
  }

  return (
    <div className="p-6 space-y-4">
      <button type="button" className="btn-secondary mb-2" onClick={() => navigate('/admin/courses')}>
        ← Назад к списку курсов
      </button>
      <h1 className="text-2xl font-bold mb-4">Редактор курса: {course.title}</h1>

      {error && (
        <div className="card mb-4 bg-red-50 text-red-700 border border-red-200 flex items-start justify-between gap-2">
          <span>{error}</span>
          <button type="button" onClick={() => setError(null)} className="shrink-0 underline text-sm">
            Закрыть
          </button>
        </div>
      )}

      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
        {/* ── Левая колонка: дерево ── */}
        <div className="card">
          <div className="flex items-center justify-between mb-3">
            <h2 className="font-semibold text-lg">Структура курса</h2>
            <button
              type="button"
              className="btn-primary btn-sm"
              onClick={() => openCreateForm(null, null)}
            >
              + Добавить
            </button>
          </div>

          {/* Форма создания узла верхнего уровня */}
          {createForm && createForm.parentId === null && (
            <div className="mb-3 border border-primary-200 rounded p-2 bg-primary-50">
              <form onSubmit={handleCreateNode} className="flex gap-2 items-center flex-wrap">
                <select
                  className="input text-sm py-0.5"
                  value={createForm.type}
                  onChange={(e) =>
                    setCreateForm({ ...createForm, type: e.target.value as CourseNodeType })
                  }
                >
                  {(['module', 'submodule', 'topic', 'subtopic'] as CourseNodeType[]).map((t) => (
                    <option key={t} value={t}>
                      {NODE_ICONS[t]} {NODE_TYPE_LABELS[t]}
                    </option>
                  ))}
                </select>
                <input
                  autoFocus
                  className="input text-sm flex-1 min-w-[140px] py-0.5"
                  placeholder="Название"
                  value={createTitle}
                  onChange={(e) => setCreateTitle(e.target.value)}
                  required
                />
                <button type="submit" className="btn-primary btn-sm" disabled={creating}>
                  Создать
                </button>
                <button
                  type="button"
                  className="btn-secondary btn-sm"
                  onClick={() => setCreateForm(null)}
                >
                  Отмена
                </button>
              </form>
            </div>
          )}

          {tree.length === 0 && !createForm ? (
            <div className="text-sm text-surface-400">
              Нет узлов. Нажмите «+ Добавить», чтобы начать.
            </div>
          ) : (
            renderTree(tree)
          )}
        </div>

        {/* ── Правая колонка: панель узла ── */}
        <div className="card">
          <h2 className="font-semibold text-lg mb-3">Свойства узла</h2>
          {!selectedNode ? (
            <div className="text-sm text-surface-400">Выберите узел в дереве слева.</div>
          ) : (
            <div className="space-y-4">
              <form onSubmit={handleUpdateNode} className="space-y-3">
                <div>
                  <label className="block text-sm font-medium mb-1">Название</label>
                  <input
                    className="input w-full"
                    value={selectedNode.title}
                    onChange={(e) => setSelectedNode({ ...selectedNode, title: e.target.value })}
                    required
                  />
                </div>
                <div>
                  <label className="block text-sm font-medium mb-1">Тип</label>
                  <div className="flex items-center gap-2">
                    <span className="text-lg">{NODE_ICONS[selectedNode.type]}</span>
                    <input
                      className="input w-full bg-surface-50"
                      value={NODE_TYPE_LABELS[selectedNode.type]}
                      disabled
                    />
                  </div>
                </div>
                <div>
                  <label className="block text-sm font-medium mb-1">Описание</label>
                  <textarea
                    className="input w-full"
                    rows={3}
                    value={selectedNode.description || ''}
                    onChange={(e) =>
                      setSelectedNode({ ...selectedNode, description: e.target.value })
                    }
                  />
                </div>
                <div className="grid grid-cols-2 gap-3">
                  <div>
                    <label className="block text-sm font-medium mb-1">Статус</label>
                    <select
                      className="input w-full"
                      value={selectedNode.status}
                      onChange={(e) =>
                        setSelectedNode({
                          ...selectedNode,
                          status: e.target.value as CourseNodeStatus,
                        })
                      }
                    >
                      <option value="draft">Черновик</option>
                      <option value="published">Опубликован</option>
                      <option value="archived">Архив</option>
                    </select>
                  </div>
                  <div>
                    <label className="block text-sm font-medium mb-1">Порядок</label>
                    <input
                      type="number"
                      className="input w-full"
                      value={selectedNode.sort_order}
                      onChange={(e) =>
                        setSelectedNode({ ...selectedNode, sort_order: Number(e.target.value) || 0 })
                      }
                    />
                  </div>
                </div>
                <div className="flex gap-2 flex-wrap">
                  <button type="submit" className="btn-primary btn-sm" disabled={saving}>
                    💾 Сохранить
                  </button>
                  <button
                    type="button"
                    className="btn-secondary btn-sm"
                    onClick={handleArchiveNode}
                    disabled={saving}
                  >
                    {selectedNode.status === 'archived' ? '📤 Разархивировать' : '📦 Архивировать'}
                  </button>
                  <button
                    type="button"
                    className="btn-sm bg-red-50 text-red-700 hover:bg-red-100 border border-red-200 rounded px-3 py-1"
                    onClick={() => handleDeleteNode(selectedNode.id, selectedNode.title)}
                    disabled={saving}
                  >
                    🗑 Удалить
                  </button>
                </div>
              </form>

              {/* Добавить дочерний узел из панели */}
              {ALLOWED_CHILD_TYPES[selectedNode.type].length > 0 && (
                <div className="pt-3 border-t border-surface-200">
                  <button
                    type="button"
                    className="btn-secondary btn-sm w-full"
                    onClick={() => openCreateForm(selectedNode.id, selectedNode.type)}
                  >
                    + Добавить вложенный узел
                  </button>
                </div>
              )}

              {/* Блок лекционных материалов */}
              <div className="pt-4 border-t border-surface-200">
                <div className="flex items-center justify-between mb-2">
                  <h3 className="font-semibold text-sm">📖 Лекционные материалы</h3>
                  {!contentForm && (
                    <button
                      type="button"
                      className="btn-secondary btn-sm"
                      onClick={() => {
                        setContentForm({ title: '', content: '' });
                        setEditingContentId(null);
                      }}
                    >
                      + Добавить
                    </button>
                  )}
                </div>

                {nodeContent.length === 0 && !contentForm && (
                  <div className="text-sm text-surface-400 mb-2">Нет лекционных материалов.</div>
                )}

                <ul className="space-y-1 mb-3">
                  {nodeContent.map((c) => (
                    <li key={c.id} className="flex items-center justify-between text-sm gap-2 bg-surface-50 rounded px-2 py-1.5">
                      <span className="truncate flex-1 font-medium">{c.title}</span>
                      <div className="flex items-center gap-2 shrink-0">
                        <button
                          type="button"
                          className="text-xs text-primary-600 hover:underline"
                          onClick={() => {
                            setContentForm({ title: c.title, content: c.content });
                            setEditingContentId(c.id);
                          }}
                        >
                          ✏️ Редактировать
                        </button>
                        <button
                          type="button"
                          className="text-xs text-red-600 hover:underline"
                          onClick={() => handleDeleteContent(c.id)}
                          disabled={saving}
                        >
                          Удалить
                        </button>
                      </div>
                    </li>
                  ))}
                </ul>

                {contentForm && (
                  <form onSubmit={handleSaveContent} className="space-y-2 border border-primary-200 rounded p-3 bg-primary-50">
                    <div className="text-xs font-semibold text-primary-700 mb-1">
                      {editingContentId != null ? 'Редактировать материал' : 'Новый материал'}
                    </div>
                    <input
                      autoFocus
                      className="input w-full text-sm"
                      placeholder="Заголовок"
                      value={contentForm.title}
                      onChange={(e) => setContentForm({ ...contentForm, title: e.target.value })}
                      required
                    />
                    <textarea
                      className="input w-full text-sm font-mono"
                      placeholder="Содержимое (поддерживается Markdown)"
                      rows={8}
                      value={contentForm.content}
                      onChange={(e) => setContentForm({ ...contentForm, content: e.target.value })}
                      required
                    />
                    <div className="flex gap-2">
                      <button type="submit" className="btn-primary btn-sm" disabled={saving}>
                        💾 Сохранить
                      </button>
                      <button
                        type="button"
                        className="btn-secondary btn-sm"
                        onClick={() => { setContentForm(null); setEditingContentId(null); }}
                      >
                        Отмена
                      </button>
                    </div>
                  </form>
                )}
              </div>

              {/* Блок задач */}
              <div className="pt-4 border-t border-surface-200">
                <div className="flex items-center justify-between mb-2">
                  <h3 className="font-semibold text-sm">Задачи узла</h3>
                  {!selectedNode.can_attach_tasks && (
                    <span className="text-xs text-surface-400">
                      {selectedNode.has_children
                        ? 'Задачи нельзя прикрепить к контейнеру'
                        : 'Недоступно'}
                    </span>
                  )}
                </div>
                {nodeTasks.length === 0 ? (
                  <div className="text-sm text-surface-400 mb-2">Нет задач.</div>
                ) : (
                  <ul className="space-y-1 mb-3">
                    {nodeTasks.map((t) => (
                      <li key={t.id} className="flex items-center justify-between text-sm gap-2">
                        <span className="truncate">
                          <span className="text-surface-400 mr-1">#{t.sort_order}</span>
                          {t.task_title}
                        </span>
                        <div className="flex items-center gap-2 shrink-0">
                          <Link
                            to={`/admin/tasks/${t.task_id}?back=${encodeURIComponent(`/admin/courses/${courseId}`)}`}
                            className="text-xs text-primary-600 hover:underline"
                          >
                            ✏️ Редактировать
                          </Link>
                          <button
                            type="button"
                            onClick={() => handleDetachTask(t.id)}
                            className="text-xs text-red-600 hover:underline"
                            disabled={saving}
                          >
                            Удалить
                          </button>
                        </div>
                      </li>
                    ))}
                  </ul>
                )}
                {selectedNode.can_attach_tasks && (
                  <form onSubmit={handleAttachTask} className="flex gap-2 items-center flex-wrap">
                    <input
                      name="title"
                      className="input text-sm flex-1 min-w-[200px]"
                      placeholder="Название новой задачи"
                      required
                    />
                    <button type="submit" className="btn-primary btn-sm" disabled={saving}>
                      + Создать задачу
                    </button>
                  </form>
                )}
              </div>
            </div>
          )}
        </div>
      </div>
    </div>
  );
}
