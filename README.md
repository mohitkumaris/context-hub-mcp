# Context Hub MCP Server

A production-grade **Model Context Protocol (MCP)** server for AI agent context orchestration, tool execution, and memory management.

## What is MCP?

The **Model Context Protocol** is an architectural pattern for building AI-powered applications that require:

- **Context Orchestration**: Managing conversation history, user preferences, and session state across multiple interactions
- **Tool Execution**: Coordinating the execution of specialized tools (analytics, insights, reports) based on user intent
- **Memory Management**: Combining short-term (Redis) and long-term (PostgreSQL) memory for comprehensive context
- **Prompt Governance**: Enforcing consistent, hallucination-free responses through structured prompts
- **LLM Agnosticism**: Supporting multiple LLM providers without code changes

## Architecture

```
┌─────────────────────────────────────────────────────────────────┐
│                        FastAPI Server                           │
│                         POST /execute                           │
└─────────────────────────────────────────────────────────────────┘
                                │
                                ▼
┌─────────────────────────────────────────────────────────────────┐
│                     Executor (Orchestrator)                      │
│  ┌─────────────┐  ┌─────────────┐  ┌─────────────────────────┐  │
│  │   Planner   │  │   Execute   │  │       Formatter         │  │
│  │  (Intent)   │──│   (Tools)   │──│   (Response)            │  │
│  └─────────────┘  └─────────────┘  └─────────────────────────┘  │
└─────────────────────────────────────────────────────────────────┘
        │                   │                      │
        ▼                   ▼                      ▼
┌───────────────┐  ┌───────────────┐  ┌─────────────────────────┐
│   Registry    │  │    Memory     │  │        Prompts          │
│  ┌─────────┐  │  │  ┌─────────┐  │  │  ┌─────────────────┐    │
│  │  Tools  │  │  │  │  Redis  │  │  │  │  system.txt     │    │
│  │ Schemas │  │  │  │ (short) │  │  │  │  analysis.txt   │    │
│  │Policies │  │  │  │Postgres │  │  │  └─────────────────┘    │
│  └─────────┘  │  │  │ (long)  │  │  └─────────────────────────┘
└───────────────┘  │  └─────────┘  │
                   └───────────────┘
```

## Features

- **Clean HTTP API**: Single `/execute` endpoint for all context requests
- **Plan-Based Access Control**: Free, Pro, and Agency tier tool restrictions
- **Deterministic Planning**: Rule-based tool selection with explainable reasoning
- **Memory Layers**: Redis for conversation state, PostgreSQL for historical data
- **LLM Agnostic**: Configure any LLM provider via environment variables
- **Docker Ready**: Production Dockerfile with health checks

## Project Structure

```
context-hub-mcp/
├── server.py              # FastAPI application entry point
├── config.py              # Centralized configuration
├── Dockerfile             # Production container image
├── requirements.txt       # Python dependencies
├── README.md              # This file
│
├── executor/              # Core orchestration logic
│   ├── execute.py         # Main execution coordinator
│   ├── planner.py         # Intent classification & tool planning
│   └── formatter.py       # Response formatting
│
├── registry/              # Tool and schema definitions
│   ├── tools.py           # Tool registry with implementations
│   ├── schemas.py         # Pydantic request/response models
│   └── policies.py        # Plan-based access control
│
├── memory/                # Data persistence
│   ├── redis_store.py     # Short-term memory (conversations)
│   └── postgres_store.py  # Long-term memory (analytics)
│
└── prompts/               # LLM prompt templates
    ├── system.txt         # Core system prompt
    └── analysis.txt       # Deep analysis mode prompt
```

## Quick Start

### Prerequisites

- Python 3.11+
- Docker (optional, for containerized deployment)
- Redis (optional, falls back to in-memory)
- PostgreSQL (optional, falls back to in-memory)

### Local Development

1. **Clone and navigate to the project:**

```bash
cd context-hub-mcp
```

2. **Create a virtual environment:**

```bash
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate
```

3. **Install dependencies:**

```bash
pip install -r requirements.txt
```

4. **Set environment variables:**

```bash
export LLM_PROVIDER=openai
export LLM_API_KEY=your-api-key
export LLM_MODEL=gpt-4
export DEBUG=true
```

