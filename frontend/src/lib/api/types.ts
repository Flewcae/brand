export interface Paginated<T> {
  count: number;
  next: string | null;
  previous: string | null;
  results: T[];
}

export interface User {
  id: string;
  email: string;
  first_name: string;
  last_name: string;
}

export interface Agency {
  id: string;
  name: string;
  is_active: boolean;
  created_at: string;
}

export interface AgencyMembership {
  id: string;
  user: User;
  role: "member";
  is_active: boolean;
  joined_at: string;
}

export type AssetType = "logo" | "identity_document";
export type AnalysisStatus = "pending" | "processing" | "done" | "failed";
export type ContentFormat = "image" | "video";
export type AspectRatio = "landscape" | "portrait" | "square";
export type CalendarEntryStatus =
  | "draft"
  | "suggested"
  | "approved"
  | "rejected"
  | "generated"
  | "published";
export type CalendarEntrySource = "user_input" | "claude_suggestion";
export type GenerationStatus =
  | "pending_prompt"
  | "prompt_ready"
  | "submitted"
  | "processing"
  | "done"
  | "failed";
export type HolidayCategory = "official" | "religious" | "popular";
export type UsageProvider = "claude" | "grok";
export type UsageOperation =
  | "vision_analysis"
  | "prompt_generation"
  | "suggestion_generation"
  | "image_generation"
  | "video_generation";
export type NotificationType =
  | "generation_done"
  | "generation_failed"
  | "reminder_24h"
  | "reminder_12h"
  | "reminder_3h"
  | "reminder_due"
  | "suggestion_batch_ready";

export interface BrandColor {
  id: string;
  name: string;
  hex_value: string;
  role: string;
  source: "manual" | "extracted_from_logo";
  order: number;
}

export interface BrandProfile {
  id: string;
  name: string;
  slug: string;
  is_active: boolean;
  style_description: string;
  voice_tone_description: string;
  voice_traits: string[];
  target_audience: string;
  font_primary: string;
  font_secondary: string;
  country_code: string;
  timezone: string;
  default_publish_time: string;
  colors: BrandColor[];
  created_at: string;
  updated_at: string;
}

export interface BrandAsset {
  id: string;
  asset_type: AssetType;
  file: string;
  original_filename: string;
  content_type: string;
  page_images: string[];
  claude_vision_analysis: Record<string, unknown> | null;
  analysis_status: AnalysisStatus;
  is_primary: boolean;
  uploaded_at: string;
}

export interface BrandAIContext {
  style_keywords: string[];
  mood_descriptors: string[];
  visual_donts: string[];
  enrichment_summary: string;
  last_enriched_at: string | null;
}

export interface ContentCalendarEntry {
  id: string;
  scheduled_date: string;
  scheduled_time: string | null;
  content_format: ContentFormat;
  aspect_ratio: AspectRatio;
  status: CalendarEntryStatus;
  source: CalendarEntrySource;
  brief: string;
  brand_holiday: string | null;
  suggestion_batch: string | null;
  parent_entry: string | null;
  active_generation_version: string | null;
  created_at: string;
  updated_at: string;
}

export interface CalendarSuggestionBatch {
  id: string;
  trigger: "weekly_beat" | "manual";
  status: "pending" | "running" | "done" | "failed";
  entry_count: number;
  created_at: string;
  completed_at: string | null;
}

export interface CountryHolidayTemplate {
  country_code: string;
  popular_days_last_refreshed_at: string | null;
}

export interface BrandHoliday {
  id: string;
  name: string;
  date: string;
  category: HolidayCategory;
  is_active: boolean;
  notes: string;
  created_at: string;
  updated_at: string;
}

export interface GenerationVersion {
  id: string;
  version_number: number;
  media_type: ContentFormat;
  status: GenerationStatus;
  claude_prompt_text: string;
  grok_request_payload: Record<string, unknown>;
  grok_response_meta: Record<string, unknown> | null;
  media_file: string | null;
  thumbnail_file: string | null;
  error_message: string;
  requested_by: string | null;
  created_at: string;
  updated_at: string;
}

export interface UsageLog {
  id: string;
  provider: UsageProvider;
  model: string;
  operation: UsageOperation;
  cost_in_usd_ticks: number | null;
  input_tokens: number | null;
  output_tokens: number | null;
  estimated_cost_usd: string | null;
  generation_version: string | null;
  suggestion_batch: string | null;
  brand_asset: string | null;
  created_at: string;
}

export interface UsageSummaryRow {
  provider?: UsageProvider;
  operation?: UsageOperation;
  // The aggregate view returns a raw dict (not run through a DecimalField),
  // so this comes back as a JSON number, not a string like estimated_cost_usd
  // elsewhere -- accept both rather than assuming one.
  total_cost_usd: string | number | null;
  call_count: number;
}

export interface UsageSummary {
  totals: { total_cost_usd: string | number | null; call_count: number };
  by_provider: UsageSummaryRow[];
  by_operation: UsageSummaryRow[];
}

export interface PushSubscription {
  id: string;
  registration_token: string;
  user_agent: string;
  is_active: boolean;
  created_at: string;
}

export interface Notification {
  id: string;
  brand: string | null;
  notification_type: NotificationType;
  title: string;
  body: string;
  related_calendar_entry: string | null;
  related_generation_version: string | null;
  is_read: boolean;
  channel: "fcm" | "in_app_only";
  delivery_status: "pending" | "sent" | "failed" | "skipped_no_subscription";
  created_at: string;
  sent_at: string | null;
}
