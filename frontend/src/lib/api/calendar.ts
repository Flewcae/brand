import { apiClient } from "@/lib/api/client";
import type {
  AspectRatio,
  CalendarSuggestionBatch,
  ContentCalendarEntry,
  ContentFormat,
  Paginated,
} from "@/lib/api/types";

export interface CalendarListFilters {
  status?: string;
  content_format?: string;
  date_from?: string;
  date_to?: string;
}

export async function listCalendarEntries(brandId: string, filters: CalendarListFilters = {}) {
  const { data } = await apiClient.get<Paginated<ContentCalendarEntry>>(
    `/brands/${brandId}/calendar/`,
    { params: filters }
  );
  return data;
}

export async function getCalendarEntry(brandId: string, entryId: string) {
  const { data } = await apiClient.get<ContentCalendarEntry>(
    `/brands/${brandId}/calendar/${entryId}/`
  );
  return data;
}

export interface CreateCalendarEntryPayload {
  scheduled_date: string;
  scheduled_time?: string | null;
  content_format: ContentFormat;
  aspect_ratio: AspectRatio;
  brief?: string;
}

export async function createCalendarEntry(brandId: string, payload: CreateCalendarEntryPayload) {
  const { data } = await apiClient.post<ContentCalendarEntry>(
    `/brands/${brandId}/calendar/`,
    payload
  );
  return data;
}

export async function updateCalendarEntry(
  brandId: string,
  entryId: string,
  payload: Partial<CreateCalendarEntryPayload>
) {
  const { data } = await apiClient.patch<ContentCalendarEntry>(
    `/brands/${brandId}/calendar/${entryId}/`,
    payload
  );
  return data;
}

export async function deleteCalendarEntry(brandId: string, entryId: string) {
  await apiClient.delete(`/brands/${brandId}/calendar/${entryId}/`);
}

export async function approveCalendarEntry(brandId: string, entryId: string) {
  const { data } = await apiClient.post<ContentCalendarEntry>(
    `/brands/${brandId}/calendar/${entryId}/approve/`
  );
  return data;
}

export async function rejectCalendarEntry(brandId: string, entryId: string) {
  const { data } = await apiClient.post<ContentCalendarEntry>(
    `/brands/${brandId}/calendar/${entryId}/reject/`
  );
  return data;
}

export async function evaluateCalendarEntry(brandId: string, entryId: string) {
  await apiClient.post(`/brands/${brandId}/calendar/${entryId}/evaluate/`);
}

export async function moreLikeThis(brandId: string, entryId: string, count = 3) {
  await apiClient.post(`/brands/${brandId}/calendar/${entryId}/more-like-this/`, { count });
}

export async function generateSuggestionsNow(brandId: string) {
  const { data } = await apiClient.post<CalendarSuggestionBatch>(
    `/brands/${brandId}/calendar/suggestions/generate-now/`
  );
  return data;
}

export async function getSuggestionBatch(brandId: string, batchId: string) {
  const { data } = await apiClient.get<CalendarSuggestionBatch>(
    `/brands/${brandId}/calendar/suggestion-batches/${batchId}/`
  );
  return data;
}
