import { Activity, AlertTriangle, Gauge, TrendingUp } from 'lucide-react';
import { Badge, Card, CardContent, CardHeader, CardTitle, EmptyState, Skeleton } from '@/components/ui';
import { useBrief } from '@/lib/queries';
import { formatDate, formatNumber, formatPercent } from '@/lib/utils';
import { useAuthStore } from '@/store/auth';

const HEALTH_TONE = {
  healthy: 'green',
  watch: 'amber',
  at_risk: 'red',
} as const;

export default function MorningBriefPage() {
  const user = useAuthStore((state) => state.user);
  const { data, isLoading, isError, error } = useBrief(user?.store_nbr ?? null);

  if (isLoading) {
    return (
      <div className="grid gap-4 md:grid-cols-2 xl:grid-cols-4">
        {Array.from({ length: 8 }).map((_, index) => (
          <Skeleton key={index} className="h-32" />
        ))}
      </div>
    );
  }

  if (isError || !data) {
    return (
      <Card>
        <CardContent>
          <p role="alert" className="text-sm text-rose-600">
            Could not load the morning brief: {(error as Error)?.message}
          </p>
        </CardContent>
      </Card>
    );
  }

  const { yesterday_accuracy: accuracy } = data;

  return (
    <div className="space-y-4">
      <div className="grid gap-4 sm:grid-cols-2 xl:grid-cols-4">
        <Card>
          <CardContent className="flex items-center gap-4">
            <Gauge className="h-8 w-8 text-teal" aria-hidden />
            <div>
              <p className="text-xs uppercase text-slate-400">Store health score</p>
              <p className="text-3xl font-semibold text-navy">{data.store_health_score}</p>
              <Badge tone={HEALTH_TONE[data.health_label]}>{data.health_label.replace('_', ' ')}</Badge>
            </div>
          </CardContent>
        </Card>
        <Card>
          <CardContent>
            <p className="text-xs uppercase text-slate-400">Yesterday MAPE</p>
            <p className="text-3xl font-semibold text-navy">{formatNumber(accuracy.mape, 2)}%</p>
            <p className="text-xs text-slate-400">as of {formatDate(accuracy.as_of)}</p>
          </CardContent>
        </Card>
        <Card>
          <CardContent>
            <p className="text-xs uppercase text-slate-400">Coverage rate</p>
            <p className="text-3xl font-semibold text-navy">{formatPercent(accuracy.coverage_rate)}</p>
            <Badge tone={accuracy.coverage_rate >= accuracy.coverage_target ? 'green' : 'amber'}>
              target {formatPercent(accuracy.coverage_target, 0)}
            </Badge>
          </CardContent>
        </Card>
        <Card>
          <CardContent>
            <p className="text-xs uppercase text-slate-400">Open alerts</p>
            <p className="text-3xl font-semibold text-navy">
              {data.stockout_alerts.length + data.anomaly_flags.length}
            </p>
            <p className="text-xs text-slate-400">
              {data.stockout_alerts.length} stockout / {data.anomaly_flags.length} anomaly
            </p>
          </CardContent>
        </Card>
      </div>

      <div className="grid gap-4 xl:grid-cols-2">
        <Card>
          <CardHeader>
            <CardTitle>
              <span className="flex items-center gap-2">
                <AlertTriangle className="h-4 w-4 text-rose-500" aria-hidden /> Stockout risk
              </span>
            </CardTitle>
            <span className="text-xs text-slate-400">sorted by revenue impact</span>
          </CardHeader>
          <CardContent className="p-0">
            {data.stockout_alerts.length === 0 ? (
              <EmptyState title="No stockout risks" description="Every P10 is above its safe threshold." />
            ) : (
              <div className="max-h-80 overflow-auto">
                <table className="w-full text-sm" aria-label="Stockout risk alerts">
                  <thead className="table-header sticky top-0">
                    <tr>
                      <th className="px-4 py-2">Product</th>
                      <th className="px-4 py-2">Store</th>
                      <th className="px-4 py-2 text-right">P10</th>
                      <th className="px-4 py-2 text-right">Safe level</th>
                      <th className="px-4 py-2 text-right">Revenue at risk</th>
                    </tr>
                  </thead>
                  <tbody>
                    {data.stockout_alerts.map((alert) => (
                      <tr key={`${alert.product_id}-${alert.store_nbr}`} className="border-t border-slate-100">
                        <td className="px-4 py-2">
                          <span className="font-medium text-navy">{alert.product_id}</span>
                          <span className="block text-xs text-slate-400">{alert.family}</span>
                        </td>
                        <td className="px-4 py-2">#{alert.store_nbr}</td>
                        <td className="px-4 py-2 text-right">{formatNumber(alert.p10)}</td>
                        <td className="px-4 py-2 text-right">{formatNumber(alert.safe_threshold)}</td>
                        <td className="px-4 py-2 text-right font-semibold text-rose-600">
                          ${formatNumber(alert.revenue_impact)}
                        </td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            )}
          </CardContent>
        </Card>

        <Card>
          <CardHeader>
            <CardTitle>
              <span className="flex items-center gap-2">
                <Activity className="h-4 w-4 text-amber-500" aria-hidden /> Anomaly demand flags
              </span>
            </CardTitle>
            <span className="text-xs text-slate-400">next 7 days, score &gt; 0.7</span>
          </CardHeader>
          <CardContent className="p-0">
            {data.anomaly_flags.length === 0 ? (
              <EmptyState title="No anomalies flagged" description="IsolationForest scores are all below 0.7." />
            ) : (
              <div className="max-h-80 overflow-auto">
                <table className="w-full text-sm" aria-label="Anomaly demand flags">
                  <thead className="table-header sticky top-0">
                    <tr>
                      <th className="px-4 py-2">Product</th>
                      <th className="px-4 py-2">Store</th>
                      <th className="px-4 py-2">Date</th>
                      <th className="px-4 py-2 text-right">Score</th>
                      <th className="px-4 py-2 text-right">P50</th>
                    </tr>
                  </thead>
                  <tbody>
                    {data.anomaly_flags.map((flag) => (
                      <tr
                        key={`${flag.product_id}-${flag.store_nbr}-${flag.forecast_date}`}
                        className="border-t border-slate-100"
                      >
                        <td className="px-4 py-2">
                          <span className="font-medium text-navy">{flag.product_id}</span>
                          <span className="block text-xs text-slate-400">{flag.family}</span>
                        </td>
                        <td className="px-4 py-2">#{flag.store_nbr}</td>
                        <td className="px-4 py-2">{formatDate(flag.forecast_date)}</td>
                        <td className="px-4 py-2 text-right">
                          <Badge tone={flag.anomaly_score > 0.8 ? 'red' : 'amber'}>
                            {flag.anomaly_score.toFixed(2)}
                          </Badge>
                        </td>
                        <td className="px-4 py-2 text-right">{formatNumber(flag.p50)}</td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            )}
          </CardContent>
        </Card>
      </div>

      <Card>
        <CardHeader>
          <CardTitle>
            <span className="flex items-center gap-2">
              <TrendingUp className="h-4 w-4 text-teal" aria-hidden /> Top 10 movers today
            </span>
          </CardTitle>
          <span className="text-xs text-slate-400">highest P50 demand</span>
        </CardHeader>
        <CardContent className="p-0">
          {data.top_movers.length === 0 ? (
            <EmptyState title="No forecast rows for today" />
          ) : (
            <table className="w-full text-sm" aria-label="Top movers">
              <thead className="table-header">
                <tr>
                  <th className="px-4 py-2">#</th>
                  <th className="px-4 py-2">Product</th>
                  <th className="px-4 py-2">Store</th>
                  <th className="px-4 py-2">Family</th>
                  <th className="px-4 py-2 text-right">P50</th>
                  <th className="px-4 py-2 text-right">P90</th>
                  <th className="px-4 py-2 text-right">Anomaly</th>
                </tr>
              </thead>
              <tbody>
                {data.top_movers.map((mover, index) => (
                  <tr key={`${mover.product_id}-${mover.store_nbr}`} className="border-t border-slate-100">
                    <td className="px-4 py-2 text-slate-400">{index + 1}</td>
                    <td className="px-4 py-2 font-medium text-navy">{mover.product_id}</td>
                    <td className="px-4 py-2">#{mover.store_nbr}</td>
                    <td className="px-4 py-2 text-slate-500">{mover.family}</td>
                    <td className="px-4 py-2 text-right font-semibold">{formatNumber(mover.p50)}</td>
                    <td className="px-4 py-2 text-right">{formatNumber(mover.p90)}</td>
                    <td className="px-4 py-2 text-right">{mover.anomaly_score.toFixed(2)}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          )}
        </CardContent>
      </Card>
    </div>
  );
}
