import { FileSearch, FileUp, Highlighter, MessageSquareText, ShieldCheck } from "lucide-react";
import { RecentDocuments } from "@/components/documents/recent-documents";
import { BackendStatus } from "@/components/system/backend-status";
import { Disclaimer } from "@/components/system/disclaimer";
import { UserMenu } from "@/components/system/user-menu";
import { UploadDropzone } from "@/components/upload/upload-dropzone";

const STEPS = [
  {
    icon: FileUp,
    title: "Upload",
    text: "Add a contract, agreement or policy as a PDF.",
  },
  {
    icon: MessageSquareText,
    title: "Ask in your own words",
    text: "“What is my notice period?” or “What happens if I leave early?”",
  },
  {
    icon: Highlighter,
    title: "See the source",
    text: "Every answer shows the page and clause, and highlights the original wording.",
  },
  {
    icon: ShieldCheck,
    title: "Prepare for advice",
    text: "Get a list of questions to discuss with a qualified legal professional.",
  },
];

export default function Home() {
  return (
    <>
      <header className="sticky top-0 z-20 border-b bg-background/85 backdrop-blur supports-[backdrop-filter]:bg-background/70">
        <div className="mx-auto flex h-14 w-full max-w-5xl items-center justify-between gap-4 px-4">
          <span className="flex items-center gap-2 text-sm font-semibold text-primary">
            <FileSearch className="size-5" aria-hidden />
            ClauseLens AI
          </span>
          <UserMenu />
        </div>
      </header>
      <main className="mx-auto flex w-full max-w-3xl flex-1 flex-col items-center gap-10 px-4 py-10 sm:py-14">
        <div className="flex flex-col items-center gap-5 text-center">
          <h1 className="text-4xl font-semibold tracking-tight text-balance sm:text-5xl">
            Understand what your document says.
          </h1>
          <p className="max-w-xl text-lg text-pretty text-muted-foreground">
            Upload a legal document, find important information, and jump directly to the source.
          </p>
        </div>

        <UploadDropzone />
        <a href="#how-it-works" className="-mt-6 text-sm font-medium text-primary hover:underline">
          See how it works
        </a>
        <RecentDocuments />

        <section
          id="how-it-works"
          aria-labelledby="how-title"
          className="w-full scroll-mt-8 space-y-4"
        >
          <h2 id="how-title" className="text-center text-xl font-semibold">
            How it works
          </h2>
          <ol className="grid gap-3 sm:grid-cols-2">
            {STEPS.map(({ icon: Icon, title, text }, index) => (
              <li key={title} className="flex gap-3 rounded-xl border bg-card p-4">
                <span className="flex size-9 shrink-0 items-center justify-center rounded-full bg-accent text-primary">
                  <Icon className="size-4" aria-hidden />
                </span>
                <div>
                  <p className="text-sm font-semibold">
                    {index + 1}. {title}
                  </p>
                  <p className="text-sm text-muted-foreground">{text}</p>
                </div>
              </li>
            ))}
          </ol>
        </section>

        <footer className="flex flex-col items-center gap-2">
          <Disclaimer />
          <BackendStatus />
        </footer>
      </main>
    </>
  );
}
