import api from './client';
import type { Course, Module, Submodule, Task, Submission, Progress, User, PersonalLink, TaskHint } from '../types';

export const authApi = {
  login: (login: string, password: string) =>
    api.post<{ token: string; refresh_token: string; user: User }>('/auth/login', { login, password }),
  refresh: (refresh_token: string) =>
    api.post<{ token: string; refresh_token: string }>('/auth/refresh', { refresh_token }),
  changePassword: (old_password: string, new_password: string) =>
    api.post('/auth/change-password', { old_password, new_password }),
};

export interface CourseEnrollment {
  course_id: number;
  course_title: string;
}

export const usersApi = {
  list: () => api.get<User[]>('/users'),
  get: (id: number) => api.get<User>(`/users/${id}`),
  create: (data: { login: string; password: string; role?: string; email?: string; full_name?: string }) => api.post<User>('/users', data),
  update: (id: number, data: Partial<User>) => api.put<User>(`/users/${id}`, data),
  resetPassword: (id: number, new_password: string) => api.post<User>(`/users/${id}/reset-password`, { new_password }),
  getEnrollments: (id: number) => api.get<CourseEnrollment[]>(`/users/${id}/enrollments`),
  enroll: (userId: number, courseId: number) => api.post(`/users/${userId}/enrollments/${courseId}`),
  unenroll: (userId: number, courseId: number) => api.delete(`/users/${userId}/enrollments/${courseId}`),
  forgotPassword: (email: string) => api.post('/users/forgot-password', { email }),
  resetPasswordByToken: (token: string, new_password: string) => api.post('/users/reset-password-by-token', { token, new_password }),
  getStats: (id: number) => api.get<{ user_id: number; total_attempts: number; solved_tasks: number; in_progress_tasks: number }>(`/users/${id}/stats`),
};

export const coursesApi = {
  list: () => api.get<Course[]>('/courses'),
  get: (id: number) => api.get<Course>(`/courses/${id}`),
  create: (data: Partial<Course>) => api.post<Course>('/courses', data),
  update: (id: number, data: Partial<Course>) => api.put<Course>(`/courses/${id}`, data),
  delete: (id: number) => api.delete(`/courses/${id}`),
  listModules: (courseId: number) => api.get<Module[]>(`/courses/${courseId}/modules`),
  createModule: (courseId: number, data: Partial<Module>) => api.post<Module>(`/courses/${courseId}/modules`, data),
  updateModule: (moduleId: number, data: Partial<Module>) => api.put<Module>(`/courses/modules/${moduleId}`, data),
  deleteModule: (moduleId: number) => api.delete(`/courses/modules/${moduleId}`),
  createSubmodule: (moduleId: number, data: Partial<Submodule>) => api.post<Submodule>(`/courses/modules/${moduleId}/submodules`, data),
  updateSubmodule: (submoduleId: number, data: Partial<Submodule>) => api.put<Submodule>(`/courses/submodules/${submoduleId}`, data),
  deleteSubmodule: (submoduleId: number) => api.delete(`/courses/submodules/${submoduleId}`),
};

export type CourseNodeType = 'module' | 'submodule' | 'topic' | 'subtopic';
export type CourseNodeStatus = 'draft' | 'published' | 'archived';

export interface CourseNodeTree {
  id: number;
  course_id: number;
  parent_id: number | null;
  type: CourseNodeType;
  title: string;
  sort_order: number;
  status: CourseNodeStatus;
  has_children: boolean;
  task_count: number;
  can_attach_tasks: boolean;
  can_create_children: boolean;
  children: CourseNodeTree[];
}

export interface CourseNodeDetails {
  id: number;
  course_id: number;
  parent_id: number | null;
  type: CourseNodeType;
  title: string;
  description: string | null;
  sort_order: number;
  status: CourseNodeStatus;
  has_children: boolean;
  task_count: number;
  can_attach_tasks: boolean;
  can_create_children: boolean;
  created_at: string;
  updated_at: string;
  archived_at: string | null;
}

export interface AdminCourse {
  id: number;
  title: string;
  slug: string | null;
  description: string | null;
  short_description: string | null;
  cover_image_url: string | null;
  status: 'draft' | 'published' | 'archived';
  sort_order: number;
  created_at: string;
  updated_at: string;
  archived_at: string | null;
}

export interface CourseNodeTask {
  id: number;
  node_id: number;
  task_id: number;
  task_title: string;
  sort_order: number;
  is_required: boolean;
}

