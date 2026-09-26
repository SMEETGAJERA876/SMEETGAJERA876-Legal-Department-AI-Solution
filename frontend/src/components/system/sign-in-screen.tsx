"use client";

import {
  BadgeCheck,
  ChevronDown,
  EyeOff,
  FileCheck2,
  FileDown,
  FileSearch,
  Fingerprint,
  Highlighter,
  History,
  KeyRound,
  ListChecks,
  LoaderCircle,
  LockKeyhole,
  PlayCircle,
  MessageSquareText,
  Search,
  ShieldCheck,
  Trash2,
  UploadCloud,
  type LucideIcon,
} from "lucide-react";
import Link from "next/link";
import { useAuth } from "@/components/providers/auth-provider";
import { Disclaimer } from "@/components/system/disclaimer";
import { SignInDemo } from "@/components/system/sign-in-demo";
import { Button } from "@/components/ui/button";
import { cn } from "@/lib/utils";

function GoogleLogo() {
  return (
    <svg viewBox="0 0 48 48" className="size-4" aria-hidden>
      <path fill="#FFC107" d="M43.6 20.5H42V20H24v8h11.3C33.7 32.7 29.2 36 24 36c-6.6 0-12-5.4-12-12s5.4-12 12-12c3.1 0 5.8 1.2 7.9 3l5.7-5.7C34 6.1 29.3 4 24 4 12.9 4 4 12.9 4 24s8.9 20 20 20 20-8.9 20-20c0-1.3-.1-2.4-.4-3.5z" />
      <path fill="#FF3D00" d="m6.3 14.7 6.6 4.8C14.7 15.1 19 12 24 12c3.1 0 5.8 1.2 7.9 3l5.7-5.7C34 6.1 29.3 4 24 4 16.3 4 9.7 8.3 6.3 14.7z" />
      <path fill="#4CAF50" d="M24 44c5.2 0 9.9-2 13.4-5.2l-6.2-5.2C29.2 35.1 26.7 36 24 36c-5.2 0-9.6-3.3-11.3-8l-6.5 5C9.5 39.6 16.2 44 24 44z" />
      <path fill="#1976D2" d="M43.6 20.5H42V20H24v8h11.3c-.8 2.2-2.2 4.2-4.1 5.6l6.2 5.2C37 39.2 44 34 44 24c0-1.3-.1-2.4-.4-3.5z" />
    </svg>
  );
}

const FEATURES: { icon: LucideIcon; title: string; text: string }[] = [
  { icon: MessageSquareText, title: "Ask in your own words", text: "“What is my notice period?” or “What happens if I leave early?” — no legal terms needed." },
  { icon: Highlighter, title: "Every answer shows its source", text: "See the page and clause, with the original wording highlighted in the document." },
  { icon: Search, title: "Find anything fast", text: "Search by exact words or by meaning, even with small spelling mistakes." },
  { icon: FileCheck2, title: "Check your document", text: "Spot typos and mistakes with the page and a suggested fix, then download a corrected copy." },
  { icon: FileDown, title: "One-page summary PDF", text: "Key dates, notice periods, deadlines and amounts — each with its page — in one file." },
  { icon: ListChecks, title: "Prepare for advice", text: "Get a list of questions to discuss with a qualified legal professional." },
]; // fmt: skip

const DOCUMENT_TYPES = [
  "Employment agreements",
  "Rental & property",
  "Contracts & NDAs",
  "Government notices",
  "Acts, rules & circulars",
  "Court orders",
  "Company documents",
  "Financial documents",
  "Education",
  "Policies",
];

const PRIVACY: { icon: LucideIcon; title: string; text: string }[] = [
  { icon: Fingerprint, title: "Sign in with Google only", text: "No new password to create. Your sign-in is checked by our server on every request." },
  { icon: LockKeyhole, title: "Only you can open your documents", text: "Each document belongs to your Google account. Anyone else is told it doesn't exist." },
  { icon: EyeOff, title: "Never used to train AI", text: "Your uploads are used only to answer your questions — never to train models." },
  { icon: Trash2, title: "Delete whenever you want", text: "Deleting removes the file and everything extracted from it — one document or all of them." },
  { icon: KeyRound, title: "Encrypted storage", text: "Uploaded files are encrypted on the server with AES-256." },
  { icon: History, title: "See every access", text: "Your activity log shows each upload, view, download and deletion." },
]; // fmt: skip

