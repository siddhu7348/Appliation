import { useMutation } from '@tanstack/react-query';
import { FileSpreadsheet, FileText } from 'lucide-react';
import { useMemo, useState } from 'react';
import {
  Badge,
  Button,
  Card,
  CardContent,
  CardHeader,
  CardTitle,
  EmptyState,
  Select,
  Skeleton,
} from '@/components/ui';
import { api, downloadBlob } from '@/lib/api';
import { useInventory } from '@/lib/queries';
import { formatNumber } from '@/lib/utils';
import { useUiStore } from '@/store/ui';
import type { ConfidenceMode, InventoryRow, RiskLevel } from '@/types/api';

const MODES: { value: ConfidenceMode; label: string; hint: string }[] = [
  { value: 'lean', label: 'Lean', hint: 'P50 base' },
  { value: 'balanced', label: 'Balanced', hint: 'P75 base' },
  { value: 'safe', label: 'Safe', hint: 'P90 base' },
];

const REASON_CODES = [
  'promotion_planned',
  'supplier_constraint',
  'local_event',
  'storage_limit',
  'model_underestimates',
  'model_overestimates',
];

const RISK_TONE: Record<RiskLevel, 'green' | 'amber' | 'red'> = {
  low: 'green',
  medium: 'amber',
  high: 'red',
};

/** Client-side mirror of the server formula so toggling modes is instant. */
function quantityForMode(row: InventoryRow, mode: ConfidenceMode): number {
  const highRisk = row.anomaly_score >= 0.8;
  const base = highRisk
    ? row.p90
    : mode === 'lean'
      ? row.p50
      : mode === 'safe'
        ? row.p90
        : row.p50 + 0.5 * (row.p90 - row.p50);
  const buffer = highRisk ? row.p90 * 0.15 : 0;
  return Math.max(0, Number((base - row.current_stock + buffer).toFixed(2)));
}

export default function InventoryPage() {
  const { confidenceMode, setConfidenceMode } = useUiStore();
  const { data, isLoading, isError, error } = useInventory(confidenceMode);
  const [overrides, setOverrides] = useState<Record<string, number>>({});
  const [editing, setEditing] = useState<InventoryRow | null>(null);

  const rows = useMemo(
    () =>
      (data?.rows ?? []).map((row) => ({
        ...row,
        recommended_qty: quantityForMode(row, confidenceMode),
      })),
    [data, confidenceMode],
  );

  const overrideMutation = useMutation({
    mutationFn: (payload: { row: InventoryRow; quantity: number; reason: string; note: string }) =>
      api.createOverride({
        product_id: payload.row.product_id,
        store_nbr: payload.row.store_nbr,
        recommended_qty: payload.row.recommended_qty,
        override_qty: payload.quantity,
        reason_code: payload.reason,
        note: payload.note || null,
        confidence_mode: confidenceMode,
      }),
    onSuccess: (_result, variables) => {
      setOverrides((current) => ({
        ...current,
        [`${variables.row.product_id}-${variables.row.store_nbr}`]: variables.quantity,
      }));
      setEditing(null);
    },
  });

  const exportMutation = useMutation({
    mutationFn: async (format: 'xlsx' | 'pdf') => {
      const lines = rows.map((row) => ({
        product_id: row.product_id,
        store_nbr: row.store_nbr,
        family: row.family,
        order_qty: overrides[`${row.product_id}-${row.store_nbr}`] ?? row.recommended_qty,
        unit_cost: 4.75,
      }));
      const blob = await api.exportPurchaseOrder(format, confidenceMode, lines);
      downloadBlob(blob, `forecastiq-purchase-order.${format}`);
    },
  });

  const totalUnits = rows.reduce(
    (sum, row) => sum + (overrides[`${row.product_id}-${row.store_nbr}`] ?? row.recommended_qty),
    0,
  );

  return (
    <div className="space-y-4">
      <Card>
        <CardContent className="flex flex-wrap items-center gap-4">
          <div role="group" aria-label="Confidence mode" className="flex rounded-md border border-slate-200 p-1">
            {MODES.map((mode) => (
              <button
                key={mode.value}
                type="button"
                aria-pressed={confidenceMode === mode.value}
                onClick={() => setConfidenceMode(mode.value)}
                className={
                  confidenceMode === mode.value
                    ? 'rounded px-4 py-1.5 text-sm font-semibold bg-teal text-white'
                    : 'rounded px-4 py-1.5 text-sm font-medium text-slate-600 hover:bg-slate-100'
                }
              >
                {mode.label}
                <span className="ml-1 text-[10px] opacity-70">{mode.hint}</span>
              </button>
            ))}
          </div>
          <div className="text-sm text-slate-500">
            <span className="font-semibold text-navy">{formatNumber(totalUnits, 0)}</span> units across{' '}
            {rows.length} lines
          </div>
          <div className="ml-auto flex gap-2">
            <Button variant="outline" onClick={() => exportMutation.mutate('xlsx')} disabled={rows.length === 0}>
              <FileSpreadsheet className="h-4 w-4" aria-hidden /> Excel
            </Button>
            <Button variant="secondary" onClick={() => exportMutation.mutate('pdf')} disabled={rows.length === 0}>
              <FileText className="h-4 w-4" aria-hidden /> PDF
            </Button>
          </div>
        </CardContent>
      </Card>

      <Card>
        <CardHeader>
          <CardTitle>Smart order recommendations</CardTitle>
          <span className="text-xs text-slate-400">
            P90 - stock + safety buffer when anomaly risk is high, otherwise mode base - stock
          </span>
        </CardHeader>
        <CardContent className="p-0">
          {isLoading ? (
            <Skeleton className="m-5 h-80" />
          ) : isError ? (
            <p role="alert" className="p-5 text-sm text-rose-600">
              Failed to load recommendations: {(error as Error)?.message}
            </p>
          ) : rows.length === 0 ? (
            <EmptyState title="No recommendations" description="No forecast rows for the selected scope." />
          ) : (
            <div className="max-h-[560px] overflow-auto">
              <table className="w-full text-sm" aria-label="Inventory recommendations">
                <thead className="table-header sticky top-0">
                  <tr>
                    <th className="px-4 py-2">Product</th>
                    <th className="px-4 py-2">Store</th>
                    <th className="px-4 py-2">Family</th>
                    <th className="px-4 py-2 text-right">Stock</th>
                    <th className="px-4 py-2 text-right">P10</th>
                    <th className="px-4 py-2 text-right">P50</th>
                    <th className="px-4 py-2 text-right">P90</th>
                    <th className="px-4 py-2 text-right">Order qty</th>
                    <th className="px-4 py-2">Risk</th>
                    <th className="px-4 py-2" />
                  </tr>
                </thead>
                <tbody>
                  {rows.map((row) => {
                    const key = `${row.product_id}-${row.store_nbr}`;
                    const overridden = overrides[key];
                    return (
                      <tr key={key} className="border-t border-slate-100">
                        <td className="px-4 py-2 font-medium text-navy">{row.product_id}</td>
                        <td className="px-4 py-2">#{row.store_nbr}</td>
                        <td className="px-4 py-2 text-slate-500">{row.family}</td>
                        <td className="px-4 py-2 text-right">{formatNumber(row.current_stock)}</td>
                        <td className="px-4 py-2 text-right">{formatNumber(row.p10)}</td>
                        <td className="px-4 py-2 text-right">{formatNumber(row.p50)}</td>
                        <td className="px-4 py-2 text-right">{formatNumber(row.p90)}</td>
                        <td className="px-4 py-2 text-right font-semibold">
                          {overridden !== undefined ? (
                            <span className="text-teal-dark">
                              {formatNumber(overridden)}
                              <span className="ml-1 text-[10px] uppercase">override</span>
                            </span>
                          ) : (
                            formatNumber(row.recommended_qty)
                          )}
                        </td>
                        <td className="px-4 py-2">
                          <Badge tone={RISK_TONE[row.risk_level]}>{row.risk_level}</Badge>
                        </td>
                        <td className="px-4 py-2 text-right">
                          <Button variant="ghost" size="sm" onClick={() => setEditing(row)}>
                            Override
                          </Button>
                        </td>
                      </tr>
                    );
                  })}
                </tbody>
              </table>
            </div>
          )}
        </CardContent>
      </Card>

      {editing ? (
        <OverrideDialog
          row={editing}
          onCancel={() => setEditing(null)}
          onSubmit={(quantity, reason, note) =>
            overrideMutation.mutate({ row: editing, quantity, reason, note })
          }
          pending={overrideMutation.isPending}
        />
      ) : null}
    </div>
  );
}

