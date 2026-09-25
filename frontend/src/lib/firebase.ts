import { getApp, getApps, initializeApp } from "firebase/app";
import { getAuth, type Auth } from "firebase/auth";
import { env } from "@/lib/config";

/** Google sign-in is on unless the app runs in local development mode without it. */
export const authEnabled = env.NEXT_PUBLIC_AUTH_MODE === "firebase";

const firebaseConfig = {
  apiKey: env.NEXT_PUBLIC_FIREBASE_API_KEY,
  authDomain: env.NEXT_PUBLIC_FIREBASE_AUTH_DOMAIN,
  projectId: env.NEXT_PUBLIC_FIREBASE_PROJECT_ID,
  appId: env.NEXT_PUBLIC_FIREBASE_APP_ID,
};

/** All four web-app values from the Firebase console are present. */
export const firebaseConfigured = Object.values(firebaseConfig).every(Boolean);

let auth: Auth | null = null;

/** Firebase Auth, created on first use (browser only). */
export function firebaseAuth(): Auth {
  if (!auth) {
    const app = getApps().length ? getApp() : initializeApp(firebaseConfig);
    auth = getAuth(app);
  }
  return auth;
}

/** The signed-in user's Firebase ID token (refreshed by Firebase when near expiry). */
export async function getIdToken(): Promise<string | null> {
  if (!authEnabled || !firebaseConfigured) return null;
  const user = firebaseAuth().currentUser;
  return user ? user.getIdToken() : null;
}
