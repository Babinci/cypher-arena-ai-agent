# Cypher Arena AI Agent

An AI-powered automation and chat agent for the Cypher Arena platform. Integrates with the Cypher Arena backend API, MCP server, and (optionally) Open WebUI to automate data management and provide developer-centric tools.

---

## Features

- Batch create, retrieve, and rate contrastive pairs
- Batch insert, update, and retrieve topics
- Fetch news records by date/type
- Robust Gemini API integration with rate-limiting and model fallback
- Optional: Interactive chat via Open WebUI
- All Cypher Arena API endpoints exposed as MCP tools

---

## Current Status

- ✅ **MCP server:** First iteration implemented
- ✅ **Cypher Arena API agent:** First iteration implemented and exposed via MCP server
- ⏳ **Automation scripts:** To be implemented
- ⏳ **Open WebUI integration:** To be implemented

---

## Quickstart / Setup

```bash
# 1. Clone the repo
git clone <repo-url>
cd Cypher_arena_ai_agent

# 2. Install Python 3.12.9 and uv (if not already installed)
#    See: https://github.com/astral-sh/uv

# 3. Create and activate a virtual environment
python -m venv .venv
# On Windows:
.venv\Scripts\activate
# On Unix/macOS:
source .venv/bin/activate

# 4. Install dependencies
uv pip install -r requirements.txt

# 5. Configure the agent (see Configuration below)
```

---

## Configuration

Create a `config.yaml` (or `.env`) in the project root. Example:

```yaml
api_keys:
  gemini: "YOUR_GEMINI_KEY"
models:
  default_provider: "gemini"
  lm_studio_enabled: false
  lm_studio_endpoint: "http://localhost:1234/v1"
  gemini_pro_model_id: "gemini-2.5-pro-preview-03-25"
  gemini_flash_model_id: "gemini-2.5-flash-preview-04-17"
  gemini_rate_limit_strategy: "prefer_pro_fallback_flash"
automation:
  batch_size_contrast_pairs: 50
  batch_size_topics: 100
```

---

## Usage

### Automation Scripts

_Coming soon: Python scripts for batch operations (contrast pairs, topics, news)._  
Scripts will use the MCP client and configuration above.

### Open WebUI (Optional)

_Coming soon: Interactive chat interface via Open WebUI._  
To install:  
```bash
pip install open-webui
open-webui serve
```
Then visit [http://localhost:8080](http://localhost:8080) or [http://localhost:3000](http://localhost:3000).

---

## Development Roadmap

- [x] Project structure, MCP server, and Cypher Arena API agent
- [ ] Automation scripts for CRUD operations
- [ ] Robust rate-limiting and model fallback logic
- [ ] Open WebUI integration for interactive chat
- [ ] Documentation and usage examples

---

## References & Documentation

- [Cypher Arena API Endpoints](cypher_arena_endpoints.md)
- [MCP Python SDK Docs](https://modelcontextprotocol.com/python-sdk) (see also context7)
- [Open WebUI Docs](https://github.com/open-webui/open-webui) (see also context7)

---

## License

_Add your license here if applicable._
