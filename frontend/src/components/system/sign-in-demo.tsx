"use client";

import { FileText, MessageSquareText, Sparkles } from "lucide-react";
import { useEffect, useState, useSyncExternalStore } from "react";
import { cn } from "@/lib/utils";

type Clause = { id: string; page: number; ref: string; heading: string; text: string };

const CLAUSES: Clause[] = [
  {
    id: "probation",
    page: 1,
    ref: "Clause 4",
    heading: "Probation",
    text: "The first six (6) months of employment shall be a probation period.",
  },
  {
    id: "notice",
    page: 2,
    ref: "Clause 7",
    heading: "Notice period",
    text: "Either party may end this agreement by giving ninety (90) days' written notice.",
  },
  {
    id: "salary",
    page: 2,
    ref: "Clause 9",
    heading: "Salary",
    text: "The Employee shall receive ₹75,000 per month, paid on the last working day.",
  },
  {
    id: "early",
    page: 3,
    ref: "Clause 12",
    heading: "Leaving early",
    text: "If the Employee leaves within twelve (12) months, training costs of ₹50,000 are recoverable.",
  },
];

const QUESTIONS = [
  { question: "What is my notice period?", clause: "notice", answer: "90 days' written notice — and it applies to both you and the employer." },
  { question: "What happens if I leave early?", clause: "early", answer: "If you leave within 12 months, the employer can recover ₹50,000 in training costs." },
  { question: "How long is probation?", clause: "probation", answer: "Six months from when you start." },
  { question: "When is salary paid?", clause: "salary", answer: "₹75,000 every month, on the last working day." },
] as const; // fmt: skip

const TYPING_MS = 22;
const AUTO_ADVANCE_MS = 4500;

function subscribeReducedMotion(onChange: () => void) {
  const query = window.matchMedia("(prefers-reduced-motion: reduce)");
  query.addEventListener("change", onChange);
  return () => query.removeEventListener("change", onChange);
}

function useReducedMotion(): boolean {
  return useSyncExternalStore(
    subscribeReducedMotion,
    () => window.matchMedia("(prefers-reduced-motion: reduce)").matches,
    () => true,
  );
}

/** A small, clickable example of asking a question and seeing the exact source. */
export function SignInDemo() {
  const reducedMotion = useReducedMotion();
  const [active, setActive] = useState(0);
  const [typed, setTyped] = useState(0);
  const [touched, setTouched] = useState(false);

  const current = QUESTIONS[active];
  const clause = CLAUSES.find((c) => c.id === current.clause)!;
  const shown = reducedMotion ? current.answer.length : typed;
  const done = shown >= current.answer.length;

  useEffect(() => {
    if (reducedMotion) return;
    if (!done) {
      const timer = setTimeout(() => setTyped((n) => n + 1), TYPING_MS);
      return () => clearTimeout(timer);
    }
    if (touched) return;
    const timer = setTimeout(() => {
      setActive((i) => (i + 1) % QUESTIONS.length);
      setTyped(0);
    }, AUTO_ADVANCE_MS);
    return () => clearTimeout(timer);
  }, [done, touched, reducedMotion, typed]);

  function choose(index: number) {
    setTouched(true);
    setActive(index);
    setTyped(0);
  }

  return (
    <div className="relative">
      <div
        className="absolute -inset-4 -z-10 rounded-[2rem] bg-gradient-to-br from-primary/15 via-accent to-transparent blur-2xl"
        aria-hidden
      />
      <div className="overflow-hidden rounded-2xl border bg-card shadow-xl shadow-primary/5">
        <div className="flex items-center justify-between border-b bg-muted/50 px-4 py-2.5">
          <span className="flex items-center gap-2 text-xs font-medium">
            <FileText className="size-3.5 text-primary" aria-hidden />
            employment_agreement.pdf
          </span>
          <span className="rounded-full bg-accent px-2 py-0.5 text-[11px] font-medium text-primary">
            Example
          </span>
        </div>

        <div className="grid gap-0 sm:grid-cols-[1fr_1.1fr]">
          <ol className="space-y-2 border-b p-4 text-[12.5px] leading-relaxed sm:border-r sm:border-b-0" aria-label="Example document">
            {CLAUSES.map((c) => {
              const highlighted = c.id === clause.id && done;
              return (
                <li
                  key={c.id}
                  className={cn(
                    "rounded-md border border-transparent p-2 transition-colors duration-300",
                    highlighted && "border-amber-300 bg-amber-50",
                  )}
                >
                  <p className="mb-0.5 flex items-center justify-between text-[11px] text-muted-foreground">
                    <span className="font-semibold text-foreground">
                      {c.ref} · {c.heading}
                    </span>
                    <span>p. {c.page}</span>
                  </p>
                  <p className={cn(highlighted ? "text-foreground" : "text-muted-foreground")}>
                    {highlighted ? <mark className="bg-amber-200/70 px-0.5">{c.text}</mark> : c.text}
                  </p>
                </li>
              );
            })}
          </ol>

          <div className="flex flex-col gap-3 p-4">
            <p className="flex items-center gap-1.5 text-xs font-medium text-muted-foreground">
              <MessageSquareText className="size-3.5" aria-hidden />
              Try a question
            </p>
            <div className="flex flex-wrap gap-1.5" role="group" aria-label="Example questions">
              {QUESTIONS.map((q, index) => (
                <button
                  key={q.question}
                  type="button"
                  onClick={() => choose(index)}
                  aria-pressed={index === active}
                  className="rounded-full border px-2.5 py-1 text-xs transition-colors hover:border-primary/50 hover:text-primary focus-visible:outline-2 focus-visible:outline-ring aria-pressed:border-primary aria-pressed:bg-primary aria-pressed:text-primary-foreground"
                >
                  {q.question}
                </button>
              ))}
            </div>

            <div className="mt-1 flex min-h-36 flex-col gap-2 rounded-xl bg-muted/60 p-3" aria-live="polite">
              <p className="self-end rounded-lg rounded-br-sm bg-primary px-3 py-1.5 text-xs text-primary-foreground">
                {current.question}
              </p>
              <div className="rounded-lg rounded-bl-sm border bg-card px-3 py-2 text-xs">
                <p className="mb-1 flex items-center gap-1 font-medium text-primary">
                  <Sparkles className="size-3" aria-hidden />
                  Answer
                </p>
                <p>
                  {current.answer.slice(0, shown)}
                  {!done && <span className="ml-0.5 inline-block h-3 w-px animate-pulse bg-foreground align-middle" />}
                </p>
                <p
                  className={cn(
                    "mt-2 inline-flex items-center gap-1 rounded-md bg-accent px-1.5 py-0.5 text-[11px] font-medium text-primary transition-opacity duration-300",
                    done ? "opacity-100" : "opacity-0",
                  )}
                >
                  Source: page {clause.page} · {clause.ref}
                </p>
              </div>
            </div>
          </div>
        </div>
      </div>
    </div>
  );
}
