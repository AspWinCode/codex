import { useEffect, useState } from 'react';
import { Routes, Route, useNavigate } from 'react-router-dom';
import { useAuthStore } from './store/auth';
import OnboardingIntro from './components/OnboardingIntro';
import CaseIntro from './components/CaseIntro';

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
      // Битый fragment — оставляем как есть
    }
  }, [navigate, setAuth]);

  return null;
}

const KODEX_ALWAYS_SHOW = true;

function OnboardingFlow() {
  const { token, user } = useAuthStore();

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

  if (!token || !user) {
    return <div className="flex items-center justify-center h-screen text-white">Войдите через SSO</div>;
  }

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

  if (!seenCase) {
    return (
      <CaseIntro
        agentName={agentName}
        onComplete={() => {
          try { localStorage.setItem('kodex_case_seen', '1'); } catch {}
          setSeenCase(true);
        }}
      />
    );
  }

  return <div className="flex items-center justify-center h-screen text-white">Онбординг завершён</div>;
}

export default function App() {
  return (
    <>
      <SsoBootstrap />
      <Routes>
        <Route path="*" element={<OnboardingFlow />} />
      </Routes>
    </>
  );
}
