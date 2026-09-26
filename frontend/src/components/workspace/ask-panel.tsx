"use client";

import { useMutation } from "@tanstack/react-query";
import {
  ArrowLeftRight,
  Check,
  CircleHelp,
  Copy,
  Info,
  LoaderCircle,
  MessageSquareText,
  SearchX,
  SendHorizontal,
  Sparkles,
} from "lucide-react";
import { useEffect, useRef, useState } from "react";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Textarea } from "@/components/ui/textarea";
import {
  askDocument,
  fetchQuestions,
  type Answer,
  type ProfessionalQuestions,
  type Term,
} from "@/lib/api";
import { formatSource } from "@/lib/format";
import { SourceQuote, type ShowSource } from "./source-quote";

type Props = {
  documentId: string;
  onShowSource: ShowSource;
  conceptLabel: (key: string) => string;
};

const SUGGESTED_QUESTIONS = [
  "What is the notice period?",
  "What are the deadlines or last dates?",
  "How much do I have to pay?",
  "What happens if I miss a deadline?",
  "How can I appeal or complain?",
  "What documents do I need?",
  "Why should I use ClauseLens?",
];

export function AskPanel({ documentId, onShowSource, conceptLabel }: Props) {
  const [question, setQuestion] = useState("");
  const [conversationId, setConversationId] = useState<string | null>(null);
  const [answers, setAnswers] = useState<Answer[]>([]);
  const endRef = useRef<HTMLDivElement>(null);

  const ask = useMutation({
    mutationFn: (text: string) => askDocument(documentId, text, conversationId),
    onSuccess: (answer) => {
      setConversationId(answer.conversation_id);
      setAnswers((previous) => [...previous, answer]);
      setQuestion("");
      const first = answer.citations[0];
      if (first) onShowSource(first.page_number, first.quote);
    },
  });

  const questions = useMutation({ mutationFn: () => fetchQuestions(documentId) });

  useEffect(() => {
    endRef.current?.scrollIntoView({ behavior: "smooth", block: "end" });
  }, [answers.length, ask.isPending, questions.data]);

  const submit = (text: string) => {
    const trimmed = text.trim();
    if (trimmed.length >= 2 && !ask.isPending) ask.mutate(trimmed);
  };

  return (
    <section aria-labelledby="ask-title" className="flex h-full min-h-0 flex-col">
      <div className="flex items-center gap-2 border-b px-4 py-3">
        <MessageSquareText className="size-4 text-primary" aria-hidden />
        <h2 id="ask-title" className="text-sm font-semibold">
          Ask about your document
        </h2>
      </div>

      <div className="min-h-0 flex-1 space-y-4 overflow-y-auto p-4" aria-live="polite">
        {answers.length === 0 && !ask.isPending && (
          <div className="space-y-3">
            <p className="text-sm text-muted-foreground">
              Ask a question in your own words. Answers come only from this document, with the
              page and clause they came from.
            </p>
            <div className="flex flex-wrap gap-1.5">
              {SUGGESTED_QUESTIONS.map((suggestion) => (
                <Button
                  key={suggestion}
                  variant="outline"
                  size="sm"
                  className="h-auto py-1 whitespace-normal text-left"
                  onClick={() => submit(suggestion)}
                >
                  {suggestion}
                </Button>
              ))}
            </div>
          </div>
        )}

        {answers.map((answer) => (
          <AnswerCard
            key={answer.message_id}
            documentId={documentId}
            answer={answer}
            onShowSource={onShowSource}
            conceptLabel={conceptLabel}
            onAskRelated={(key) => submit(`What does the document say about ${conceptLabel(key).toLowerCase()}?`)}
          />
        ))}

        {ask.isPending && (
          <p className="flex items-center gap-2 text-sm text-muted-foreground" role="status">
            <LoaderCircle className="size-4 animate-spin" aria-hidden />
            Reading the relevant parts of your document…
          </p>
        )}
        {ask.error && (
          <p className="text-sm text-danger" role="alert">
            {ask.error.message}
          </p>
        )}

        {questions.data && (
          <QuestionsCard data={questions.data} onShowSource={onShowSource} />
        )}
        {questions.error && (
          <p className="text-sm text-danger" role="alert">
            {questions.error.message}
          </p>
        )}
        <div ref={endRef} />
      </div>

      <div className="space-y-2 border-t bg-card p-3">
        <form
          className="flex items-end gap-2"
          onSubmit={(event) => {
            event.preventDefault();
            submit(question);
          }}
        >
          <label htmlFor="ask-input" className="sr-only">
            Your question
          </label>
          <Textarea
            id="ask-input"
            value={question}
            onChange={(event) => setQuestion(event.target.value)}
            onKeyDown={(event) => {
              if (event.key === "Enter" && !event.shiftKey) {
                event.preventDefault();
                submit(question);
              }
            }}
            placeholder={answers.length ? "Ask a follow-up question…" : "e.g. What is my notice period?"}
            rows={2}
            maxLength={1000}
            className="min-h-0 resize-none"
          />
          <Button type="submit" size="icon" aria-label="Ask" disabled={ask.isPending || question.trim().length < 2}>
            <SendHorizontal />
          </Button>
        </form>
        <Button
          variant="ghost"
          size="sm"
          className="w-full"
          onClick={() => questions.mutate()}
          disabled={questions.isPending}
        >
          {questions.isPending ? <LoaderCircle className="animate-spin" /> : <CircleHelp />}
          Questions to ask a legal professional
        </Button>
      </div>
    </section>
  );
}

