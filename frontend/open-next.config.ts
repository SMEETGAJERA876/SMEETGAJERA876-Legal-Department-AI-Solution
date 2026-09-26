import { defineCloudflareConfig } from "@opennextjs/cloudflare";

// No incremental cache (R2) configured: every route here is either static or reads live,
// auth-gated data, so there's nothing worth caching between requests yet.
export default defineCloudflareConfig();
