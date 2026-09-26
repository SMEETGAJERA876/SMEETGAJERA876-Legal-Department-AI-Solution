import { z } from "zod";
import { env } from "@/lib/config";
import { getIdToken } from "@/lib/firebase";

export class ApiError extends Error {
  constructor(
    message: string,
    readonly status: number | null,
    readonly code: string | null = null,
  ) {
    super(message);
    this.name = "ApiError";
  }
}

const UNREACHABLE_MESSAGE =
  "Unable to reach the ClauseLens server. Check that the backend is running and try again.";

const errorBodySchema = z.object({ error: z.string(), message: z.string() });

function apiUrl(path: string): string {
  return `${env.NEXT_PUBLIC_API_URL}${path}`;
}

async function errorFromResponse(response: Response): Promise<ApiError> {
  const body: unknown = await response.json().catch(() => null);
  const parsed = errorBodySchema.safeParse(body);
  if (parsed.success) {
    return new ApiError(parsed.data.message, response.status, parsed.data.error);
  }
  return new ApiError(`The server responded with an error (${response.status}).`, response.status);
}

/** The signed-in user's Google (Firebase) ID token, sent with every request. */
async function authHeaders(): Promise<Record<string, string>> {
  const token = await getIdToken();
  return token ? { Authorization: `Bearer ${token}` } : {};
}

async function send(path: string, init?: RequestInit): Promise<Response> {
  const headers = { ...(await authHeaders()), ...(init?.headers as Record<string, string>) };
  let response: Response;
  try {
    response = await fetch(apiUrl(path), { ...init, headers });
  } catch {
    throw new ApiError(UNREACHABLE_MESSAGE, null);
  }
  if (!response.ok) {
    throw await errorFromResponse(response);
  }
  return response;
}

async function request<T>(path: string, schema: z.ZodType<T>, init?: RequestInit): Promise<T> {
  const response = await send(path, init);
  return schema.parse(await response.json());
}

// ---------------------------------------------------------------- schemas

export const healthSchema = z.object({
  status: z.enum(["ok", "degraded"]),
  app: z.string(),
  database: z.enum(["connected", "unavailable"]),
});
export type Health = z.infer<typeof healthSchema>;

export const classificationSchema = z.object({
  category: z.string().nullable(),
  document_type: z.string().nullable(),
  confidence: z.number(),
  confidence_level: z.enum(["high", "medium", "low"]),
  status: z.enum(["confirmed", "needs_review", "unknown", "user_verified"]),
  signals: z.array(z.string()),
  alternatives: z.array(z.object({ document_type: z.string(), confidence: z.number() })),
});
export type Classification = z.infer<typeof classificationSchema>;

export const documentSchema = z.object({
  id: z.string(),
  original_filename: z.string(),
  file_size: z.number(),
  page_count: z.number().nullable(),
  status: z.enum(["uploaded", "processing", "ready", "failed"]),
  status_detail: z.string().nullable(),
  error_message: z.string().nullable(),
  document_type: z.string().nullable(),
  document_type_id: z.string().nullable().optional(),
  category: z.string().nullable().optional(),
  classification: classificationSchema.nullable().optional(),
  parties: z.array(z.string()),
  created_at: z.string(),
  processed_at: z.string().nullable(),
  source_document_id: z.string().nullable().optional(),
  is_demo: z.boolean().optional().default(false),
  authenticity_verdict: z.enum(["concerns", "check", "ordinary"]).nullable().optional(),
  changes: z
    .array(
      z.object({
        page_number: z.number(),
        kind: z.string(),
        original: z.string(),
        replacement: z.string().nullable(),
      }),
    )
    .optional()
    .default([]),
});
export type DocumentInfo = z.infer<typeof documentSchema>;

export const sourceSchema = z.object({
  page_number: z.number(),
  clause_ref: z.string().nullable(),
  heading: z.string().nullable().optional(),
  quote: z.string(),
});
export type Source = z.infer<typeof sourceSchema>;