5. **Run the server:**

```bash
python server.py
```

The server will start at `http://localhost:8000`.

### Docker Deployment

1. **Build the image:**

```bash
docker build -t context-hub-mcp .
```

2. **Run the container:**

```bash
docker run -d \
  --name context-hub-mcp \
  -p 8000:8000 \
  -e LLM_PROVIDER=openai \
  -e LLM_API_KEY=your-api-key \
  -e LLM_MODEL=gpt-4 \
  -e REDIS_HOST=redis \
  -e POSTGRES_HOST=postgres \
  context-hub-mcp
```

### Docker Compose (with dependencies)

Create a `docker-compose.yml`:

```yaml
version: "3.8"

services:
  mcp:
    build: .
    ports:
      - "8000:8000"
    environment:
      - LLM_PROVIDER=openai
      - LLM_API_KEY=${LLM_API_KEY}
      - LLM_MODEL=gpt-4
      - REDIS_HOST=redis
      - POSTGRES_HOST=postgres
      - POSTGRES_USER=mcp
      - POSTGRES_PASSWORD=mcp_secret
      - POSTGRES_DB=context_hub
    depends_on:
      - redis
      - postgres

  redis:
    image: redis:7-alpine
    ports:
      - "6379:6379"

  postgres:
    image: postgres:15-alpine
    environment:
      - POSTGRES_USER=mcp
      - POSTGRES_PASSWORD=mcp_secret
      - POSTGRES_DB=context_hub
    ports:
      - "5432:5432"
    volumes:
      - pgdata:/var/lib/postgresql/data

volumes:
  pgdata:
```

Run with:

```bash
docker-compose up -d
```

## API Reference

### Base URL

```
http://localhost:8000
```

### Endpoints Overview

| Method | Endpoint   | Description                              |
| ------ | ---------- | ---------------------------------------- |
| GET    | `/`        | Root endpoint with API info              |
| GET    | `/health`  | Health check for container orchestration |
| POST   | `/execute` | Main execution endpoint                  |
| GET    | `/docs`    | Swagger UI (debug mode only)             |
| GET    | `/redoc`   | ReDoc documentation (debug mode only)    |

---

### GET /

Root endpoint with API information.

**Request:**

```
GET http://localhost:8000/
```

**Response:**

```json
{
  "service": "Context Hub MCP Server",
  "version": "1.0.0",
  "docs": "/docs"
}
```

---

### GET /health

Health check endpoint for container orchestration.

**Request:**

```
GET http://localhost:8000/health
```

**Response:**

```json
{
  "status": "healthy",
  "version": "1.0.0",
  "llm_provider": "openai"
}
```

---

### POST /execute

Execute a context request with tool orchestration.

**Request:**

```
POST http://localhost:8000/execute
Content-Type: application/json
```

**Request Body:**

```json
{
  "user_id": "user_abc123",
  "channel_id": "channel_xyz789",
  "message": "Show me my channel's performance this week",
  "metadata": {
    "user_plan": "pro",
    "timezone": "UTC"
  }
}
```

**Response:**

```json
{
  "success": true,
  "content": "Your channel had a strong week with 15,420 views...",
  "content_type": "analytics",
  "tools_used": ["fetch_analytics", "compute_metrics"],
  "tool_outputs": {
    "data": {
      "views": 15420,
      "subscribers": 1250
    },
    "metrics": {
      "growth_rate": 15.2
    }
  },
  "metadata": {
    "timestamp": "2024-01-15T10:30:00Z",
    "intent": "analytics",
    "confidence": 0.92
  }
}
```

---

## Postman Collection

### Import Instructions

1. Open Postman
2. Click **Import** → **Raw text**
3. Paste the JSON below and import

### Postman Collection JSON