function AnswerCard({
  answer,
  documentId,
  onShowSource,
  conceptLabel,
  onAskRelated,
}: {
  documentId: string;
  answer: Answer;
  onShowSource: ShowSource;
  conceptLabel: (key: string) => string;
  onAskRelated: (key: string) => void;
}) {
  return (
    <article className="space-y-3">
      <p className="ml-auto w-fit max-w-[90%] rounded-2xl rounded-br-sm bg-primary px-3 py-2 text-sm text-primary-foreground">
        {answer.question}
      </p>
      <div className="space-y-3 rounded-xl border bg-card p-4">
        {answer.searched_as && (
          <p className="text-xs text-muted-foreground">
            Searched for: <span className="font-medium text-foreground">“{answer.searched_as}”</span>
          </p>
        )}
        {answer.kind === "about" ? (
          <AboutAnswer answer={answer} />
        ) : answer.found ? (
          <>
            <p className="text-sm font-medium leading-relaxed">{answer.answer}</p>
            {answer.matched_terms.length > 0 && <TermBridge terms={answer.matched_terms} />}
            {answer.simple_explanation && (
              <AnswerSection title="In simple words">{answer.simple_explanation}</AnswerSection>
            )}
            {answer.quoted_terms.length > 0 && <TermGlossary terms={answer.quoted_terms} />}
            {answer.why_it_matters && (
              <AnswerSection title="Why it matters">{answer.why_it_matters}</AnswerSection>
            )}
            <div className="space-y-2">
              <h3 className="text-xs font-semibold uppercase tracking-wide text-muted-foreground">
                What the document says
              </h3>
              {answer.citations.map((citation, index) => (
                <SourceQuote
                  key={`${citation.page_number}-${index}`}
                  source={citation}
                  onShowSource={onShowSource}
                  simplifyFor={documentId}
                />
              ))}
            </div>
            {answer.generated_by === "none" && (
              <p className="flex items-center gap-1.5 text-xs text-muted-foreground">
                <Sparkles className="size-3.5" aria-hidden />
                Quoted directly from your document.
              </p>
            )}
          </>
        ) : (
          <p className="flex items-start gap-2 text-sm">
            <SearchX className="mt-0.5 size-4 shrink-0 text-muted-foreground" aria-hidden />
            {answer.answer} Try different words, or search the document on the left.
          </p>
        )}
        {answer.related_concepts.length > 0 && (
          <div className="space-y-1.5 border-t pt-3">
            <p className="text-xs font-medium text-muted-foreground">You may also want to check</p>
            <div className="flex flex-wrap gap-1.5">
              {answer.related_concepts.map((key) => (
                <Badge
                  key={key}
                  variant="secondary"
                  render={<button type="button" onClick={() => onAskRelated(key)} />}
                >
                  {conceptLabel(key)}
                </Badge>
              ))}
            </div>
          </div>
        )}
      </div>
    </article>
  );
}

