"use client";

import Link from "next/link";
import { usePathname } from "next/navigation";
import { useQuery } from "@tanstack/react-query";
import { Bell, Building2, LogOut } from "lucide-react";

import {
  Avatar,
  AvatarFallback,
} from "@/components/ui/avatar";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import {
  DropdownMenu,
  DropdownMenuContent,
  DropdownMenuItem,
  DropdownMenuSeparator,
  DropdownMenuTrigger,
} from "@/components/ui/dropdown-menu";
import { listNotifications } from "@/lib/api/notifications";
import { queryKeys } from "@/lib/query-keys";
import { cn } from "@/lib/utils";
import { useAuth } from "@/lib/auth/auth-context";

const navItems = [
  { href: "/brands", label: "Markalar", icon: Building2 },
  { href: "/notifications", label: "Bildirimler", icon: Bell },
];

function initialsFor(name: string) {
  return name
    .split(" ")
    .filter(Boolean)
    .slice(0, 2)
    .map((part) => part[0]?.toUpperCase())
    .join("");
}

export function DashboardShell({ children }: { children: React.ReactNode }) {
  const pathname = usePathname();
  const { agency, logout } = useAuth();

  const { data: unread } = useQuery({
    queryKey: queryKeys.notifications(false),
    queryFn: () => listNotifications(false),
    refetchInterval: 30000,
  });
  const unreadCount = unread?.count ?? 0;

  return (
    <div className="flex min-h-screen w-full">
      <aside className="hidden w-56 shrink-0 flex-col border-r border-sidebar-border bg-sidebar md:flex">
        <div className="flex h-14 items-center gap-2 border-b border-sidebar-border px-4">
          <span className="font-mono text-sm font-semibold tracking-tight text-sidebar-foreground">
            flewcae
          </span>
        </div>
        <nav className="flex flex-1 flex-col gap-1 p-3">
          {navItems.map((item) => {
            const isActive = pathname === item.href || pathname.startsWith(`${item.href}/`);
            const Icon = item.icon;
            return (
              <Link
                key={item.href}
                href={item.href}
                className={cn(
                  "flex items-center gap-2.5 rounded-md px-3 py-2 text-sm font-medium transition-colors",
                  isActive
                    ? "bg-sidebar-accent text-sidebar-accent-foreground"
                    : "text-sidebar-foreground/70 hover:bg-sidebar-accent hover:text-sidebar-accent-foreground"
                )}
              >
                <Icon className="size-4" />
                {item.label}
                {item.href === "/notifications" && unreadCount > 0 && (
                  <Badge className="ml-auto h-5 min-w-5 justify-center px-1 text-xs">
                    {unreadCount}
                  </Badge>
                )}
              </Link>
            );
          })}
        </nav>
      </aside>

      <div className="flex flex-1 flex-col">
        <header className="flex h-14 items-center justify-between border-b border-border px-4 md:px-6">
          <span className="text-sm font-medium text-muted-foreground">
            {agency?.name ?? ""}
          </span>
          <DropdownMenu>
            <DropdownMenuTrigger
              render={<Button variant="ghost" size="icon" className="cursor-pointer rounded-full" />}
            >
              <Avatar className="size-8">
                <AvatarFallback className="bg-secondary text-xs">
                  {initialsFor(agency?.name ?? "AG")}
                </AvatarFallback>
              </Avatar>
            </DropdownMenuTrigger>
            <DropdownMenuContent align="end">
              <DropdownMenuItem disabled className="text-xs text-muted-foreground">
                {agency?.name}
              </DropdownMenuItem>
              <DropdownMenuSeparator />
              <DropdownMenuItem onClick={logout} className="cursor-pointer">
                <LogOut className="size-4" />
                Cikis yap
              </DropdownMenuItem>
            </DropdownMenuContent>
          </DropdownMenu>
        </header>
        <main className="flex-1 px-4 py-6 md:px-6">{children}</main>
      </div>
    </div>
  );
}
