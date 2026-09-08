import { ArrowDownRight, ArrowRight, ArrowUpRight } from 'lucide-react';
import {
  CartesianGrid,
  Legend,
  Line,
  LineChart,
  ResponsiveContainer,
  Tooltip,
  XAxis,
  YAxis,
} from 'recharts';
import { Badge, Card, CardContent, CardHeader, CardTitle, EmptyState, Skeleton } from '@/components/ui';
import { useMonitor } from '@/lib/queries';
import { formatDate, formatNumber, formatPercent } from '@/lib/utils';

const MODEL_COLORS: Record<string, string> = {
  TFT: '#0D9488',
  LightGBM: '#F59E0B',
  ARIMA: '#94A3B8',
  'Chronos-Bolt-Base 2024': '#7C3AED',
};

const TREND_ICON = { up: ArrowUpRight, down: ArrowDownRight, flat: ArrowRight };

export default function MonitorPage() {
  const { data, isLoading, isError, error } = useMonitor();

  if (isLoading) return <Skeleton className="h-[600px]" />;
  if (isError || !data) {
    return (
      <Card>
        <CardContent>
          <p role="alert" className="text-sm text-rose-600">
            Failed to load model metrics: {(error as Error)?.message}
          </p>
        </CardContent>
      </Card>
    );
  }

  const chartData = data.comparison.map((point) => ({ week: point.week_start, ...point.values }));

  return (
    <div className="space-y-4">
      <div className="grid gap-4 sm:grid-cols-2 xl:grid-cols-4">
        {data.scorecards.map((card) => {
          const Icon = TREND_ICON[card.trend];
          return (
            <Card key={card.model_name}>
              <CardContent>
                <div className="flex items-center justify-between">
                  <p className="text-xs font-semibold uppercase text-slate-400">{card.model_name}</p>
                  <Badge tone={card.status}>{card.status}</Badge>
                </div>
                <p className="mt-2 text-3xl font-semibold text-navy">{formatNumber(card.current_mape, 2)}%</p>
                <p className="flex items-center gap-1 text-xs text-slate-500">
                  <Icon className="h-3.5 w-3.5" aria-hidden />
                  {card.delta_pp >= 0 ? '+' : ''}
                  {formatNumber(card.delta_pp, 2)}pp vs {formatNumber(card.previous_mape, 2)}% last week
                </p>
                <div className="mt-3 flex items-center justify-between border-t border-slate-100 pt-2 text-xs">
                  <span className="text-slate-500">
                    Coverage {formatPercent(card.coverage_rate)} / target {formatPercent(data.coverage_target, 0)}
                  </span>
                  <Badge tone={card.coverage_status}>{card.coverage_status}</Badge>
                </div>
              </CardContent>
            </Card>
          );
        })}
      </div>

      <Card>
        <CardHeader>
          <CardTitle>Rolling weekly MAPE - 4 model comparison</CardTitle>
          <span className="text-xs text-slate-400">lower is better</span>
        </CardHeader>
        <CardContent className="h-[380px]">
          {chartData.length === 0 ? (
            <EmptyState title="No weekly metrics available" />
          ) : (
            <ResponsiveContainer width="100%" height="100%">
              <LineChart data={chartData} margin={{ top: 10, right: 16, bottom: 0, left: 0 }}>
                <CartesianGrid strokeDasharray="3 3" stroke="#E2E8F0" />
                <XAxis dataKey="week" tickFormatter={formatDate} fontSize={11} stroke="#94A3B8" />
                <YAxis fontSize={11} stroke="#94A3B8" unit="%" />
                <Tooltip
                  labelFormatter={(label) => `Week of ${formatDate(String(label))}`}
                  formatter={(value: number, name: string) => [`${formatNumber(value, 2)}%`, name]}
                />
                <Legend />
                {data.models.map((model) => (
                  <Line
                    key={model}
                    type="monotone"
                    dataKey={model}
                    stroke={MODEL_COLORS[model] ?? '#1B3A5C'}
                    strokeWidth={model === 'TFT' ? 2.5 : 1.75}
                    dot={false}
                  />
                ))}
              </LineChart>
            </ResponsiveContainer>
          )}
        </CardContent>
      </Card>

      <Card>
        <CardHeader>
          <CardTitle>Drift detector</CardTitle>
          <Badge tone={data.drift.triggered ? 'amber' : 'green'}>
            {data.drift.triggered ? 'warning' : 'stable'}
          </Badge>
        </CardHeader>
        <CardContent className="text-sm text-slate-600">
          <p>{data.drift.message}</p>
          <p className="mt-2 text-xs text-slate-400">
            Rolling MAPE delta {formatNumber(data.drift.mape_delta_pp, 2)}pp over{' '}
            {data.drift.consecutive_weeks} consecutive degrading weeks. A retraining email is sent to HQ when
            the &gt;5pp / 3-week rule fires.
          </p>
        </CardContent>
      </Card>
    </div>
  );
}