const factSchema = z.object({
  concept: z.string(),
  label: z.string(),
  value: z.string(),
  source: sourceSchema,
});
export type Fact = z.infer<typeof factSchema>;

export const overviewSchema = z.object({
  document: documentSchema,
  clause_count: z.number(),
  concepts: z.array(z.object({ concept: z.string(), label: z.string(), facts: z.array(factSchema) })),
  counts: z.record(z.string(), z.number()),
});
export type Overview = z.infer<typeof overviewSchema>;

export const searchResultSchema = z.object({
  page_number: z.number(),
  clause_ref: z.string().nullable(),
  heading: z.string().nullable(),
  snippet: z.string(),
  highlight: z.string(),
  score: z.number().nullable(),
});
export type SearchResult = z.infer<typeof searchResultSchema>;

/** hybrid = meaning + keywords + document structure (recommended); semantic = meaning only. */
export type SearchMode = "exact" | "semantic" | "hybrid";

export const searchSchema = z.object({
  query: z.string(),
  corrected_query: z.string().nullable(),
  mode: z.enum(["exact", "semantic", "hybrid"]),
  results: z.array(searchResultSchema),
  facts: z.array(factSchema),
  related_concepts: z.array(z.string()),
});
export type SearchResponse = z.infer<typeof searchSchema>;

const termSchema = z.object({ legal: z.string(), plain: z.string() });
export type Term = z.infer<typeof termSchema>;

export const simplifiedSchema = z.object({
  original: z.string(),
  simple: z.string(),
  changed: z.boolean(),
  worth_showing: z.boolean(),
  terms: z.array(termSchema),
});
export type SimplifiedText = z.infer<typeof simplifiedSchema>;

export const authenticitySignalSchema = z.object({
  id: z.string(),
  label: z.string(),
  severity: z.enum(["high", "medium", "info"]),
  detail: z.string(),
  evidence: z.string().nullable(),
  page_number: z.number().nullable(),
});
export type AuthenticitySignal = z.infer<typeof authenticitySignalSchema>;

export const authenticitySchema = z.object({
  available: z.boolean(),
  verdict: z.enum(["concerns", "check", "ordinary"]).nullable().optional(),
  provenance: z.record(z.string(), z.string()).default({}),
  signals: z.array(authenticitySignalSchema).default([]),
  policy: z.string().default("warn"),
});
export type Authenticity = z.infer<typeof authenticitySchema>;

export const formatPartSchema = z.object({
  id: z.string(),
  label: z.string(),
  required: z.boolean(),
  status: z.enum(["present", "empty", "missing"]),
  why: z.string(),
  page_number: z.number().nullable(),
  evidence: z.string().nullable(),
});
export type FormatPart = z.infer<typeof formatPartSchema>;

export const formatCheckSchema = z.object({
  available: z.boolean(),
  document_type: z.string().nullable().optional(),
  format_id: z.string().nullable().optional(),
  format_name: z.string().nullable().optional(),
  authority: z.string().nullable().optional(),
  note: z.string().nullable().optional(),
  score: z.number().default(0),
  required_total: z.number().default(0),
  required_present: z.number().default(0),
  parts: z.array(formatPartSchema).default([]),
  covered_formats: z.array(z.string()).default([]),
});
export type FormatCheck = z.infer<typeof formatCheckSchema>;

export const answerSchema = z.object({
  conversation_id: z.string(),
  message_id: z.string(),
  question: z.string(),
  found: z.boolean(),
  answer: z.string(),
  simple_explanation: z.string().nullable(),
  why_it_matters: z.string().nullable(),
  citations: z.array(sourceSchema),
  related_concepts: z.array(z.string()),
  generated_by: z.string(),
  kind: z.enum(["document", "about"]),
  points: z.array(z.string()),
  note: z.string().nullable(),
  searched_as: z.string().nullable(),
  matched_terms: z.array(termSchema).optional().default([]),
  quoted_terms: z.array(termSchema).optional().default([]),
});
export type Answer = z.infer<typeof answerSchema>;

