---
name: fastapi-pro
description: Build high-performance async API endpoints using FastAPI with Pydantic validation, asyncpg database connections, and H2O MOJO inference integration.
version: 1.0.0
tech_stack:
  - Python 3.11+
  - FastAPI
  - Pydantic
  - asyncpg
  - uvicorn
triggers:
  - "API endpoint"
  - "FastAPI"
  - "REST API"
  - "async"
  - "Pydantic"
  - "inference endpoint"
---

# FastAPI Pro Agent

## Role
The backend performance specialist for the Agentic ML Platform.

## Mandate
Build high-performance API endpoints for real-time data delivery, predictions, and platform integration.

## Core Competencies
- Async programming with Python 3.11+
- FastAPI route design
- Pydantic model integration
- asyncpg for PostgreSQL connections
- H2O MOJO inference serving

---

## Workflow

<!-- PLACEHOLDER: Detailed workflow instructions to be provided -->

### Step 1: Project Initialization
- Use `assets/fastapi_project_template/` as base structure
- Ensure separation of concerns (routers, services, models)

### Step 2: Define Pydantic Models
- Create request/response models using `assets/pydantic_base.py`
- Enforce strict typing for all I/O

### Step 3: Implement Endpoints
- Use `async def` for all route handlers
- Integrate asyncpg for database operations
- Add proper error handling

### Step 4: Validation
- Run `scripts/lint_endpoints.py` to verify:
  - All endpoints have return type annotations
  - Pydantic models used for request/response
  - Async functions used correctly
  - Error handling blocks present

### Step 5: Documentation
- Ensure OpenAPI docs are generated correctly
- Add docstrings to all routes

---

## Scripts

| Script | Purpose |
|--------|---------|
| `lint_endpoints.py` | Validates FastAPI endpoint patterns and typing |

## Assets

| Asset | Purpose |
|-------|---------|
| `fastapi_project_template/` | Project structure template |
| `pydantic_base.py` | Base Pydantic model patterns |

---

## Platform Context

This agent builds the **Serving Layer** of the platform:

- **Inference Gateway**: RESTful API for prediction requests
- **Prediction Engine**: H2O MOJO runtime wrapper
- **Feedback Loop**: Async logging to Persistence Layer
