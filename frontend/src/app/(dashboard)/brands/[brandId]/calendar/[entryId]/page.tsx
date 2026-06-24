"use client";

import Link from "next/link";
import { useParams, useRouter } from "next/navigation";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import {
  ArrowLeft,
  CheckCircle2,
  Loader2,
  Sparkles,
  Trash2,
  Wand2,
  XCircle,
} from "lucide-react";
import { toast } from "sonner";

import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardFooter, CardHeader, CardTitle } from "@/components/ui/card";
import {
  approveCalendarEntry,
  deleteCalendarEntry,
  evaluateCalendarEntry,
  getCalendarEntry,
  moreLikeThis,
  rejectCalendarEntry,
} from "@/lib/api/calendar";
import {
  createGenerationVersion,
  IN_PROGRESS_STATUSES,
  listGenerationVersions,
  selectGenerationVersion,
} from "@/lib/api/generation";
import type { CalendarEntryStatus, GenerationStatus } from "@/lib/api/types";
import { queryKeys } from "@/lib/query-keys";

const STATUS_LABEL: Record<CalendarEntryStatus, string> = {
  draft: "Taslak",
  suggested: "Onerildi",
  approved: "Onaylandi",
  rejected: "Reddedildi",
  generated: "Uretildi",
  published: "Yayinlandi",
};

const GENERATION_STATUS_LABEL: Record<GenerationStatus, string> = {
  pending_prompt: "Prompt hazirlaniyor",
  prompt_ready: "Prompt hazir",
  submitted: "Gonderildi",
  processing: "Isleniyor",
  done: "Tamamlandi",
  failed: "Basarisiz",
};

