# 🏦 Multi-Currency Wallet Platform — Complete Architecture & Design Guide

> **Project**: Green Wheels — Multi-Currency Wallet Platform  
> **Assignment**: Full Stack Engineering Challenge (Senior | 5+ Years)  
> **Stack**: FastAPI (Python) · React + TypeScript · PostgreSQL · Redis · Celery · Docker

---

## Table of Contents

1. [Project Overview](#1-project-overview)
2. [High-Level Architecture](#2-high-level-architecture)
3. [Backend Architecture](#3-backend-architecture)
   - [Layered Architecture (Clean Architecture)](#31-layered-architecture-clean-architecture)
   - [Design Patterns Used](#32-design-patterns-used)
4. [Frontend Architecture](#4-frontend-architecture)
5. [Database Design](#5-database-design)
6. [Infrastructure & DevOps](#6-infrastructure--devops)
7. [Security Architecture](#7-security-architecture)
8. [Real-Time Architecture (SSE)](#8-real-time-architecture-sse)
9. [Async / Background Processing](#9-async--background-processing)
10. [Scalability Design Note (500k users / 100 TPS)](#10-scalability-design-note)
11. [Error Handling Strategy](#11-error-handling-strategy)
12. [Key Architectural Decisions & Trade-offs](#12-key-architectural-decisions--trade-offs)

---

## 1. Project Overview

The **Multi-Currency Wallet Platform** is a production-minded financial application that allows users to:

- **Register / Login** with JWT-based authentication (access + refresh token rotation)
- **Manage wallets** in any currency (USD, EUR, GBP, JPY, INR, NGN, etc.)
- **Credit / Debit** wallets with automatic currency conversion
- **Transfer funds** between users across currencies with real exchange rates
- **View transaction history** with filtering and pagination
- **Receive real-time balance updates** via Server-Sent Events (SSE)

---

## 2. High-Level Architecture

```
┌─────────────────────────────────────────────────────────────────────┐
│                         CLIENT LAYER                                │
│  React + TypeScript SPA  │  Redux Toolkit  │  SSE Hook             │
│  (served via Nginx)      │  (State Mgmt)   │  (live updates)        │
└───────────────────────────────────┬─────────────────────────────────┘
                                    │  HTTP / SSE
                                    ▼
┌─────────────────────────────────────────────────────────────────────┐
│                        API GATEWAY LAYER                            │
│         Nginx (reverse proxy, static file serving, SSL)            │
└───────────────────────────────────┬─────────────────────────────────┘
                                    │
                                    ▼
┌─────────────────────────────────────────────────────────────────────┐
│                      APPLICATION LAYER                              │
│  FastAPI (Async Python)  │  Uvicorn ASGI Server                   │
│  ┌─────────────────────────────────────────────────────────────┐   │
│  │  Middleware Stack                                            │   │
│  │  CORSMiddleware → ExceptionMiddleware → RateLimitMiddleware  │   │
│  └─────────────────────────────────────────────────────────────┘   │
│  ┌──────────┐  ┌──────────┐  ┌──────────┐  ┌──────────────────┐   │
│  │  auth    │  │  wallets │  │ exchange │  │   health / SSE   │   │
│  │ endpoint │  │ endpoint │  │  rates   │  │    endpoints     │   │
│  └──────────┘  └──────────┘  └──────────┘  └──────────────────┘   │
│  ┌──────────────────────────────────────────────────────────────┐  │
│  │  Services Layer (Business Logic)                             │  │
│  │  AuthService │ WalletService │ ExchangeRateService │ ...     │  │
│  └──────────────────────────────────────────────────────────────┘  │
│  ┌──────────────────────────────────────────────────────────────┐  │
│  │  Repository Layer (Data Access)                              │  │
│  │  UserRepository │ WalletRepository │ ExchangeRateRepository  │  │
│  └──────────────────────────────────────────────────────────────┘  │
└──────────────────────┬───────────────────┬──────────────────────────┘
                       │                   │
          ┌────────────▼──────┐   ┌────────▼────────────────────┐
          │   PostgreSQL 16   │   │   Redis 7                   │
          │  (Primary Store)  │   │  DB0: Cache + SSE Pub/Sub   │
          │                   │   │  DB1: Celery Broker         │
          │  - users          │   │  DB2: Celery Results        │
          │  - wallets        │   │  (LRU eviction, 256MB cap)  │
          │  - transactions   │   └────────────────────────────-┘
          │  - transfers      │
          │  - exchange_rates │   ┌──────────────────────────────┐
          │  - audit_logs     │   │  Celery Worker + Beat        │
          │  - idempotency_   │   │  - Exchange rate refresh     │
          │    keys           │   │  - Audit log writes          │
          └───────────────────┘   │  - Notification dispatch     │
                                  │  - Dead-letter queue handler │
                                  └──────────────────────────────┘
```

---

## 3. Backend Architecture

### 3.1 Layered Architecture (Clean Architecture)

The backend strictly follows a **Clean Architecture / Layered Architecture** pattern. Each layer has a **single responsibility** and only depends on the layer below it.

```
┌──────────────────────────────────────────────────────────┐
│  Layer 1: API / Presentation Layer                       │
│  app/api/v1/endpoints/                                   │
│  Handles HTTP, validates input via Pydantic schemas,     │
│  returns structured JSON responses. No business logic.   │
└─────────────────────────┬────────────────────────────────┘
                          │ calls
┌─────────────────────────▼────────────────────────────────┐
│  Layer 2: Service / Application Layer                    │
│  app/services/                                           │
│  Contains all business logic. Orchestrates repositories, │
│  applies domain rules, raises domain exceptions.         │
│  AuthService · WalletService · ExchangeRateService       │
└─────────────────────────┬────────────────────────────────┘
                          │ calls
┌─────────────────────────▼────────────────────────────────┐
│  Layer 3: Repository / Infrastructure Layer              │
│  app/repositories/                                       │
│  Abstracts all database access. Returns ORM models.      │
│  UserRepository · WalletRepository · ExchangeRateRepo   │
└─────────────────────────┬────────────────────────────────┘
                          │ calls
┌─────────────────────────▼────────────────────────────────┐
│  Layer 4: Domain / Model Layer                           │
│  app/models/                                             │
│  SQLAlchemy ORM models: User, Wallet, Transaction,       │
│  Transfer, ExchangeRate, AuditLog, IdempotencyKey        │
└──────────────────────────────────────────────────────────┘
```

**Why Layered / Clean Architecture?**
- **Testability**: Services can be tested with mock repositories. No HTTP context needed.
- **Maintainability**: Business logic lives in one place. API contract changes don't touch services.
- **Extensibility**: Swap PostgreSQL for another DB by replacing only the repository layer.

---

### 3.2 Design Patterns Used

#### 1. 🏭 Factory Pattern — Application Factory

```python
# app/main.py
def create_application() -> FastAPI:
    app = FastAPI(title=settings.APP_NAME, ...)
    app.add_middleware(CORSMiddleware, ...)
    app.add_middleware(ExceptionMiddleware)
    app.add_middleware(RateLimitMiddleware)
    app.include_router(api_router)
    return app

app = create_application()
```

**Where**: `app/main.py`  
**Why**: The factory function makes it trivially easy to create test instances with overridden dependencies. Tests call `create_application()` with test settings; production uses the default. Avoids module-level side effects.

---

#### 2. 🗄️ Repository Pattern — Data Access Abstraction

```python
# app/repositories/base.py
class BaseRepository[T]:
    def __init__(self, model: Type[T], db: AsyncSession): ...
    async def save(self, entity: T) -> T: ...
    async def delete(self, entity: T) -> None: ...

# app/repositories/wallet_repository.py
class WalletRepository(BaseRepository[Wallet]):
    async def get_by_id_with_lock(self, wallet_id) -> Optional[Wallet]:
        # SELECT ... FOR UPDATE (pessimistic locking)
        return await self.db.execute(
            select(Wallet).where(Wallet.id == wallet_id).with_for_update()
        )
```

**Where**: `app/repositories/`  
**Why**: Decouples business logic from SQL. Services don't write queries — they call methods like `get_by_id_with_lock()`. This makes testing easy (mock the repository) and keeps SQL changes in one place.

**Why Pessimistic Locking (SELECT FOR UPDATE)?**  
In payment systems, concurrent balance updates must be serialised. Pessimistic locking holds the row lock for the duration of the transaction (milliseconds). Optimistic locking (version columns) causes cascading retries under contention and makes retry logic complex when side effects (notifications, audit logs) exist.

---

#### 3. 🔌 Adapter Pattern — Exchange Rate Providers

```python
# app/adapters/exchange_rate.py
class ExchangeRateProvider(ABC):  # Abstract interface
    @abstractmethod
    async def get_rates(self, base_currency: str) -> Dict[str, Decimal]: ...

class OpenExchangeAdapter(ExchangeRateProvider):  # Concrete adapter
    async def get_rates(self, base_currency: str): ...

class FixerAdapter(ExchangeRateProvider):          # Another concrete adapter
    async def get_rates(self, base_currency: str): ...

class MockExchangeAdapter(ExchangeRateProvider):   # Test/fallback adapter
    async def get_rates(self, base_currency: str): ...

def get_exchange_rate_provider() -> ExchangeRateProvider:
    if settings.EXCHANGE_RATE_PROVIDER == "open_exchange":
        return OpenExchangeAdapter(settings.OPEN_EXCHANGE_APP_ID)
    return MockExchangeAdapter()  # Fallback
```

**Where**: `app/adapters/exchange_rate.py`  
**Why**: The service layer depends only on the `ExchangeRateProvider` abstract interface. Switching providers (OpenExchange → Fixer → CurrencyLayer) requires zero changes to business logic. The mock adapter enables offline development and testing.

**Cross-rate calculation**: The base class implements a 3-step rate resolution: Direct → Inverse → Cross via USD. This ensures any currency pair works even if the provider only returns USD-based rates.

---

#### 4. ⚡ Circuit Breaker Pattern — External Provider Resilience

```python
# app/adapters/circuit_breaker.py
class CircuitBreaker:
    # State machine: CLOSED → (N failures) → OPEN → (timeout) → HALF_OPEN → CLOSED
    # State is stored in Redis so ALL replicas share circuit state.
    
    async def call(self, func: Callable, *args, **kwargs):
        state = await self.get_state()
        if state == CircuitState.OPEN:
            raise CircuitOpenException(self.name)  # Fail fast
        try:
            result = await func(*args, **kwargs)
            if state == CircuitState.HALF_OPEN:
                await self.record_success()  # Reset circuit
            return result
        except Exception:
            await self.record_failure()      # Trip circuit if threshold hit
            raise

# Module-level singleton
exchange_rate_circuit_breaker = CircuitBreaker(name="exchange_rate_provider")
```

**Where**: `app/adapters/circuit_breaker.py`  
**Why**: External exchange rate APIs go down. Without a circuit breaker, every request hangs for the HTTP timeout (10s+), exhausting the async event loop. The circuit breaker fails fast, falls back to cached rates, and retries the provider automatically after the recovery window. Redis backing ensures all app replicas share the same circuit state.

**States**:
- `CLOSED`: Normal — requests pass through
- `OPEN`: Provider failed N times — reject immediately, return cached rates
- `HALF_OPEN`: Recovery probe — allow one request; success resets to CLOSED, failure returns to OPEN

---

#### 5. 🔑 Singleton Pattern — Settings & Redis Client

```python
# app/core/config.py
@lru_cache()
def get_settings() -> Settings:
    """Parse environment only once. Avoids repeated I/O on every request."""
    return Settings()

settings = get_settings()
```

**Where**: `app/core/config.py`, `app/db/redis.py`  
**Why**: Configuration is read-once at startup and cached. Using `lru_cache` makes the singleton pattern idiomatic in Python while remaining testable (override with `get_settings.cache_clear()`).

---

#### 6. 🏗️ Dependency Injection — FastAPI DI Container

```python
# app/dependencies/auth.py
async def get_current_user(
    token: str = Depends(oauth2_scheme),
    db: AsyncSession = Depends(get_db)
) -> User:
    return await AuthService(db).verify_token(token)

# app/api/v1/endpoints/wallets.py
@router.post("/wallets")
async def create_wallet(
    request: WalletCreateRequest,
    current_user: User = Depends(get_current_user),  # DI resolves this
    db: AsyncSession = Depends(get_db),
):
    return await WalletService(db).create_wallet(current_user.id, request)
```

**Where**: `app/dependencies/`, all endpoint files  
**Why**: FastAPI's DI system provides automatic scoping (per-request DB sessions), testability (inject mocks in tests), and no global state. Each request gets its own DB session, which is automatically closed after the request completes.

---

#### 7. 🔄 Strategy Pattern — Exchange Rate Resolution

The `ExchangeRateProvider` base class implements a 3-strategy resolution:

```python
async def get_rate(self, base_currency, target_currency):
    # Strategy 1: Direct lookup
    # Strategy 2: Inverse (1/rate)  
    # Strategy 3: Cross-rate via USD
```

**Where**: `app/adapters/exchange_rate.py`  
**Why**: Any currency pair must be resolvable. The strategies are tried in order of cost/accuracy. This makes the system robust even when providers only support USD-based rates.

---

#### 8. 💌 Observer Pattern — SSE Real-Time Updates

```python
# After every commit, publish to Redis pub/sub channel
await publish_wallet_event(
    user_id=owner_id,
    event_type="credit",
    wallet_id=wallet.id,
    currency=wallet.currency,
    new_balance=wallet.balance,
    ...
)
# The SSE endpoint subscribes and pushes to the browser
```

**Frontend consumer (Observer)**:
```typescript
// frontend/src/hooks/useWalletSSE.ts
const useWalletSSE = () => {
    useEffect(() => {
        const source = new EventSource('/api/v1/events/stream');
        source.onmessage = (e) => {
            dispatch(updateWalletBalance(...));  // Update Redux state
            dispatch(prependTransaction(...));    // Add live transaction row
        };
        return () => source.close();
    }, []);
};
```

**Where**: `app/utils/events.py`, `app/api/v1/endpoints/events.py`, `frontend/src/hooks/useWalletSSE.ts`  
**Why**: SSE is simpler than WebSockets for one-directional server→client push. No upgrade protocol, works through proxies, and uses native browser EventSource. After a balance-changing commit, the event is published to Redis. The SSE endpoint's subscriber pushes it to the browser instantly — no polling needed.

---

#### 9. 🔐 Idempotency Pattern — Transfer Safety

```python
# Idempotency key prevents duplicate transfers from network retries
async def transfer(self, ..., idempotency_key: str | None = None):
    if idempotency_key:
        existing = await self.idempotency_repo.get_by_key(idempotency_key)
        if existing:
            raise DuplicateTransactionException(idempotency_key)
    # ... process transfer ...
    # Save idempotency key with response body for exact replay
    await self.idempotency_repo.create(
        key=idempotency_key, response_body=json.dumps({"transfer_id": ...})
    )
```

**Where**: `app/models/__init__.py` (IdempotencyKey model), `app/services/wallet_service.py`  
**Why**: Network retries can cause duplicate transfers. By storing the idempotency key + response, duplicate requests return the original response without re-processing. This is critical for financial operations.

---

#### 10. 🔒 Deadlock Prevention — Wallet Locking Order

```python
# Lock wallets in consistent UUID order to prevent deadlocks
id_a, id_b = sorted([request.sender_wallet_id, request.recipient_wallet_id])
locked_a = await self.wallet_repo.get_by_id_with_lock(id_a)
locked_b = await self.wallet_repo.get_by_id_with_lock(id_b)
```

**Where**: `app/services/wallet_service.py`  
**Why**: If Transaction A locks Wallet-1 then Wallet-2, while Transaction B locks Wallet-2 then Wallet-1, a deadlock occurs. Sorting UUIDs and always locking in the same order breaks the circular dependency. This is a classic solution to the "dining philosophers" problem in databases.

---

#### 11. 📬 Dead Letter Queue — Celery Task Reliability

```python
# When max retries exceeded, move to DLQ for manual ops review
except MaxRetriesExceededError:
    celery_app.send_task(
        "app.workers.tasks.dead_letter_handler",
        args=["refresh_exchange_rates_task", {}],
        queue="dead_letter",
    )
```

**Where**: `app/workers/tasks.py`  
**Why**: Celery tasks that permanently fail (after exponential backoff + max retries) must not be silently lost. The DLQ allows ops teams to inspect, fix the root cause, and replay tasks safely.

---

## 4. Frontend Architecture

### Framework: React 18 + TypeScript + Vite

```
frontend/src/
├── pages/            # Route-level page components
│   ├── LoginPage.tsx
│   ├── RegisterPage.tsx
│   └── DashboardPage.tsx
├── components/       # Reusable UI components
├── store/            # Redux Toolkit state management
│   ├── index.ts      # Store configuration
│   ├── authSlice.ts  # Auth state (user, token)
│   └── walletSlice.ts# Wallet + transaction state
├── services/         # API client (Axios)
│   └── api.ts        # All backend API calls
├── hooks/            # Custom React hooks
│   └── useWalletSSE.ts # Server-Sent Events listener
└── utils/            # Helpers (formatters, validators)
```

### State Management Pattern: Redux Toolkit (Flux)

```
User Action
    │
    ▼
Async Thunk (API Call) ──────────────────────────────────────────────┐
    │                                                                 │
    ▼                                                                 │
Redux Store (authSlice, walletSlice)                                  │
    │                                                                 │
    ▼                                                                 ▼
React Component (re-render)             SSE Event → dispatch(updateWalletBalance)
```

**Design Decisions**:
- **Redux Toolkit**: Reduces boilerplate of raw Redux. `createAsyncThunk` handles loading/error/success states automatically.
- **Optimistic SSE updates**: SSE events dispatch `updateWalletBalance` and `prependTransaction` actions directly to Redux, giving instant UI feedback without a second API call.
- **Typed API client**: Axios instance with TypeScript interfaces ensures compile-time safety on API response shapes.

---

## 5. Database Design

### Entity Relationship Overview

```
users (1) ──────── (N) wallets (1) ──────────── (N) transactions
   │                      │
   └── (N) refresh_tokens  └── sender/recipient of (N) transfers
   └── (N) audit_logs
                          
exchange_rates (independent lookup table)
idempotency_keys (per-user deduplication store)
```

### Key Design Decisions

| Decision | What | Why |
|----------|------|-----|
| **UUID Primary Keys** | All tables use UUID v4 | Non-sequential — prevents ID enumeration attacks. Globally unique across shards. |
| **Numeric(18, 8)** | Balance and amount columns | Avoids floating-point precision errors. 8 decimal places supports crypto. |
| **Composite UniqueConstraint** | `(owner_id, currency)` on wallets | Enforces one wallet per currency per user at the DB level. |
| **Soft enums** | `native_enum=False` on Enum columns | Allows adding new enum values without DB migrations. |
| **Indexed foreign keys** | All FK columns have explicit indexes | Prevents full table scans on join queries. |
| **Immutable Audit Logs** | AuditLog model — no update/delete | Compliance requirement. The code comment explicitly forbids mutations. |
| **TimestampMixin** | `created_at`, `updated_at` on all models | Automatic timestamps via SQLAlchemy event hooks. |

### Alembic Migrations

All schema changes are managed through Alembic:
- `backend/alembic/` — migration scripts
- `backend/alembic.ini` — connection config
- Auto-generated revision chain ensures reproducible schema across environments

---

## 6. Infrastructure & DevOps

### Docker Compose Services

```
docker-compose.yml
├── postgres:16-alpine       — Primary database (port 5432)
├── redis:7-alpine           — Cache + Pub/Sub + Celery broker (port 6379)
├── backend (FastAPI)        — ASGI app via Uvicorn (port 8000)
├── celery_worker            — Background task executor
├── celery_beat              — Cron scheduler (exchange rate refresh hourly)
├── flower:2.0               — Celery monitoring UI (port 5555)
└── frontend (Nginx)         — Pre-built React SPA (port 3000 → 80)
```

### Service Health Checks

Every service has explicit health checks to ensure `depends_on` conditions are met:

| Service | Health Check |
|---------|-------------|
| postgres | `pg_isready` command |
| redis | `redis-cli ping` |
| backend | `GET /api/v1/health` |
| frontend | HTTP request to Nginx |

### Startup Strategy

The frontend is **pre-built on the host** (`npm run build`) and the resulting `dist/` folder is copied into the Nginx Docker image. This avoids npm network issues inside Docker containers and produces a clean, immutable image.

### CI/CD — GitHub Actions

```
.github/
└── workflows/
    └── ci.yml
        ├── Lint & Format (ruff, black)
        ├── Type Check (mypy)
        ├── Unit Tests (pytest)
        ├── Integration Tests
        └── Docker Build Validation
```

---

## 7. Security Architecture

### Authentication Flow

```
Client                           Backend
  │                                │
  ├── POST /auth/signup ──────────▶│  Hash password (bcrypt)
  │                                │  Create user + default USD wallet
  │◀── {access_token, refresh_token}
  │
  ├── POST /auth/login ───────────▶│  Verify bcrypt hash
  │                                │  Generate JWT (30min) + Refresh (7days)
  │                                │  Store hashed refresh token in DB
  │◀── {access_token, refresh_token}
  │
  ├── GET /api/v1/wallets ────────▶│  Validate JWT signature + expiry
  │   Authorization: Bearer <jwt>  │  Extract user_id from claims
  │◀── wallet data                 │
  │
  ├── POST /auth/refresh ─────────▶│  Validate refresh token hash
  │   {refresh_token}              │  Rotate: revoke old, issue new pair
  │◀── {new access_token, ...}     │
```

### Security Controls

| Control | Implementation |
|---------|---------------|
| **Password Hashing** | bcrypt via `passlib` — salted, slow by design |
| **JWT Tokens** | HS256 algorithm, 30-min access + 7-day refresh |
| **Refresh Token Rotation** | Tokens stored as SHA-256 hashes, revoked on use |
| **Rate Limiting** | Redis-backed: 5/min login, 3/min signup, 60/min default |
| **CORS** | Strict allowlist of allowed origins |
| **Input Validation** | Pydantic schemas on all endpoints — auto 422 on invalid input |
| **No Stack Trace Leaks** | ExceptionMiddleware catches all errors, returns structured JSON |
| **Swagger Disabled in Prod** | `docs_url=None` when `DEBUG=False` |
| **Idempotency** | Transfer deduplication prevents double-spend via network retry |
| **Audit Trail** | All sensitive ops written to immutable `audit_logs` table |

---

## 8. Real-Time Architecture (SSE)

```
Browser                 FastAPI               Redis
   │                      │                    │
   ├──GET /events/stream──▶│  Subscribe to      │
   │  (SSE connection)     │  channel:user:{id}─▶
   │                       │                    │
   │            ... user credits a wallet ...   │
   │                       │                    │
   │              WalletService.credit()        │
   │              → DB commit                   │
   │              → publish_wallet_event()──────▶ PUBLISH channel:user:{id}
   │                       │                    │
   │                       │◀──── PUSH event ───│
   │◀── SSE: data: {...} ──│                    │
   │                       │                    │
   │  Redux dispatch:       │                    │
   │  updateWalletBalance() │                    │
   │  prependTransaction()  │                    │
```

**Why SSE over WebSockets?**
- SSE is simpler — native `EventSource` browser API, no upgrade handshake
- Works transparently through HTTP proxies and load balancers
- One-directional (server → client) which is all we need for balance updates
- Automatic reconnect is built into the browser spec

---

## 9. Async / Background Processing

### Celery Task Pipeline

```
Celery Beat (Scheduler)
    │
    │  Every hour
    ▼
refresh_exchange_rates_task
    │
    ├── Fetch rates from provider (OpenExchange/Fixer/Mock)
    │       │
    │       ├── Success → Update exchange_rates table → Cache in Redis
    │       │
    │       └── Failure → Retry with exponential backoff (60s, 120s, 240s)
    │                    Max 3 retries → Dead Letter Queue
    │
audit_log_task (fire-and-forget)
    │
    └── Write AuditLog row asynchronously — off the critical API path
    
send_notification_task
    └── Email/push notifications — decoupled from API response
```

### Why Celery + Redis?

| Alternative | Trade-off |
|-------------|-----------|
| Celery + Redis | Simple, battle-tested, good visibility via Flower |
| APScheduler (in-process) | Single-instance only — can't scale horizontally |
| Celery + RabbitMQ | Better message guarantees, but more complex infra |
| AWS SQS + Lambda | Vendor lock-in; adds cost complexity |

---

## 10. Scalability Design Note

> **Assumed scale**: 500k users, 20k DAU, 100 TPS, exchange provider downtime

### Scaling Approach

#### Horizontal API Scaling
- FastAPI is stateless (JWT-based auth, Redis for shared state)
- Run N replicas behind a load balancer (Nginx upstream / AWS ALB)
- Circuit breaker state is in Redis — shared across all replicas

#### Database Strategy
| Technique | Detail |
|-----------|--------|
| **Read Replicas** | Route read-heavy queries (transaction history, wallet listing) to replicas |
| **Connection Pooling** | PgBouncer in front of PostgreSQL — pools connections from N app instances |
| **Partitioning** | Partition `transactions` table by `created_at` (range) or `wallet_id` (hash) |
| **Archival** | Move transactions older than 1 year to a cold storage / data warehouse |

#### Caching Strategy
| Cache | TTL | Content |
|-------|-----|---------|
| Exchange rates | 1 hour | Cached per currency pair — reduces provider calls 99% |
| User profile | 5 min | Reduces user lookups on authenticated routes |
| Redis pub/sub | N/A | SSE channel per user — lightweight, no polling |

#### Async Processing
- All non-critical work (audit logs, notifications, rate refresh) goes to Celery
- API responses return in <50ms; background tasks run asynchronously
- Dead-letter queue ensures permanent failures are inspectable and replayable

#### Exchange Provider Downtime
1. Circuit breaker trips after 5 consecutive failures
2. Fallback: serve cached rates from Redis (up to 1hr stale)
3. Celery Beat keeps retrying rate refresh with exponential backoff
4. When provider recovers, Celery refreshes cache; circuit resets on next half-open probe

#### Cost Optimisation
- Redis `allkeys-lru` eviction (256MB cap) — no cache management overhead
- Exchange rates cached in Redis + DB — single provider call per hour for all users
- Async Celery tasks keep API instances free for user-facing requests
- Nginx serves static frontend — no Python involved for asset delivery

#### Operational Considerations
- **Health checks** on all services; Docker Compose restarts on failure
- **Structured logging** (structlog) with `request_id` + `user_id` in every log line
- **Prometheus metrics** endpoint for scraping (`/metrics`)
- **Flower** dashboard for real-time Celery worker visibility
- **4XX/5XX detection**: ExceptionMiddleware logs every response with status code. Feed to ELK/Datadog; alert if `5XX rate > 1%` or `4XX rate > 10%` over 5-minute window

---

## 11. Error Handling Strategy

### Layered Error Handling

```
Exception Hierarchy:
AppException (base)
├── AuthenticationException     → 401
├── AuthorizationException      → 403
├── NotFoundException           → 404
├── ConflictException           → 409
├── DuplicateTransactionException → 409
├── InsufficientFundsException  → 422
├── WalletSuspendedException    → 422
├── ValidationException         → 422
├── RateLimitException          → 429
└── CircuitOpenException        → 503
```

### Response Envelope

All errors return a consistent structure:
```json
{
  "success": false,
  "error": {
    "code": "INSUFFICIENT_FUNDS",
    "message": "Balance 50.00 USD is less than requested 100.00 USD"
  }
}
```

### Where Errors Are Handled

| Location | Responsibility |
|----------|---------------|
| Pydantic schemas | Input validation (types, ranges, required fields) |
| Service layer | Domain rule violations (insufficient funds, wallet suspended) |
| ExceptionMiddleware | Maps domain exceptions → HTTP status codes |
| RequestValidationError handler | Pydantic 422 → structured field errors |
| Unhandled Exception catch-all | Returns 500 without leaking stack traces |

---

## 12. Key Architectural Decisions & Trade-offs

| Decision | Chosen | Alternative | Why |
|----------|--------|-------------|-----|
| **ASGI Framework** | FastAPI | Flask, Django | Native async, auto Swagger, Pydantic validation |
| **ORM** | SQLAlchemy 2.0 async | Django ORM, Tortoise | Best async support, familiar, fine-grained control |
| **Database** | PostgreSQL | MySQL, MongoDB | ACID transactions essential for financial data |
| **Cache/Broker** | Redis | Memcached, RabbitMQ | Pub/Sub for SSE + Celery broker in one service |
| **Background Tasks** | Celery | asyncio tasks | Persistent, retryable, horizontally scalable |
| **Real-time** | SSE | WebSocket | Simpler, sufficient for server→client push |
| **Auth** | JWT + Refresh Rotation | Sessions | Stateless API, mobile-friendly |
| **Migrations** | Alembic | Django migrations | Decoupled from app code, version controlled |
| **Frontend** | React + Vite + Redux | Next.js, Vue | Fast HMR, TypeScript, predictable state |
| **Decimal Precision** | Numeric(18, 8) | Float | Financial accuracy — no IEEE 754 errors |
| **Locking** | Pessimistic (SELECT FOR UPDATE) | Optimistic (version) | Simpler retry logic for financial transactions |

---

*Document generated: 2026-07-12 | Version: 1.0.0*
