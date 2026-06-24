import { apiClient } from "@/lib/api/client";
import type { GenerationVersion, Paginated } from "@/lib/api/types";

export async function listGenerationVersions(brandId: string, entryId: string) {
  const { data } = await apiClient.get<Paginated<GenerationVersion>>(
    `/brands/${brandId}/calendar/${entryId}/generations/`
  );
  return data;
}

export async function createGenerationVersion(brandId: string, entryId: string) {
  const { data } = await apiClient.post<GenerationVersion>(
    `/brands/${brandId}/calendar/${entryId}/generations/`
  );
  return data;
}

export async function getGenerationVersion(
  brandId: string,
  entryId: string,
  versionId: string
) {
  const { data } = await apiClient.get<GenerationVersion>(
    `/brands/${brandId}/calendar/${entryId}/generations/${versionId}/`
  );
  return data;
}

export async function deleteGenerationVersion(
  brandId: string,
  entryId: string,
  versionId: string
) {
  await apiClient.delete(`/brands/${brandId}/calendar/${entryId}/generations/${versionId}/`);
}

export async function selectGenerationVersion(
  brandId: string,
  entryId: string,
  versionId: string
) {
  const { data } = await apiClient.post<GenerationVersion>(
    `/brands/${brandId}/calendar/${entryId}/generations/${versionId}/select/`
  );
  return data;
}

export const IN_PROGRESS_STATUSES: GenerationVersion["status"][] = [
  "pending_prompt",
  "prompt_ready",
  "submitted",
  "processing",
];
