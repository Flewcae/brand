"use client";

import Link from "next/link";
import { useParams, usePathname } from "next/navigation";
import { useQuery } from "@tanstack/react-query";
import { ArrowLeft } from "lucide-react";

import { getBrand } from "@/lib/api/brands";
import { queryKeys } from "@/lib/query-keys";
import { cn } from "@/lib/utils";

const tabs = [
  { href: "", label: "Profil" },
  { href: "/colors", label: "Renkler" },
  { href: "/assets", label: "Varliklar" },
  { href: "/calendar", label: "Takvim" },
  { href: "/holidays", label: "Ozel Gunler" },
  { href: "/usage", label: "Kullanim" },
];

export default function BrandDetailLayout({ children }: { children: React.ReactNode }) {
  const { brandId } = useParams<{ brandId: string }>();
  const pathname = usePathname();
  const basePath = `/brands/${brandId}`;

  const { data: brand } = useQuery({
    queryKey: queryKeys.brand(brandId),
    queryFn: () => getBrand(brandId),
  });

  return (
    <div className="flex flex-col gap-6">
      <div>
        <Link
          href="/brands"
          className="mb-2 inline-flex items-center gap-1 text-sm text-muted-foreground hover:text-foreground"
        >
          <ArrowLeft className="size-3.5" />
          Markalar
        </Link>
        <h1 className="font-mono text-xl font-semibold">{brand?.name ?? "..."}</h1>
      </div>

      <div className="flex gap-1 overflow-x-auto border-b border-border">
        {tabs.map((tab) => {
          const href = `${basePath}${tab.href}`;
          const isActive = pathname === href;
          return (
            <Link
              key={tab.href}
              href={href}
              className={cn(
                "shrink-0 border-b-2 px-3 py-2 text-sm font-medium transition-colors",
                isActive
                  ? "border-accent text-foreground"
                  : "border-transparent text-muted-foreground hover:text-foreground"
              )}
            >
              {tab.label}
            </Link>
          );
        })}
      </div>

      {children}
    </div>
  );
}
