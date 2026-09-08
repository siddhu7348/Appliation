import { AlertTriangle } from 'lucide-react';
import { useMonitor } from '@/lib/queries';

/** Yellow warning shown on every page while the drift detector is triggered. */
export function DriftBanner() {
  const { data } = useMonitor();
  if (!data?.drift.triggered) return null;

  return (
    <div
      role="alert"
      aria-live="polite"
      className="flex items-start gap-3 border-b border-amber-300 bg-amber-100 px-6 py-3 text-sm text-amber-900"
    >
      <AlertTriangle className="mt-0.5 h-4 w-4 shrink-0" aria-hidden />
      <div>
        <span className="font-semibold">Model drift detected. </span>
        {data.drift.message}
      </div>
    </div>
  );
}
