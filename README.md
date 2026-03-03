# fast_multi_tenant

A high-performance multi-tenant SaaS scaffold built with **FastAPI**, **SQLAlchemy 2.0**, and **PostgreSQL** using **row-level isolation** — every tenant's data lives in the same schema, separated by a `tenant_id` UUID column on every table.

---

## Architecture

### Row-Level Isolation

All tenant-scoped models inherit `TenantMixin` which automatically injects a `tenant_id` UUID foreign key column. Every query must filter by `tenant_id` — there are no separate schemas or databases per tenant.

```
public.tenants          ← tenant registry
public.roles            ← tenant_id FK → tenants.id
public.users            ← tenant_id FK → tenants.id
```

### Request Flow

```
HTTP Request
  └─ TenantMiddleware
       ├─ reads X-Tenant-ID header
       ├─ validates UUID format
       ├─ looks up tenant in DB (sync, run_in_executor)
       ├─ 400 if header missing
       ├─ 403 if tenant not found or inactive
       └─ sets tenant UUID in ContextVar
            └─ FastAPI route handler
                 └─ all DB queries scoped to tenant_id
```

### Key Design Decisions

| Decision | Choice | Reason |
|---|---|---|
| Isolation model | Row-level | Simpler migrations, single schema |
| Tenant context | `ContextVar` | Safe for async, no thread-local issues |
| Async DB | `AsyncSession` + psycopg3 | Native async, no greenlet bridging |
| Sync DB (middleware) | `SyncSessionLocal` + `run_in_executor` | Middleware runs before async context |
| Tenant PK | UUID | No enumeration attacks, globally unique |

---

## Project Structure

```
fast_multi_tenant/
├── app/
│   ├── api/v1/endpoints/
│   │   └── tenants.py          # Tenant provisioning CRUD
│   ├── core/
│   │   ├── config.py           # Pydantic settings, ENV-based config
│   │   └── tenant_context.py   # ContextVar for tenant UUID
│   ├── database/
│   │   ├── base.py             # Base + TenantMixin
│   │   └── session.py          # Async + sync engines
│   ├── middleware/
│   │   └── tenant_gate.py      # X-Tenant-ID validation
│   ├── models/
│   │   ├── tenant.py           # Tenant registry (PublicBase)
│   │   ├── user.py             # TenantMixin → tenant_id
│   │   └── role.py             # TenantMixin → tenant_id
│   ├── schemas/
│   │   └── tenant.py           # Pydantic request/response models
│   └── main.py                 # FastAPI app, middleware registration
├── alembic/                    # DB migrations
├── tests/
│   ├── conftest.py             # Shared fixtures (Postgres, rollback isolation)
│   ├── unit/                   # Context, model, schema tests
│   └── integration/            # HTTP endpoint tests
├── config.env                  # Docker environment (POSTGRES_SERVER=db)
├── config.local.env            # Local environment (POSTGRES_SERVER=localhost)
├── docker-compose.yaml
└── pyproject.toml
```

---

## Getting Started

### Prerequisites

- Python 3.12+
- Docker & Docker Compose
- Poetry

### Local Development

```bash
# Install dependencies
poetry install --with dev

# Start Postgres
docker-compose up db -d

# Run migrations
alembic upgrade head

# Seed default tenant
python -m app.seed

# Start the API
uvicorn app.main:app --reload
```

The API will be available at `http://localhost:8000`.  
Swagger docs at `http://localhost:8000/docs`.

### Docker (full stack)

```bash
docker-compose up --build
```

---

## Configuration

The app uses two env files selected by the `ENV` environment variable:

| `ENV` value | File loaded | `POSTGRES_SERVER` |
|---|---|---|
| `local` (default) | `config.local.env` | `localhost` |
| `docker` | `config.env` | `db` |

`config.local.env` is gitignored — create it locally:

```env
POSTGRES_SERVER=localhost
POSTGRES_USER=local
POSTGRES_PASSWORD=local
POSTGRES_DB=app_db
POSTGRES_PORT=5432
PROJECT_NAME=Multi-Tenant Platform
API_V1_STR=/api/v1
```

---

## API Reference

### Tenant Provisioning (public — no `X-Tenant-ID` required)

| Method | Endpoint | Description |
|---|---|---|
| `POST` | `/api/v1/tenants/` | Create a new tenant |
| `GET` | `/api/v1/tenants/` | List all tenants |
| `GET` | `/api/v1/tenants/{id}` | Get tenant by UUID |
| `PATCH` | `/api/v1/tenants/{id}/deactivate` | Deactivate a tenant |

### Tenant-Scoped Routes (require `X-Tenant-ID` header)

All other routes require the header:

```
X-Tenant-ID: <tenant-uuid>
```

Missing or invalid header returns `400` or `403` respectively.

### Example

```bash
# Create a tenant
curl -X POST http://localhost:8000/api/v1/tenants/ \
  -H "Content-Type: application/json" \
  -d '{"name": "Acme Corp"}'

# Response
{
  "id": "3f6b2c1a-...",
  "name": "Acme Corp",
  "is_active": true,
  "created_at": "2026-01-01T00:00:00Z"
}

# Use the tenant UUID in subsequent requests
curl http://localhost:8000/debug/context \
  -H "X-Tenant-ID: 3f6b2c1a-..."
```

---

## Testing

Tests use a real Postgres instance. Each test runs inside a rolled-back transaction — no data persists between tests.

```bash
# Start Postgres first
docker-compose up db -d

# Run all tests with coverage
poetry run pytest tests/unit tests/integration --cov=app --cov-report=term-missing

# Run only unit tests
poetry run pytest tests/unit -v

# Run only integration tests
poetry run pytest tests/integration -v
```

### Test Structure

| Layer | Location | What it tests |
|---|---|---|
| Unit | `tests/unit/` | Tenant context, models, schemas, middleware logic |
| Integration | `tests/integration/` | Full HTTP request/response cycle |

---

## CI/CD

GitHub Actions pipeline (`.github/workflows/ci.yml`) runs on every push and PR to `main`, `master`, `develop`:

1. Spins up Postgres 15 as a service container
2. Installs dependencies via Poetry (with virtualenv caching)
3. Runs Alembic migrations
4. Runs full test suite with 70% coverage threshold
5. Uploads coverage report to Codecov

---

## Database Migrations

```bash
# Generate a new migration
alembic revision --autogenerate -m "description"

# Apply migrations
alembic upgrade head

# Rollback one step
alembic downgrade -1
```

**Note:** When running locally, Postgres must be running (`docker-compose up db -d`) before any Alembic commands.

---

## Adding a New Tenant-Scoped Model

1. Create the model inheriting `TenantMixin` and `Base`:

```python
from app.database.base import Base, TenantMixin

class Invoice(TenantMixin, Base):
    __tablename__ = "invoices"
    id = Column(Integer, primary_key=True)
    amount = Column(Numeric, nullable=False)
    # tenant_id is injected automatically by TenantMixin
```

2. Import it in `app/models/__init__.py`
3. Generate and apply migration:

```bash
alembic revision --autogenerate -m "add invoices table"
alembic upgrade head
```

All queries against `Invoice` must filter by `tenant_id` — the platform does not enforce this automatically at the query level.