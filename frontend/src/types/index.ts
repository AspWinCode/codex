export interface User {
  id: number;
  login: string;
  role: 'admin' | 'student';
  status: 'active' | 'blocked' | 'archived';
  email: string | null;
  full_name: string | null;
  created_at: string;
  updated_at: string;
}

export interface Course {
  id: number;
  title: string;
  description: string | null;
  status: 'draft' | 'published' | 'archived';
  created_at: string;
  modules?: Module[];
}

export interface Module {
  id: number;
  course_id: number;
  title: string;
  order_index: number;
  submodules?: Submodule[];
}

export interface Submodule {
  id: number;
  module_id: number;
  title: string;
  order_index: number;
}

export type TaskType = 'python_io' | 'python_oop' | 'python_numpy' | 'sql_query' | 'cpp_io' | 'js_io';
export type RunnerType = 'stdin_runner' | 'pytest_runner' | 'sql_runner' | 'cpp_runner' | 'js_runner';
export type Verdict = 'AC' | 'WA' | 'RE' | 'TLE' | 'MLE' | 'CE' | 'PE' | 'IE';

export interface TestFile {
  name: string;
  content: string;
}

export interface TaskTest {
  id: number;
  task_id: number;
  test_type: 'public' | 'hidden';
  input_data: string | null;
  expected_output: string | null;
  verification_sql: string | null;
  test_files: TestFile[] | null;
  weight: number;
  order_index: number;
}

export interface TaskHint {
  id: number;
  task_id: number;
  hint_level: number;
  unlock_attempts: number;
  coin_cost: number;
  content: string | null;
  is_unlocked: boolean;
}

export interface TaskLecture {
  id: number;
  task_id: number;
  content: string;
  unlock_attempts: number;
}

export interface Task {
  id: number;
  submodule_id: number | null;
  title: string;
  description: string | null;
  task_type: TaskType;
  runner_type: RunnerType;
  status: 'draft' | 'published' | 'archived';
  version: number;
  reward_coins: number;
  sql_schema?: string | null;
  sql_seed?: string | null;
  created_at: string;
  updated_at: string;
  tests?: TaskTest[];
  hints?: TaskHint[];
  lectures?: TaskLecture[];
}

export interface SubmissionTestResult {
  id: number;
  test_id: number;
  verdict: Verdict | null;
  runtime: number | null;
  actual_output: string | null;
  test_type?: 'public' | 'hidden' | null;
  input_data?: string | null;
  expected_output?: string | null;
}

export interface Submission {
  id: number;
  task_id: number;
  user_id: number;
  code: string;
  status: 'queued' | 'running' | 'finished';
  verdict: Verdict | null;
  runtime: number | null;
  memory: number | null;
  error_output: string | null;
  created_at: string;
  test_results?: SubmissionTestResult[];
}

export interface Progress {
  id: number;
  user_id: number;
  task_id: number;
  attempts: number;
  best_verdict: string | null;
  solved_at: string | null;
  last_submission_id: number | null;
}

export interface PersonalLink {
  id: number;
  task_id: number;
  user_id: number;
  token: string;
  expires_at: string | null;
  usage_limit: number | null;
  usage_count: number;
  url: string;
}
