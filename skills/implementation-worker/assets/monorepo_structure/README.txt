# Monorepo Structure Reference
# ============================
#
# This directory contains the reference monorepo layout from the
# Development View (DEV) of the 4+1 Architectural View Model.
#
# Purpose:
# - Provide a template for structuring the platform codebase
# - Ensure separation of concerns between ETL and API
# - Share contracts and utilities between components
#
# Directory Layout:
# /
# ├── src/
# │   ├── etl/                # Mage project root
# │   │   ├── data_loaders/
# │   │   ├── transformers/
# │   │   └── pipelines/
# │   ├── api/                # FastAPI application
# │   │   ├── main.py
# │   │   └── prediction/
# │   └── shared/             # Shared Pydantic models & Utility code
# │       └── schemas.py
# ├── tests/
# │   ├── integration/
# │   └── unit/
# ├── docker/
# │   ├── Dockerfile.mage
# │   └── Dockerfile.api
# └── pyproject.toml          # Single source of dependency truth
#
# Usage:
# Copy this structure when scaffolding a new platform instance.
