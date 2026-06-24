"use client";

import { useState } from "react";
import { useParams } from "next/navigation";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { Loader2, Plus, Trash2 } from "lucide-react";
import { useForm } from "react-hook-form";
import { toast } from "sonner";

import { Button } from "@/components/ui/button";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import {
  createBrandColor,
  deleteBrandColor,
  listBrandColors,
} from "@/lib/api/brands";
import type { BrandColor } from "@/lib/api/types";
import { queryKeys } from "@/lib/query-keys";

interface ColorFormValues {
  name: string;
  hex_value: string;
  role: string;
}

const HEX_PATTERN = /^#[0-9a-fA-F]{6}$/;

export default function BrandColorsPage() {
  const { brandId } = useParams<{ brandId: string }>();
  const queryClient = useQueryClient();
  const [formError, setFormError] = useState<string | null>(null);

  const { data, isLoading } = useQuery({
    queryKey: queryKeys.brandColors(brandId),
    queryFn: () => listBrandColors(brandId),
  });

  const { register, handleSubmit, reset } = useForm<ColorFormValues>({
    defaultValues: { name: "", hex_value: "#22c55e", role: "" },
  });

  const createMutation = useMutation({
    mutationFn: (values: ColorFormValues) =>
      createBrandColor(brandId, {
        name: values.name,
        hex_value: values.hex_value,
        role: values.role,
        source: "manual",
        order: data?.results.length ?? 0,
      }),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: queryKeys.brandColors(brandId) });
      reset({ name: "", hex_value: "#22c55e", role: "" });
      setFormError(null);
    },
    onError: () => toast.error("Renk eklenemedi."),
  });

  const deleteMutation = useMutation({
    mutationFn: (colorId: string) => deleteBrandColor(brandId, colorId),
    onSuccess: () => queryClient.invalidateQueries({ queryKey: queryKeys.brandColors(brandId) }),
    onError: () => toast.error("Renk silinemedi."),
  });

  const onSubmit = (values: ColorFormValues) => {
    if (!HEX_PATTERN.test(values.hex_value)) {
      setFormError("Gecerli bir hex deger girin (orn. #22C55E).");
      return;
    }
    createMutation.mutate(values);
  };

  return (
    <div className="grid grid-cols-1 gap-6 lg:grid-cols-3">
      <Card className="lg:col-span-2">
        <CardHeader>
          <CardTitle className="text-base">Marka renk paleti</CardTitle>
        </CardHeader>
        <CardContent>
          {isLoading && <p className="text-sm text-muted-foreground">Yukleniyor...</p>}
          {!isLoading && data?.results.length === 0 && (
            <p className="text-sm text-muted-foreground">Henuz renk eklenmedi.</p>
          )}
          <div className="flex flex-col gap-2">
            {data?.results.map((color: BrandColor) => (
              <div
                key={color.id}
                className="flex items-center justify-between rounded-md border border-border px-3 py-2"
              >
                <div className="flex items-center gap-3">
                  <span
                    className="size-7 rounded-md border border-border"
                    style={{ backgroundColor: color.hex_value }}
                  />
                  <div className="text-sm">
                    <p className="font-medium">{color.name || color.hex_value}</p>
                    <p className="font-mono text-xs text-muted-foreground">
                      {color.hex_value} {color.role && `· ${color.role}`}
                    </p>
                  </div>
                </div>
                <Button
                  variant="ghost"
                  size="icon-sm"
                  className="cursor-pointer text-muted-foreground hover:text-destructive"
                  disabled={deleteMutation.isPending}
                  onClick={() => deleteMutation.mutate(color.id)}
                  aria-label={`${color.name || color.hex_value} rengini sil`}
                >
                  <Trash2 className="size-3.5" />
                </Button>
              </div>
            ))}
          </div>
        </CardContent>
      </Card>

      <Card>
        <CardHeader>
          <CardTitle className="text-base">Renk ekle</CardTitle>
        </CardHeader>
        <CardContent>
          <form onSubmit={handleSubmit(onSubmit)} className="flex flex-col gap-4">
            <div className="flex flex-col gap-1.5">
              <Label htmlFor="color-name">Isim</Label>
              <Input id="color-name" placeholder="Marka yesili" {...register("name")} />
            </div>
            <div className="flex flex-col gap-1.5">
              <Label htmlFor="color-hex">Hex</Label>
              <div className="flex items-center gap-2">
                <input
                  type="color"
                  className="size-9 cursor-pointer rounded-md border border-input bg-transparent"
                  {...register("hex_value")}
                  aria-label="Renk secici"
                />
                <Input id="color-hex" className="font-mono" {...register("hex_value")} />
              </div>
            </div>
            <div className="flex flex-col gap-1.5">
              <Label htmlFor="color-role">Rol (opsiyonel)</Label>
              <Input id="color-role" placeholder="primary, accent..." {...register("role")} />
            </div>
            {formError && <p className="text-sm text-destructive">{formError}</p>}
            <Button type="submit" disabled={createMutation.isPending} className="w-fit cursor-pointer gap-1.5">
              {createMutation.isPending ? (
                <Loader2 className="size-4 animate-spin" />
              ) : (
                <Plus className="size-4" />
              )}
              Ekle
            </Button>
          </form>
        </CardContent>
      </Card>
    </div>
  );
}
