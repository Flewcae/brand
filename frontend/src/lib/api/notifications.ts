import { apiClient } from "@/lib/api/client";
import type { Notification, Paginated, PushSubscription } from "@/lib/api/types";

export async function listNotifications(isRead?: boolean) {
  const { data } = await apiClient.get<Paginated<Notification>>("/notifications/", {
    params: isRead === undefined ? undefined : { is_read: isRead },
  });
  return data;
}

export async function markNotificationRead(notificationId: string) {
  const { data } = await apiClient.patch<Notification>(`/notifications/${notificationId}/`, {
    is_read: true,
  });
  return data;
}

export async function markAllNotificationsRead() {
  await apiClient.post("/notifications/mark-all-read/");
}

export async function registerPushSubscription(registrationToken: string) {
  const { data } = await apiClient.post<PushSubscription>("/push-subscriptions/", {
    registration_token: registrationToken,
    user_agent: typeof navigator === "undefined" ? "" : navigator.userAgent,
  });
  return data;
}

export async function deletePushSubscription(subscriptionId: string) {
  await apiClient.delete(`/push-subscriptions/${subscriptionId}/`);
}