export const adminCoursesApi = {
  list: () => api.get<AdminCourse[]>('/admin/courses'),
  create: (data: { title: string; description?: string; short_description?: string; cover_image_url?: string; status?: 'draft' | 'published' | 'archived'; sort_order?: number }) =>
    api.post<AdminCourse>('/admin/courses', data),
  get: (id: number) => api.get<AdminCourse>(`/admin/courses/${id}`),
  update: (id: number, data: Partial<{ title: string; description?: string; short_description?: string; cover_image_url?: string; status: 'draft' | 'published' | 'archived'; sort_order: number }>) =>
    api.patch<AdminCourse>(`/admin/courses/${id}`, data),
  archive: (id: number) => api.post(`/admin/courses/${id}/archive`),
  unarchive: (id: number) => api.post(`/admin/courses/${id}/unarchive`),
  delete: (id: number) => api.delete(`/admin/courses/${id}`),
  getTree: (courseId: number) => api.get<CourseNodeTree[]>(`/admin/courses/${courseId}/tree`),
  getNode: (nodeId: number) => api.get<CourseNodeDetails>(`/admin/courses/nodes/${nodeId}`),
  createNode: (courseId: number, data: { parent_id?: number | null; type: CourseNodeType; title: string; description?: string; sort_order?: number; status?: CourseNodeStatus }) =>
    api.post<CourseNodeTree>(`/admin/courses/${courseId}/nodes`, data),
  updateNode: (nodeId: number, data: Partial<{ title: string; description?: string; sort_order: number; status: CourseNodeStatus }>) =>
    api.patch(`/admin/courses/nodes/${nodeId}`, data),
  deleteNode: (nodeId: number) => api.delete(`/admin/courses/nodes/${nodeId}`),
  archiveNode: (nodeId: number) => api.post(`/admin/courses/nodes/${nodeId}/archive`),
  unarchiveNode: (nodeId: number) => api.post(`/admin/courses/nodes/${nodeId}/unarchive`),
  getNodeTasks: (nodeId: number) => api.get<CourseNodeTask[]>(`/admin/courses/nodes/${nodeId}/tasks`),
  attachTaskToNode: (nodeId: number, data: { task_id?: number; create_new_task?: boolean; task_title?: string; sort_order?: number; is_required?: boolean }) =>
    api.post<CourseNodeTask>(`/admin/courses/nodes/${nodeId}/tasks`, data),
  detachTaskFromNode: (nodeId: number, nodeTaskId: number) =>
    api.delete(`/admin/courses/nodes/${nodeId}/tasks/${nodeTaskId}`),
  reorderNodeTasks: (nodeId: number, items: { id: number; sort_order: number }[]) =>
    api.post(`/admin/courses/nodes/${nodeId}/tasks/reorder`, items),
};

export interface TaskCourseContext {
  course_id: number;
  course_title: string;
  node_title: string;
}

export const tasksApi = {
  list: (params?: { submodule_id?: number; task_type?: string }) => api.get<Task[]>('/tasks', { params }),
  get: (id: number) => api.get<Task>(`/tasks/${id}`),
  getCourseContext: (id: number) => api.get<TaskCourseContext[]>(`/tasks/${id}/context`),
  create: (data: any) => api.post<Task>('/tasks', data),
  update: (id: number, data: Partial<Task>) => api.put<Task>(`/tasks/${id}`, data),
  delete: (id: number) => api.delete(`/tasks/${id}`),
  addTest: (taskId: number, data: any) => api.post(`/tasks/${taskId}/tests`, data),
  updateTest: (testId: number, data: any) => api.patch(`/tasks/tests/${testId}`, data),
  deleteTest: (testId: number) => api.delete(`/tasks/tests/${testId}`),
  addHint: (taskId: number, data: any) => api.post(`/tasks/${taskId}/hints`, data),
  deleteHint: (hintId: number) => api.delete(`/tasks/hints/${hintId}`),
  addLecture: (taskId: number, data: any) => api.post(`/tasks/${taskId}/lectures`, data),
  deleteLecture: (lectureId: number) => api.delete(`/tasks/lectures/${lectureId}`),
};

export interface NodeTaskProgress {
  node_task_id: number;
  task_id: number;
  task_title: string;
  status: 'not_started' | 'in_progress' | 'completed';
  completed_at: string | null;
}

export interface CourseProgressStats {
  course_id: number;
  progress_percent: number;
  completed_tasks_count: number;
  total_tasks_count: number;
}

