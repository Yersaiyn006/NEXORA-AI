# Changelog: audited engineering update

Changes preserve the existing Django apps, data model purpose, Gemini SDK integration, .env loading and public links. No deployment or external business system was modified.

## Authentication and tenancy

Added ordinary-owner login, POST logout, bounded login attempts and private response caching. Centralized tenant membership selection and rejected malformed IDs. Owner-facing workspace links preserve the selected company. Invitation validation now includes the candidate username/email; acceptance uses an atomic one-use claim.

## Conversation reliability

Moved external AI work out of database write transactions. Added expiring conversation leases and turn UUIDs with uniqueness. Completed retries reuse stored answers; failed processing keeps the customer question; stale workers cannot overwrite a newer lease. Public sessions have a company-scoped digest uniqueness rule; Playground first-turn retries recover the same conversation. Deletion is blocked during an active Playground response.

## Abuse and cost controls

Replaced per-process sliding get/set cache limits with atomic database fixed-window counters: session/minute, direct peer IP/minute, business/day and platform/day. Added cleanup command. Gemini timeout and one-attempt retry configuration are explicit; actual total token usage is persisted and safe metadata is logged. SQLite uses short IMMEDIATE transactions to avoid lock-upgrade failures found during the concurrent smoke test.

## AI and factual context

Separated system instructions from company JSON and role-aware history. Added tenant-filtered lexical candidate retrieval, relevance sorting, bounded profile/catalog/knowledge context, a truncation flag, recent dialogue and known-contact redaction. Kept Gemini first for normal answers and clearly labelled provider-unavailable fallback. Removed unused industry-specific fallback wording and inconsistent broad request routing. Active collection accepts offered cancellation variants and can answer information questions without storing them as names.

## Requests, catalog and metrics

Fixed CRM search after queryset slicing. Unified status changes and serialized timed confirmations by business. Untimed requests can be confirmed; past/conflicting appointments remain blocked. Added server-side nonnegative price and duration validation. Dashboard conversion counts distinct real conversations and ignores Playground; Gemini response counts exclude local/request replies. Sales Radar cancelled requests no longer inflate conversion. The Conversation list uses one annotated first-message subquery instead of an N+1 loop.

## Interface and installation

Fixed newest-history display and template indentation in public messages. Added public starting questions, loading/error/retry handling, no raw provider details in client flow and separate-window widget fallback. Added shared focus/reduced-motion/mobile foundation, system-font fallback and mobile catalog layout fixes. Catalog/profile labels are Russian. Updated requirements, installation notes and additive migrations; preserved BigAutoField and the existing catalog index name.

## Verification and documentation

Added security/AI/turn/abuse/access/browser/migration/concurrency evidence and bounded opt-in live eval tooling. Ordinary regression runner disables ambient live AI while mocked provider tests explicitly exercise SDK wiring. Prepared 14 requested deliverable areas: executive summary, architecture, confirmed findings, AI review, competitor research, UX, hackathon, portfolio, strategy, roadmap, source, test results, changelog and next steps.

## Compatibility

Back up before applying. Keep your existing .env and database. Install dependencies, run included migrations, then check/test. Requirements retain Django 6.0.9; package metadata requires Python >=3.12. Verification ran on Python 3.13.16. New fields are nullable; old dialogue/message/lead data is preserved. Concurrent behavior on PostgreSQL, real Gemini, real browser embedding and production infrastructure remain separate acceptance gates.

Playground malformed turn UUIDs return 400 without referencing an absent conversation; successful retries bypass quota consumption. Added regression tests for first-response loss, malformed turn IDs and constant list query count. Additional QA scripts create temporary synthetic SQLite files and make no real provider calls.

## Revalidation changes — 9 October

- B24: cache a server request response atomically with Lead writes; recover safely from a failed assistant-message write. New migration 0005. Six new tests include rollback, lease fencing and shared provider budgets.
- B25: shared daily Gemini attempt budgets for both chat channels; graceful local fallback when exhausted. Zero prevents paid calls. Production AI-enabled default and .env loading are preserved.
- B26: local SDK transport test now disables environment proxies for both sync and async clients; this changes only the synthetic localhost harness.
- Re-ran original baseline, full regression, SQL concurrency, invitations/confirmations, migration preservation and desktop/mobile browser smoke. Current logs use the REVERIFY prefix.
