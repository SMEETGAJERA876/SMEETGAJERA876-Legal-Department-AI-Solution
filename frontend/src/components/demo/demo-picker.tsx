"use client";

import { useQuery } from "@tanstack/react-query";
import {
  ArrowRight,
  CircleAlert,
  FileSearch,
  FileText,
  LoaderCircle,
  MessageSquareText,
  ShieldCheck,
} from "lucide-react";
import Link from "next/link";
import { SiteFooter } from "@/components/system/site-footer";
import { Button } from "@/components/ui/button";
import { fetchDemo } from "@/lib/api";

/** Documents anyone can open without signing in, with a reason to open each one. */
export function DemoPicker() {
  const { data, error, isPending } = useQuery({ queryKey: ["demo"], queryFn: fetchDemo });

  return (
    <div className="flex flex-1 flex-col">
      <header className="border-b bg-card">
        <div className="mx-auto flex max-w-5xl items-center justify-between gap-4 px-4 py-3">
          <Link href="/" className="flex items-center gap-2 text-sm font-semibold text-primary">
            <FileSearch className="size-5" aria-hidden />
            ClauseLens AI
          </Link>
          <Button
            size="sm"
            variant="outline"
            nativeButton={false}
            render={<Link href="/" />}
          >
            Sign in to use your own document
          </Button>
        </div>
      </header>

      <main className="mx-auto w-full max-w-5xl flex-1 space-y-8 px-4 py-10 sm:py-14">
        <div className="space-y-3 text-center">
          <p className="inline-flex items-center gap-1.5 rounded-full border bg-card px-3 py-1 text-xs font-medium text-muted-foreground">
            <ShieldCheck className="size-3.5 text-success" aria-hidden />
            No sign-in, nothing to install
          </p>
          <h1 className="text-3xl font-semibold tracking-tight text-balance sm:text-4xl">
            Try ClauseLens on a real document
          </h1>
          <p className="mx-auto max-w-2xl text-pretty text-muted-foreground">
            These documents are already loaded. Search them, ask questions in plain language, and
            click any answer to see the exact page and wording it came from. Ask something the
            document doesn&apos;t cover and it will tell you so rather than guess.
          </p>
        </div>

        {isPending ? (
          <p
            className="flex items-center justify-center gap-2 py-16 text-sm text-muted-foreground"
            role="status"
          >
            <LoaderCircle className="size-4 animate-spin" aria-hidden />
            Loading the demo documents…
          </p>
        ) : error ? (
          <Message
            title="The demo isn't available right now"
            text={error.message}
          />
        ) : !data.enabled || data.documents.length === 0 ? (
          <Message
            title="No demo documents are loaded"
            text="The server has the demo turned on but nothing seeded yet. Run `uv run python -m scripts.seed_demo` on the API."
          />
        ) : (
          <ul className="grid gap-4 md:grid-cols-2 lg:grid-cols-3">
            {data.documents.map((document) => (
              <li key={document.id}>
                <Link
                  href={`/demo/${document.id}`}
                  className="group flex h-full flex-col gap-3 rounded-xl border bg-card p-5 transition-all hover:-translate-y-0.5 hover:border-primary/40 hover:shadow-md focus-visible:outline-2 focus-visible:outline-ring motion-reduce:transition-none motion-reduce:hover:translate-y-0"
                >
                  <span className="flex size-10 items-center justify-center rounded-lg bg-accent text-primary transition-colors group-hover:bg-primary group-hover:text-primary-foreground">
                    <FileText className="size-5" aria-hidden />
                  </span>
                  <div className="space-y-1">
                    <h2 className="leading-snug font-semibold">
                      {document.document_type ?? document.original_filename}
                    </h2>
                    <p className="text-xs text-muted-foreground">
                      {document.original_filename}
                      {document.page_count ? ` · ${document.page_count} pages` : ""}
                    </p>
                  </div>
                  <p className="text-sm text-pretty text-muted-foreground">
                    {document.description}
                  </p>
                  {document.questions.length > 0 && (
                    <ul className="mt-auto space-y-1.5 pt-1">
                      {document.questions.slice(0, 2).map((question) => (
                        <li
                          key={question}
                          className="flex gap-1.5 text-xs text-muted-foreground"
                        >
                          <MessageSquareText
                            className="mt-0.5 size-3.5 shrink-0 text-primary"
                            aria-hidden
                          />
                          <span className="italic">“{question}”</span>
                        </li>
                      ))}
                    </ul>
                  )}
                  <span className="flex items-center gap-1 text-sm font-medium text-primary">
                    Open
                    <ArrowRight
                      className="size-4 transition-transform group-hover:translate-x-0.5 motion-reduce:transition-none"
                      aria-hidden
                    />
                  </span>
                </Link>
              </li>
            ))}
          </ul>
        )}

        <p className="text-center text-sm text-muted-foreground">
          The demo documents are shared and read-only.{" "}
          <Link href="/" className="font-medium text-primary hover:underline">
            Sign in with Google
          </Link>{" "}
          to upload your own — those stay private to your account.
        </p>
      </main>

      <SiteFooter />
    </div>
  );
}

function Message({ title, text }: { title: string; text: string }) {
  return (
    <div className="mx-auto max-w-lg space-y-2 rounded-xl border bg-card p-6 text-center" role="alert">
      <CircleAlert className="mx-auto size-6 text-danger" aria-hidden />
      <h2 className="font-semibold">{title}</h2>
      <p className="text-sm text-muted-foreground">{text}</p>
    </div>
  );
}
