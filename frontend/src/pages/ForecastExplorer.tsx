import { useMemo, useState } from 'react';
import {
  Area,
  CartesianGrid,
  ComposedChart,
  Legend,
  Line,
  ReferenceLine,
  ResponsiveContainer,
  Tooltip,
  XAxis,
  YAxis,
} from 'recharts';
import { AttentionHeatmap } from '@/components/AttentionHeatmap';
import { Badge, Card, CardContent, CardHeader, CardTitle, EmptyState, Select, Skeleton } from '@/components/ui';
import { useCatalog, useForecast } from '@/lib/queries';
import { cn, formatDate, formatNumber } from '@/lib/utils';

interface ChartRow {
  date: string;
  actual?: number;
  p10?: number;
  p50?: number;
  p90?: number;
  band?: [number, number];
  lgbm?: number | null;
}

function anomalyTone(score: number): string {
  if (score >= 0.8) return 'bg-rose-500';
  if (score >= 0.5) return 'bg-amber-400';
  return 'bg-emerald-500';
}

export default function ForecastExplorerPage() {
  const { data: catalog, isLoading: catalogLoading } = useCatalog();
  const [productId, setProductId] = useState<string | null>(null);
  const [storeNbr, setStoreNbr] = useState<number | null>(null);

  const activeStore = storeNbr ?? catalog?.stores[0] ?? null;
  const productsForStore = useMemo(
    () => catalog?.products.filter((product) => product.store_nbr === activeStore) ?? [],
    [catalog, activeStore],
  );
  const activeProduct = productId ?? productsForStore[0]?.product_id ?? null;

  const { data, isLoading, isError, error } = useForecast(activeProduct, activeStore);

  const chartData: ChartRow[] = useMemo(() => {
    if (!data) return [];
    const history = data.history.slice(-30).map<ChartRow>((point) => ({
      date: point.date,
      actual: point.actual,
    }));
    const horizon = data.horizon.map<ChartRow>((point) => ({
      date: point.forecast_date,
      p10: point.p10,
      p50: point.p50,
      p90: point.p90,
      band: [point.p10, point.p90],
      lgbm: point.lgbm_point,
    }));
    return [...history, ...horizon];
  }, [data]);

  if (catalogLoading) return <Skeleton className="h-[600px]" />;

  return (
    <div className="space-y-4">
      <Card>
        <CardContent className="flex flex-wrap items-end gap-4">
          <div>
            <label htmlFor="store" className="mb-1 block text-xs font-semibold text-slate-600">
              Store
            </label>
            <Select
              id="store"
              value={activeStore ?? ''}
              onChange={(event) => {
                setStoreNbr(Number(event.target.value));
                setProductId(null);
              }}
            >
              {catalog?.stores.map((store) => (
                <option key={store} value={store}>
                  Store #{store}
                </option>
              ))}
            </Select>
          </div>
          <div>
            <label htmlFor="product" className="mb-1 block text-xs font-semibold text-slate-600">
              Product
            </label>
            <Select
              id="product"
              value={activeProduct ?? ''}
              onChange={(event) => setProductId(event.target.value)}
            >
              {productsForStore.map((product) => (
                <option key={product.product_id} value={product.product_id}>
                  {product.product_id} - {product.family}
                </option>
              ))}
            </Select>
          </div>
          {data ? (
            <div className="ml-auto flex items-center gap-2 text-xs text-slate-500">
              <Badge tone="teal">{data.series.family}</Badge>
              <Badge tone="neutral">source: {data.data_source}</Badge>
            </div>
          ) : null}
        </CardContent>
      </Card>

      {isError ? (
        <Card>
          <CardContent>
            <p role="alert" className="text-sm text-rose-600">
              Failed to load forecast: {(error as Error)?.message}
            </p>
          </CardContent>
        </Card>
      ) : null}

      <Card>
        <CardHeader>
          <CardTitle>16-day probabilistic forecast</CardTitle>
          <span className="text-xs text-slate-400">P50 line with P10-P90 band, actuals in dark</span>
        </CardHeader>
        <CardContent className="h-[420px]">
          {isLoading ? (
            <Skeleton className="h-full w-full" />
          ) : chartData.length === 0 ? (
            <EmptyState title="Select a product and store" />
          ) : (
            <ResponsiveContainer width="100%" height="100%">
              <ComposedChart data={chartData} margin={{ top: 10, right: 16, bottom: 0, left: 0 }}>
                <CartesianGrid strokeDasharray="3 3" stroke="#E2E8F0" />
                <XAxis dataKey="date" tickFormatter={formatDate} fontSize={11} stroke="#94A3B8" />
                <YAxis fontSize={11} stroke="#94A3B8" />
                <Tooltip
                  labelFormatter={(label) => formatDate(String(label))}
                  formatter={(value: number | [number, number], name: string) =>
                    Array.isArray(value)
                      ? [`${formatNumber(value[0])} - ${formatNumber(value[1])}`, 'P10-P90']
                      : [formatNumber(value), name]
                  }
                />
                <Legend />
                <Area
                  type="monotone"
                  dataKey="band"
                  name="P10-P90"
                  stroke="none"
                  fill="#0D9488"
                  fillOpacity={0.18}
                  connectNulls
                />
                <Line
                  type="monotone"
                  dataKey="actual"
                  name="Actual"
                  stroke="#1B3A5C"
                  strokeWidth={2}
                  dot={false}
                />
                <Line
                  type="monotone"
                  dataKey="p50"
                  name="TFT P50"
                  stroke="#0D9488"
                  strokeWidth={2.5}
                  dot={false}
                />
                <Line
                  type="monotone"
                  dataKey="lgbm"
                  name="LightGBM point"
                  stroke="#F59E0B"
                  strokeDasharray="4 3"
                  strokeWidth={1.75}
                  dot={false}
                />
                {data?.events.map((event) => (
                  <ReferenceLine
                    key={`${event.type}-${event.date}`}
                    x={event.date}
                    stroke={event.type === 'holiday' ? '#7C3AED' : '#DC2626'}
                    strokeDasharray="3 3"
                    label={{ value: event.type === 'holiday' ? 'Holiday' : 'Oil', fontSize: 10 }}
                  />
                ))}
              </ComposedChart>
            </ResponsiveContainer>
          )}
        </CardContent>
      </Card>

      <div className="grid gap-4 xl:grid-cols-2">
        <Card>
          <CardHeader>
            <CardTitle>Anomaly score - 16 day horizon</CardTitle>
          </CardHeader>
          <CardContent>
            {data ? (
              <div className="grid grid-cols-16 gap-1" style={{ gridTemplateColumns: 'repeat(16, minmax(0, 1fr))' }}>
                {data.horizon.map((point) => (
                  <div
                    key={point.forecast_date}
                    title={`${formatDate(point.forecast_date)}: ${point.anomaly_score.toFixed(2)}`}
                    aria-label={`Anomaly score ${point.anomaly_score.toFixed(2)} on ${point.forecast_date}`}
                    className={cn('flex h-12 items-end justify-center rounded text-[9px] text-white', anomalyTone(point.anomaly_score))}
                  >
                    {point.anomaly_score.toFixed(2)}
                  </div>
                ))}
              </div>
            ) : (
              <Skeleton className="h-12 w-full" />
            )}
          </CardContent>
        </Card>

        <Card>
          <CardHeader>
            <CardTitle>Attention over 90-day lookback</CardTitle>
            <span className="text-xs text-slate-400">peaks at 7 / 14 / 21 / 28 days</span>
          </CardHeader>
          <CardContent>
            {data ? <AttentionHeatmap weights={data.attention} /> : <Skeleton className="h-44 w-full" />}
          </CardContent>
        </Card>
      </div>
    </div>
  );
}
