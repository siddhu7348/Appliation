import { Download } from 'lucide-react';
import { useCallback, useRef } from 'react';
import { GridHeatmap } from '@/components/GridHeatmap';
import { Badge, Button, Card, CardContent, CardHeader, CardTitle, EmptyState, Skeleton } from '@/components/ui';
import { useAnalytics } from '@/lib/queries';
import { formatNumber, formatPercent } from '@/lib/utils';

export default function AnalyticsPage() {
  const { data, isLoading, isError, error } = useAnalytics();
  const exporterRef = useRef<(() => void) | null>(null);
  const registerExporter = useCallback((exporter: () => void) => {
    exporterRef.current = exporter;
  }, []);

  if (isLoading) return <Skeleton className="h-[600px]" />;
  if (isError || !data) {
    return (
      <Card>
        <CardContent>
          <p role="alert" className="text-sm text-rose-600">
            Failed to load analytics: {(error as Error)?.message}
          </p>
        </CardContent>
      </Card>
    );
  }

  const best = data.category_leaderboard.slice(0, 5);
  const worst = [...data.category_leaderboard].slice(-5).reverse();

  return (
    <div className="space-y-4">
      <Card>
        <CardHeader>
          <CardTitle>
            {data.stores.length} stores x {data.families.length} categories - coverage probability
          </CardTitle>
          <Button variant="outline" size="sm" onClick={() => exporterRef.current?.()}>
            <Download className="h-4 w-4" aria-hidden /> PNG
          </Button>
        </CardHeader>
        <CardContent>
          {data.cells.length === 0 ? (
            <EmptyState title="No analytics cells" />
          ) : (
            <GridHeatmap
              cells={data.cells}
              stores={data.stores}
              families={data.families}
              onExportRef={registerExporter}
            />
          )}
          <p className="mt-3 text-xs text-slate-400">
            Red = high forecast uncertainty, green = high confidence. Hover a cell for coverage and MAPE.
          </p>
        </CardContent>
      </Card>

      <div className="grid gap-4 xl:grid-cols-2">
        <Card>
          <CardHeader>
            <CardTitle>Category MAPE leaderboard</CardTitle>
          </CardHeader>
          <CardContent className="grid gap-6 sm:grid-cols-2">
            <div>
              <p className="mb-2 text-xs font-semibold uppercase text-emerald-600">Best families</p>
              <ul className="space-y-1 text-sm">
                {best.map((row) => (
                  <li key={row.family} className="flex items-center justify-between gap-2">
                    <span className="truncate text-slate-600">{row.family}</span>
                    <Badge tone="green">{formatNumber(row.mape, 2)}%</Badge>
                  </li>
                ))}
              </ul>
            </div>
            <div>
              <p className="mb-2 text-xs font-semibold uppercase text-rose-600">Worst families</p>
              <ul className="space-y-1 text-sm">
                {worst.map((row) => (
                  <li key={row.family} className="flex items-center justify-between gap-2">
                    <span className="truncate text-slate-600">{row.family}</span>
                    <Badge tone="red">{formatNumber(row.mape, 2)}%</Badge>
                  </li>
                ))}
              </ul>
            </div>
          </CardContent>
        </Card>

        <Card>
          <CardHeader>
            <CardTitle>Store health ranking</CardTitle>
          </CardHeader>
          <CardContent className="p-0">
            <div className="max-h-96 overflow-auto">
              <table className="w-full text-sm" aria-label="Store health ranking">
                <thead className="table-header sticky top-0">
                  <tr>
                    <th className="px-4 py-2">Rank</th>
                    <th className="px-4 py-2">Store</th>
                    <th className="px-4 py-2 text-right">Health</th>
                    <th className="px-4 py-2 text-right">Coverage</th>
                    <th className="px-4 py-2 text-right">MAPE</th>
                  </tr>
                </thead>
                <tbody>
                  {data.store_ranking.map((row) => (
                    <tr key={row.store_nbr} className="border-t border-slate-100">
                      <td className="px-4 py-2 text-slate-400">{row.rank}</td>
                      <td className="px-4 py-2 font-medium text-navy">#{row.store_nbr}</td>
                      <td className="px-4 py-2 text-right font-semibold">{formatNumber(row.health_score)}</td>
                      <td className="px-4 py-2 text-right">{formatPercent(row.coverage_probability)}</td>
                      <td className="px-4 py-2 text-right">{formatNumber(row.mape, 2)}%</td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          </CardContent>
        </Card>
      </div>
    </div>
  );
}
