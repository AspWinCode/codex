import { useEffect, useState } from 'react';
import { Routes, Route, useNavigate } from 'react-router-dom';
import { useAuthStore } from './store/auth';
import OnboardingIntro from './components/OnboardingIntro';
import CaseIntro from './components/CaseIntro';
import Layout from './components/Layout';
import ProtectedRoute from './components/ProtectedRoute';
import LoginPage from './pages/LoginPage';
import TaskPage from './pages/TaskPage';
import TasksPage from './pages/TasksPage';
import ProgressPage from './pages/ProgressPage';
import ProfilePage from './pages/ProfilePage';
import AdminUsersPage from './pages/AdminUsersPage';
import AdminCoursesPage from './pages/AdminCoursesPage';
import AdminCourseEditorPage from './pages/AdminCourseEditorPage';
import AdminTasksPage from './pages/AdminTasksPage';
import AdminTaskEditPage from './pages/AdminTaskEditPage';
import AdminLinksPage from './pages/AdminLinksPage';
import AdminSettingsPage from './pages/AdminSettingsPage';
import ForgotPasswordPage from './pages/ForgotPasswordPage';
import ResetPasswordPage from './pages/ResetPasswordPage';
import PersonalTaskPage from './pages/PersonalTaskPage';
import CourseLearnPage from './pages/CourseLearnPage';
import CoursesPage from './pages/CoursesPage';
import ContestsPage from './pages/ContestsPage';
import ContestDetailPage from './pages/ContestDetailPage';
import LeaderboardPage from './pages/LeaderboardPage';

function SsoBootstrap() {
  const navigate = useNavigate();
  const setAuth = useAuthStore((s) => s.setAuth);

  useEffect(() => {
    const hash = window.location.hash;
    if (!hash || !hash.includes('access_token=')) return;

    const params = new URLSearchParams(hash.slice(1));
    const accessToken = params.get('access_token');
    const refreshToken = params.get('refresh_token');
    const userB64 = params.get('user');
    if (!accessToken || !refreshToken || !userB64) return;

    try {
      const userJson = atob(userB64.replace(/-/g, '+').replace(/_/g, '/'));
      const user = JSON.parse(decodeURIComponent(escape(userJson)));
      setAuth(accessToken, refreshToken, user);
      window.history.replaceState(null, '', window.location.pathname);
      navigate('/', { replace: true });
    } catch {
      // Битый fragment — просто оставляем как есть, ProtectedRoute отправит на /login
    }
  }, [navigate, setAuth]);

  return null;
}

// Flip to false once onboarding + case intro are tested and ready.
// When true, ALWAYS_SHOW resets in-memory state on each login so both
// screens play every time — without looping back to onboarding after step 1.
const KODEX_ALWAYS_SHOW = true;

function OnboardingGate({ children }: { children: React.ReactNode }) {
  const { token, user } = useAuthStore();
  const navigate = useNavigate();

  // When ALWAYS_SHOW is on, initialize as unseen so both steps play in order.
  const [seenOnboarding, setSeenOnboarding] = useState(() => {
    if (KODEX_ALWAYS_SHOW) return false;
    try { return localStorage.getItem('kodex_onboarding_seen') === '1'; }
    catch { return true; }
  });

  const [seenCase, setSeenCase] = useState(() => {
    if (KODEX_ALWAYS_SHOW) return false;
    try { return localStorage.getItem('kodex_case_seen') === '1'; }
    catch { return true; }
  });

  const [agentName, setAgentName] = useState(() => {
    try { return localStorage.getItem('kodex_agent_name') || ''; }
    catch { return ''; }
  });

  if (token && user && user.role === 'student') {
    // Step 1: cinematic onboarding intro
    if (!seenOnboarding) {
      return (
        <OnboardingIntro
          onComplete={(name) => {
            try {
              localStorage.setItem('kodex_onboarding_seen', '1');
              localStorage.setItem('kodex_agent_name', name);
            } catch {}
            setAgentName(name);
            setSeenOnboarding(true);
          }}
        />
      );
    }

    // Step 2: case opening cinematic
    if (!seenCase) {
      return (
        <CaseIntro
          agentName={agentName}
          onComplete={() => {
            try { localStorage.setItem('kodex_case_seen', '1'); } catch {}
            setSeenCase(true);
            navigate('/tasks');
          }}
        />
      );
    }
  }

  return <>{children}</>;
}

export default function App() {
  return (
    <>
      <SsoBootstrap />
      <OnboardingGate>
        <Routes>
          <Route path="/login" element={<LoginPage />} />
          <Route path="/forgot-password" element={<ForgotPasswordPage />} />
          <Route path="/reset-password" element={<ResetPasswordPage />} />
          <Route path="/shared/:token" element={<PersonalTaskPage />} />
          <Route path="task/:taskId" element={<ProtectedRoute><TaskPage /></ProtectedRoute>} />
          <Route element={<ProtectedRoute><Layout /></ProtectedRoute>}>
            <Route index element={<ProgressPage />} />
            <Route path="courses" element={<CoursesPage />} />
            <Route path="tasks" element={<TasksPage />} />
              <Route path="course/:courseId" element={<CourseLearnPage />} />
            <Route path="progress" element={<ProgressPage />} />
            <Route path="profile/:userId" element={<ProfilePage />} />
            <Route path="contests" element={<ContestsPage />} />
            <Route path="contests/:contestId" element={<ContestDetailPage />} />
            <Route path="leaderboard" element={<LeaderboardPage />} />
            <Route path="admin/users" element={<ProtectedRoute requireAdmin><AdminUsersPage /></ProtectedRoute>} />
            <Route path="admin/courses" element={<ProtectedRoute requireAdmin><AdminCoursesPage /></ProtectedRoute>} />
            <Route path="admin/courses/:courseId" element={<ProtectedRoute requireAdmin><AdminCourseEditorPage /></ProtectedRoute>} />
            <Route path="admin/tasks" element={<ProtectedRoute requireAdmin><AdminTasksPage /></ProtectedRoute>} />
            <Route path="admin/tasks/:taskId" element={<ProtectedRoute requireAdmin><AdminTaskEditPage /></ProtectedRoute>} />
            <Route path="admin/links" element={<ProtectedRoute requireAdmin><AdminLinksPage /></ProtectedRoute>} />
            <Route path="admin/settings" element={<ProtectedRoute requireAdmin><AdminSettingsPage /></ProtectedRoute>} />
          </Route>
        </Routes>
      </OnboardingGate>
    </>
  );
}
