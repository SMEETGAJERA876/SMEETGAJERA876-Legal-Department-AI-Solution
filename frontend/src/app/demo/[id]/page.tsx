import type { Metadata } from "next";
import { DocumentWorkspace } from "@/components/workspace/document-workspace";

export const metadata: Metadata = { title: "Live demo · ClauseLens AI" };

export default async function DemoDocumentPage(props: PageProps<"/demo/[id]">) {
  const { id } = await props.params;
  return <DocumentWorkspace documentId={id} demo />;
}