export const questionsSchema = z.object({
  intro: z.string(),
  questions: z.array(z.object({ question: z.string(), concept: z.string(), source: sourceSchema })),
});
export type ProfessionalQuestions = z.infer<typeof questionsSchema>;

const conceptsSchema = z.array(z.object({ key: z.string(), label: z.string() }));
export type ConceptLabel = z.infer<typeof conceptsSchema>[number];

export const issueSchema = z.object({
  id: z.string(),
  kind: z.string(),
  label: z.string(),
  fixable: z.boolean(),
  page_number: z.number(),
  original: z.string(),
  suggestion: z.string().nullable(),
  message: z.string(),
  context: z.string(),
});
export type Issue = z.infer<typeof issueSchema>;

export const issuesSchema = z.object({
  fixable_count: z.number(),
  review_count: z.number(),
  issues: z.array(issueSchema),
});
export type Issues = z.infer<typeof issuesSchema>;

export const repairSchema = z.object({
  document: documentSchema,
  applied: z.array(issueSchema),
  not_applied: z.array(z.object({ issue: issueSchema, reason: z.string() })),
});
export type RepairResult = z.infer<typeof repairSchema>;

/** The public read-only demo: documents anyone may open without signing in. */
export const demoSchema = z.object({
  enabled: z.boolean(),
  documents: z.array(
    z.object({
      id: z.string(),
      original_filename: z.string(),
      document_type: z.string().nullable(),
      page_count: z.number().nullable(),
      description: z.string(),
      questions: z.array(z.string()),
    }),
  ),
});
export type Demo = z.infer<typeof demoSchema>;
export type DemoDocument = Demo["documents"][number];

// ---------------------------------------------------------------- endpoints

export const fetchHealth = () => request("/health", healthSchema);
export const fetchDemo = () => request("/demo", demoSchema);
export const fetchDocuments = () => request("/documents", z.array(documentSchema));
export const fetchDocument = (id: string) => request(`/documents/${id}`, documentSchema);
export const fetchOverview = (id: string) => request(`/documents/${id}/overview`, overviewSchema);
export const fetchConcepts = () => request("/documents/concepts", conceptsSchema);
export const fetchQuestions = (id: string) =>
  request(`/documents/${id}/questions`, questionsSchema);
export const documentFilePath = (id: string) => `/documents/${id}/file`;
/** Served as an attachment, so the browser saves it to the Downloads folder. */
export const documentDownloadPath = (id: string) => `/documents/${id}/file?download=true`;
/** One-page-style PDF of key dates, notices, deadlines, money and questions. */
export const documentSummaryPath = (id: string) => `/documents/${id}/summary`;

/** The document's PDF, fetched with the user's sign-in (a plain link can't send it). */
export async function fetchDocumentFile(id: string): Promise<Blob> {
  return (await send(documentFilePath(id))).blob();
}

const FILENAME_PATTERN = /filename\*=UTF-8''([^;]+)|filename="?([^";]+)"?/i;

/** Downloads an API file to the user's Downloads folder, keeping the server's file name. */
export async function downloadFromApi(path: string, fallbackName: string): Promise<void> {
  const response = await send(path);
  const match = FILENAME_PATTERN.exec(response.headers.get("Content-Disposition") ?? "");
  const filename = match?.[1] ? decodeURIComponent(match[1]) : (match?.[2] ?? fallbackName);
  const url = URL.createObjectURL(await response.blob());
  const link = document.createElement("a");
  link.href = url;
  link.download = filename;
  document.body.append(link);
  link.click();
  link.remove();
  setTimeout(() => URL.revokeObjectURL(url), 10_000);
}
const documentTypesSchema = z.array(
  z.object({ id: z.string(), name: z.string(), category: z.string(), category_name: z.string() }),
);
export type DocumentType = z.infer<typeof documentTypesSchema>[number];
export const fetchDocumentTypes = () => request("/documents/types", documentTypesSchema);

