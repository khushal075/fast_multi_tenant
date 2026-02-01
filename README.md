# Multi-Tenant SaaS Platform

A high-performance, event-driven scaffold demonstrating Staff-level architecture for tenant isolation and distributed systems.

## Key Architectural Features
- **Data Isolation:** Schema-based multi-tenancy using PostgreSQL.
- **Observability:** Prometheus/Grafana integration for per-tenant metrics.
- **Resilience:** Redis-backed rate limiting and circuit breakers.
- **DevOps:** Multi-stage Docker builds and automated migration pipelines.

## Tech Stack
- **Language:** Python 3.14 (Bleeding edge) / 3.12 (Stable)
- **Framework:** FastAPI
- **Data:** PostgreSQL + SQLAlchemy 2.0
- **Cache:** Redis


## 🚀 How to Run

### 1. Prerequisites
* **Docker** and **Docker Compose** installed.
* **Git** (configured with your SSH keys).

### 2. Setup & Start
Run these commands from the project root:

```bash
# 1. Clone the repository
git clone git@github.com:khushal075/fast_multi_tenant.git
cd fast_multi_tenant

# 2. Build and start the Docker containers in detached mode
# This starts the PostgreSQL database and the FastAPI application
docker-compose up --build -d
```

### 3. Initialize Database
```bash
# Seeding initial DB setup
docker-compose exec web poetry run python -m app.seed
```

### 4. Verify the Setup
```bash
# Test the 'default' tenant
curl -H "X-Tenant-ID: default" http://localhost:8000/test-db
```

## 🛠 Project Architecture
**Isolation Strategy:** Each tenant has its own dedicated PostgreSQL Schema.

**Routing:** Custom middleware detects the X-Tenant-ID header and dynamically sets the database search_path.

### **Models**
- **Tenant:** Stored in the public schema (Global).
- **User & Role:** Stored in individual tenant schemas (Isolated).