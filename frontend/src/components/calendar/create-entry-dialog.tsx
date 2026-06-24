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
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select";
import { Textarea } from "@/components/ui/textarea";
import { createCalendarEntry, type CreateCalendarEntryPayload } from "@/lib/api/calendar";
import type { AspectRatio, ContentFormat } from "@/lib/api/types";

const schema = z.object({
  scheduled_date: z.string().min(1, "Tarih gerekli."),
  brief: z.string().optional(),
});

type FormValues = z.infer<typeof schema>;

export function CreateEntryDialog({ brandId }: { brandId: string }) {
  const [open, setOpen] = useState(false);
  const [contentFormat, setContentFormat] = useState<ContentFormat>("image");
  const [aspectRatio, setAspectRatio] = useState<AspectRatio>("square");
  const queryClient = useQueryClient();
  const {
    register,
    handleSubmit,
    reset,
    formState: { errors },
  } = useForm<FormValues>({ resolver: zodResolver(schema) });

  const mutation = useMutation({
    mutationFn: (values: CreateCalendarEntryPayload) => createCalendarEntry(brandId, values),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["brands", brandId, "calendar"] });
      toast.success("Icerik eklendi.");
      setOpen(false);
      reset();
      setContentFormat("image");
      setAspectRatio("square");
    },
    onError: () => toast.error("Eklenemedi."),
  });

  const onSubmit = (values: FormValues) => {
    mutation.mutate({ ...values, content_format: contentFormat, aspect_ratio: aspectRatio });
  };

  return (
    <Dialog open={open} onOpenChange={setOpen}>
      <DialogTrigger render={<Button className="cursor-pointer gap-1.5" />}>
        <Plus className="size-4" />
        Yeni icerik
      </DialogTrigger>
      <DialogContent>
        <DialogHeader>
          <DialogTitle>Yeni icerik ekle</DialogTitle>
          <DialogDescription>Takvime kullanici tarafindan girilen bir fikir ekle.</DialogDescription>
        </DialogHeader>
        <form onSubmit={handleSubmit(onSubmit)} className="flex flex-col gap-4" noValidate>
          <div className="flex flex-col gap-1.5">
            <Label htmlFor="scheduled_date">Tarih</Label>
            <Input id="scheduled_date" type="date" {...register("scheduled_date")} />
            {errors.scheduled_date && (
              <p className="text-sm text-destructive">{errors.scheduled_date.message}</p>
            )}
          </div>
          <div className="grid grid-cols-2 gap-4">
            <div className="flex flex-col gap-1.5">
              <Label>Format</Label>
              <Select value={contentFormat} onValueChange={(value) => setContentFormat(value as ContentFormat)}>
                <SelectTrigger>
                  <SelectValue />
                </SelectTrigger>
                <SelectContent>
                  <SelectItem value="image">Gorsel</SelectItem>
                  <SelectItem value="video">Video</SelectItem>
                </SelectContent>
              </Select>
            </div>
            <div className="flex flex-col gap-1.5">
              <Label>En-boy orani</Label>
              <Select value={aspectRatio} onValueChange={(value) => setAspectRatio(value as AspectRatio)}>
                <SelectTrigger>
                  <SelectValue />
                </SelectTrigger>
                <SelectContent>
                  <SelectItem value="square">Kare</SelectItem>
                  <SelectItem value="portrait">Dikey</SelectItem>
                  <SelectItem value="landscape">Yatay</SelectItem>
                </SelectContent>
              </Select>
            </div>
          </div>
          <div className="flex flex-col gap-1.5">
            <Label htmlFor="brief">Brief</Label>
            <Textarea id="brief" rows={3} placeholder="Icerik fikrini yaz..." {...register("brief")} />
          </div>
          <DialogFooter>
            <Button type="submit" disabled={mutation.isPending} className="cursor-pointer">
              {mutation.isPending && <Loader2 className="size-4 animate-spin" />}
              Ekle
            </Button>
          </DialogFooter>
        </form>
      </DialogContent>
    </Dialog>
  );
}