function AboutAnswer({ answer }: { answer: Answer }) {
  return (
    <div className="space-y-3">
      <Badge variant="secondary">
        <Info aria-hidden />
        About ClauseLens
      </Badge>
      <p className="text-sm font-medium leading-relaxed">{answer.answer}</p>
      <ul className="list-disc space-y-1.5 pl-5 text-sm leading-relaxed">
        {answer.points.map((point) => (
          <li key={point}>{point}</li>
        ))}
      </ul>
      {answer.note && <p className="text-xs text-muted-foreground">{answer.note}</p>}
    </div>
  );
}

/** "You said 'builder' — this document says 'promoter'." The bridge between the two languages. */
function TermBridge({ terms }: { terms: Term[] }) {
  return (
    <div className="space-y-1 rounded-lg border border-primary/20 bg-accent p-3">
      <h3 className="flex items-center gap-1.5 text-xs font-semibold tracking-wide text-primary uppercase">
        <ArrowLeftRight className="size-3.5" aria-hidden />
        Your words in this document&apos;s language
      </h3>
      <ul className="space-y-0.5">
        {terms.map(({ plain, legal }) => (
          <li key={`${plain}-${legal}`} className="text-sm">
            You said <span className="font-medium">“{plain}”</span> — this document says{" "}
            <span className="font-medium">“{legal}”</span>.
          </li>
        ))}
      </ul>
    </div>
  );
}

/** The formal words inside the quoted passage, and what each one means. */
function TermGlossary({ terms }: { terms: Term[] }) {
  return (
    <details className="rounded-lg border bg-muted/40 p-3">
      <summary className="cursor-pointer text-xs font-semibold tracking-wide text-muted-foreground uppercase">
        What these formal words mean ({terms.length})
      </summary>
      <dl className="mt-2 space-y-1">
        {terms.map(({ legal, plain }) => (
          <div key={legal} className="flex flex-wrap gap-x-1.5 text-sm">
            <dt className="font-medium">“{legal}”</dt>
            <dd className="text-muted-foreground">means {plain}</dd>
          </div>
        ))}
      </dl>
    </details>
  );
}

function AnswerSection({ title, children }: { title: string; children: string }) {
  return (
    <div className="space-y-1">
      <h3 className="text-xs font-semibold uppercase tracking-wide text-muted-foreground">
        {title}
      </h3>
      <p className="text-sm leading-relaxed">{children}</p>
    </div>
  );
}

function QuestionsCard({
  data,
  onShowSource,
}: {
  data: ProfessionalQuestions;
  onShowSource: ShowSource;
}) {
  const [copied, setCopied] = useState(false);
  const copy = async () => {
    const text = data.questions
      .map((q, i) => `${i + 1}. ${q.question} (${formatSource(q.source.page_number, q.source.clause_ref)})`)
      .join("\n");
    try {
      await navigator.clipboard.writeText(text);
      setCopied(true);
    } catch {
      setCopied(false);
    }
  };

  return (
    <article className="space-y-3 rounded-xl border border-primary/30 bg-accent/40 p-4">
      <div className="flex items-start justify-between gap-2">
        <h3 className="text-sm font-semibold">Questions for a legal professional</h3>
        {data.questions.length > 0 && (
          <Button variant="outline" size="xs" onClick={copy}>
            {copied ? <Check /> : <Copy />}
            {copied ? "Copied" : "Copy list"}
          </Button>
        )}
      </div>
      <p className="text-xs text-muted-foreground">{data.intro}</p>
      {data.questions.length === 0 ? (
        <p className="text-sm text-muted-foreground">
          No specific questions could be generated from the terms found in this document.
        </p>
      ) : (
        <ol className="list-decimal space-y-2 pl-5 text-sm">
          {data.questions.map((q, index) => (
            <li key={index}>
              <span>{q.question}</span>{" "}
              <button
                type="button"
                className="text-xs font-medium text-primary underline-offset-2 hover:underline"
                onClick={() => onShowSource(q.source.page_number, q.source.quote)}
              >
                {formatSource(q.source.page_number, q.source.clause_ref)}
              </button>
            </li>
          ))}
        </ol>
      )}
    </article>
  );
}
