# 🏦 Multi-Currency Wallet Platform — Architecture Diagrams

> All diagrams are written in Mermaid syntax. Render with any Mermaid-compatible viewer (GitHub, VS Code Mermaid plugin, mermaid.live).

---

## Diagram 1: High-Level System Architecture

```mermaid
graph TB
    subgraph CLIENT["🖥️ Client Layer"]
        BROWSER["Browser\nReact + TypeScript SPA"]
        SSE_HOOK["useWalletSSE Hook\nServer-Sent Events"]
        REDUX["Redux Toolkit Store\nauthSlice · walletSlice"]
    end

    subgraph GATEWAY["🌐 Gateway Layer"]
        NGINX["Nginx\nReverse Proxy + Static Files"]
    end

    subgraph APP["⚙️ Application Layer — FastAPI"]
        direction TB
        MIDDLEWARE["Middleware Stack\nCORS → Exception → RateLimit"]
        API["API Routers v1\nauth · wallets · exchange · events · health"]
        SERVICES["Service Layer\nAuthService · WalletService · ExchangeRateService"]
        REPOS["Repository Layer\nUserRepo · WalletRepo · ExchangeRateRepo"]
    end

    subgraph WORKERS["🔄 Background Workers"]
        CELERY_WORKER["Celery Worker\ndefault + dead_letter queues"]
        CELERY_BEAT["Celery Beat\nCron Scheduler"]
        FLOWER["Flower\nTask Monitor :5555"]
    end

    subgraph DATA["🗄️ Data Layer"]
        POSTGRES[("PostgreSQL 16\nPrimary Store")]
        REDIS_CACHE[("Redis DB0\nCache + SSE Pub/Sub")]
        REDIS_BROKER[("Redis DB1\nCelery Broker")]
        REDIS_RESULTS[("Redis DB2\nCelery Results")]
    end

    subgraph EXTERNAL["🌍 External Services"]
        OPEN_EXCHANGE["OpenExchangeRates API"]
        FIXER["Fixer.io API"]
    end

    BROWSER -->|"HTTP/SSE"| NGINX
    NGINX -->|"proxy_pass :8000"| MIDDLEWARE
    MIDDLEWARE --> API
    API --> SERVICES
    SERVICES --> REPOS
    REPOS --> POSTGRES

    SERVICES -->|"publish event"| REDIS_CACHE
    REDIS_CACHE -->|"SSE push"| NGINX
    NGINX -->|"EventSource stream"| SSE_HOOK
    SSE_HOOK --> REDUX
    REDUX --> BROWSER

    CELERY_BEAT -->|"schedule"| CELERY_WORKER
    CELERY_WORKER -->|"fetch rates"| OPEN_EXCHANGE
    CELERY_WORKER -->|"fallback"| FIXER
    CELERY_WORKER --> POSTGRES
    CELERY_WORKER --> REDIS_BROKER
    CELERY_WORKER --> REDIS_RESULTS
    SERVICES -->|"enqueue tasks"| REDIS_BROKER

    SERVICES -->|"circuit breaker"| REDIS_CACHE
```

---

## Diagram 2: Layered / Clean Architecture