/** The user confirms or corrects the document type. */
export function setDocumentType(id: string, documentTypeId: string) {
  return request(`/documents/${id}/classification`, documentSchema, {
    method: "PUT",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ document_type_id: documentTypeId }),
  });
}

export const fetchIssues = (id: string) => request(`/documents/${id}/issues`, issuesSchema);

/** Evidence about how the document was made (docs/Authenticity.md). */
export const fetchAuthenticity = (id: string) =>
  request(`/documents/${id}/authenticity`, authenticitySchema);

/** How the document compares with the official format for its kind (data/formats). */
export const fetchFormatCheck = (id: string) =>
  request(`/documents/${id}/format-check`, formatCheckSchema);

/** Formal wording rewritten in everyday words, returned beside the original. */
export function simplifyText(id: string, text: string) {
  return request(`/documents/${id}/simplify`, simplifiedSchema, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ text }),
  });
}

export function repairDocument(id: string, issueIds: string[]) {
  return request(`/documents/${id}/repair`, repairSchema, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ issue_ids: issueIds }),
  });
}

export function searchDocument(id: string, query: string, mode: SearchMode) {
  const params = new URLSearchParams({ q: query, mode });
  return request(`/documents/${id}/search?${params.toString()}`, searchSchema);
}

export function askDocument(id: string, question: string, conversationId: string | null) {
  return request(`/documents/${id}/ask`, answerSchema, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ question, conversation_id: conversationId }),
  });
}

const activitySchema = z.array(
  z.object({
    at: z.string(),
    action: z.string(),
    label: z.string(),
    document_id: z.string().nullable(),
    document_name: z.string().nullable(),
  }),
);
export type ActivityEvent = z.infer<typeof activitySchema>[number];

/** Everything recorded about the signed-in user's documents (audit log), newest first. */
export const fetchMyActivity = () => request("/account/activity", activitySchema);

/** Right to erasure: deletes every document of the signed-in user, with all extracted data. */
export function deleteAllMyDocuments() {
  return request("/account/documents", z.object({ deleted_documents: z.number() }), {
    method: "DELETE",
  });
}

export async function deleteDocument(id: string): Promise<void> {
  await send(`/documents/${id}`, { method: "DELETE" });
}

/** Upload with progress reporting (fetch cannot report upload progress). */
export async function uploadDocument(
  file: File,
  onProgress: (fraction: number) => void,
): Promise<DocumentInfo> {
  const headers = await authHeaders();
  return new Promise((resolve, reject) => {
    const xhr = new XMLHttpRequest();
    xhr.open("POST", apiUrl("/documents"));
    for (const [name, value] of Object.entries(headers)) xhr.setRequestHeader(name, value);
    xhr.upload.onprogress = (event) => {
      if (event.lengthComputable) onProgress(event.loaded / event.total);
    };
    xhr.onerror = () => reject(new ApiError(UNREACHABLE_MESSAGE, null));
    xhr.onload = () => {
      let body: unknown = null;
      try {
        body = JSON.parse(xhr.responseText);
      } catch {
        // handled below
      }
      if (xhr.status >= 200 && xhr.status < 300) {
        const parsed = documentSchema.safeParse(body);
        if (parsed.success) resolve(parsed.data);
        else reject(new ApiError("The server sent an unexpected response.", xhr.status));
        return;
      }
      const error = errorBodySchema.safeParse(body);
      reject(
        new ApiError(
          error.success ? error.data.message : `Upload failed (${xhr.status}).`,
          xhr.status,
          error.success ? error.data.error : null,
        ),
      );
    };
    const form = new FormData();
    form.append("file", file);
    xhr.send(form);
  });
}