const STEPS: { icon: LucideIcon; title: string; text: string }[] = [
  { icon: BadgeCheck, title: "Sign in with Google", text: "One click. We only receive your name and email." },
  { icon: UploadCloud, title: "Upload a PDF", text: "Up to 25 MB. ClauseLens reads it and finds the clauses, dates and amounts." },
  { icon: MessageSquareText, title: "Ask, search and check", text: "Answers come with the page, so you can verify them yourself." },
]; // fmt: skip

const FAQ = [
  {
    question: "Is this legal advice?",
    answer:
      "No. ClauseLens explains what your document says and shows where it says it. For decisions, consult a qualified legal professional — ClauseLens even prepares questions for that conversation.",
  },
  {
    question: "Can the answers be wrong?",
    answer:
      "Answers are taken from your document and always show the page and clause, so you can check the original wording. If the document doesn't cover something, ClauseLens says so instead of guessing.",
  },
  {
    question: "Who can see my documents?",
    answer:
      "Only you, when signed in with the same Google account. Other ClauseLens users can't list, open, search or download them.",
  },
  {
    question: "What files can I upload?",
    answer:
      "PDF files up to 25 MB — contracts, agreements, government notices, Acts and rules, court orders, policies and other official documents. Scanned PDFs work too: their pages are read with text recognition (OCR).",
  },
  {
    question: "What does ClauseLens get from my Google account?",
    answer:
      "Only your name, email address and profile photo, to show who is signed in and keep your documents private. It can't read your email or Google Drive.",
  },
];

function SignInButton({ size = "lg", className }: { size?: "lg" | "default"; className?: string }) {
  const { signingIn, signIn } = useAuth();
  return (
    <Button
      size={size}
      onClick={() => void signIn()}
      disabled={signingIn}
      className={cn("gap-2 bg-ink text-white shadow-md hover:bg-ink/90", className)}
    >
      {signingIn ? (
        <LoaderCircle className="animate-spin" aria-hidden />
      ) : (
        <span className="flex size-5 items-center justify-center rounded-full bg-white">
          <GoogleLogo />
        </span>
      )}
      {signingIn ? "Waiting for Google…" : "Continue with Google"}
    </Button>
  );
}

/** Lets anyone — a judge, a colleague, someone deciding whether to trust it — try it first. */
function DemoButton({
  variant = "outline",
  size = "lg",
  className,
}: {
  variant?: "outline" | "ghost";
  size?: "lg" | "default";
  className?: string;
}) {
  return (
    <Button
      size={size}
      variant={variant}
      nativeButton={false}
      render={<Link href="/demo" />}
      className={cn("gap-2", className)}
    >
      <PlayCircle aria-hidden />
      Try the live demo
    </Button>
  );
}

function SignInError() {
  const { error } = useAuth();
  if (!error) return null;
  return (
    <p role="alert" className="rounded-lg border border-danger/30 bg-red-50 px-3 py-2 text-sm text-danger">
      {error}
    </p>
  );
}

function SectionHeading({ eyebrow, title, text }: { eyebrow: string; title: string; text?: string }) {
  return (
    <div className="mx-auto max-w-2xl space-y-2 text-center">
      <p className="text-xs font-semibold tracking-wider text-primary uppercase">{eyebrow}</p>
      <h2 className="text-2xl font-semibold tracking-tight text-balance sm:text-3xl">{title}</h2>
      {text && <p className="text-pretty text-muted-foreground">{text}</p>}
    </div>
  );
}

function CenteredState({ children }: { children: React.ReactNode }) {
  return (
    <main className="flex flex-1 flex-col items-center justify-center gap-4 px-4 py-16 text-center">
      <p className="flex items-center gap-2 text-sm font-semibold text-primary">
        <FileSearch className="size-5" aria-hidden />
        ClauseLens AI
      </p>
      {children}
    </main>
  );
}

