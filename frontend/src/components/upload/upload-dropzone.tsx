"use client";

import { useQueryClient } from "@tanstack/react-query";
import { CircleAlert, FileUp, LoaderCircle, Upload } from "lucide-react";
import { useRouter } from "next/navigation";
import { useId, useRef, useState, type DragEvent } from "react";
import { Button } from "@/components/ui/button";
import { ApiError, uploadDocument } from "@/lib/api";
import { formatBytes } from "@/lib/format";

const MAX_UPLOAD_MB = 25;
const MAX_UPLOAD_BYTES = MAX_UPLOAD_MB * 1024 * 1024;

type UploadState =
  | { kind: "idle" }
  | { kind: "uploading"; fileName: string; progress: number }
  | { kind: "error"; title: string; message: string };

function validate(file: File): { title: string; message: string } | null {
  const isPdf = file.type === "application/pdf" || file.name.toLowerCase().endsWith(".pdf");
  if (!isPdf) {
    return {
      title: "This file isn't a PDF",
      message: `“${file.name}” can't be read yet. Only PDF files are supported — export the document as PDF and try again.`,
    };
  }
  if (file.size > MAX_UPLOAD_BYTES) {
    return {
      title: "This file is too large",
      message: `The file is ${formatBytes(file.size)}. The limit is ${MAX_UPLOAD_MB} MB — try compressing it or splitting it into parts.`,
    };
  }
  if (file.size === 0) {
    return { title: "This file is empty", message: "Choose a PDF that contains your document." };
  }
  return null;
}

export function UploadDropzone() {
  const router = useRouter();
  const queryClient = useQueryClient();
  const inputRef = useRef<HTMLInputElement>(null);
  const inputId = useId();
  const [state, setState] = useState<UploadState>({ kind: "idle" });
  const [dragging, setDragging] = useState(false);

  const start = async (file: File | undefined) => {
    if (!file || state.kind === "uploading") return;
    const problem = validate(file);
    if (problem) {
      setState({ kind: "error", ...problem });
      return;
    }
    setState({ kind: "uploading", fileName: file.name, progress: 0 });
    try {
      const document = await uploadDocument(file, (progress) =>
        setState({ kind: "uploading", fileName: file.name, progress }),
      );
      await queryClient.invalidateQueries({ queryKey: ["documents"] });
      router.push(`/documents/${document.id}`);
    } catch (error) {
      setState({
        kind: "error",
        title: "Upload didn't finish",
        message: error instanceof ApiError ? error.message : "Please try again.",
      });
    }
  };

  const onDrop = (event: DragEvent<HTMLDivElement>) => {
    event.preventDefault();
    setDragging(false);
    void start(event.dataTransfer.files[0]);
  };

  const uploading = state.kind === "uploading";
  const percent = uploading ? Math.round(state.progress * 100) : 0;

  return (
    <div className="w-full space-y-3">
      <div
        onDragOver={(event) => {
          event.preventDefault();
          setDragging(true);
        }}
        onDragLeave={() => setDragging(false)}
        onDrop={onDrop}
        className={`flex flex-col items-center gap-3 rounded-2xl border-2 border-dashed bg-card px-6 py-10 text-center transition-colors ${
          dragging ? "border-primary bg-accent" : "border-border"
        }`}
      >
        {uploading ? (
          <>
            <LoaderCircle className="size-8 animate-spin text-primary" aria-hidden />
            <p className="text-sm font-medium">Uploading “{state.fileName}”…</p>
            <div
              className="h-2 w-full max-w-xs overflow-hidden rounded-full bg-muted"
              role="progressbar"
              aria-label="Upload progress"
              aria-valuenow={percent}
              aria-valuemin={0}
              aria-valuemax={100}
            >
              <div className="h-full bg-primary transition-[width]" style={{ width: `${percent}%` }} />
            </div>
            <p className="text-xs text-muted-foreground">{percent}%</p>
          </>
        ) : (
          <>
            <span className="flex size-12 items-center justify-center rounded-full bg-accent text-primary">
              <FileUp className="size-6" aria-hidden />
            </span>
            <div className="space-y-1">
              <p className="font-medium">Drag and drop your PDF here</p>
              <p className="text-sm text-muted-foreground">PDF only · up to {MAX_UPLOAD_MB} MB</p>
            </div>
            <Button size="lg" onClick={() => inputRef.current?.click()}>
              <Upload aria-hidden />
              Upload document
            </Button>
            <label htmlFor={inputId} className="sr-only">
              Choose a PDF document
            </label>
            <input
              ref={inputRef}
              id={inputId}
              type="file"
              accept="application/pdf,.pdf"
              className="sr-only"
              tabIndex={-1}
              onChange={(event) => {
                void start(event.target.files?.[0]);
                event.target.value = "";
              }}
            />
          </>
        )}
      </div>
      {state.kind === "error" && (
        <div className="flex gap-2 rounded-lg border border-danger/30 bg-red-50 p-3 text-left text-sm" role="alert">
          <CircleAlert className="mt-0.5 size-4 shrink-0 text-danger" aria-hidden />
          <div>
            <p className="font-medium text-danger">{state.title}</p>
            <p className="text-foreground/80">{state.message}</p>
          </div>
        </div>
      )}
    </div>
  );
}
