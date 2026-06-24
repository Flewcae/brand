import { initializeApp, getApps } from "firebase/app";
import { getMessaging, getToken } from "firebase/messaging";

import { firebaseConfig, firebaseVapidKey, isFirebaseConfigured } from "@/lib/firebase/config";

export async function requestPushRegistrationToken(): Promise<string | null> {
  if (!isFirebaseConfigured) {
    throw new Error(
      "Firebase web config eksik. NEXT_PUBLIC_FIREBASE_* degiskenlerini ve " +
        "public/firebase-messaging-sw.js icindeki config'i doldur."
    );
  }
  if (typeof window === "undefined" || !("serviceWorker" in navigator)) {
    throw new Error("Bu tarayici push bildirimlerini desteklemiyor.");
  }

  const permission = await Notification.requestPermission();
  if (permission !== "granted") {
    return null;
  }

  const app = getApps()[0] ?? initializeApp(firebaseConfig);
  const registration = await navigator.serviceWorker.register("/firebase-messaging-sw.js");
  const messaging = getMessaging(app);
  return getToken(messaging, {
    vapidKey: firebaseVapidKey,
    serviceWorkerRegistration: registration,
  });
}
