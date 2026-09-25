"use client";

import { useQueryClient } from "@tanstack/react-query";
import { FirebaseError } from "firebase/app";
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

export function AuthProvider({ children }: { children: ReactNode }) {
  const queryClient = useQueryClient();
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

  const signIn = useCallback(async () => {
    setError(null);
    setSigningIn(true);
    try {
      const provider = new GoogleAuthProvider();
      provider.setCustomParameters({ prompt: "select_account" });
      await signInWithPopup(firebaseAuth(), provider);
    } catch (caught) {
      setError(signInErrorMessage(caught));
    } finally {
      setSigningIn(false);
    }
  }, []);

  const signOut = useCallback(async () => {
    await firebaseSignOut(firebaseAuth());
    queryClient.clear();
  }, [queryClient]);

  const value = useMemo<AuthState>(
    () => ({ enabled: authEnabled, status, user, signingIn, error, signIn, signOut }),
    [status, user, signingIn, error, signIn, signOut],
  );

  let content = children;
  if (authEnabled && !firebaseConfigured) {
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
