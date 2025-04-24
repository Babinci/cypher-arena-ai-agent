# Product Requirements Document (PRD)

## Context

This project is an **AI agent for the Cypher Arena platform**. The agent integrates with the MCP server and Open WebUI to provide advanced chat and automation capabilities for Cypher Arena users and workflows.

## Overview

The AI agent will support chat and automation via the MCP server, integrating with:
- **Open WebUI** (using the [open-webui](https://github.com/open-webui/open-webui) Python package with uv)
- **Local LM Studio models** (optional, see configuration)
- **Google Gemini models**

## Key Features

- **Contrastive Mode:**
  - Get contrasting pairs (with IDs, paginated, support query parameters)
  - Rate contrastive mode pairs (in batches)
  - Create contrastive mode pairs (in batches)
- **News:**
  - Get news (with query parameters: start time, end time, news_type)
- **Topics:**
  - Insert topics (in batches)
  - Get topics (paginated, support query parameters)
  - Change topics (in batches)

See `endpoints_descriptions.md` for detailed endpoint documentation.

## Deployment Scenarios

### 1. AI PC (Interactive)
- Run scripts and interact with Open WebUI using either Gemini or LM Studio models.
- LM Studio is **optional** and can be enabled/disabled via a global configuration file.

### 2. Remote Server (Automated)
- Only daily automation scripts are run (no interactive chat).
- Scripts use Gemini models exclusively (no LM Studio).
- Automation is managed via Celery (Celery is pre-configured on the server; only the script and settings are needed).

## Automation Requirements

- **Automatic scripts must run once a day** using Gemini models on the remote server.
- These scripts should be compatible with Celery for scheduled execution.
- LM Studio should not be required or used on the remote server.

## Configuration

- There must be a **global configuration file** to control model usage (e.g., enable/disable LM Studio, select model provider).
- The system should default to Gemini models if LM Studio is not enabled.

## Implementation Language

- Python

## Package Management

- Use `uv` as the package manager
- Use `.venv` folder for the virtual environment

## Development Workflow

1. Activate the Python environment in CMD:
   ```sh
   .venv\Scripts\activate
   ```

## Deliverables / Needs

- Proper documentation and endpoints from Cypher Arena API
- Instructions on how to make the system instantly working