# Architecture Decision Record

## Overview

This document explains every major architectural decision made in the Multi-Currency Wallet Platform, including the trade-offs considered and the rationale for each choice.

---

## 1. Clean Architecture with Strict Layer Separation

**Decision:** Enforce a hard rule that business logic never lives in API routes, and database access never lives in services.

**Rationale:**
- Routes are thin — they validate, delegate, and return. This makes routes trivially testable and replaceable.
- Services hold the domain — swapping transport (REST → gRPC → CLI) requires zero service changes.
- Repositories isolate the ORM — switching from SQLAlchemy to another ORM means rewriting only repositories.

**Trade-off:** More files and indirection vs. the ability to test each layer independently and change any layer without cascading rewrites.

---

## 2. Repository Pattern

**Decision:** All database access goes through repository classes. Routes and services never call `db.execute()` directly.

**Rationale:**
- Services become free of SQL concerns — they express intent (`get user by email`) not mechanics (`SELECT * FROM users WHERE email = ?`).
- Repositories are easily mocked in unit tests, enabling fast tests without a real database.
- Centralises query optimisation — adding an index or changing a query happens in one place.

---

## 3. Pessimistic Locking (`SELECT FOR UPDATE`)

**Decision:** All wallet balance updates acquire a row-level lock before reading and modifying the balance.

**Why pessimistic over optimistic?**

Optimistic locking works by reading a version number, computing a new value, then attempting an UPDATE WHERE version = old_version. Under low contention this is efficient. However, in payment systems:

1. **Hot wallets** (popular merchants, high-traffic accounts) receive many concurrent update requests. Optimistic locking produces a thundering herd of retries when many transactions contest the same row.
2. **Business logic complexity** — a failed optimistic retry means re-executing the entire transfer (potentially involving exchange rate lookups, notification triggers, and multiple row reads). This multiplies work under contention.
3. **Predictability** — pessimistic locking serialises concurrent updates at the database level. Latency is predictable: one transaction waits, completes, then the next proceeds. Optimistic locking makes latency unpredictable under contention.

**Trade-off:** Reduced throughput for hot wallets. Mitigated by keeping transactions as short as possible (lock acquired → balance computed → balance written → commit, all in milliseconds).

---

## 4. Adapter Pattern for Exchange Rate Providers

**Decision:** Abstract the exchange rate provider behind an interface (`ExchangeRateProvider`). Concrete implementations are `OpenExchangeAdapter`, `FixerAdapter`, and `MockExchangeAdapter`.

**Rationale:**
- Provider switching (e.g., Fixer goes down, switch to OpenExchange) requires changing one environment variable and zero application code.
- `MockExchangeAdapter` makes all tests deterministic — no flaky tests from external API failures.
- New providers can be added by creating a new class implementing `get_rates()` and `get_rate()` — Open/Closed Principle.

---

## 5. Circuit Breaker for External APIs

**Decision:** Wrap all calls to exchange rate providers in a Redis-backed circuit breaker.

**States:**
- **Closed** (normal): requests pass through
- **Open** (failing): requests are rejected immediately, cached rates are returned
- **Half-Open** (recovering): one probe request is allowed; success closes the circuit, failure re-opens it

**Rationale:**
- Without a circuit breaker, every request hangs for the HTTP timeout (10s) when the provider is down. Under load this exhausts the connection pool and cascades into full service degradation.
- Redis-backed state means all application replicas share circuit state — one replica's failure observations affect the entire fleet.
- Falling back to cached rates (Redis → DB) means the system degrades gracefully rather than crashing.

---

## 6. Idempotency Keys

**Decision:** Transfers support an optional `Idempotency-Key` header. If a key has been processed, the stored response is returned without reprocessing.

**Rationale:**
- Network timeouts cause clients to retry requests. Without idempotency, a retry could debit a wallet twice.
- Keys are stored in PostgreSQL (not Redis) for durability — a Redis restart would not cause duplicate processing.
- The response body is stored alongside the key so clients receive an identical response on retry, enabling safe client-side retry logic.

---

## 7. Celery for Async Processing

