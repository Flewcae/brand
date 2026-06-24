// Background push handler for FCM web push. Service workers are static
// files Next.js can't inject env vars into at request time, so this config
// must be filled in by hand -- copy the same values used for
// NEXT_PUBLIC_FIREBASE_* in .env.local (Firebase console > Project settings
// > General > Your apps > Web app).
importScripts("https://www.gstatic.com/firebasejs/10.12.0/firebase-app-compat.js");
importScripts("https://www.gstatic.com/firebasejs/10.12.0/firebase-messaging-compat.js");

firebase.initializeApp({
  apiKey: "REPLACE_ME",
  authDomain: "REPLACE_ME",
  projectId: "REPLACE_ME",
  storageBucket: "REPLACE_ME",
  messagingSenderId: "REPLACE_ME",
  appId: "REPLACE_ME",
});

firebase.messaging();