```mermaid
graph TB
    subgraph PRESENTATION["Presentation Layer — app/api/v1/endpoints/"]
        AUTH_EP["auth.py\nPOST /auth/signup\nPOST /auth/login\nPOST /auth/refresh"]
        WALLET_EP["wallets.py\nGET/POST /wallets\nPOST /wallets/transfer\nGET /wallets/{id}/transactions"]
        EXCHANGE_EP["exchange_rates.py\nGET /exchange-rates"]
        EVENTS_EP["events.py\nGET /events/stream"]
        HEALTH_EP["health.py\nGET /health"]
    end

    subgraph SERVICE["Service Layer — app/services/"]
        AUTH_SVC["AuthService\n• signup / login\n• JWT generation\n• token refresh & rotation"]
        WALLET_SVC["WalletService\n• create wallet\n• credit / debit\n• transfer (atomic)\n• transaction history"]
        EXCHANGE_SVC["ExchangeRateService\n• get_rate()\n• refresh_all_rates()\n• cross-rate calculation"]
    end

    subgraph REPOSITORY["Repository Layer — app/repositories/"]
        USER_REPO["UserRepository\n• get_by_email()\n• create()"]
        WALLET_REPO["WalletRepository\n• get_by_id_with_lock() ← SELECT FOR UPDATE\n• update_balance()"]
        TXN_REPO["TransactionRepository\n• create_transaction()\n• get_wallet_transactions()"]
        RATE_REPO["ExchangeRateRepository\n• upsert_rate()\n• get_rate()"]
        IDEMPOTENCY_REPO["IdempotencyRepository\n• get_by_key()\n• create()"]
    end

    subgraph MODEL["Domain / Model Layer — app/models/"]
        USER_MODEL["User\nemail · hashed_password\ndefault_currency · role"]
        WALLET_MODEL["Wallet\nowner_id · currency\nbalance (Numeric 18,8)\nstatus"]
        TXN_MODEL["Transaction\nwallet_id · type · amount\nbalance_before · balance_after\nreference · metadata_json"]
        TRANSFER_MODEL["Transfer\nsender_wallet_id\nrecipient_wallet_id\nexchange_rate · converted_amount\nidempotency_key"]
        RATE_MODEL["ExchangeRate\nbase_currency · target_currency\nrate · provider"]
        AUDIT_MODEL["AuditLog\naction · resource_type\nip_address · details"]
        IDEMPOTENCY_MODEL["IdempotencyKey\nkey · user_id · request_path\nresponse_status · response_body"]
    end

    PRESENTATION --> SERVICE
    SERVICE --> REPOSITORY
    REPOSITORY --> MODEL

    style PRESENTATION fill:#1a365d,color:#fff
    style SERVICE fill:#2d6a4f,color:#fff
    style REPOSITORY fill:#7b2d00,color:#fff
    style MODEL fill:#3d1a6e,color:#fff
```

---

## Diagram 3: Design Patterns Map

```mermaid
mindmap
  root((Design Patterns))
    Creational
      Factory Pattern
        create_application() in main.py
        Testable app instances
        No module-level side effects
      Singleton Pattern
        lru_cache on get_settings()
        Redis client singleton
        Parse env once at startup
    Structural
      Repository Pattern
        BaseRepository generic class
        WalletRepository
        UserRepository
        ExchangeRateRepository
        Decouples SQL from business logic
      Adapter Pattern
        ExchangeRateProvider ABC
        OpenExchangeAdapter
        FixerAdapter
        MockExchangeAdapter
        Swap providers with zero service changes
    Behavioral
      Circuit Breaker
        Redis-backed shared state
        CLOSED → OPEN → HALF-OPEN → CLOSED
        Fail fast on provider downtime
      Strategy Pattern
        Exchange rate resolution
        Direct → Inverse → Cross-via-USD
      Observer Pattern
        Redis Pub/Sub
        SSE endpoint subscribes
        Browser EventSource receives
        Redux dispatches updates
      Idempotency Pattern
        Transfer deduplication
        IdempotencyKey model
        Exact response replay
    Concurrency
      Pessimistic Locking
        SELECT FOR UPDATE on wallets
        Sorted UUID lock order
        Deadlock prevention
      Deadlock Prevention
        Lock lower UUID first always
        Consistent lock ordering
      Dead Letter Queue
        MaxRetriesExceeded handler
        Ops inspection and replay
```

---

## Diagram 4: Database Entity Relationship Diagram

