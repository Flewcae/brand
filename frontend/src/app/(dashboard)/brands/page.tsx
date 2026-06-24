"use client";

import Link from "next/link";
import { useQuery } from "@tanstack/react-query";
import { Building2 } from "lucide-react";

import { CreateBrandDialog } from "@/components/brands/create-brand-dialog";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Skeleton } from "@/components/ui/skeleton";
import { listBrands } from "@/lib/api/brands";
import { queryKeys } from "@/lib/query-keys";

export default function BrandsPage() {
  const { data, isLoading } = useQuery({
    queryKey: queryKeys.brands,
    queryFn: listBrands,
  });

  return (
    <div className="flex flex-col gap-6">
      <div className="flex items-center justify-between">
        <div>
          <h1 className="font-mono text-xl font-semibold">Markalar</h1>
          <p className="text-sm text-muted-foreground">
            Ajansinin yonettigi musteri markalari.
          </p>
        </div>
        <CreateBrandDialog />
      </div>

      {isLoading && (
        <div className="grid grid-cols-1 gap-4 sm:grid-cols-2 lg:grid-cols-3">
          {[0, 1, 2].map((i) => (
            <Skeleton key={i} className="h-32 rounded-lg" />
          ))}
        </div>
      )}

      {!isLoading && data?.results.length === 0 && (
        <Card className="border-dashed">
          <CardContent className="flex flex-col items-center gap-2 py-12 text-center">
            <Building2 className="size-8 text-muted-foreground" />
            <p className="text-sm text-muted-foreground">
              Henuz marka eklenmedi. Baslamak icin &quot;Yeni marka&quot; butonunu kullan.
            </p>
          </CardContent>
        </Card>
      )}

      <div className="grid grid-cols-1 gap-4 sm:grid-cols-2 lg:grid-cols-3">
        {data?.results.map((brand) => (
          <Link key={brand.id} href={`/brands/${brand.id}`}>
            <Card className="cursor-pointer transition-colors hover:border-accent/50">
              <CardHeader>
                <CardTitle className="flex items-center justify-between text-base">
                  {brand.name}
                  <span className="font-mono text-xs font-normal text-muted-foreground">
                    {brand.country_code || "--"}
                  </span>
                </CardTitle>
              </CardHeader>
              <CardContent>
                <p className="truncate text-sm text-muted-foreground">/{brand.slug}</p>
              </CardContent>
            </Card>
          </Link>
        ))}
      </div>
    </div>
  );
}
