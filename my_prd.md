# Product Requirements Document (PRD)

## Overview

Build an AI agent with an MCP server that integrates with Open WebUI (using the [open-webui](https://github.com/open-webui/open-webui) Python package with uv). The agent should support chat via the MCP server with:

- **Local LM Studio models**
- **Google Gemini models:**
  - `gemini-2.5-pro-preview-03-25` (Free tier: 5 requests/minute, 25 requests/day; preferred, but respect RPM limits)
  - `gemini-2.5-flash-preview-04-17` (10 requests/minute, 500 requests/day; fallback if pro model is rate-limited)

## MCP Server Requirements

The MCP server must provide the following tools/endpoints:

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

Endpoints description: endpoints_descriptions.md


- **Implementation language:** Python

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