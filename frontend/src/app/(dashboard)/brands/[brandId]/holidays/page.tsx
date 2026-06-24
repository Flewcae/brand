"use client";

import { useState } from "react";
import { useParams } from "next/navigation";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { CalendarHeart, Loader2, Trash2 } from "lucide-react";
import { toast } from "sonner";

import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { Checkbox } from "@/components/ui/checkbox";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Switch } from "@/components/ui/switch";
import { Tabs, TabsList, TabsTrigger } from "@/components/ui/tabs";
import { getBrand } from "@/lib/api/brands";
import {
  deleteBrandHoliday,
  importBrandHolidays,
  listBrandHolidays,
  updateBrandHoliday,
} from "@/lib/api/special-days";
import type { HolidayCategory } from "@/lib/api/types";
import { queryKeys } from "@/lib/query-keys";

const CATEGORY_LABEL: Record<HolidayCategory, string> = {
  official: "Resmi",
  religious: "Dini",
  popular: "Populer",
};

const CATEGORY_FILTERS: { value: string; label: string }[] = [
  { value: "all", label: "Tumu" },
  { value: "official", label: "Resmi" },
  { value: "religious", label: "Dini" },
  { value: "popular", label: "Populer" },
];

function nextYears(count: number) {
  const current = new Date().getFullYear();
  return Array.from({ length: count }, (_, i) => current + i);
}

export default function BrandHolidaysPage() {
  const { brandId } = useParams<{ brandId: string }>();
  const queryClient = useQueryClient();
  const [categoryFilter, setCategoryFilter] = useState("all");
  const [countryCode, setCountryCode] = useState("");
  const [selectedYears, setSelectedYears] = useState<number[]>([new Date().getFullYear()]);

  const { data: brand } = useQuery({
    queryKey: queryKeys.brand(brandId),
    queryFn: () => getBrand(brandId),
  });

  const filters = categoryFilter === "all" ? {} : { category: categoryFilter };
  const { data, isLoading } = useQuery({
    queryKey: queryKeys.brandHolidays(brandId, filters),
    queryFn: () => listBrandHolidays(brandId, filters),
  });

  const importMutation = useMutation({
    mutationFn: () =>
      importBrandHolidays(brandId, countryCode || brand?.country_code || "TR", selectedYears),
    onSuccess: () => {
      toast.success("Ice aktarma baslatildi, birazdan listede gorunecek.");
      setTimeout(() => {
        queryClient.invalidateQueries({ queryKey: ["brands", brandId, "holidays"] });
      }, 3000);
    },
    onError: () => toast.error("Ice aktarilamadi."),
  });

  const toggleActiveMutation = useMutation({
    mutationFn: ({ holidayId, isActive }: { holidayId: string; isActive: boolean }) =>
      updateBrandHoliday(brandId, holidayId, { is_active: isActive }),
    onSuccess: () =>
      queryClient.invalidateQueries({ queryKey: ["brands", brandId, "holidays"] }),
    onError: () => toast.error("Guncellenemedi."),
  });

  const deleteMutation = useMutation({
    mutationFn: (holidayId: string) => deleteBrandHoliday(brandId, holidayId),
    onSuccess: () =>
      queryClient.invalidateQueries({ queryKey: ["brands", brandId, "holidays"] }),
    onError: () => toast.error("Silinemedi."),
  });

  const years = nextYears(3);

  return (
    <div className="flex flex-col gap-6">
      <Card>
        <CardHeader>
          <CardTitle className="text-base">Ozel gunleri ice aktar</CardTitle>
          <CardDescription>
            Resmi/dini gunler `holidays` kutuphanesinden, populer/ticari gunler Claude&apos;dan
            gelir.
          </CardDescription>
        </CardHeader>
        <CardContent className="flex flex-wrap items-end gap-4">
          <div className="flex flex-col gap-1.5">
            <Label htmlFor="country-code">Ulke kodu</Label>
            <Input
              id="country-code"
              className="w-24"
              maxLength={2}
              placeholder={brand?.country_code || "TR"}
              value={countryCode}
              onChange={(event) => setCountryCode(event.target.value.toUpperCase())}
            />
          </div>
          <div className="flex flex-col gap-1.5">
            <Label>Yillar</Label>
            <div className="flex gap-3">
              {years.map((year) => (
                <label key={year} className="flex items-center gap-1.5 text-sm">
                  <Checkbox
                    checked={selectedYears.includes(year)}
                    onCheckedChange={(checked) =>
                      setSelectedYears((prev) =>
                        checked ? [...prev, year] : prev.filter((y) => y !== year)
                      )
                    }
                  />
                  {year}
                </label>
              ))}
            </div>
          </div>
          <Button
            className="cursor-pointer gap-1.5"
            disabled={importMutation.isPending || selectedYears.length === 0}
            onClick={() => importMutation.mutate()}
          >
            {importMutation.isPending && <Loader2 className="size-4 animate-spin" />}
            Ice aktar
          </Button>
        </CardContent>
      </Card>

      <Tabs value={categoryFilter} onValueChange={(value) => setCategoryFilter(value)}>
        <TabsList>
          {CATEGORY_FILTERS.map((filter) => (
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
            <CalendarHeart className="size-8 text-muted-foreground" />
            <p className="text-sm text-muted-foreground">Bu filtrede ozel gun yok.</p>
          </CardContent>
        </Card>
      )}

      <div className="flex flex-col gap-2">
        {data?.results.map((holiday) => (
          <Card key={holiday.id}>
            <CardContent className="flex items-center justify-between gap-4 py-3">
              <div className="flex items-center gap-3">
                <span className="w-24 shrink-0 font-mono text-sm text-muted-foreground">
                  {holiday.date}
                </span>
                <span className="text-sm">{holiday.name}</span>
                <Badge variant="outline">{CATEGORY_LABEL[holiday.category]}</Badge>
              </div>
              <div className="flex items-center gap-3">
                <Switch
                  checked={holiday.is_active}
                  onCheckedChange={(checked) =>
                    toggleActiveMutation.mutate({ holidayId: holiday.id, isActive: checked })
                  }
                  aria-label={`${holiday.name} aktif/pasif`}
                />
                <Button
                  variant="ghost"
                  size="icon-sm"
                  className="cursor-pointer text-muted-foreground hover:text-destructive"
                  disabled={deleteMutation.isPending}
                  onClick={() => deleteMutation.mutate(holiday.id)}
                  aria-label={`${holiday.name} ozel gununu sil`}
                >
                  <Trash2 className="size-3.5" />
                </Button>
              </div>
            </CardContent>
          </Card>
        ))}
      </div>
    </div>
  );
}