```mermaid
erDiagram
    users {
        UUID id PK
        string email UK
        string hashed_password
        string first_name
        string last_name
        string profile_image_url
        string default_currency
        boolean is_active
        boolean is_verified
        string role
        timestamp created_at
        timestamp updated_at
    }

    refresh_tokens {
        UUID id PK
        UUID user_id FK
        string token_hash UK
        string expires_at
        boolean revoked
        timestamp created_at
    }

    wallets {
        UUID id PK
        UUID owner_id FK
        string currency
        Numeric_18_8 balance
        string status
        string label
        timestamp created_at
        timestamp updated_at
    }

    transactions {
        UUID id PK
        UUID wallet_id FK
        string transaction_type
        Numeric_18_8 amount
        string currency
        Numeric_18_8 balance_before
        Numeric_18_8 balance_after
        string status
        string reference
        text description
        text metadata_json
        timestamp created_at
    }

    transfers {
        UUID id PK
        UUID sender_wallet_id FK
        UUID recipient_wallet_id FK
        Numeric_18_8 amount
        string currency
        Numeric_18_8 exchange_rate
        Numeric_18_8 converted_amount
        string status
        string idempotency_key UK
        text note
        timestamp created_at
    }

    exchange_rates {
        UUID id PK
        string base_currency
        string target_currency
        Numeric_18_8 rate
        string provider
        timestamp created_at
        timestamp updated_at
    }

    idempotency_keys {
        UUID id PK
        string key UK
        UUID user_id FK
        string request_path
        int response_status
        text response_body
        timestamp created_at
    }

    audit_logs {
        UUID id PK
        UUID user_id FK
        string action
        string resource_type
        string resource_id
        string ip_address
        string user_agent
        text details
        timestamp created_at
    }

    users ||--o{ refresh_tokens : "has"
    users ||--o{ wallets : "owns"
    users ||--o{ audit_logs : "generates"
    users ||--o{ idempotency_keys : "owns"
    wallets ||--o{ transactions : "has"
    wallets ||--o{ transfers : "sends"
    wallets ||--o{ transfers : "receives"
```

---

## Diagram 5: Authentication & Token Flow

```mermaid
sequenceDiagram
    actor User
    participant Frontend as React Frontend
    participant API as FastAPI Backend
    participant DB as PostgreSQL
    participant Redis

    Note over User, Redis: Registration Flow
    User->>Frontend: Fill signup form
    Frontend->>API: POST /auth/signup {email, password, ...}
    API->>API: Hash password (bcrypt)
    API->>DB: INSERT users row
    API->>DB: INSERT wallets (default USD wallet)
    API-->>Frontend: {access_token, refresh_token, user}
    Frontend->>Frontend: Store tokens in memory / localStorage

    Note over User, Redis: Login Flow
    User->>Frontend: Enter credentials
    Frontend->>API: POST /auth/login {email, password}
    API->>DB: SELECT user WHERE email = ?
    API->>API: Verify bcrypt hash
    API->>DB: INSERT refresh_tokens (store hash)
    API-->>Frontend: {access_token (30min), refresh_token (7days)}

    Note over User, Redis: Authenticated Request
    User->>Frontend: View wallets
    Frontend->>API: GET /wallets (Bearer <access_token>)
    API->>API: Verify JWT signature + expiry
    API->>DB: Fetch wallets for user
    API-->>Frontend: [{wallet data}]

    Note over User, Redis: Token Refresh
    Frontend->>API: POST /auth/refresh {refresh_token}
    API->>DB: Find token by hash
    API->>DB: Revoke old token (revoked=true)
    API->>DB: INSERT new refresh_token
    API-->>Frontend: {new_access_token, new_refresh_token}
```

---

## Diagram 6: Transfer / Payment Flow

