"use client";

import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { Bell, BellRing, CheckCheck, Loader2 } from "lucide-react";
import { toast } from "sonner";

import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Card, CardContent } from "@/components/ui/card";
import { isFirebaseConfigured } from "@/lib/firebase/config";
import { requestPushRegistrationToken } from "@/lib/firebase/messaging";
import {
  listNotifications,
  markAllNotificationsRead,
  markNotificationRead,
  registerPushSubscription,
} from "@/lib/api/notifications";
import type { Notification, NotificationType } from "@/lib/api/types";
import { queryKeys } from "@/lib/query-keys";

const TYPE_LABEL: Record<NotificationType, string> = {
  generation_done: "Uretim tamamlandi",
  generation_failed: "Uretim basarisiz",
  reminder_24h: "Hatirlatma (24 saat)",
  reminder_12h: "Hatirlatma (12 saat)",
  reminder_3h: "Hatirlatma (3 saat)",
  reminder_due: "Paylasim zamani",
  suggestion_batch_ready: "Yeni oneriler hazir",
};

function NotificationRow({ notification }: { notification: Notification }) {
  const queryClient = useQueryClient();
  const mutation = useMutation({
    mutationFn: () => markNotificationRead(notification.id),
    onSuccess: () => queryClient.invalidateQueries({ queryKey: ["notifications"] }),
  });

  return (
    <Card className={notification.is_read ? "opacity-60" : undefined}>
      <CardContent className="flex items-start justify-between gap-4 py-4">
        <div className="flex flex-col gap-1">
          <div className="flex items-center gap-2">
            <Badge variant={notification.is_read ? "secondary" : "default"} className="text-xs">
              {TYPE_LABEL[notification.notification_type]}
            </Badge>
            <span className="text-xs text-muted-foreground">
              {new Date(notification.created_at).toLocaleString("tr-TR")}
            </span>
          </div>
          <p className="text-sm font-medium">{notification.title}</p>
          <p className="text-sm text-muted-foreground">{notification.body}</p>
        </div>
        {!notification.is_read && (
          <Button
            size="sm"
            variant="ghost"
            className="cursor-pointer shrink-0"
            disabled={mutation.isPending}
            onClick={() => mutation.mutate()}
          >
            Okundu isaretle
          </Button>
        )}
      </CardContent>
    </Card>
  );
}

function PushRegistrationCard() {
  const mutation = useMutation({
    mutationFn: async () => {
      const token = await requestPushRegistrationToken();
      if (!token) {
        throw new Error("permission_denied");
      }
      return registerPushSubscription(token);
    },
    onSuccess: () => toast.success("Bu tarayici icin push bildirimleri etkinlestirildi."),
    onError: (error: Error) => {
      if (error.message === "permission_denied") {
        toast.error("Bildirim izni verilmedi.");
      } else {
        toast.error("Etkinlestirilemedi.", { description: error.message });
      }
    },
  });

  if (!isFirebaseConfigured) {
    return (
      <Card className="border-dashed">
        <CardContent className="flex items-center gap-3 py-4 text-sm text-muted-foreground">
          <Bell className="size-4 shrink-0" />
          Push bildirimleri icin Firebase web config henuz tanimlanmadi (.env.local).
        </CardContent>
      </Card>
    );
  }

  return (
    <Card>
      <CardContent className="flex items-center justify-between gap-4 py-4">
        <div className="flex items-center gap-3 text-sm">
          <BellRing className="size-4 text-accent" />
          Bu cihazda tarayici bildirimlerini etkinlestir.
        </div>
        <Button
          size="sm"
          variant="outline"
          className="cursor-pointer gap-1.5"
          disabled={mutation.isPending}
          onClick={() => mutation.mutate()}
        >
          {mutation.isPending && <Loader2 className="size-4 animate-spin" />}
          Etkinlestir
        </Button>
      </CardContent>
    </Card>
  );
}

export default function NotificationsPage() {
  const queryClient = useQueryClient();
  const { data, isLoading } = useQuery({
    queryKey: queryKeys.notifications(),
    queryFn: () => listNotifications(),
  });

  const markAllMutation = useMutation({
    mutationFn: markAllNotificationsRead,
    onSuccess: () => queryClient.invalidateQueries({ queryKey: ["notifications"] }),
    onError: () => toast.error("Islem basarisiz."),
  });

  const hasUnread = data?.results.some((n) => !n.is_read);

  return (
    <div className="flex flex-col gap-6">
      <div className="flex items-center justify-between">
        <div>
          <h1 className="font-mono text-xl font-semibold">Bildirimler</h1>
          <p className="text-sm text-muted-foreground">Uretim, hatirlatma ve oneri bildirimleri.</p>
        </div>
        <Button
          variant="outline"
          size="sm"
          className="cursor-pointer gap-1.5"
          disabled={!hasUnread || markAllMutation.isPending}
          onClick={() => markAllMutation.mutate()}
        >
          <CheckCheck className="size-4" />
          Tumunu okundu isaretle
        </Button>
      </div>

      <PushRegistrationCard />

      {isLoading && <p className="text-sm text-muted-foreground">Yukleniyor...</p>}
      {!isLoading && data?.results.length === 0 && (
        <Card className="border-dashed">
          <CardContent className="flex flex-col items-center gap-2 py-12 text-center">
            <Bell className="size-8 text-muted-foreground" />
            <p className="text-sm text-muted-foreground">Henuz bildirim yok.</p>
          </CardContent>
        </Card>
      )}

      <div className="flex flex-col gap-2">
        {data?.results.map((notification) => (
          <NotificationRow key={notification.id} notification={notification} />
        ))}
      </div>
    </div>
  );
}
