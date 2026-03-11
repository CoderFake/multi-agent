<div align="center">

<img src="assets/banner.png" alt="Knowsee Banner" width="100%" />

# Multi-agent AI Assistant

**Google ADK · CopilotKit · AG-UI**

[![License](https://img.shields.io/badge/License-Apache_2.0-blue.svg)](LICENSE)
[![Try Demo](https://img.shields.io/badge/Try_Demo-Live-green.svg)](https://knowsee-frontend-yrptvkizbq-ew.a.run.app)

</div>

---

## 📖 Table of Contents
- [Prerequisites](#prerequisites)
- [Quick Start](#quick-start)
- [Architecture](#architecture)
- [Project Structure](#project-structure)
- [Make Commands](#make-commands)
- [Changing Models](#changing-models)
- [Customising Prompts](#customising-prompts)
- [License](#license)

---

## Prerequisites

| Tool | Install |
|------|---------|
| Node.js 20+ | `brew install node` |
| Python 3.11+ | https://python.org |
| uv | `curl -LsSf https://astral.sh/uv/install.sh \| sh` |
| Docker Desktop | https://docker.com |
| gcloud CLI | `brew install google-cloud-sdk` |

---

## Quick Start

### 1. Clone & Install

```bash
git clone https://github.com/coderfake/agent.git
cd agent
make install
```

### 2. Configure `.env`

```bash
cp .env.example .env
```

Open `.env` and fill in **required** values:

| Variable | Required | Notes |
|----------|----------|-------|
| `GOOGLE_CLOUD_PROJECT` | **Yes** | GCP project ID |
| `DATABASE_URL` | **Yes** | Postgres URL (default matches Docker) |

Web frontend has its own `.env`:

```bash
cp web/.env.example web/.env.development
```

| Variable | Required | Notes |
|----------|----------|-------|
| `NEXT_PUBLIC_COPILOTKIT_PUBLIC_KEY` | **Yes** | [Free at cloud.copilotkit.ai](https://cloud.copilotkit.ai) |
| `BETTER_AUTH_SECRET` | **Yes** | `openssl rand -base64 32` |
| `DATABASE_URL` | **Yes** | Same Postgres URL |
| `FIREBASE_*` | **Yes** | Required for Firebase Identity Auth |

> **Note**: Be sure to copy the entire list of `FIREBASE_` configuration variables exactly as generated from your Firebase project settings into `.env.development`.

### 3. Authenticate with GCP

Required for Vertex AI (Gemini models, RAG):

```bash
make gcp-login
```

### 4. Run

#### A — Basic (sagent + web only, no RAG/retrieval)

```bash
make dev
```

Starts: Postgres in Docker → Drizzle migrations → sagent on :8000 → web on :3000

#### B — Full stack (sagent + retrieval on host, everything else in Docker)

```bash
# Terminal 0: infrastructure
make services-up-infra     # postgres, rabbitmq, milvus, minio, nginx
make db-migrate            # Drizzle schema migrations

# Terminal 1
make dev-agent             # sagent :8000

# Terminal 2
make dev-retrieval         # retrieval :8001

# Terminal 3
make dev-web               # Next.js :3000
```

### 5. Open

Go to [http://localhost:3000](http://localhost:3000), sign up, verify email → done.

---

## Architecture

```text
Browser
  └── Next.js :3000 (CopilotKit + Better Auth)
        └── AG-UI Protocol
              └── sagent :8000 (FastAPI + ADK)
                    ├── Root Agent (gemini-2.5-pro)
                    │     ├── Web Search Agent (gemini-2.5-flash)
                    │     ├── Team Knowledge Agent (RAG, gemini-2.5-flash)
                    │     └── Data Analyst Agent (BigQuery, gemini-2.5-pro)
                    └── retrieval :8001 (Milvus vector search)
```

**Infrastructure:**

| Service | Dev | Prod |
|---------|-----|------|
| Database | Postgres (Docker) | Cloud SQL |
| Vector DB | Milvus (Docker) | Milvus (Docker) |
| Message Queue | RabbitMQ (Docker) | RabbitMQ (Docker) |
| Object Storage | MinIO (Docker) | GCS |
| Auth | Better Auth | Better Auth |
| LLM | Vertex AI (Gemini) | Vertex AI (Gemini) |

**Schema ownership:** Drizzle (`web/src/lib/schema.ts`) owns all database tables. `sagent` only reads/writes — never creates tables.

---

## Project Structure

```text
.
├── .env                      # Single env file for all services
├── docker-compose.yml        # All infrastructure dependencies
├── services/
│   ├── sagent/               # Python backend (FastAPI + ADK)
│   │   ├── agents/           # Orchestrator and sub-agents
│   │   │   ├── root.py       # Main orchestrator (delegates to sub-agents)
│   │   │   ├── search.py     # Web search via Google Search
│   │   │   ├── rag/agent.py  # Team knowledge (Milvus RAG)
│   │   │   └── data_analyst/ # BigQuery SQL + chart generation
│   │   ├── instructions/
│   │   │   └── prompts/      # YAML prompt files (system + user prompts)
│   │   ├── config/settings.py# Typed environment variables
│   │   └── main.py           # FastAPI entry point
│   └── retrieval/            # Python retrieval microservice
│       ├── app/config/settings.py # Retrieval-specific config
│       └── app/worker.py     # RabbitMQ consumers (index + RAG RPC)
└── web/                      # Next.js frontend (CopilotKit)
    ├── src/lib/schema.ts     # Drizzle schema (source of truth for DB)
    └── src/app/
        ├── api/copilotkit/   # AG-UI bridge
        └── chat/             # Chat pages
```

---

## Make Commands

```bash
# Dev
make dev                  # basic: postgres + sagent + web
make dev-agent            # sagent only (:8000)
make dev-retrieval        # retrieval only (:8001)
make dev-web              # Next.js only (:3000)

# Infrastructure
make services-up-infra    # all Docker services except services/sagent/retrieval
make services-up          # all Docker services including containerised services/sagent/retrieval
make services-down        # stop all

# Database (Drizzle owns schema)
make db-up                # start Postgres only
make db-migrate           # apply Drizzle migrations
make db-generate          # generate migration files after schema change
make db-reset             # drop + re-migrate (dev only)

# Install
make install              # sagent + web
make install-agent        # sagent only
make install-retrieval    # retrieval only
make install-web          # web only

# GCP
make gcp-login            # full auth (gcloud + ADC)
make gcp-status           # show current project

# Deploy (production)
make docker-build ENV=dev
make docker-push ENV=dev
make tf-bootstrap ENV=dev # first time Terraform setup
make db-migrate-prod ENV=dev
```

---

## Changing Models

All model names are in `.env` — no code changes needed:

```bash
MODEL_ROOT=gemini-2.5-pro          # root orchestrator
MODEL_SEARCH=gemini-2.5-flash      # web search
MODEL_RAG=gemini-2.5-flash         # team knowledge
MODEL_DATA_ANALYST=gemini-2.5-pro  # BigQuery analyst
MODEL_TITLE=gemini-2.0-flash-lite  # title generation
```

## Customising Prompts

System prompts are in `services/sagent/instructions/prompts/`:

```text
root.yml          # routing + behaviour rules
search.yml        # citation rules
team_knowledge.yml# search-first, cite source files
data_analyst.yml  # BigQuery workflow, SQL guidelines, chart logic
titles.yml        # conversation title generation template
```

Edit the `system:` block in any file — no restart needed if using `--reload`.

---

## License

[Apache 2.0](LICENSE)