**Decision:** Long-running tasks (exchange rate refresh, audit logging, notifications) run as Celery tasks rather than inline in the API.

**Rationale:**
- API response times stay under 100ms for the user even if background work takes seconds.
- Failed tasks can be retried with exponential backoff — the API cannot retry a request a user has already received a response for.
- Workers scale independently of API servers.

**Retry strategy:** `autoretry_for=(Exception,)` with `retry_backoff=True` implements exponential backoff. `max_retries=3` prevents infinite loops. Exhausted retries are routed to a `dead_letter` queue for manual inspection.

---

## 8. Redis Caching Strategy

**Decision:** Cache exchange rates and user profiles. Never cache wallet balances.

**Why not cache balances?**
- Balance reads are most often followed immediately by a mutation (debit/credit). Serving a stale balance leads to incorrect availability decisions.
- Balances are updated atomically inside DB transactions. Caching would require cache invalidation on every write — effectively eliminating the cache benefit.

**Exchange rate caching:** Rates are valid for 1 hour (configurable). The cache chain is Redis → PostgreSQL → Provider. This means rates are served in < 1ms from Redis in the common case.

---

## 9. JWT with Refresh Tokens

**Decision:** Short-lived access tokens (30 min) with long-lived refresh tokens (7 days) stored in PostgreSQL.

**Rationale:**
- Access tokens are stateless — validation requires no DB lookup, enabling high throughput.
- Short expiry limits the damage window if a token is stolen.
- Refresh tokens stored in DB can be revoked individually (logout) or in bulk (compromised account). Pure stateless JWTs cannot be revoked without a blocklist.
- Refresh token hashes (not plaintext) are stored — a DB leak does not expose usable tokens.

---

## 10. Atomic Transfers

**Decision:** The transfer operation (debit sender, credit recipient, create transaction records) executes inside a single PostgreSQL transaction.

**Guarantee:** Either all operations commit or all roll back. There is no state where a sender is debited but the recipient is not credited.

**Implementation:** SQLAlchemy's `begin_nested()` creates a savepoint. The outer session commits only after all nested operations succeed.

---

## 11. Database Design

**UUIDs as primary keys:**
- No enumeration attacks (sequential IDs reveal record counts and allow ID scanning)
- Safe for distributed systems where multiple services generate IDs
- Trade-off: slightly larger storage and slower index scans vs. integers

**Numeric(18, 8) for amounts:**
- Floating-point arithmetic introduces rounding errors. `0.1 + 0.2 != 0.3` in IEEE 754.
- `Numeric`/`Decimal` is exact. Financial calculations must be exact.

**Audit log is append-only:**
- Never DELETE or UPDATE audit_logs rows. This maintains a tamper-evident record.
- In production, grant the application user INSERT-only permissions on this table.

---

## 12. Scalability Path

**Current state:** Single PostgreSQL, single Redis, multiple app replicas behind a load balancer.

**At 500k users / 100 TPS:**

1. **Read replicas** — Direct all SELECT queries (profile reads, transaction history, exchange rate reads) to a read replica. Only writes go to primary. Reduces primary load by ~70% for typical fintech workloads.

2. **Connection pooling** — PgBouncer in transaction mode sits between the app and PostgreSQL. Each app server maintains a small pool (10 connections). PgBouncer multiplexes thousands of app connections through ~100 DB connections. This is critical at 100 TPS with many simultaneous requests.

3. **Redis Cluster** — Single Redis handles ~100k ops/sec. At scale, Redis Cluster shards data across nodes. Rate limiting keys and exchange rate cache shard naturally.

4. **Celery autoscaling** — Celery workers scale horizontally. Add workers as queue depth grows. Kubernetes HPA can autoscale based on Redis queue depth (via KEDA).

5. **Wallet partitioning** — If a single wallet becomes a hot row (high-traffic merchant), consider wallet sharding: split a single wallet into N sub-wallets, distribute credits across sub-wallets, sum for balance reads. Eliminates the single row contention bottleneck.

6. **Exchange rate provider HA** — Configure multiple providers. The adapter pattern makes failover trivial: if Provider A circuit opens, Provider B becomes primary until A recovers.