```mermaid
sequenceDiagram
    actor Sender
    participant API as WalletService
    participant IdempotencyRepo as IdempotencyRepository
    participant WalletRepo as WalletRepository
    participant ExchangeSvc as ExchangeRateService
    participant TxnRepo as TransactionRepository
    participant DB as PostgreSQL
    participant Redis

    Sender->>API: POST /wallets/transfer\n{sender_wallet_id, recipient_wallet_id, amount}\nIdempotency-Key: uuid

    API->>IdempotencyRepo: Check if key already exists
    IdempotencyRepo-->>API: None (not duplicate)

    API->>WalletRepo: get_by_id(sender_wallet_id) — read-only check
    WalletRepo-->>API: sender wallet (verify ownership)

    API->>WalletRepo: get_by_id(recipient_wallet_id) — read-only check
    WalletRepo-->>API: recipient wallet

    Note over API: Different currencies?
    API->>ExchangeSvc: get_rate(sender_currency, recipient_currency)
    ExchangeSvc-->>API: exchange_rate (from cache or provider)

    Note over API,DB: Lock both wallets — deadlock prevention via sorted UUID order
    API->>WalletRepo: get_by_id_with_lock(lower_uuid) ← SELECT FOR UPDATE
    API->>WalletRepo: get_by_id_with_lock(higher_uuid) ← SELECT FOR UPDATE

    API->>API: Check sender.balance >= amount
    API->>WalletRepo: update_balance(sender, sender - amount)
    API->>WalletRepo: update_balance(recipient, recipient + converted_amount)

    API->>TxnRepo: create_transaction(sender_wallet, TRANSFER, debit)
    API->>TxnRepo: create_transaction(recipient_wallet, TRANSFER, credit)

    API->>DB: INSERT transfer record
    API->>IdempotencyRepo: Save idempotency key + response

    API->>DB: COMMIT (atomic — all or nothing)

    API->>Redis: PUBLISH wallet_update to sender channel
    API->>Redis: PUBLISH wallet_update to recipient channel

    API-->>Sender: 201 {transfer_id, exchange_rate, converted_amount}
```

---

## Diagram 7: Circuit Breaker State Machine

```mermaid
stateDiagram-v2
    [*] --> CLOSED : App starts

    CLOSED --> CLOSED : Request succeeds
    CLOSED --> OPEN : Failure count >= threshold (5)\nStore opened_at in Redis

    OPEN --> OPEN : Request arrives\nFail immediately (CircuitOpenException)\nReturn cached rates from Redis

    OPEN --> HALF_OPEN : recovery_timeout elapsed (60s)\nAllow one probe request

    HALF_OPEN --> CLOSED : Probe succeeds\nClear failure count in Redis\nResume normal operation

    HALF_OPEN --> OPEN : Probe fails\nReset opened_at timer\nBack to fast-fail mode

    note right of OPEN
        All replicas share state
        via Redis keys:
        circuit_breaker:name:state
        circuit_breaker:name:failures
        circuit_breaker:name:opened_at
    end note
```

---

## Diagram 8: Real-Time SSE Architecture

```mermaid
sequenceDiagram
    participant Browser as React Browser
    participant Nginx as Nginx Proxy
    participant FastAPI as FastAPI /events/stream
    participant Redis as Redis Pub/Sub
    participant WalletSvc as WalletService

    Note over Browser, WalletSvc: Connection Setup
    Browser->>Nginx: GET /api/v1/events/stream\nAccept: text/event-stream
    Nginx->>FastAPI: Proxy SSE request
    FastAPI->>Redis: SUBSCRIBE channel:user:{user_id}
    FastAPI-->>Browser: HTTP 200 (keep-alive stream open)

    Note over Browser, WalletSvc: Balance Change Triggers Update
    Browser->>FastAPI: POST /wallets/{id}/credit {amount}
    FastAPI->>WalletSvc: credit_wallet()
    WalletSvc->>WalletSvc: Update DB balance
    WalletSvc->>WalletSvc: COMMIT transaction
    WalletSvc->>Redis: PUBLISH channel:user:{user_id}\n{event_type:credit, new_balance, wallet_id}

    Redis->>FastAPI: Push message (SSE subscriber)
    FastAPI->>Nginx: data: {"event":"wallet_update",...}\n\n
    Nginx->>Browser: SSE event arrives

    Browser->>Browser: dispatch(updateWalletBalance)\n→ Wallet card re-renders instantly
    Browser->>Browser: dispatch(prependTransaction)\n→ New row appears at top of table
```

---

## Diagram 9: Docker Infrastructure

