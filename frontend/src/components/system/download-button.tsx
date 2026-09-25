"use client";

import { LoaderCircle } from "lucide-react";
import { useState, type ComponentProps, type ReactNode } from "react";
import { Button } from "@/components/ui/button";
import { downloadFromApi } from "@/lib/api";

type Props = Omit<ComponentProps<typeof Button>, "onClick" | "children"> & {
  /** API path of the file, e.g. /documents/{id}/summary */
  path: string;
  fallbackName: string;
  children: ReactNode;
};

/** Downloads a file from the API with the user's sign-in (a plain link can't send it). */
export function DownloadButton({ path, fallbackName, children, disabled, ...props }: Props) {
  const [pending, setPending] = useState(false);
  const [error, setError] = useState<string | null>(null);

  async function download() {
    setPending(true);
    setError(null);
    try {
      await downloadFromApi(path, fallbackName);
    } catch (caught) {
      setError(caught instanceof Error ? caught.message : "The download didn't work.");
    } finally {
      setPending(false);
    }
  }

  return (
    <>
      <Button
        {...props}
        disabled={disabled || pending}
        aria-busy={pending}
        title={error ?? undefined}
        onClick={() => void download()}
      >
        {pending && <LoaderCircle className="animate-spin" aria-hidden />}
        {children}
      </Button>
      {error && (
        <span role="alert" className="text-xs text-danger">
          Download failed: {error}
        </span>
      )}
    </>
  );
}