export default function CalendarEntryDetailPage() {
  const { brandId, entryId } = useParams<{ brandId: string; entryId: string }>();
  const router = useRouter();
  const queryClient = useQueryClient();

  const { data: entry } = useQuery({
    queryKey: queryKeys.calendarEntry(brandId, entryId),
    queryFn: () => getCalendarEntry(brandId, entryId),
  });

  const { data: generations } = useQuery({
    queryKey: queryKeys.generationVersions(brandId, entryId),
    queryFn: () => listGenerationVersions(brandId, entryId),
    refetchInterval: (query) => {
      const hasInFlight = query.state.data?.results.some((version) =>
        IN_PROGRESS_STATUSES.includes(version.status)
      );
      return hasInFlight ? 3000 : false;
    },
  });

  const invalidateEntry = () =>
    queryClient.invalidateQueries({ queryKey: queryKeys.calendarEntry(brandId, entryId) });

  const approveMutation = useMutation({
    mutationFn: () => approveCalendarEntry(brandId, entryId),
    onSuccess: invalidateEntry,
    onError: () => toast.error("Onaylanamadi."),
  });

  const rejectMutation = useMutation({
    mutationFn: () => rejectCalendarEntry(brandId, entryId),
    onSuccess: invalidateEntry,
    onError: () => toast.error("Reddedilemedi."),
  });

  const evaluateMutation = useMutation({
    mutationFn: () => evaluateCalendarEntry(brandId, entryId),
    onSuccess: () => toast.success("Claude degerlendiriyor, varyasyonlar takvime eklenecek."),
    onError: () => toast.error("Baslatilamadi."),
  });

  const moreLikeThisMutation = useMutation({
    mutationFn: () => moreLikeThis(brandId, entryId, 3),
    onSuccess: () => toast.success("Benzer varyasyonlar isteniyor."),
    onError: () => toast.error("Baslatilamadi."),
  });

  const deleteMutation = useMutation({
    mutationFn: () => deleteCalendarEntry(brandId, entryId),
    onSuccess: () => {
      toast.success("Icerik silindi.");
      router.push(`/brands/${brandId}/calendar`);
    },
    onError: () => toast.error("Silinemedi."),
  });

  const generateMutation = useMutation({
    mutationFn: () => createGenerationVersion(brandId, entryId),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: queryKeys.generationVersions(brandId, entryId) });
      toast.success("Uretim baslatildi.");
    },
    onError: () => toast.error("Uretim baslatilamadi."),
  });

  const selectMutation = useMutation({
    mutationFn: (versionId: string) => selectGenerationVersion(brandId, entryId, versionId),
    onSuccess: () => {
      invalidateEntry();
      toast.success("Aktif versiyon guncellendi.");
    },
    onError: () => toast.error("Secilemedi."),
  });

  if (!entry) {
    return null;
  }

  return (
    <div className="flex flex-col gap-6">
      <Link
        href={`/brands/${brandId}/calendar`}
        className="inline-flex items-center gap-1 text-sm text-muted-foreground hover:text-foreground"
      >
        <ArrowLeft className="size-3.5" />
        Takvim
      </Link>

      <Card>
        <CardHeader>
          <div className="flex flex-wrap items-center justify-between gap-3">
            <div className="flex items-center gap-2 text-xs text-muted-foreground">
              <span className="font-mono">{entry.scheduled_date}</span>
              {entry.scheduled_time && <span>{entry.scheduled_time}</span>}
              <span>·</span>
              <span className="uppercase">{entry.content_format}</span>
              <span>·</span>
              <span>{entry.aspect_ratio}</span>
              <span>·</span>
              <span>{entry.source === "claude_suggestion" ? "Claude onerisi" : "Kullanici"}</span>
            </div>
            <Badge>{STATUS_LABEL[entry.status]}</Badge>
          </div>
          <CardTitle className="text-base font-normal text-foreground">
            {entry.brief || "(brief yok)"}
          </CardTitle>
        </CardHeader>
        <CardFooter className="flex flex-wrap gap-2">
          <Button
            size="sm"
            className="cursor-pointer gap-1.5"
            disabled={approveMutation.isPending}
            onClick={() => approveMutation.mutate()}
          >
            <CheckCircle2 className="size-3.5" />
            Onayla
          </Button>
          <Button
            size="sm"
            variant="outline"
            className="cursor-pointer gap-1.5"
            disabled={rejectMutation.isPending}
            onClick={() => rejectMutation.mutate()}
          >
            <XCircle className="size-3.5" />
            Reddet
          </Button>
          <Button
            size="sm"
            variant="outline"
            className="cursor-pointer gap-1.5"
            disabled={evaluateMutation.isPending}
            onClick={() => evaluateMutation.mutate()}
          >
            <Sparkles className="size-3.5" />
            Claude degerlendirsin
          </Button>
          <Button
            size="sm"
            variant="outline"
            className="cursor-pointer gap-1.5"
            disabled={moreLikeThisMutation.isPending}
            onClick={() => moreLikeThisMutation.mutate()}
          >
            <Sparkles className="size-3.5" />
            Buna benzer oner
          </Button>
          <Button
            size="sm"
            variant="ghost"
            className="cursor-pointer gap-1.5 text-muted-foreground hover:text-destructive"
            disabled={deleteMutation.isPending}
            onClick={() => deleteMutation.mutate()}
          >
            <Trash2 className="size-3.5" />
            Sil
          </Button>
        </CardFooter>
      </Card>

      <div className="flex items-center justify-between">
        <h2 className="font-mono text-base font-semibold">Uretim versiyonlari</h2>
        <Button
          size="sm"
          className="cursor-pointer gap-1.5"
          disabled={generateMutation.isPending}
          onClick={() => generateMutation.mutate()}
        >
          {generateMutation.isPending ? (
            <Loader2 className="size-4 animate-spin" />
          ) : (
            <Wand2 className="size-4" />
          )}
          Yeni uretim baslat
        </Button>
      </div>

      {generations?.results.length === 0 && (
        <p className="text-sm text-muted-foreground">Henuz uretim yapilmadi.</p>
      )}

      <div className="grid grid-cols-1 gap-4 sm:grid-cols-2 lg:grid-cols-3">
        {generations?.results.map((version) => {
          const isActive = entry.active_generation_version === version.id;
          const isInProgress = IN_PROGRESS_STATUSES.includes(version.status);
          return (
            <Card key={version.id} className={isActive ? "border-accent" : undefined}>
              <CardContent className="flex flex-col gap-3 pt-6">
                <div className="flex h-40 items-center justify-center overflow-hidden rounded-md bg-muted">
                  {version.status === "done" && version.media_file ? (
                    version.media_type === "video" ? (
                      <video src={version.media_file} className="h-full w-full object-contain" controls />
                    ) : (
                      // eslint-disable-next-line @next/next/no-img-element
                      <img
                        src={version.media_file}
                        alt={`Versiyon ${version.version_number}`}
                        className="h-full w-full object-contain"
                      />
                    )
                  ) : isInProgress ? (
                    <Loader2 className="size-6 animate-spin text-muted-foreground" />
                  ) : (
                    <span className="text-xs text-muted-foreground">Medya yok</span>
                  )}
                </div>
                <div className="flex items-center justify-between">
                  <span className="font-mono text-xs text-muted-foreground">
                    v{version.version_number}
                  </span>
                  <Badge variant={version.status === "failed" ? "destructive" : "secondary"}>
                    {isInProgress && <Loader2 className="size-3 animate-spin" />}
                    {GENERATION_STATUS_LABEL[version.status]}
                  </Badge>
                </div>
                {version.status === "failed" && version.error_message && (
                  <p className="text-xs text-destructive">{version.error_message}</p>
                )}
              </CardContent>
              {version.status === "done" && (
                <CardFooter>
                  <Button
                    size="sm"
                    variant={isActive ? "secondary" : "outline"}
                    className="w-full cursor-pointer"
                    disabled={isActive || selectMutation.isPending}
                    onClick={() => selectMutation.mutate(version.id)}
                  >
                    {isActive ? "Aktif versiyon" : "Bu versiyonu sec"}
                  </Button>
                </CardFooter>
              )}
            </Card>
          );
        })}
      </div>
    </div>
  );
}
