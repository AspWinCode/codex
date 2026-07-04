import { create } from 'zustand';

export interface CourseSidebarItem {
  kind: 'section' | 'task' | 'lecture';
  nodeId: number;
  number: string;
  label: string;
  depth: number;
  taskId?: number;
  nodeTaskId?: number;
  lectureId?: number;
  status?: 'not_started' | 'in_progress' | 'completed';
}

interface CourseLearnStore {
  courseId: number | null;
  courseTitle: string | null;
  sidebarItems: CourseSidebarItem[];
  selectedTaskId: number | null;
  completedCount: number;
  totalCount: number;
  setCourseData: (
    courseId: number,
    title: string,
    items: CourseSidebarItem[],
    completed: number,
    total: number,
  ) => void;
  setSelectedTaskId: (id: number | null) => void;
  clear: () => void;
}

export const useCourseLearnStore = create<CourseLearnStore>((set) => ({
  courseId: null,
  courseTitle: null,
  sidebarItems: [],
  selectedTaskId: null,
  completedCount: 0,
  totalCount: 0,
  setCourseData: (courseId, courseTitle, sidebarItems, completedCount, totalCount) =>
    set({ courseId, courseTitle, sidebarItems, completedCount, totalCount }),
  setSelectedTaskId: (selectedTaskId) => set({ selectedTaskId }),
  clear: () =>
    set({
      courseId: null,
      courseTitle: null,
      sidebarItems: [],
      selectedTaskId: null,
      completedCount: 0,
      totalCount: 0,
    }),
}));