/** The welcome and sign-in page, shown until the person signs in with Google. */
export function SignInScreen({ notConfigured = false }: { notConfigured?: boolean }) {
  const { status } = useAuth();

  if (notConfigured) {
    return (
      <CenteredState>
        <p className="max-w-md text-sm text-muted-foreground">
          Sign-in isn&apos;t set up yet. Add the Firebase web-app values (NEXT_PUBLIC_FIREBASE_…)
          to <code>frontend/.env.local</code> and restart the app.
        </p>
      </CenteredState>
    );
  }
  if (status === "loading") {
    return (
      <CenteredState>
        <p className="flex items-center gap-2 text-sm text-muted-foreground" role="status">
          <LoaderCircle className="size-4 animate-spin" aria-hidden />
          Checking your sign-in…
        </p>
      </CenteredState>
    );
  }

  return (
    <div className="flex flex-1 flex-col">
      <header className="sticky top-0 z-20 border-b border-transparent bg-background/80 backdrop-blur supports-[backdrop-filter]:bg-background/70">
        <div className="mx-auto flex max-w-6xl items-center justify-between px-4 py-3">
          <span className="flex items-center gap-2 text-sm font-semibold text-primary">
            <FileSearch className="size-5" aria-hidden />
            ClauseLens AI
          </span>
          <nav className="flex items-center gap-1 sm:gap-4" aria-label="Page sections">
            <a href="#features" className="hidden text-sm text-muted-foreground hover:text-foreground sm:inline">
              Features
            </a>
            <a href="#privacy" className="hidden text-sm text-muted-foreground hover:text-foreground sm:inline">
              Privacy
            </a>
            <a href="#faq" className="hidden text-sm text-muted-foreground hover:text-foreground sm:inline">
              FAQ
            </a>
            <DemoButton size="default" variant="ghost" />
            <SignInButton size="default" />
          </nav>
        </div>
      </header>

      <main className="flex-1">
        {/* Hero */}
        <section className="mx-auto grid max-w-6xl items-center gap-12 px-4 pt-10 pb-16 sm:pt-16 lg:grid-cols-[1fr_1.05fr] lg:gap-10">
          <div className="space-y-6">
            <p className="inline-flex items-center gap-1.5 rounded-full border bg-card px-3 py-1 text-xs font-medium text-muted-foreground">
              <ShieldCheck className="size-3.5 text-success" aria-hidden />
              Private to your Google account
            </p>
            <h1 className="text-4xl font-semibold tracking-tight text-balance sm:text-5xl">
              Understand any legal or official document —{" "}
              <span className="text-primary">with the page to prove it.</span>
            </h1>
            <p className="max-w-xl text-lg text-pretty text-muted-foreground">
              Upload a contract, agreement or government notice. Ask questions in plain language
              and get answers that point to the exact page and clause.
            </p>
            <div className="flex flex-col items-start gap-3">
              <div className="flex flex-wrap items-center gap-3">
                <SignInButton />
                <DemoButton />
              </div>
              <p className="text-xs text-muted-foreground">
                The demo opens a real Act of Parliament and a sample contract — no sign-in, no
                upload needed.
              </p>
              <SignInError />
              <ul className="flex flex-wrap gap-x-4 gap-y-1.5 text-xs text-muted-foreground">
                {["No password to create", "Never used to train AI", "Delete any time"].map((item) => (
                  <li key={item} className="flex items-center gap-1">
                    <BadgeCheck className="size-3.5 text-success" aria-hidden />
                    {item}
                  </li>
                ))}
              </ul>
            </div>
          </div>
          <SignInDemo />
        </section>

        {/* Document types */}
        <section aria-label="Documents ClauseLens understands" className="border-y bg-card/60">
          <div className="mx-auto flex max-w-6xl flex-wrap items-center justify-center gap-2 px-4 py-5">
            <span className="mr-1 text-xs font-medium text-muted-foreground">Works with</span>
            {DOCUMENT_TYPES.map((type) => (
              <span key={type} className="rounded-full border bg-background px-3 py-1 text-xs">
                {type}
              </span>
            ))}
          </div>
        </section>

        {/* Features */}
        <section id="features" className="mx-auto max-w-6xl scroll-mt-20 space-y-10 px-4 py-16 sm:py-20">
          <SectionHeading
            eyebrow="Built for real work"
            title="Everything you need to read a document with confidence"
            text="Not a general chatbot: every answer comes from your document, with the source to check it."
          />
          <ul className="grid gap-4 sm:grid-cols-2 lg:grid-cols-3">
            {FEATURES.map(({ icon: Icon, title, text }) => (
              <li
                key={title}
                className="group rounded-xl border bg-card p-5 transition-all hover:-translate-y-0.5 hover:border-primary/40 hover:shadow-md motion-reduce:transition-none motion-reduce:hover:translate-y-0"
              >
                <span className="mb-3 flex size-10 items-center justify-center rounded-lg bg-accent text-primary transition-colors group-hover:bg-primary group-hover:text-primary-foreground">
                  <Icon className="size-5" aria-hidden />
                </span>
                <h3 className="font-semibold">{title}</h3>
                <p className="mt-1 text-sm text-muted-foreground">{text}</p>
              </li>
            ))}
          </ul>
        </section>

        {/* Privacy */}
        <section id="privacy" className="scroll-mt-20 bg-ink text-white">
          <div className="mx-auto grid max-w-6xl gap-10 px-4 py-16 sm:py-20 lg:grid-cols-[0.9fr_1.1fr] lg:items-center">
            <div className="space-y-4">
              <p className="text-xs font-semibold tracking-wider text-blue-300 uppercase">Security & privacy</p>
              <h2 className="text-2xl font-semibold tracking-tight text-balance sm:text-3xl">
                Your documents stay yours.
              </h2>
              <p className="text-pretty text-white/70">
                Legal and official documents are personal. ClauseLens is built so that only the
                Google account that uploaded a document can ever see it.
              </p>
            </div>
            <ul className="grid gap-4 sm:grid-cols-2">
              {PRIVACY.map(({ icon: Icon, title, text }) => (
                <li key={title} className="rounded-xl border border-white/10 bg-white/5 p-5">
                  <Icon className="mb-3 size-5 text-blue-300" aria-hidden />
                  <h3 className="font-semibold">{title}</h3>
                  <p className="mt-1 text-sm text-white/70">{text}</p>
                </li>
              ))}
            </ul>
          </div>
        </section>

        {/* How it works */}
        <section className="mx-auto max-w-6xl space-y-10 px-4 py-16 sm:py-20">
          <SectionHeading eyebrow="How it works" title="Start in three steps" />
          <ol className="grid gap-4 md:grid-cols-3">
            {STEPS.map(({ icon: Icon, title, text }, index) => (
              <li key={title} className="relative rounded-xl border bg-card p-5">
                <span className="absolute top-5 right-5 text-3xl font-semibold text-muted-foreground/25" aria-hidden>
                  {index + 1}
                </span>
                <Icon className="mb-3 size-6 text-primary" aria-hidden />
                <h3 className="font-semibold">
                  <span className="sr-only">Step {index + 1}: </span>
                  {title}
                </h3>
                <p className="mt-1 text-sm text-muted-foreground">{text}</p>
              </li>
            ))}
          </ol>
        </section>

        {/* FAQ */}
        <section id="faq" className="mx-auto max-w-3xl scroll-mt-20 space-y-8 px-4 pb-16 sm:pb-20">
          <SectionHeading eyebrow="Questions" title="Good to know" />
          <div className="divide-y rounded-xl border bg-card">
            {FAQ.map(({ question, answer }) => (
              <details key={question} className="group px-5 py-4 [&_summary::-webkit-details-marker]:hidden">
                <summary className="flex cursor-pointer list-none items-center justify-between gap-4 font-medium focus-visible:outline-2 focus-visible:outline-ring">
                  {question}
                  <ChevronDown
                    className="size-4 shrink-0 text-muted-foreground transition-transform group-open:rotate-180"
                    aria-hidden
                  />
                </summary>
                <p className="mt-2 text-sm text-muted-foreground">{answer}</p>
              </details>
            ))}
          </div>
        </section>

        {/* Final call to action */}
        <section className="mx-auto max-w-6xl px-4 pb-16">
          <div className="flex flex-col items-center gap-4 rounded-2xl bg-gradient-to-br from-primary to-primary-dark px-6 py-12 text-center text-white">
            <h2 className="text-2xl font-semibold tracking-tight text-balance sm:text-3xl">
              Know what your document says before you sign or reply.
            </h2>
            <p className="max-w-xl text-white/80">
              Sign in with Google and upload your first document.
            </p>
            <div className="flex flex-wrap items-center justify-center gap-3">
              <SignInButton className="bg-white text-ink hover:bg-white/90" />
              <DemoButton className="border-white/40 bg-transparent text-white hover:bg-white/10" />
            </div>
            <SignInError />
          </div>
        </section>
      </main>

      <footer className="border-t bg-card">
        <div className="mx-auto flex max-w-6xl flex-col items-center justify-between gap-3 px-4 py-6 sm:flex-row">
          <span className="flex items-center gap-2 text-sm font-semibold text-primary">
            <FileSearch className="size-4" aria-hidden />
            ClauseLens AI
          </span>
          <Disclaimer />
        </div>
      </footer>
    </div>
  );
}
