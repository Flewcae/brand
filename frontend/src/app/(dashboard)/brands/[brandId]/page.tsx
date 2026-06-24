"use client";

import { useEffect } from "react";
import { useParams } from "next/navigation";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { Loader2, Sparkles } from "lucide-react";
import { useForm } from "react-hook-form";
import { toast } from "sonner";

import { Button } from "@/components/ui/button";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Textarea } from "@/components/ui/textarea";
import {
  applyBrandAIContext,
  getBrand,
  getBrandAIContext,
  updateBrand,
  type CreateBrandPayload,
} from "@/lib/api/brands";
import { queryKeys } from "@/lib/query-keys";

type ProfileFormValues = Pick<
  CreateBrandPayload,
  "style_description" | "voice_tone_description" | "target_audience" | "font_primary" | "font_secondary"
>;

export default function BrandProfilePage() {
  const { brandId } = useParams<{ brandId: string }>();
  const queryClient = useQueryClient();

  const { data: brand } = useQuery({
    queryKey: queryKeys.brand(brandId),
    queryFn: () => getBrand(brandId),
  });

  const { data: aiContext } = useQuery({
    queryKey: queryKeys.brandAIContext(brandId),
    queryFn: () => getBrandAIContext(brandId),
  });

  const { register, handleSubmit, reset } = useForm<ProfileFormValues>();

  useEffect(() => {
    if (brand) {
      reset({
        style_description: brand.style_description,
        voice_tone_description: brand.voice_tone_description,
        target_audience: brand.target_audience,
        font_primary: brand.font_primary,
        font_secondary: brand.font_secondary,
      });
    }
  }, [brand, reset]);

  const saveMutation = useMutation({
    mutationFn: (values: ProfileFormValues) => updateBrand(brandId, values),
    onSuccess: (updated) => {
      queryClient.setQueryData(queryKeys.brand(brandId), updated);
      toast.success("Profil kaydedildi.");
    },
    onError: () => toast.error("Kaydedilemedi."),
  });

  const applyMutation = useMutation({
    mutationFn: ({
      field,
      mode,
    }: {
      field: "style_description" | "voice_tone_description";
      mode: "append" | "replace";
    }) => applyBrandAIContext(brandId, field, mode),
    onSuccess: (updated) => {
      queryClient.setQueryData(queryKeys.brand(brandId), updated);
      reset({
        style_description: updated.style_description,
        voice_tone_description: updated.voice_tone_description,
        target_audience: updated.target_audience,
        font_primary: updated.font_primary,
        font_secondary: updated.font_secondary,
      });
      toast.success("AI onerisi uygulandi.");
    },
    onError: () => toast.error("Uygulanamadi."),
  });

  if (!brand) {
    return null;
  }

  return (
    <div className="grid grid-cols-1 gap-6 lg:grid-cols-3">
      <Card className="lg:col-span-2">
        <CardHeader>
          <CardTitle className="text-base">Marka profili</CardTitle>
          <CardDescription>
            Bu alanlar kullanici tarafindan yazilir; Claude&apos;un vision analizi buraya
            otomatik yazilmaz.
          </CardDescription>
        </CardHeader>
        <CardContent>
          <form
            onSubmit={handleSubmit((values) => saveMutation.mutate(values))}
            className="flex flex-col gap-4"
          >
            <div className="flex flex-col gap-1.5">
              <Label htmlFor="style_description">Stil aciklamasi</Label>
              <Textarea id="style_description" rows={3} {...register("style_description")} />
            </div>
            <div className="flex flex-col gap-1.5">
              <Label htmlFor="voice_tone_description">Ses tonu</Label>
              <Textarea id="voice_tone_description" rows={3} {...register("voice_tone_description")} />
            </div>
            <div className="flex flex-col gap-1.5">
              <Label htmlFor="target_audience">Hedef kitle</Label>
              <Textarea id="target_audience" rows={2} {...register("target_audience")} />
            </div>
            <div className="grid grid-cols-2 gap-4">
              <div className="flex flex-col gap-1.5">
                <Label htmlFor="font_primary">Birincil font</Label>
                <Input id="font_primary" {...register("font_primary")} />
              </div>
              <div className="flex flex-col gap-1.5">
                <Label htmlFor="font_secondary">Ikincil font</Label>
                <Input id="font_secondary" {...register("font_secondary")} />
              </div>
            </div>
            <Button type="submit" disabled={saveMutation.isPending} className="w-fit cursor-pointer">
              {saveMutation.isPending && <Loader2 className="size-4 animate-spin" />}
              Kaydet
            </Button>
          </form>
        </CardContent>
      </Card>

      <Card>
        <CardHeader>
          <CardTitle className="flex items-center gap-1.5 text-base">
            <Sparkles className="size-4 text-accent" />
            AI baglami
          </CardTitle>
          <CardDescription>
            Logo/kimlik dokumanlarindan Claude&apos;un cikardigi izlenim. Kendi alanlarina cekmek
            icin asagidan uygula.
          </CardDescription>
        </CardHeader>
        <CardContent className="flex flex-col gap-4 text-sm">
          {!aiContext?.enrichment_summary && (
            <p className="text-muted-foreground">
              Henuz analiz yok. Varliklar sekmesinden logo veya kimlik dokumani yukle.
            </p>
          )}
          {aiContext?.enrichment_summary && (
            <>
              <p className="text-muted-foreground">{aiContext.enrichment_summary}</p>
              {aiContext.style_keywords.length > 0 && (
                <div className="flex flex-wrap gap-1.5">
                  {aiContext.style_keywords.map((keyword) => (
                    <span
                      key={keyword}
                      className="rounded-full bg-secondary px-2 py-0.5 font-mono text-xs text-secondary-foreground"
                    >
                      {keyword}
                    </span>
                  ))}
                </div>
              )}
              <div className="flex flex-col gap-2 border-t border-border pt-3">
                <Button
                  variant="outline"
                  size="sm"
                  className="cursor-pointer justify-start"
                  disabled={applyMutation.isPending}
                  onClick={() =>
                    applyMutation.mutate({ field: "style_description", mode: "append" })
                  }
                >
                  Stil aciklamasina ekle
                </Button>
                <Button
                  variant="outline"
                  size="sm"
                  className="cursor-pointer justify-start"
                  disabled={applyMutation.isPending}
                  onClick={() =>
                    applyMutation.mutate({ field: "voice_tone_description", mode: "append" })
                  }
                >
                  Ses tonuna ekle
                </Button>
              </div>
            </>
          )}
        </CardContent>
      </Card>
    </div>
  );
}