export interface CourseNodeContent {
  id: number;
  node_id: number;
  title: string;
  content: string;
  sort_order: number;
  created_at: string;
  updated_at: string;
}

export const courseStudentApi = {
  getTree: (courseId: number) => api.get<CourseNodeTree[]>(`/courses/${courseId}/tree`),
  getNodeTasks: (nodeId: number) => api.get<NodeTaskProgress[]>(`/nodes/${nodeId}/tasks`),
  getNodeContent: (nodeId: number) => api.get<CourseNodeContent[]>(`/nodes/${nodeId}/content`),
  getProgress: (courseId: number) => api.get<CourseProgressStats>(`/courses/${courseId}/progress`),
};

export const adminNodeContentApi = {
  list: (nodeId: number) => api.get<CourseNodeContent[]>(`/admin/courses/nodes/${nodeId}/content`),
  create: (nodeId: number, data: { title: string; content: string; sort_order?: number }) =>
    api.post<CourseNodeContent>(`/admin/courses/nodes/${nodeId}/content`, data),
  update: (nodeId: number, contentId: number, data: Partial<{ title: string; content: string; sort_order: number }>) =>
    api.patch<CourseNodeContent>(`/admin/courses/nodes/${nodeId}/content/${contentId}`, data),
  delete: (nodeId: number, contentId: number) =>
    api.delete(`/admin/courses/nodes/${nodeId}/content/${contentId}`),
};

export const submissionsApi = {
  submit: (task_id: number, code: string) => api.post<Submission>('/submissions', { task_id, code }),
  get: (id: number) => api.get<Submission>(`/submissions/${id}`),
  list: (task_id?: number) => api.get<Submission[]>('/submissions', { params: task_id ? { task_id } : {} }),
};

export const progressApi = {
  get: (task_id?: number) => api.get<Progress[]>('/progress', { params: task_id ? { task_id } : {} }),
  getHints: (taskId: number) => api.get<TaskHint[]>(`/progress/hints/${taskId}`),
};

export const personalLinksApi = {
  create: (data: { task_id: number; user_id: number; expires_at?: string; usage_limit?: number }) =>
    api.post<PersonalLink>('/personal-links', data),
  list: () => api.get<PersonalLink[]>('/personal-links'),
  resolve: (token: string) => api.get<Task>(`/personal-links/resolve/${token}`),
};

export const contestsApi = {
  list: () => api.get<any[]>('/contests'),
  get: (id: number) => api.get<any>(`/contests/${id}`),
  create: (data: any) => api.post<any>('/contests', data),
  join: (id: number) => api.post(`/contests/${id}/join`),
  leaderboard: (id: number) => api.get<any[]>(`/contests/${id}/leaderboard`),
};

export const ratingsApi = {
  leaderboard: (limit?: number) => api.get<any[]>('/ratings/leaderboard', { params: limit ? { limit } : {} }),
  me: () => api.get<any>('/ratings/me'),
  history: (userId: number) => api.get<any[]>(`/ratings/history/${userId}`),
};

export const platformSettingsApi = {
  getLogo: () => api.get<{ url: string | null }>('/settings/logo'),
  uploadLogo: (file: File) => {
    const fd = new FormData();
    fd.append('file', file);
    return api.post<{ url: string }>('/settings/logo', fd, {
      headers: { 'Content-Type': 'multipart/form-data' },
    });
  },
  deleteLogo: () => api.delete<{ url: null }>('/settings/logo'),
};

export interface GamificationMe {
  balance: number;
  rank: string;
  solved_count: number;
  current_streak_days: number;
  max_streak_days: number;
}

export interface CoinTransaction {
  id: number;
  amount: number;
  reason: string;
  task_id: number | null;
  created_at: string;
}

export const gamificationApi = {
  me: () => api.get<GamificationMe>('/gamification/me'),
  transactions: (limit?: number) => api.get<CoinTransaction[]>('/gamification/transactions', { params: limit ? { limit } : {} }),
};

export const hintsApi = {
  unlock: (hintId: number) => api.post<TaskHint>(`/tasks/hints/${hintId}/unlock`),
};

export const achievementsApi = {
  list: () => api.get<any[]>('/achievements'),
  my: () => api.get<any[]>('/achievements/my'),
  profile: (userId: number) => api.get<any>(`/achievements/profile/${userId}`),
  seed: () => api.post('/achievements/seed'),
};
