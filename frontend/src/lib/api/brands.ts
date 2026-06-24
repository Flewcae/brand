import { apiClient } from "@/lib/api/client";
import type {
  BrandAIContext,
  BrandAsset,
  BrandColor,
  BrandProfile,
  Paginated,
} from "@/lib/api/types";

export async function listBrands() {
  const { data } = await apiClient.get<Paginated<BrandProfile>>("/brands/");
  return data;
}

export async function getBrand(brandId: string) {
  const { data } = await apiClient.get<BrandProfile>(`/brands/${brandId}/`);
  return data;
}

export type CreateBrandPayload = Partial<
  Pick<
    BrandProfile,
    | "name"
    | "slug"
    | "style_description"
    | "voice_tone_description"
    | "voice_traits"
    | "target_audience"
    | "font_primary"
    | "font_secondary"
    | "country_code"
    | "timezone"
    | "default_publish_time"
  >
>;

export async function createBrand(payload: CreateBrandPayload) {
  const { data } = await apiClient.post<BrandProfile>("/brands/", payload);
  return data;
}

export async function updateBrand(brandId: string, payload: CreateBrandPayload) {
  const { data } = await apiClient.patch<BrandProfile>(`/brands/${brandId}/`, payload);
  return data;
}

export async function deleteBrand(brandId: string) {
  await apiClient.delete(`/brands/${brandId}/`);
}

export async function listBrandColors(brandId: string) {
  const { data } = await apiClient.get<Paginated<BrandColor>>(`/brands/${brandId}/colors/`);
  return data;
}

export async function createBrandColor(
  brandId: string,
  payload: Omit<BrandColor, "id">
) {
  const { data } = await apiClient.post<BrandColor>(`/brands/${brandId}/colors/`, payload);
  return data;
}

export async function deleteBrandColor(brandId: string, colorId: string) {
  await apiClient.delete(`/brands/${brandId}/colors/${colorId}/`);
}

export async function listBrandAssets(brandId: string) {
  const { data } = await apiClient.get<Paginated<BrandAsset>>(`/brands/${brandId}/assets/`);
  return data;
}

export async function uploadBrandAsset(
  brandId: string,
  file: File,
  assetType: BrandAsset["asset_type"]
) {
  const formData = new FormData();
  formData.append("file", file);
  formData.append("asset_type", assetType);
  const { data } = await apiClient.post<BrandAsset>(`/brands/${brandId}/assets/`, formData, {
    headers: { "Content-Type": "multipart/form-data" },
  });
  return data;
}

export async function deleteBrandAsset(brandId: string, assetId: string) {
  await apiClient.delete(`/brands/${brandId}/assets/${assetId}/`);
}

export async function getBrandAssetAnalysis(brandId: string, assetId: string) {
  const { data } = await apiClient.get<BrandAsset>(`/brands/${brandId}/assets/${assetId}/analysis/`);
  return data;
}

export async function getBrandAIContext(brandId: string) {
  const { data } = await apiClient.get<BrandAIContext>(`/brands/${brandId}/ai-context/`);
  return data;
}

export async function applyBrandAIContext(
  brandId: string,
  targetField: "style_description" | "voice_tone_description",
  mode: "append" | "replace"
) {
  const { data } = await apiClient.post<BrandProfile>(`/brands/${brandId}/ai-context/apply/`, {
    target_field: targetField,
    mode,
  });
  return data;
}
