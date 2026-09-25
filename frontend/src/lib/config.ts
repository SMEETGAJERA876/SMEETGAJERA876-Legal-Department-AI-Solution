import { z } from "zod";

const optional = z
  .string()
  .optional()
  .transform((value) => (value ? value : undefined));

const envSchema = z.object({
  NEXT_PUBLIC_API_URL: z.string().url(),
  /** "firebase" = Google sign-in required; "disabled" = local development without sign-in. */
  NEXT_PUBLIC_AUTH_MODE: z.enum(["firebase", "disabled"]).default("firebase"),
  NEXT_PUBLIC_FIREBASE_API_KEY: optional,
  NEXT_PUBLIC_FIREBASE_AUTH_DOMAIN: optional,
  NEXT_PUBLIC_FIREBASE_PROJECT_ID: optional,
  NEXT_PUBLIC_FIREBASE_APP_ID: optional,
});

// NEXT_PUBLIC_* values are inlined at build time, so each must be referenced by its full name.
export const env = envSchema.parse({
  NEXT_PUBLIC_API_URL: process.env.NEXT_PUBLIC_API_URL,
  NEXT_PUBLIC_AUTH_MODE: process.env.NEXT_PUBLIC_AUTH_MODE || undefined,
  NEXT_PUBLIC_FIREBASE_API_KEY: process.env.NEXT_PUBLIC_FIREBASE_API_KEY,
  NEXT_PUBLIC_FIREBASE_AUTH_DOMAIN: process.env.NEXT_PUBLIC_FIREBASE_AUTH_DOMAIN,
  NEXT_PUBLIC_FIREBASE_PROJECT_ID: process.env.NEXT_PUBLIC_FIREBASE_PROJECT_ID,
  NEXT_PUBLIC_FIREBASE_APP_ID: process.env.NEXT_PUBLIC_FIREBASE_APP_ID,
});
