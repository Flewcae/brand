export const queryKeys = {
  agency: ["agency"] as const,
  agencyMembers: (agencyId: string) => ["agency", agencyId, "members"] as const,
  brands: ["brands"] as const,
  brand: (brandId: string) => ["brands", brandId] as const,
  brandColors: (brandId: string) => ["brands", brandId, "colors"] as const,
  brandAssets: (brandId: string) => ["brands", brandId, "assets"] as const,
  brandAIContext: (brandId: string) => ["brands", brandId, "ai-context"] as const,
  calendarEntries: (brandId: string, filters: object = {}) =>
    ["brands", brandId, "calendar", filters] as const,
  calendarEntry: (brandId: string, entryId: string) =>
    ["brands", brandId, "calendar", entryId] as const,
  holidayCountries: ["holiday-countries"] as const,
  brandHolidays: (brandId: string, filters: object = {}) =>
    ["brands", brandId, "holidays", filters] as const,
  generationVersions: (brandId: string, entryId: string) =>
    ["brands", brandId, "calendar", entryId, "generations"] as const,
  usageSummary: (brandId: string) => ["brands", brandId, "usage", "summary"] as const,
  usageLogs: (brandId: string, filters: object = {}) =>
    ["brands", brandId, "usage", filters] as const,
  notifications: (isRead?: boolean) => ["notifications", isRead ?? "all"] as const,
};
