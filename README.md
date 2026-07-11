# Multi-Currency Wallet Platform

A production-ready fintech backend built with FastAPI, PostgreSQL, Redis, and Celery — demonstrating clean architecture, SOLID principles, and enterprise-grade engineering patterns.

---

## Quick Start

```bash
# 1. Clone the repo
git clone <repo-url>
cd "Green wheels"

# 2. Copy environment file
cp .env.example .env

# 3. Start everything
docker compose up --build

# 4. API is available at http://localhost:8000
# 5. Swagger docs at http://localhost:8000/docs (DEBUG=true only)
# 6. Celery Flower at http://localhost:5555
```

That's it. No local Python, PostgreSQL, or Redis installation required.

---

## Architecture Overview

```
Request → Nginx → FastAPI → Middleware → Router → Service → Repository → PostgreSQL
                                                      ↓
                                                    Redis (cache)
                                                      ↓
                                                 Celery (async jobs)
```

Layers have strict responsibilities:
- **API layer** — validates input, calls services, returns responses
- **Service layer** — all business logic lives here
- **Repository layer** — all database access lives here
- **Adapter layer** — external service abstraction (exchange rate providers)
- **Workers** — Celery async task processing

---

## API Endpoints

### Authentication
| Method | Endpoint | Description |
|--------|----------|-------------|
| POST | `/api/v1/auth/register` | Register new user |
| POST | `/api/v1/auth/login` | Login, receive JWT tokens |
| POST | `/api/v1/auth/refresh` | Refresh access token |
| POST | `/api/v1/auth/logout` | Revoke refresh token |

### User Profile
| Method | Endpoint | Description |
|--------|----------|-------------|
| GET | `/api/v1/users/me` | Get profile |
| PATCH | `/api/v1/users/me` | Update profile |
| POST | `/api/v1/users/me/avatar` | Upload profile image |

### Wallets
| Method | Endpoint | Description |
|--------|----------|-------------|
| POST | `/api/v1/wallets` | Create wallet |
| GET | `/api/v1/wallets` | List user wallets |
| POST | `/api/v1/wallets/{id}/credit` | Add funds |
| POST | `/api/v1/wallets/{id}/debit` | Withdraw funds |
| POST | `/api/v1/wallets/transfer` | Transfer to another user |
| GET | `/api/v1/wallets/{id}/transactions` | Paginated history |

### Exchange Rates
| Method | Endpoint | Description |
|--------|----------|-------------|
| GET | `/api/v1/exchange-rates?base=USD` | All rates for base currency |
| GET | `/api/v1/exchange-rates/{base}/{target}` | Specific pair |
| POST | `/api/v1/exchange-rates/refresh` | Trigger refresh (admin) |

### Health
| Method | Endpoint | Description |
|--------|----------|-------------|
| GET | `/api/v1/health` | Liveness check |
| GET | `/api/v1/ready` | Readiness check (DB + Redis) |
| GET | `/api/v1/live` | Kubernetes liveness alias |

---

## Idempotency

Include the `Idempotency-Key` header on transfer requests to prevent duplicate processing:

```bash
curl -X POST /api/v1/wallets/transfer \
  -H "Idempotency-Key: unique-client-generated-key-123" \
  -H "Authorization: Bearer <token>" \
  -d '{"recipient_wallet_id": "...", "amount": "50.00"}'
```

Duplicate requests with the same key return the original response without reprocessing.

---

## Environment Variables

See `.env.example` for all available variables. Key ones:

| Variable | Description |
|----------|-------------|
| `DATABASE_URL` | PostgreSQL async connection string |
| `REDIS_URL` | Redis connection string |
| `JWT_SECRET_KEY` | Secret for signing JWTs — **must be changed in production** |
| `EXCHANGE_RATE_PROVIDER` | `mock`, `open_exchange`, or `fixer` |
| `OPEN_EXCHANGE_APP_ID` | API key for openexchangerates.org |

---

## Running Tests

```bash
# Unit tests only (no external services needed)
pytest tests/unit/ -m unit -v

# Integration tests (requires PostgreSQL + Redis)
docker compose up postgres redis -d
pytest tests/integration/ -m integration -v

# All tests with coverage
pytest --cov=app --cov-report=html
```

---

## Frontend

```bash
cd frontend
npm install
npm start
# Runs on http://localhost:3000
```

---

## Services

| Service | Port | Description |
|---------|------|-------------|
| FastAPI backend | 8000 | REST API |
| PostgreSQL | 5432 | Primary database |
| Redis | 6379 | Cache + Celery broker |
| Celery Worker | — | Background task processor |
| Celery Beat | — | Periodic task scheduler |
| Flower | 5555 | Celery monitoring UI |
