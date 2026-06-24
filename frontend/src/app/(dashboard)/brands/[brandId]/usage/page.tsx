"use client";

import { useParams } from "next/navigation";
import { useQuery } from "@tanstack/react-query";

import {
  Card,
  CardContent,
  CardDescription,
  CardHeader,
  CardTitle,
} from "@/components/ui/card";
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from "@/components/ui/table";
import { getUsageSummary, listUsageLogs } from "@/lib/api/usage";
import type { UsageSummaryRow } from "@/lib/api/types";
import { queryKeys } from "@/lib/query-keys";

function formatUsd(value: string | number | null) {
  if (value === null) return "$0.00";
  return `$${Number(value).toFixed(4)}`;
}

function BreakdownBar({
  rows,
  labelKey,
}: {
  rows: UsageSummaryRow[];
  labelKey: "provider" | "operation";
}) {
  const max = Math.max(...rows.map((row) => Number(row.total_cost_usd ?? 0)), 0.0001);
  return (
    <div className="flex flex-col gap-3">
      {rows.map((row) => {
        const cost = Number(row.total_cost_usd ?? 0);
        const widthPct = Math.max((cost / max) * 100, 2);
        return (
          <div key={row[labelKey]} className="flex flex-col gap-1">
            <div className="flex items-center justify-between text-xs">
              <span className="font-mono uppercase text-muted-foreground">{row[labelKey]}</span>
              <span className="font-mono">
                {formatUsd(row.total_cost_usd)} · {row.call_count} cagri
              </span>
            </div>
            <div className="h-1.5 w-full overflow-hidden rounded-full bg-muted">
              <div
                className="h-full rounded-full bg-accent transition-all"
                style={{ width: `${widthPct}%` }}
              />
            </div>
          </div>
        );
      })}
    </div>
  );
}

export default function BrandUsagePage() {
  const { brandId } = useParams<{ brandId: string }>();

  const { data: summary } = useQuery({
    queryKey: queryKeys.usageSummary(brandId),
    queryFn: () => getUsageSummary(brandId),
  });

  const { data: logs } = useQuery({
    queryKey: queryKeys.usageLogs(brandId),
    queryFn: () => listUsageLogs(brandId),
  });

  return (
    <div className="flex flex-col gap-6">
      <div>
        <h1 className="font-mono text-xl font-semibold">Kullanim ve maliyet</h1>
        <p className="text-sm text-muted-foreground">
          Claude ve Grok cagrilarinin marka bazli maliyet takibi.
        </p>
      </div>

      <div className="grid grid-cols-1 gap-4 sm:grid-cols-2">
        <Card>
          <CardHeader>
            <CardDescription>Toplam maliyet</CardDescription>
            <CardTitle className="font-mono text-2xl">
              {formatUsd(summary?.totals.total_cost_usd ?? null)}
            </CardTitle>
          </CardHeader>
          <CardContent className="text-sm text-muted-foreground">
            {summary?.totals.call_count ?? 0} toplam cagri
          </CardContent>
        </Card>
        <Card>
          <CardHeader>
            <CardTitle className="text-base">Saglayiciya gore</CardTitle>
          </CardHeader>
          <CardContent>
            {summary?.by_provider && summary.by_provider.length > 0 ? (
              <BreakdownBar rows={summary.by_provider} labelKey="provider" />
            ) : (
              <p className="text-sm text-muted-foreground">Henuz veri yok.</p>
            )}
          </CardContent>
        </Card>
      </div>

      <Card>
        <CardHeader>
          <CardTitle className="text-base">Islem turune gore</CardTitle>
        </CardHeader>
        <CardContent>
          {summary?.by_operation && summary.by_operation.length > 0 ? (
            <BreakdownBar rows={summary.by_operation} labelKey="operation" />
          ) : (
            <p className="text-sm text-muted-foreground">Henuz veri yok.</p>
          )}
        </CardContent>
      </Card>

      <Card>
        <CardHeader>
          <CardTitle className="text-base">Son islemler</CardTitle>
        </CardHeader>
        <CardContent>
          <Table>
            <TableHeader>
              <TableRow>
                <TableHead>Tarih</TableHead>
                <TableHead>Saglayici</TableHead>
                <TableHead>Model</TableHead>
                <TableHead>Islem</TableHead>
                <TableHead className="text-right">Maliyet</TableHead>
              </TableRow>
            </TableHeader>
            <TableBody>
              {logs?.results.map((log) => (
                <TableRow key={log.id}>
                  <TableCell className="font-mono text-xs text-muted-foreground">
                    {new Date(log.created_at).toLocaleString("tr-TR")}
                  </TableCell>
                  <TableCell className="uppercase">{log.provider}</TableCell>
                  <TableCell className="font-mono text-xs">{log.model}</TableCell>
                  <TableCell>{log.operation}</TableCell>
                  <TableCell className="text-right font-mono">
                    {formatUsd(log.estimated_cost_usd)}
                  </TableCell>
                </TableRow>
              ))}
              {logs?.results.length === 0 && (
                <TableRow>
                  <TableCell colSpan={5} className="text-center text-sm text-muted-foreground">
                    Henuz kayit yok.
                  </TableCell>
                </TableRow>
              )}
            </TableBody>
          </Table>
        </CardContent>
      </Card>
    </div>
  );
}