```mermaid
graph TB
    subgraph DOCKER["Docker Compose Network"]
        subgraph FRONTEND_BOX["Frontend Container"]
            NGINX_SVC["Nginx :80\n• Serve dist/ SPA\n• proxy_pass /api → backend:8000\n• proxy_pass /static → backend:8000"]
        end

        subgraph BACKEND_BOX["Backend Container"]
            UVICORN["Uvicorn ASGI\n:8000\nFastAPI app"]
        end

        subgraph WORKER_BOX["Worker Containers"]
            CELERY_W["Celery Worker\nqueues: default, dead_letter\nconcurrency: 2"]
            CELERY_B["Celery Beat\nExchange rate refresh: hourly\nSchedule: celerybeat-schedule"]
            FLOWER_SVC["Flower :5555\nTask monitoring dashboard"]
        end

        subgraph DATA_BOX["Data Containers"]
            POSTGRES_SVC[("PostgreSQL :5432\nwallet_db\nVolume: postgres_data")]
            REDIS_SVC[("Redis :6379\nDB0: cache + pub/sub\nDB1: celery broker\nDB2: celery results\nmaxmemory: 256mb LRU")]
        end
    end

    INTERNET["🌐 Internet"] --> NGINX_SVC
    NGINX_SVC --> UVICORN
    UVICORN --> POSTGRES_SVC
    UVICORN --> REDIS_SVC
    CELERY_W --> POSTGRES_SVC
    CELERY_W --> REDIS_SVC
    CELERY_B --> REDIS_SVC
    CELERY_B --> CELERY_W
    FLOWER_SVC --> REDIS_SVC

    HEALTH1{{"✅ pg_isready"}} -.-> POSTGRES_SVC
    HEALTH2{{"✅ redis-cli ping"}} -.-> REDIS_SVC
    HEALTH3{{"✅ GET /api/v1/health"}} -.-> UVICORN
```

---

## Diagram 10: Async Task Pipeline (Celery)

```mermaid
flowchart TD
    subgraph TRIGGERS["Trigger Sources"]
        BEAT["⏰ Celery Beat\nHourly cron"]
        API_TRG["🔗 API Request\nCompletes operation"]
    end

    subgraph QUEUE["Redis Broker"]
        DEFAULT_Q["📥 default queue"]
        DLQ["☠️ dead_letter queue"]
    end

    subgraph TASKS["Celery Tasks"]
        RATE_TASK["refresh_exchange_rates_task\nmax_retries=3\nexponential backoff\njitter enabled"]
        AUDIT_TASK["audit_log_task\nmax_retries=3\nWrite AuditLog async"]
        NOTIFY_TASK["send_notification_task\nmax_retries=5\nEmail/Push/SMS"]
        DL_HANDLER["dead_letter_handler\nAlert ops team\nStore for replay"]
    end

    subgraph OUTCOMES["Outcomes"]
        SUCCESS["✅ Update exchange_rates table\nRefresh Redis cache"]
        RETRY["🔄 Retry with backoff\n60s → 120s → 240s"]
        DL_STORE["🗄️ Store in dead_letter_jobs\nAlert on-call"]
    end

    BEAT --> DEFAULT_Q
    API_TRG --> DEFAULT_Q

    DEFAULT_Q --> RATE_TASK
    DEFAULT_Q --> AUDIT_TASK
    DEFAULT_Q --> NOTIFY_TASK
    DLQ --> DL_HANDLER

    RATE_TASK -->|"Provider responds OK"| SUCCESS
    RATE_TASK -->|"Provider fails"| RETRY
    RETRY -->|"< max_retries"| RATE_TASK
    RETRY -->|"MaxRetriesExceeded"| DLQ
    DL_HANDLER --> DL_STORE

    style DLQ fill:#7b0000,color:#fff
    style DL_HANDLER fill:#7b0000,color:#fff
    style DL_STORE fill:#7b0000,color:#fff
    style SUCCESS fill:#1a5c2a,color:#fff
```

---

## Diagram 11: Middleware Execution Order

