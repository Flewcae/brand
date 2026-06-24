import { apiClient } from "@/lib/api/client";
import type { BrandHoliday, CountryHolidayTemplate, Paginated } from "@/lib/api/types";

export async function listCountryTemplates() {
  const { data } = await apiClient.get<Paginated<CountryHolidayTemplate>>(
    "/holidays/countries/"
  );
  return data;
}

export async function importBrandHolidays(brandId: string, countryCode: string, years: number[]) {
  const { data } = await apiClient.post<{ detail: string }>(
    `/brands/${brandId}/holidays/import/`,
    { country_code: countryCode, years }
  );
  return data;
}

export interface HolidayListFilters {
  category?: string;
  is_active?: boolean;
  date_from?: string;
  date_to?: string;
}

export async function listBrandHolidays(brandId: string, filters: HolidayListFilters = {}) {
  const { data } = await apiClient.get<Paginated<BrandHoliday>>(`/brands/${brandId}/holidays/`, {
    params: filters,
  });
  return data;
}

export async function updateBrandHoliday(
  brandId: string,
  holidayId: string,
  payload: Partial<Pick<BrandHoliday, "is_active" | "notes" | "name" | "date">>
) {
  const { data } = await apiClient.patch<BrandHoliday>(
    `/brands/${brandId}/holidays/${holidayId}/`,
    payload
  );
  return data;
}

export async function deleteBrandHoliday(brandId: string, holidayId: string) {
  await apiClient.delete(`/brands/${brandId}/holidays/${holidayId}/`);
}
