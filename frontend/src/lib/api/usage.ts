import { apiClient } from "@/lib/api/client";
import type { Paginated, UsageLog, UsageSummary } from "@/lib/api/types";

export interface UsageListFilters {
  provider?: string;
  operation?: string;
  date_from?: string;
  date_to?: string;
}

export async function listUsageLogs(brandId: string, filters: UsageListFilters = {}) {
  const { data } = await apiClient.get<Paginated<UsageLog>>(`/brands/${brandId}/usage/`, {
    params: filters,
  });
  return data;
}

export async function getUsageSummary(brandId: string) {
  const { data } = await apiClient.get<UsageSummary>(`/brands/${brandId}/usage/summary/`);
  return data;
}
