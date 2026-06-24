"use client";

import { useRef } from "react";
import { useParams } from "next/navigation";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { FileText, Image as ImageIcon, Loader2, Trash2, Upload } from "lucide-react";
import { toast } from "sonner";

import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import {
  deleteBrandAsset,
  listBrandAssets,
  uploadBrandAsset,
} from "@/lib/api/brands";
import type { AnalysisStatus, AssetType } from "@/lib/api/types";
import { queryKeys } from "@/lib/query-keys";

const STATUS_LABEL: Record<AnalysisStatus, string> = {
  pending: "Beklemede",
  processing: "Analiz ediliyor",
  done: "Tamamlandi",
  failed: "Basarisiz",
};

const STATUS_VARIANT: Record<AnalysisStatus, "secondary" | "outline" | "default" | "destructive"> = {
  pending: "secondary",
  processing: "outline",
  done: "default",
  failed: "destructive",
};

function UploadButton({
  assetType,
  label,
  brandId,
}: {
  assetType: AssetType;
  label: string;
  brandId: string;
}) {
  const inputRef = useRef<HTMLInputElement>(null);
  const queryClient = useQueryClient();

  const uploadMutation = useMutation({
    mutationFn: (file: File) => uploadBrandAsset(brandId, file, assetType),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: queryKeys.brandAssets(brandId) });
      toast.success("Dosya yuklendi, analiz baslatildi.");
    },
    onError: () => toast.error("Yukleme basarisiz."),
  });

  return (
    <>
      <input
        ref={inputRef}
        type="file"
        accept="image/*,application/pdf"
        className="hidden"
        onChange={(event) => {
          const file = event.target.files?.[0];
          if (file) uploadMutation.mutate(file);
          event.target.value = "";
        }}
      />
      <Button
        variant="outline"
        className="cursor-pointer gap-1.5"
        disabled={uploadMutation.isPending}
        onClick={() => inputRef.current?.click()}
      >
        {uploadMutation.isPending ? (
          <Loader2 className="size-4 animate-spin" />
        ) : (
          <Upload className="size-4" />
        )}
        {label}
      </Button>
    </>
  );
}

export default function BrandAssetsPage() {
  const { brandId } = useParams<{ brandId: string }>();
  const queryClient = useQueryClient();

  const { data, isLoading } = useQuery({
    queryKey: queryKeys.brandAssets(brandId),
    queryFn: () => listBrandAssets(brandId),
    refetchInterval: (query) => {
      const hasInFlight = query.state.data?.results.some((asset) =>
        ["pending", "processing"].includes(asset.analysis_status)
      );
      return hasInFlight ? 3000 : false;
    },
  });

  const deleteMutation = useMutation({
    mutationFn: (assetId: string) => deleteBrandAsset(brandId, assetId),
    onSuccess: () => queryClient.invalidateQueries({ queryKey: queryKeys.brandAssets(brandId) }),
    onError: () => toast.error("Silinemedi."),
  });

  return (
    <div className="flex flex-col gap-6">
      <Card>
        <CardHeader>
          <CardTitle className="text-base">Varlik yukle</CardTitle>
          <CardDescription>
            Logo veya kimlik dokumani (PDF/gorsel) yukle; Claude otomatik olarak gorsel stil
            analizi yapar.
          </CardDescription>
        </CardHeader>
        <CardContent className="flex gap-3">
          <UploadButton assetType="logo" label="Logo yukle" brandId={brandId} />
          <UploadButton assetType="identity_document" label="Kimlik dokumani yukle" brandId={brandId} />
        </CardContent>
      </Card>

      {isLoading && <p className="text-sm text-muted-foreground">Yukleniyor...</p>}
      {!isLoading && data?.results.length === 0 && (
        <p className="text-sm text-muted-foreground">Henuz varlik yuklenmedi.</p>
      )}

      <div className="grid grid-cols-1 gap-4 sm:grid-cols-2 lg:grid-cols-3">
        {data?.results.map((asset) => {
          const isImage = asset.content_type?.startsWith("image/");
          return (
            <Card key={asset.id}>
              <CardContent className="flex flex-col gap-3 pt-6">
                <div className="flex h-32 items-center justify-center overflow-hidden rounded-md bg-muted">
                  {isImage ? (
                    // eslint-disable-next-line @next/next/no-img-element
                    <img
                      src={asset.file}
                      alt={asset.original_filename || asset.asset_type}
                      className="h-full w-full object-contain"
                    />
                  ) : (
                    <FileText className="size-8 text-muted-foreground" />
                  )}
                </div>
                <div className="flex items-center justify-between gap-2">
                  <div className="flex items-center gap-1.5 text-xs text-muted-foreground">
                    {asset.asset_type === "logo" ? (
                      <ImageIcon className="size-3.5" />
                    ) : (
                      <FileText className="size-3.5" />
                    )}
                    {asset.asset_type === "logo" ? "Logo" : "Kimlik dokumani"}
                  </div>
                  <Badge variant={STATUS_VARIANT[asset.analysis_status]} className="text-xs">
                    {asset.analysis_status === "processing" && (
                      <Loader2 className="size-3 animate-spin" />
                    )}
                    {STATUS_LABEL[asset.analysis_status]}
                  </Badge>
                </div>
                <div className="flex items-center justify-between">
                  <p className="truncate text-xs text-muted-foreground">
                    {asset.original_filename}
                  </p>
                  <Button
                    variant="ghost"
                    size="icon-sm"
                    className="cursor-pointer text-muted-foreground hover:text-destructive"
                    disabled={deleteMutation.isPending}
                    onClick={() => deleteMutation.mutate(asset.id)}
                    aria-label="Varligi sil"
                  >
                    <Trash2 className="size-3.5" />
                  </Button>
                </div>
              </CardContent>
            </Card>
          );
        })}
      </div>
    </div>
  );
}
