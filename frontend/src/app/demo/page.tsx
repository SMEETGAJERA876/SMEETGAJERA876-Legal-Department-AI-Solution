import type { Metadata } from "next";
import { DemoPicker } from "@/components/demo/demo-picker";

export const metadata: Metadata = {
  title: "Live demo · ClauseLens AI",
  description:
    "Open a real Indian Act or a sample contract and ask it questions — no sign-in needed.",
};

export default function DemoPage() {
  return <DemoPicker />;
}