```mermaid
flowchart LR
    REQ["Incoming\nHTTP Request"]

    subgraph MIDDLEWARE_STACK["FastAPI Middleware Stack\n(outermost → innermost)"]
        direction LR
        CORS["CORSMiddleware\n• Validate Origin header\n• Add CORS headers\n• Handle preflight OPTIONS"]
        EXC["ExceptionMiddleware\n• Inject request_id\n• Start timer\n• Catch all exceptions\n• Map to JSON error responses\n• Log duration + status"]
        RATE["RateLimitMiddleware\n• Check Redis counter\n• Enforce per-route limits\n• login: 5/min\n• signup: 3/min\n• default: 60/min"]
        ROUTE["FastAPI Router\n• Dependency injection\n• Pydantic validation\n• Endpoint handler"]
    end

    RESP["HTTP\nResponse"]

    REQ --> CORS --> EXC --> RATE --> ROUTE
    ROUTE --> RATE --> EXC --> CORS --> RESP

    style EXC fill:#1a3a5c,color:#fff
    style RATE fill:#3d1a00,color:#fff
    style CORS fill:#1a3d00,color:#fff
    style ROUTE fill:#2d0050,color:#fff
```

---

## Diagram 12: Scalability Architecture (Design Note — 500k Users / 100 TPS)

```mermaid
graph TB
    subgraph INTERNET_LAYER["🌐 Internet"]
        USERS["500k Users\n20k DAU\n100 TPS"]
        CDN["CDN\nStatic Assets"]
    end

    subgraph LOAD_BALANCER["⚖️ Load Balancer (AWS ALB / Nginx)"]
        ALB["Application Load Balancer\nSSL Termination\nHealth checks"]
    end

    subgraph APP_TIER["⚙️ Application Tier (Stateless — N replicas)"]
        API1["FastAPI Instance 1"]
        API2["FastAPI Instance 2"]
        API3["FastAPI Instance N"]
    end

    subgraph CACHE_TIER["⚡ Cache Tier"]
        REDIS_CLUSTER["Redis Cluster\n• Exchange rates (1hr TTL)\n• User profiles (5min TTL)\n• Session / rate limit counters\n• SSE Pub/Sub channels\n• Circuit breaker state"]
    end

    subgraph WORKER_TIER["🔄 Worker Tier"]
        CELERY_POOL["Celery Worker Pool\n(auto-scaled by queue depth)"]
    end

    subgraph DB_TIER["🗄️ Database Tier"]
        PGBOUNCER["PgBouncer\nConnection Pooler"]
        PG_PRIMARY[("PostgreSQL Primary\nWrite operations")]
        PG_REPLICA1[("Read Replica 1\nTransaction history")]
        PG_REPLICA2[("Read Replica 2\nWallet reads")]
        subgraph ARCHIVAL["Archival"]
            DATA_WAREHOUSE["Data Warehouse\nTransactions > 1yr"]
        end
    end

    subgraph MONITORING["📊 Observability"]
        PROMETHEUS["Prometheus\nMetrics scrape"]
        GRAFANA["Grafana\nDashboards + Alerts"]
        ELK["ELK Stack\nStructured logs (structlog)"]
        FLOWER_SCALE["Flower\nCelery visibility"]
    end

    USERS --> CDN
    USERS --> ALB
    ALB --> API1 & API2 & API3
    API1 & API2 & API3 --> REDIS_CLUSTER
    API1 & API2 & API3 --> PGBOUNCER
    API1 & API2 & API3 --> CELERY_POOL
    PGBOUNCER --> PG_PRIMARY
    PG_PRIMARY -->|"replication"| PG_REPLICA1 & PG_REPLICA2
    CELERY_POOL --> PG_PRIMARY
    PG_PRIMARY -->|"archive job"| DATA_WAREHOUSE

    API1 & API2 & API3 --> PROMETHEUS
    CELERY_POOL --> FLOWER_SCALE
    PROMETHEUS --> GRAFANA
    API1 & API2 & API3 --> ELK

    style PG_PRIMARY fill:#1a365d,color:#fff
    style REDIS_CLUSTER fill:#7b0000,color:#fff
    style ALB fill:#1a5c2a,color:#fff
```

---

*Diagrams version: 1.0.0 | Generated: 2026-07-12*  
*Render with: [mermaid.live](https://mermaid.live) | GitHub markdown | VS Code Mermaid Preview extension*
