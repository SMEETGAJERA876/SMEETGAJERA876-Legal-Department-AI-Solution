import type { Metadata } from "next";
import { DocumentWorkspace } from "@/components/workspace/document-workspace";

export const metadata: Metadata = { title: "Document · ClauseLens AI" };

export default async function DocumentPage(props: PageProps<"/documents/[id]">) {
  const { id } = await props.params;
  return <DocumentWorkspace documentId={id} />;
}