interface DialogProps {
  row: InventoryRow;
  pending: boolean;
  onCancel: () => void;
  onSubmit: (quantity: number, reason: string, note: string) => void;
}

function OverrideDialog({ row, pending, onCancel, onSubmit }: DialogProps) {
  const [quantity, setQuantity] = useState(row.recommended_qty);
  const [reason, setReason] = useState(REASON_CODES[0]);
  const [note, setNote] = useState('');

  return (
    <div
      role="dialog"
      aria-modal="true"
      aria-label="Manager override"
      className="fixed inset-0 z-50 flex items-center justify-center bg-black/40 p-4"
    >
      <Card className="w-full max-w-md">
        <CardHeader>
          <CardTitle>
            Override {row.product_id} - store #{row.store_nbr}
          </CardTitle>
        </CardHeader>
        <CardContent className="space-y-4">
          <div>
            <label htmlFor="qty" className="mb-1 block text-xs font-semibold text-slate-600">
              Order quantity (recommended {formatNumber(row.recommended_qty)})
            </label>
            <input
              id="qty"
              type="number"
              min={0}
              step={1}
              value={quantity}
              onChange={(event) => setQuantity(Number(event.target.value))}
              className="h-10 w-full rounded-md border border-slate-300 px-3 text-sm focus:border-teal focus:outline-none focus:ring-1 focus:ring-teal"
            />
          </div>
          <div>
            <label htmlFor="reason" className="mb-1 block text-xs font-semibold text-slate-600">
              Reason code
            </label>
            <Select id="reason" className="w-full" value={reason} onChange={(event) => setReason(event.target.value)}>
              {REASON_CODES.map((code) => (
                <option key={code} value={code}>
                  {code.replace(/_/g, ' ')}
                </option>
              ))}
            </Select>
          </div>
          <div>
            <label htmlFor="note" className="mb-1 block text-xs font-semibold text-slate-600">
              Note (optional)
            </label>
            <textarea
              id="note"
              rows={3}
              value={note}
              onChange={(event) => setNote(event.target.value)}
              className="w-full rounded-md border border-slate-300 p-2 text-sm focus:border-teal focus:outline-none focus:ring-1 focus:ring-teal"
            />
          </div>
          <div className="flex justify-end gap-2">
            <Button variant="outline" onClick={onCancel}>
              Cancel
            </Button>
            <Button disabled={pending} onClick={() => onSubmit(quantity, reason, note)}>
              {pending ? 'Saving...' : 'Save override'}
            </Button>
          </div>
        </CardContent>
      </Card>
    </div>
  );
}
