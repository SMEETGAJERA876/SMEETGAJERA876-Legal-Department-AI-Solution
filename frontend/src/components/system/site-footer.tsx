import { Lock, ScrollText, Sparkles } from "lucide-react";
import Link from "next/link";
import { Disclaimer } from "@/components/system/disclaimer";

const PRODUCT = [
  { label: "Try the live demo", href: "/demo" },
  { label: "Ask your own document", href: "/" },
];

const UNDERSTANDS = [
  "Contracts, agreements and NDAs",
  "Rent and lease agreements",
  "Employment letters",
  "Government notices and circulars",
  "Acts, rules and court orders",
];

const SAFEGUARDS = [
  { icon: ScrollText, text: "Every answer shows the page and clause it came from" },
  { icon: Sparkles, text: "Plain-language versions always sit beside the original wording" },
  { icon: Lock, text: "Your documents are private to your Google account and encrypted at rest" },
];

/** The footer at the end of every page: where to start, what it reads, and what it will not do. */
export function SiteFooter() {
  return (
    <footer className="mt-auto border-t bg-card">
      <div className="mx-auto grid w-full max-w-6xl gap-8 px-4 py-10 sm:grid-cols-2 lg:grid-cols-3">
        <nav aria-labelledby="footer-product" className="space-y-3">
          <h2 id="footer-product" className="text-sm font-semibold">
            Start here
          </h2>
          <ul className="space-y-2">
            {PRODUCT.map(({ label, href }) => (
              <li key={label}>
                <Link
                  href={href}
                  className="text-sm text-muted-foreground hover:text-foreground hover:underline"
                >
                  {label}
                </Link>
              </li>
            ))}
          </ul>
        </nav>

        <div className="space-y-3">
          <h2 className="text-sm font-semibold">Documents it reads</h2>
          <ul className="space-y-1.5">
            {UNDERSTANDS.map((item) => (
              <li key={item} className="text-sm text-muted-foreground">
                {item}
              </li>
            ))}
          </ul>
        </div>

        <div className="space-y-3">
          <h2 className="text-sm font-semibold">How it stays honest</h2>
          <ul className="space-y-2">
            {SAFEGUARDS.map(({ icon: Icon, text }) => (
              <li key={text} className="flex gap-2 text-sm text-muted-foreground">
                <Icon className="mt-0.5 size-3.5 shrink-0 text-primary" aria-hidden />
                {text}
              </li>
            ))}
          </ul>
        </div>
      </div>

      <div className="border-t">
        <div className="mx-auto flex w-full max-w-6xl flex-col gap-3 px-4 py-5 sm:flex-row sm:items-center sm:justify-between">
          <Disclaimer />
          <p className="text-xs text-muted-foreground">
            Built for citizens, tenants, employees and anyone handed a document they did not
            write.
          </p>
        </div>
      </div>
    </footer>
  );
}