```json
{
  "info": {
    "name": "Context Hub MCP Server",
    "description": "API collection for Context Hub MCP Server - AI agent context orchestration",
    "schema": "https://schema.getpostman.com/json/collection/v2.1.0/collection.json"
  },
  "variable": [
    {
      "key": "base_url",
      "value": "http://localhost:8000",
      "type": "string"
    }
  ],
  "item": [
    {
      "name": "System",
      "item": [
        {
          "name": "Root - API Info",
          "request": {
            "method": "GET",
            "header": [],
            "url": {
              "raw": "{{base_url}}/",
              "host": ["{{base_url}}"],
              "path": [""]
            },
            "description": "Get API information and version"
          }
        },
        {
          "name": "Health Check",
          "request": {
            "method": "GET",
            "header": [],
            "url": {
              "raw": "{{base_url}}/health",
              "host": ["{{base_url}}"],
              "path": ["health"]
            },
            "description": "Check server health status"
          }
        }
      ]
    },
    {
      "name": "Execute - Analytics",
      "item": [
        {
          "name": "Get Channel Analytics",
          "request": {
            "method": "POST",
            "header": [
              {
                "key": "Content-Type",
                "value": "application/json"
              }
            ],
            "body": {
              "mode": "raw",
              "raw": "{\n  \"user_id\": \"user_123\",\n  \"channel_id\": \"channel_456\",\n  \"message\": \"Show me my channel analytics for last week\",\n  \"metadata\": {\n    \"user_plan\": \"free\",\n    \"timezone\": \"UTC\"\n  }\n}"
            },
            "url": {
              "raw": "{{base_url}}/execute",
              "host": ["{{base_url}}"],
              "path": ["execute"]
            },
            "description": "Fetch analytics data for a channel"
          }
        },
        {
          "name": "Get View Statistics",
          "request": {
            "method": "POST",
            "header": [
              {
                "key": "Content-Type",
                "value": "application/json"
              }
            ],
            "body": {
              "mode": "raw",
              "raw": "{\n  \"user_id\": \"user_123\",\n  \"channel_id\": \"channel_456\",\n  \"message\": \"How many views did I get this month?\",\n  \"metadata\": {\n    \"user_plan\": \"pro\"\n  }\n}"
            },
            "url": {
              "raw": "{{base_url}}/execute",
              "host": ["{{base_url}}"],
              "path": ["execute"]
            },
            "description": "Get view statistics and metrics"
          }
        },
        {
          "name": "Compare Performance",
          "request": {
            "method": "POST",
            "header": [
              {
                "key": "Content-Type",
                "value": "application/json"
              }
            ],
            "body": {
              "mode": "raw",
              "raw": "{\n  \"user_id\": \"user_123\",\n  \"channel_id\": \"channel_456\",\n  \"message\": \"Compare my performance this week versus last week\",\n  \"metadata\": {\n    \"user_plan\": \"pro\"\n  }\n}"
            },
            "url": {
              "raw": "{{base_url}}/execute",
              "host": ["{{base_url}}"],
              "path": ["execute"]
            },
            "description": "Compare performance across time periods"
          }
        }
      ]
    },
    {
      "name": "Execute - Insights",
      "item": [
        {
          "name": "Get Growth Insights",
          "request": {
            "method": "POST",
            "header": [
              {
                "key": "Content-Type",
                "value": "application/json"
              }
            ],
            "body": {
              "mode": "raw",
              "raw": "{\n  \"user_id\": \"user_123\",\n  \"channel_id\": \"channel_456\",\n  \"message\": \"Give me insights on my channel growth\",\n  \"metadata\": {\n    \"user_plan\": \"pro\"\n  }\n}"
            },
            "url": {
              "raw": "{{base_url}}/execute",
              "host": ["{{base_url}}"],
              "path": ["execute"]
            },
            "description": "Generate growth insights and recommendations"
          }
        },
        {
          "name": "Get Recommendations",
          "request": {
            "method": "POST",
            "header": [
              {
                "key": "Content-Type",
                "value": "application/json"
              }
            ],
            "body": {
              "mode": "raw",
              "raw": "{\n  \"user_id\": \"user_123\",\n  \"channel_id\": \"channel_456\",\n  \"message\": \"What should I do to improve my engagement?\",\n  \"metadata\": {\n    \"user_plan\": \"agency\"\n  }\n}"
            },
            "url": {
              "raw": "{{base_url}}/execute",
              "host": ["{{base_url}}"],
              "path": ["execute"]
            },
            "description": "Get personalized recommendations (Agency tier)"
          }
        },
        {
          "name": "Why Analysis",
          "request": {
            "method": "POST",
            "header": [
              {
                "key": "Content-Type",
                "value": "application/json"
              }
            ],
            "body": {
              "mode": "raw",
              "raw": "{\n  \"user_id\": \"user_123\",\n  \"channel_id\": \"channel_456\",\n  \"message\": \"Why did my views drop last week?\",\n  \"metadata\": {\n    \"user_plan\": \"pro\"\n  }\n}"
            },
            "url": {
              "raw": "{{base_url}}/execute",
              "host": ["{{base_url}}"],
              "path": ["execute"]
            },
            "description": "Analyze reasons behind performance changes"
          }
        }
      ]
    },
    {
      "name": "Execute - Reports",
      "item": [
        {
          "name": "Weekly Performance Report",
          "request": {
            "method": "POST",
            "header": [
              {
                "key": "Content-Type",
                "value": "application/json"
              }
            ],
            "body": {
              "mode": "raw",
              "raw": "{\n  \"user_id\": \"user_123\",\n  \"channel_id\": \"channel_456\",\n  \"message\": \"Generate a weekly performance report\",\n  \"metadata\": {\n    \"user_plan\": \"pro\"\n  }\n}"
            },
            "url": {
              "raw": "{{base_url}}/execute",
              "host": ["{{base_url}}"],
              "path": ["execute"]
            },
            "description": "Generate comprehensive weekly report"
          }
        },
        {
          "name": "Monthly Summary",
          "request": {
            "method": "POST",
            "header": [
              {
                "key": "Content-Type",
                "value": "application/json"
              }
            ],
            "body": {
              "mode": "raw",
              "raw": "{\n  \"user_id\": \"user_123\",\n  \"channel_id\": \"channel_456\",\n  \"message\": \"Give me a summary of last month\",\n  \"metadata\": {\n    \"user_plan\": \"pro\"\n  }\n}"
            },
            "url": {
              "raw": "{{base_url}}/execute",
              "host": ["{{base_url}}"],
              "path": ["execute"]
            },
            "description": "Get monthly performance summary"
          }
        },
        {
          "name": "Catch Me Up",
          "request": {
            "method": "POST",
            "header": [
              {
                "key": "Content-Type",
                "value": "application/json"
              }
            ],
            "body": {
              "mode": "raw",
              "raw": "{\n  \"user_id\": \"user_123\",\n  \"channel_id\": \"channel_456\",\n  \"message\": \"Catch me up on what happened this week\",\n  \"metadata\": {\n    \"user_plan\": \"free\"\n  }\n}"
            },
            "url": {
              "raw": "{{base_url}}/execute",
              "host": ["{{base_url}}"],
              "path": ["execute"]
            },
            "description": "Quick recap of recent activity"
          }
        }
      ]
    },
    {
      "name": "Execute - Memory",
      "item": [
        {
          "name": "Recall Previous Discussion",
          "request": {
            "method": "POST",
            "header": [
              {
                "key": "Content-Type",
                "value": "application/json"
              }
            ],
            "body": {
              "mode": "raw",
              "raw": "{\n  \"user_id\": \"user_123\",\n  \"channel_id\": \"channel_456\",\n  \"message\": \"What did we discuss earlier about my thumbnails?\",\n  \"metadata\": {\n    \"user_plan\": \"free\"\n  }\n}"
            },
            "url": {
              "raw": "{{base_url}}/execute",
              "host": ["{{base_url}}"],
              "path": ["execute"]
            },
            "description": "Recall context from previous conversations"
          }
        },
        {
          "name": "Search History",
          "request": {
            "method": "POST",
            "header": [
              {
                "key": "Content-Type",
                "value": "application/json"
              }
            ],
            "body": {
              "mode": "raw",
              "raw": "{\n  \"user_id\": \"user_123\",\n  \"channel_id\": \"channel_456\",\n  \"message\": \"Find all the times we talked about engagement\",\n  \"metadata\": {\n    \"user_plan\": \"pro\"\n  }\n}"
            },
            "url": {
              "raw": "{{base_url}}/execute",
              "host": ["{{base_url}}"],
              "path": ["execute"]
            },
            "description": "Search through conversation history"
          }
        }
      ]
    },
    {
      "name": "Execute - Actions",
      "item": [
        {
          "name": "Schedule Task",
          "request": {
            "method": "POST",
            "header": [
              {
                "key": "Content-Type",
                "value": "application/json"
              }
            ],
            "body": {
              "mode": "raw",
              "raw": "{\n  \"user_id\": \"user_123\",\n  \"channel_id\": \"channel_456\",\n  \"message\": \"Schedule a weekly analytics report every Monday\",\n  \"metadata\": {\n    \"user_plan\": \"agency\"\n  }\n}"
            },
            "url": {
              "raw": "{{base_url}}/execute",
              "host": ["{{base_url}}"],
              "path": ["execute"]
            },
            "description": "Schedule automated tasks (Agency tier)"
          }
        },
        {
          "name": "Execute Action",
          "request": {
            "method": "POST",
            "header": [
              {
                "key": "Content-Type",
                "value": "application/json"
              }
            ],
            "body": {
              "mode": "raw",
              "raw": "{\n  \"user_id\": \"user_123\",\n  \"channel_id\": \"channel_456\",\n  \"message\": \"Create a content calendar for next week\",\n  \"metadata\": {\n    \"user_plan\": \"agency\"\n  }\n}"
            },
            "url": {
              "raw": "{{base_url}}/execute",
              "host": ["{{base_url}}"],
              "path": ["execute"]
            },
            "description": "Execute specific actions (Agency tier)"
          }
        }
      ]
    },
    {
      "name": "Execute - Search",
      "item": [
        {
          "name": "Search Data",
          "request": {
            "method": "POST",
            "header": [
              {
                "key": "Content-Type",
                "value": "application/json"
              }
            ],
            "body": {
              "mode": "raw",
              "raw": "{\n  \"user_id\": \"user_123\",\n  \"channel_id\": \"channel_456\",\n  \"message\": \"Find my best performing videos\",\n  \"metadata\": {\n    \"user_plan\": \"free\"\n  }\n}"
            },
            "url": {
              "raw": "{{base_url}}/execute",
              "host": ["{{base_url}}"],
              "path": ["execute"]
            },
            "description": "Search across all data sources"
          }
        },
        {
          "name": "List Content",
          "request": {
            "method": "POST",
            "header": [
              {
                "key": "Content-Type",
                "value": "application/json"
              }
            ],
            "body": {
              "mode": "raw",
              "raw": "{\n  \"user_id\": \"user_123\",\n  \"channel_id\": \"channel_456\",\n  \"message\": \"Show me all my videos from last month\",\n  \"metadata\": {\n    \"user_plan\": \"free\"\n  }\n}"
            },
            "url": {
              "raw": "{{base_url}}/execute",
              "host": ["{{base_url}}"],
              "path": ["execute"]
            },
            "description": "List and display content"
          }
        }
      ]
    },
    {
      "name": "Plan Tier Tests",
      "item": [
        {
          "name": "Free Tier Request",
          "request": {
            "method": "POST",
            "header": [
              {
                "key": "Content-Type",
                "value": "application/json"
              }
            ],
            "body": {
              "mode": "raw",
              "raw": "{\n  \"user_id\": \"free_user\",\n  \"channel_id\": \"channel_free\",\n  \"message\": \"Show me my analytics\",\n  \"metadata\": {\n    \"user_plan\": \"free\"\n  }\n}"
            },
            "url": {
              "raw": "{{base_url}}/execute",
              "host": ["{{base_url}}"],
              "path": ["execute"]
            },
            "description": "Test with Free tier access"
          }
        },
        {
          "name": "Pro Tier Request",
          "request": {
            "method": "POST",
            "header": [
              {
                "key": "Content-Type",
                "value": "application/json"
              }
            ],
            "body": {
              "mode": "raw",
              "raw": "{\n  \"user_id\": \"pro_user\",\n  \"channel_id\": \"channel_pro\",\n  \"message\": \"Generate a detailed report with charts\",\n  \"metadata\": {\n    \"user_plan\": \"pro\"\n  }\n}"
            },
            "url": {
              "raw": "{{base_url}}/execute",
              "host": ["{{base_url}}"],
              "path": ["execute"]
            },
            "description": "Test with Pro tier access"
          }
        },
        {
          "name": "Agency Tier Request",
          "request": {
            "method": "POST",
            "header": [
              {
                "key": "Content-Type",
                "value": "application/json"
              }
            ],
            "body": {
              "mode": "raw",
              "raw": "{\n  \"user_id\": \"agency_user\",\n  \"channel_id\": \"channel_agency\",\n  \"message\": \"Schedule a task and give me recommendations\",\n  \"metadata\": {\n    \"user_plan\": \"agency\"\n  }\n}"
            },
            "url": {
              "raw": "{{base_url}}/execute",
              "host": ["{{base_url}}"],
              "path": ["execute"]
            },
            "description": "Test with Agency tier access (all tools)"
          }
        }
      ]
    }
  ]
}
```

