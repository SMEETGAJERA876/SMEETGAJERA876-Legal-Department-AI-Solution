"use client";

import { useQuery } from "@tanstack/react-query";
import { CircleAlert, CircleCheck, LoaderCircle } from "lucide-react";
import { fetchHealth } from "@/lib/api";

export function BackendStatus() {
  const { data, error, isPending } = useQuery({ queryKey: ["health"], queryFn: fetchHealth });

  if (isPending) {
    return (
      <p className="flex items-center gap-2 text-sm text-muted-foreground" role="status">
        <LoaderCircle className="size-4 animate-spin" aria-hidden />
        Checking server connection…
      </p>
    );
  }

  if (error) {
    return (
      <p className="flex items-center gap-2 text-sm text-danger" role="alert">
        <CircleAlert className="size-4" aria-hidden />
        {error.message}
      </p>
    );
  }

  const healthy = data.status === "ok";
  return (
    <p
      className={`flex items-center gap-2 text-sm ${healthy ? "text-success" : "text-warning"}`}
      role="status"
    >
      {healthy ? (
        <CircleCheck className="size-4" aria-hidden />
      ) : (
        <CircleAlert className="size-4" aria-hidden />
      )}
      {healthy
        ? "Server and database connected."
        : "Server is running, but the database is unavailable. Start PostgreSQL and refresh."}
    </p>
  );
}
