"use client";

import { useState } from "react";
import Link from "next/link";
import { useParams } from "next/navigation";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { CalendarDays, Loader2, Sparkles } from "lucide-react";
import { toast } from "sonner";

import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Card, CardContent } from "@/components/ui/card";
import {
  Tabs,
  TabsList,
  TabsTrigger,
} from "@/components/ui/tabs";
import { CreateEntryDialog } from "@/components/calendar/create-entry-dialog";
import { generateSuggestionsNow, listCalendarEntries } from "@/lib/api/calendar";
import type { CalendarEntryStatus } from "@/lib/api/types";
import { queryKeys } from "@/lib/query-keys";

const STATUS_LABEL: Record<CalendarEntryStatus, string> = {
  draft: "Taslak",
  suggested: "Onerildi",
  approved: "Onaylandi",
  rejected: "Reddedildi",
  generated: "Uretildi",
  published: "Yayinlandi",
};

const STATUS_VARIANT: Record<
  CalendarEntryStatus,
  "secondary" | "outline" | "default" | "destructive"
> = {
  draft: "secondary",
  suggested: "outline",
  approved: "default",
  rejected: "destructive",
  generated: "default",
  published: "default",
};

const FILTERS: { value: string; label: string }[] = [
  { value: "all", label: "Tumu" },
  { value: "draft", label: "Taslak" },
  { value: "suggested", label: "Onerildi" },
  { value: "approved", label: "Onaylandi" },
  { value: "generated", label: "Uretildi" },
  { value: "published", label: "Yayinlandi" },
  { value: "rejected", label: "Reddedildi" },
];

export default function CalendarPage() {
  const { brandId } = useParams<{ brandId: string }>();
  const [statusFilter, setStatusFilter] = useState("all");
  const queryClient = useQueryClient();

  const filters = statusFilter === "all" ? {} : { status: statusFilter };

  const { data, isLoading } = useQuery({
    queryKey: queryKeys.calendarEntries(brandId, filters),
    queryFn: () => listCalendarEntries(brandId, filters),
  });

  const suggestMutation = useMutation({
    mutationFn: () => generateSuggestionsNow(brandId),
    onSuccess: () => {
      toast.success("Claude oneri olusturuyor, birazdan takvimde gorunecek.");
      setTimeout(() => {
        queryClient.invalidateQueries({ queryKey: ["brands", brandId, "calendar"] });
      }, 4000);
    },
    onError: () => toast.error("Oneri baslatilamadi."),
  });

  return (
    <div className="flex flex-col gap-6">
      <div className="flex flex-wrap items-center justify-between gap-3">
        <div>
          <h1 className="font-mono text-xl font-semibold">Icerik takvimi</h1>
          <p className="text-sm text-muted-foreground">
            Planlanan ve onerilen icerikler.
          </p>
        </div>
        <div className="flex gap-2">
          <Button
            variant="outline"
            className="cursor-pointer gap-1.5"
            disabled={suggestMutation.isPending}
            onClick={() => suggestMutation.mutate()}
          >
            {suggestMutation.isPending ? (
              <Loader2 className="size-4 animate-spin" />
            ) : (
              <Sparkles className="size-4" />
            )}
            Claude&apos;dan oneri al
          </Button>
          <CreateEntryDialog brandId={brandId} />
        </div>
      </div>

      <Tabs value={statusFilter} onValueChange={(value) => setStatusFilter(value)}>
        <TabsList>
          {FILTERS.map((filter) => (
            <TabsTrigger key={filter.value} value={filter.value} className="cursor-pointer">
              {filter.label}
            </TabsTrigger>
          ))}
        </TabsList>
      </Tabs>

      {isLoading && <p className="text-sm text-muted-foreground">Yukleniyor...</p>}
      {!isLoading && data?.results.length === 0 && (
        <Card className="border-dashed">
          <CardContent className="flex flex-col items-center gap-2 py-12 text-center">
            <CalendarDays className="size-8 text-muted-foreground" />
            <p className="text-sm text-muted-foreground">Bu filtrede icerik yok.</p>
          </CardContent>
        </Card>
      )}

      <div className="flex flex-col gap-2">
        {data?.results.map((entry) => (
          <Link key={entry.id} href={`/brands/${brandId}/calendar/${entry.id}`}>
            <Card className="cursor-pointer transition-colors hover:border-accent/50">
              <CardContent className="flex items-center justify-between gap-4 py-4">
                <div className="flex min-w-0 flex-col gap-1">
                  <div className="flex items-center gap-2 text-xs text-muted-foreground">
                    <span className="font-mono">{entry.scheduled_date}</span>
                    {entry.scheduled_time && <span>{entry.scheduled_time}</span>}
                    <span>·</span>
                    <span className="uppercase">{entry.content_format}</span>
                    <span>·</span>
                    <span>{entry.aspect_ratio}</span>
                  </div>
                  <p className="truncate text-sm">{entry.brief || "(brief yok)"}</p>
                </div>
                <Badge variant={STATUS_VARIANT[entry.status]} className="shrink-0">
                  {STATUS_LABEL[entry.status]}
                </Badge>
              </CardContent>
            </Card>
          </Link>
        ))}
      </div>
    </div>
  );
}