### Quick Test URLs

After starting the server with `DEBUG=true python server.py`, test these URLs:

| Endpoint     | URL                                    |
| ------------ | -------------------------------------- |
| Root         | `http://localhost:8000/`               |
| Health       | `http://localhost:8000/health`         |
| Swagger Docs | `http://localhost:8000/docs`           |
| ReDoc        | `http://localhost:8000/redoc`          |
| Execute      | `http://localhost:8000/execute` (POST) |

### Sample cURL Commands

**Health Check:**

```bash
curl http://localhost:8000/health
```

**Execute Request:**

```bash
curl -X POST http://localhost:8000/execute \
  -H "Content-Type: application/json" \
  -d '{
    "user_id": "user_123",
    "channel_id": "channel_456",
    "message": "Show me my analytics",
    "metadata": {"user_plan": "pro"}
  }'
```

## Configuration

All configuration is via environment variables:

| Variable            | Default       | Description             |
| ------------------- | ------------- | ----------------------- |
| `SERVER_HOST`       | `0.0.0.0`     | Server bind host        |
| `SERVER_PORT`       | `8000`        | Server bind port        |
| `DEBUG`             | `false`       | Enable debug mode       |
| `LOG_LEVEL`         | `INFO`        | Logging level           |
| `CORS_ORIGINS`      | `*`           | Allowed CORS origins    |
| `REDIS_HOST`        | `localhost`   | Redis host              |
| `REDIS_PORT`        | `6379`        | Redis port              |
| `REDIS_PASSWORD`    | -             | Redis password          |
| `POSTGRES_HOST`     | `localhost`   | PostgreSQL host         |
| `POSTGRES_PORT`     | `5432`        | PostgreSQL port         |
| `POSTGRES_USER`     | `mcp`         | PostgreSQL user         |
| `POSTGRES_PASSWORD` | -             | PostgreSQL password     |
| `POSTGRES_DB`       | `context_hub` | PostgreSQL database     |
| `LLM_PROVIDER`      | `openai`      | LLM provider name       |
| `LLM_API_KEY`       | -             | LLM API key             |
| `LLM_MODEL`         | `gpt-4`       | LLM model name          |
| `LLM_BASE_URL`      | -             | Custom LLM API endpoint |
| `LLM_MAX_TOKENS`    | `4096`        | Max tokens per request  |
| `LLM_TEMPERATURE`   | `0.7`         | LLM temperature         |

## Available Tools

### Free Tier

- `fetch_analytics` - Fetch channel analytics data
- `summarize_data` - Create data summaries
- `recall_context` - Recall conversation context
- `search_data` - Search across data sources

### Pro Tier

- `compute_metrics` - Compute derived metrics
- `generate_chart` - Generate visualization data
- `analyze_data` - Deep data analysis
- `generate_insight` - Generate actionable insights
- `generate_report` - Create comprehensive reports
- `search_history` - Search historical data

### Agency Tier

- `get_recommendations` - Personalized recommendations
- `execute_action` - Execute actions
- `schedule_task` - Schedule future tasks

## Development

### Code Quality

- Type hints are used throughout
- Docstrings on all public functions
- Modular, extensible architecture

### Extending Tools

Add new tools in `registry/tools.py`:

```python
self._register_tool(ToolDefinition(
    name="my_new_tool",
    description="Description of what it does",
    input_schema={...},
    output_schema={...},
    handler=self._my_handler,
    category="custom",
    requires_plan="pro"
))
```

### Adding LLM Providers

Extend the `_invoke_llm` method in `executor/execute.py` to support additional providers.

## License

Proprietary - All rights reserved.
