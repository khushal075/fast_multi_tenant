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
