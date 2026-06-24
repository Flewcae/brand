"use client";

import { useState } from "react";
import { useMutation, useQueryClient } from "@tanstack/react-query";
import { zodResolver } from "@hookform/resolvers/zod";
import { Loader2, Plus } from "lucide-react";
import { useForm } from "react-hook-form";
import { toast } from "sonner";
import { z } from "zod";

import { Button } from "@/components/ui/button";
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogFooter,
  DialogHeader,
  DialogTitle,
  DialogTrigger,
} from "@/components/ui/dialog";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { createBrand } from "@/lib/api/brands";
import { queryKeys } from "@/lib/query-keys";
import { slugify } from "@/lib/utils";

const schema = z.object({
  name: z.string().min(2, "Marka adi en az 2 karakter olmali."),
  slug: z
    .string()
    .min(2, "Slug en az 2 karakter olmali.")
    .regex(/^[a-z0-9-]+$/, "Slug sadece kucuk harf, rakam ve tire icerebilir."),
  country_code: z
    .string()
    .length(2, "2 harfli ulke kodu girin (orn. TR).")
    .toUpperCase(),
  timezone: z.string().min(2, "Saat dilimi gerekli."),
});

type FormValues = z.infer<typeof schema>;

export function CreateBrandDialog() {
  const [open, setOpen] = useState(false);
  const queryClient = useQueryClient();
  const {
    register,
    handleSubmit,
    setValue,
    reset,
    formState: { errors },
  } = useForm<FormValues>({
    resolver: zodResolver(schema),
    defaultValues: { country_code: "TR", timezone: "Europe/Istanbul" },
  });

  const mutation = useMutation({
    mutationFn: createBrand,
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: queryKeys.brands });
      toast.success("Marka olusturuldu.");
      setOpen(false);
      reset();
    },
    onError: () => {
      toast.error("Marka olusturulamadi.", { description: "Slug zaten kullaniliyor olabilir." });
    },
  });

  return (
    <Dialog open={open} onOpenChange={setOpen}>
      <DialogTrigger render={<Button className="cursor-pointer gap-1.5" />}>
        <Plus className="size-4" />
        Yeni marka
      </DialogTrigger>
      <DialogContent>
        <DialogHeader>
          <DialogTitle>Yeni marka olustur</DialogTitle>
          <DialogDescription>
            Marka profili olusturduktan sonra logo/kimlik dokumani yukleyip onboarding&apos;i
            tamamlayabilirsin.
          </DialogDescription>
        </DialogHeader>
        <form
          onSubmit={handleSubmit((values) => mutation.mutate(values))}
          className="flex flex-col gap-4"
          noValidate
        >
          <div className="flex flex-col gap-1.5">
            <Label htmlFor="name">Marka adi</Label>
            <Input
              id="name"
              {...register("name")}
              onChange={(event) => {
                setValue("name", event.target.value);
                setValue("slug", slugify(event.target.value));
              }}
            />
            {errors.name && <p className="text-sm text-destructive">{errors.name.message}</p>}
          </div>
          <div className="flex flex-col gap-1.5">
            <Label htmlFor="slug">Slug</Label>
            <Input id="slug" {...register("slug")} />
            {errors.slug && <p className="text-sm text-destructive">{errors.slug.message}</p>}
          </div>
          <div className="grid grid-cols-2 gap-4">
            <div className="flex flex-col gap-1.5">
              <Label htmlFor="country_code">Ulke kodu</Label>
              <Input id="country_code" maxLength={2} {...register("country_code")} />
              {errors.country_code && (
                <p className="text-sm text-destructive">{errors.country_code.message}</p>
              )}
            </div>
            <div className="flex flex-col gap-1.5">
              <Label htmlFor="timezone">Saat dilimi</Label>
              <Input id="timezone" {...register("timezone")} />
              {errors.timezone && (
                <p className="text-sm text-destructive">{errors.timezone.message}</p>
              )}
            </div>
          </div>
          <DialogFooter>
            <Button type="submit" disabled={mutation.isPending} className="cursor-pointer">
              {mutation.isPending && <Loader2 className="size-4 animate-spin" />}
              Olustur
            </Button>
          </DialogFooter>
        </form>
      </DialogContent>
    </Dialog>
  );
}
