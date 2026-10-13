# AI quality and reliability

## What the code proves

Public chat and owner Playground call the same universal `respond` engine. For normal company/catalog/general questions, Gemini is attempted first when enabled and a key is configured. The request collector writes the Lead record on the server. Gemini has no database tools, no payment execution and no booking-confirmation authority.

The original archive already routes public chat to the universal engine. The historical Chat Fix/Gemini First issue is therefore not reintroduced as a new fix. The two baseline failed tests expected the old “catalog” source label even though the code correctly labels degraded catalog replies “catalog_fallback”; expectations now reflect that distinction.

## Updated context pipeline

1. Resolve an authorized Conversation, deriving its Business server-side.
2. Read profile/catalog/knowledge only for that business. Skip inactive knowledge.
3. Select lexical matches across title/description/content, include bounded baseline candidates, rank with current question plus four recent messages.
4. Reserve context for profile, catalog, knowledge and recent dialogue; mark partial catalog/knowledge coverage explicitly.
5. Preserve the last 24 message roles in chronological order, remove the latest customer question from history so it is sent once, and omit system/human messages from model history.
6. Hide known Lead names, customer-format phones and email addresses from history/latest input. Company phone remains an intentional public company fact.
7. Send system policy separately from JSON company data and typed message history.
8. Use a configurable bounded timeout, one SDK attempt, lower temperature, capped output, safe error logging and actual usage_metadata token totals.

The budget is measured in characters. It is an input bound, not an exact model-token guarantee. Actual token totals come from the provider. Names not known to a Lead and arbitrary sensitive text can remain in free-form messages: this is limited redaction, not complete anonymization or a DLP system.

## Memory

There is persistent conversation history plus bounded recent context. This supports a short follow-up such as “А доставка?” because the previous turns are sent. It is not unlimited long-term personal memory, semantic summarization, cross-channel identity or permanent preference recall. Old details beyond the recent window can be forgotten. Synthetic tests verify history ordering, roles, duplicate removal, privacy and persistence; without a key they cannot verify whether Gemini actually resolves pronouns correctly.

A lease serializes conversation updates. A repeat turn reuses the stored answer. Failed unexpected processing preserves the question and releases the lease; retry can recover. This is stronger than holding the whole request in one DB transaction but does not guarantee exactly-once billing after a provider response and worker crash.

## Factuality

The provider receives structured prices, availability, duration, company hours and rules. Empty fields remain empty. The instructions explicitly require an honest unknown, distinguish general advice from company policy and forbid invented confirmation. Partial context is identified so missing retrieved records are not mistaken for unavailable products.

This is a grounding design, not a demonstrated hallucination rate. There is no semantic output verifier, no source citations in final answers, and no structured fact assertion check. A malicious owner can put false data in the company's own knowledge; the server cannot establish truth about the real world. Previous assistant messages are explicitly not an authoritative source, but the model still sees them for dialogue continuity.

The restaurant Tagam, shop and salon fixtures validate independent business data boundaries and server behavior. They do not reproduce the real Tagam customer experiment, whose database/transcripts were not supplied. Any claim about the original answers on delivery/payment/hours would be speculation.

## Prompt injection

System instructions, role-aware messages and JSON data make boundaries clearer. Tenant scoping and the absence of write tools form the enforceable boundary: even an injected answer cannot execute an order or read another company's rows through an exposed tool. The mock injection test proves payload placement and that no Lead is created by the sample model-text request. It does not prove that a real model obeys the policy. Lower temperature also does not eliminate injection.

Use an adversarial live corpus for data-driven, multi-turn and encoded attacks. Observe unsupported assertions, false confirmations, source disclosure and inappropriate contact requests. Do not use a naive banned-word regex as the main safety guarantee. See [OWASP](https://cheatsheetseries.owasp.org/cheatsheets/LLM_Prompt_Injection_Prevention_Cheat_Sheet.html).

## RAG decision

Do not add a vector database now. This archive contains small structured catalog/profile/knowledge sources and no file ingestion pipeline. Scoped SQL lexical candidate retrieval with a bounded context is a simpler first retrieval layer. It improves on blindly taking the first records. Synonyms, morphology and broad recommendations remain its weak points.

Add full-text or embeddings only after an evaluation set demonstrates unacceptable relevant-document recall at realistic catalog volume. Preserve business filters during retrieval, keep facts structured, record retrieved source IDs, and compare recall/latency/cost before adopting a new service. A vector store alone does not solve memory, permissions, factuality or actions.

## Free-form requests

The collector remains deterministic to keep writes predictable. Explicit request phrases enter it; information questions and short diversions can go to Gemini. It still lacks robust correction (“нет, другое имя”), topic exit, arbitrary multi-field messages and unrestricted language coverage. This is the largest remaining AI-product limitation.

Next iteration: Gemini returns a schema-validated proposal `{intent, fields, missing_fields}`. The server validates allowed fields, tenant, phone, timestamp, length and current state, then requests explicit customer confirmation before persisting a completed request. The proposal must never include an authoritative business ID or executable API instruction. Establish tests before enabling this path. Do not sell the present deterministic collector as a full agent.

## Live evaluation status

No GEMINI_API_KEY exists in the attachment or environment. `evaluate_ai --live` was run and stopped before any provider request with a missing-key error. SDK payload, errors and timeout were also checked using the real SDK against a local synthetic HTTP server. No real Gemini request was made. Real Gemini factuality, language fluency, follow-up reasoning, latency and quota errors remain unverified.

For a later bounded check, use a separate empty SQLite file, migrate it and run:

```powershell
$env:NEXORA_DATABASE_PATH = "$PWD\nexora-ai-eval.sqlite3"
python manage.py migrate
python manage.py evaluate_ai --live --max-calls 6
Remove-Item Env:NEXORA_DATABASE_PATH
```

Keep the real key in your existing local .env; do not paste it into chat. The command refuses the main db.sqlite3, creates synthetic company/catalog fixtures, allows no more than six one-attempt calls, prints answers/token totals for human review and deletes its synthetic business records. It is opt-in and is not part of routine tests.

References: [Google system instructions](https://ai.google.dev/gemini-api/docs/generate-content/text-generation), [SDK timeouts](https://ai.google.dev/gemini-api/docs/generate-content/flex-inference), [token usage](https://ai.google.dev/gemini-api/docs/tokens).

## Recovery and cost guard added in revalidation

Request transitions now persist an atomic response receipt before the final reply write. Creation, name collection and finalization replay correctly after a synthetic failure. Gemini attempt budgets cover public and staff conversations together. Counters include failed attempts, use fixed UTC-day windows, and permit a zero budget; they do not calculate currency spend. Full human evaluations remain required.
