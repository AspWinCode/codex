import type { Verdict } from '../types';

const verdictConfig: Record<string, { label: string; className: string }> = {
  AC: { label: 'Accepted', className: 'badge-green' },
  WA: { label: 'Wrong Answer', className: 'badge-red' },
  RE: { label: 'Runtime Error', className: 'badge-red' },
  TLE: { label: 'Time Limit', className: 'badge-yellow' },
  MLE: { label: 'Memory Limit', className: 'badge-yellow' },
  CE: { label: 'Compile Error', className: 'badge-red' },
  PE: { label: 'Presentation Error', className: 'badge-yellow' },
  IE: { label: 'Internal Error', className: 'badge-gray' },
};

export default function VerdictBadge({ verdict }: { verdict: Verdict | string | null }) {
  if (!verdict) return <span className="badge-gray">Pending</span>;
  const cfg = verdictConfig[verdict] || { label: verdict, className: 'badge-gray' };
  return <span className={cfg.className}>{cfg.label}</span>;
}
