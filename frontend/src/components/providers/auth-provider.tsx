"use client";

import { useQueryClient } from "@tanstack/react-query";
import { FirebaseError } from "firebase/app";
import { usePathname } from "next/navigation";
import {
  GoogleAuthProvider,
  onAuthStateChanged,
  signInWithPopup,
  signOut as firebaseSignOut,
  type User,
} from "firebase/auth";
import {
  createContext,
  useCallback,
  useContext,
  useEffect,
  useMemo,
  useRef,
  useState,
  type ReactNode,
} from "react";
import { SignInScreen } from "@/components/system/sign-in-screen";
import { authEnabled, firebaseAuth, firebaseConfigured } from "@/lib/firebase";

type AuthStatus = "loading" | "signed-in" | "signed-out";

export type AuthState = {
  /** false when the app runs without sign-in (local development). */
  enabled: boolean;
  status: AuthStatus;
  user: User | null;
  signingIn: boolean;
  error: string | null;
  signIn: () => Promise<void>;
  signOut: () => Promise<void>;
};

const AuthContext = createContext<AuthState | null>(null);

/** The public read-only demo (docs/Demo.md) is shown to anyone; the API enforces the same rule. */
const PUBLIC_PATH = /^\/demo(\/|$)/;

const SIGN_IN_ERRORS: Record<string, string | null> = {
  "auth/popup-closed-by-user": null,
  "auth/cancelled-popup-request": null,
  "auth/popup-blocked": "Your browser blocked the Google sign-in window. Allow pop-ups and try again.",
  "auth/unauthorized-domain":
    "This website address is not allowed to sign in yet. Add it under Firebase → Authentication → Settings → Authorized domains.",
  "auth/operation-not-allowed":
    "Google sign-in is not turned on for this app. Enable it under Firebase → Authentication → Sign-in method.",
  "auth/network-request-failed": "Couldn't reach Google. Check your internet connection and try again.",
};

function signInErrorMessage(error: unknown): string | null {
  if (error instanceof FirebaseError && error.code in SIGN_IN_ERRORS) {
    return SIGN_IN_ERRORS[error.code];
  }
  return "Sign-in didn't work. Please try again.";
}

// How long to wait before saying where the Google window went. signInWithPopup only settles
// when the popup finishes or Firebase notices it closed, and neither always happens: a window
// opened behind the browser, moved to another screen, or closed in a way Firebase cannot see
// leaves the promise pending for ever — and with it a button that says "Waiting for Google…"
// and can never be pressed again. Re-enabling it is safe, because a second attempt cancels the
// first and Firebase reports that as auth/cancelled-popup-request, which is ignored above.
const POPUP_HINT_AFTER_MS = 12_000;
const POPUP_HINT =
  "A Google sign-in window should have opened. It may be behind this window, on another " +
  "screen, or blocked by your browser — check for a blocked pop-up, then try again.";

export function AuthProvider({ children }: { children: ReactNode }) {
  const queryClient = useQueryClient();
  const pathname = usePathname();
  const publicPage = PUBLIC_PATH.test(pathname ?? "");
  const active = authEnabled && firebaseConfigured;
  const [user, setUser] = useState<User | null>(null);
  const [status, setStatus] = useState<AuthStatus>(active ? "loading" : "signed-out");
  const [signingIn, setSigningIn] = useState(false);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    if (!active) return;
    return onAuthStateChanged(firebaseAuth(), (next) => {
      // A different person (or nobody) now: drop everything cached for the previous one.
      setUser((previous) => {
        if (previous?.uid !== next?.uid) queryClient.clear();
        return next;
      });
      setStatus(next ? "signed-in" : "signed-out");
    });
  }, [active, queryClient]);

  const hintTimer = useRef<ReturnType<typeof setTimeout> | null>(null);
  const clearHint = useCallback(() => {
    if (hintTimer.current !== null) {
      clearTimeout(hintTimer.current);
      hintTimer.current = null;
    }
  }, []);
  useEffect(() => clearHint, [clearHint]);

  const signIn = useCallback(async () => {
    setError(null);
    setSigningIn(true);
    clearHint();
    hintTimer.current = setTimeout(() => {
      setSigningIn(false);
      setError(POPUP_HINT);
    }, POPUP_HINT_AFTER_MS);
    try {
      const provider = new GoogleAuthProvider();
      provider.setCustomParameters({ prompt: "select_account" });
      await signInWithPopup(firebaseAuth(), provider);
      setError(null);
    } catch (caught) {
      setError(signInErrorMessage(caught));
    } finally {
      clearHint();
      setSigningIn(false);
    }
  }, [clearHint]);

  const signOut = useCallback(async () => {
    await firebaseSignOut(firebaseAuth());
    queryClient.clear();
  }, [queryClient]);

  const value = useMemo<AuthState>(
    () => ({ enabled: authEnabled, status, user, signingIn, error, signIn, signOut }),
    [status, user, signingIn, error, signIn, signOut],
  );

  // The demo pages render for everyone; signing in there is optional and just adds your own
  // documents. Every other page waits for Google, as before.
  let content = children;
  if (publicPage) {
    content = children;
  } else if (authEnabled && !firebaseConfigured) {
    content = <SignInScreen notConfigured />;
  } else if (authEnabled && status !== "signed-in") {
    content = <SignInScreen />;
  }
  return <AuthContext.Provider value={value}>{content}</AuthContext.Provider>;
}

export function useAuth(): AuthState {
  const context = useContext(AuthContext);
  if (!context) throw new Error("useAuth must be used inside <AuthProvider>.");
  return context;
}
