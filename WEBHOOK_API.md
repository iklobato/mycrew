# Code Pipeline Webhook API

A FastAPI-based webhook API for triggering code pipeline crews asynchronously.

## Installation

Install dependencies:

```bash
uv sync
```

## Running the API

Start the webhook API server:

```bash
uv run webhook
```

The API will be available at `http://localhost:8000`

## API Endpoints

### 1. Trigger Pipeline
**POST** `/webhook/trigger`

Trigger a code pipeline execution with the provided parameters.

**Request Body:**
```json
{
  "task": "Add user authentication to the login page",
  "repo_path": "/path/to/repository",
  "branch": "main",
  "from_scratch": false,
  "max_retries": 3,
  "dry_run": false,
  "test_command": "pytest tests/",
  "issue_id": "#123",
  "github_repo": "owner/repo",
  "issue_url": "https://github.com/owner/repo/issues/123",
  "docs_url": "https://docs.example.com/api",
  "serper_enabled": false,
  "serper_n_results": 5,
  "callback_url": "https://api.example.com/webhook/callback",
  "metadata": {
    "source": "github_webhook",
    "priority": "high"
  }
}
```

**Required Fields:**
- `task` (string): Task description

**Optional Fields with Defaults:**
- `repo_path` (string, default: "."): Repository path
- `branch` (string, default: "main"): Git branch
- `from_scratch` (boolean, default: false): Ignore checkpoint
- `max_retries` (integer, default: 3, range: 0-10): Maximum retries
- `dry_run` (boolean, default: false): Skip git commit
- `test_command` (string, default: ""): Test command
- `issue_id` (string, default: ""): Issue ID for commit
- `github_repo` (string, default: ""): GitHub repo (owner/repo)
- `issue_url` (string, default: ""): Issue URL
- `docs_url` (string, default: ""): Documentation URL
- `serper_enabled` (boolean, default: false): Enable web search
- `serper_n_results` (integer, default: 5, range: 1-20): Search results count
- `callback_url` (string, default: null): Callback URL for completion
- `metadata` (object, default: {}): Additional metadata

**Response (202 Accepted):**
```json
{
  "webhook_id": "550e8400-e29b-41d4-a716-446655440000",
  "status": "accepted",
  "message": "Pipeline execution started for task: Add user authentication...",
  "pipeline_id": "123e4567-e89b-12d3-a456-426614174000",
  "created_at": "2024-01-01T00:00:00Z",
  "metadata": {}
}
```

### 2. Get Webhook Status
**GET** `/webhook/status/{webhook_id}`

Get the status of a webhook request by its ID.

**Response:**
```json
{
  "webhook_id": "550e8400-e29b-41d4-a716-446655440000",
  "status": "running",
  "message": "Pipeline running",
  "pipeline_id": "123e4567-e89b-12d3-a456-426614174000",
  "created_at": "2024-01-01T00:00:00Z",
  "metadata": {}
}
```

### 3. Get Pipeline Status
**GET** `/pipeline/{pipeline_id}`

Get the status of a pipeline execution by its ID.

**Response:**
```json
{
  "pipeline_id": "123e4567-e89b-12d3-a456-426614174000",
  "status": "completed",
  "webhook_id": "550e8400-e29b-41d4-a716-446655440000",
  "created_at": "2024-01-01T00:00:00Z",
  "started_at": "2024-01-01T00:00:01Z",
  "completed_at": "2024-01-01T00:05:00Z",
  "result": {
    "output": "Pipeline completed successfully"
  },
  "error": null
}
```

### 4. Health Check
**GET** `/health`

Check if the API is running.

**Response:**
```json
{
  "status": "healthy",
  "timestamp": "2024-01-01T00:00:00Z"
}
```

### 5. API Root
**GET** `/`

Get API information.

**Response:**
```json
{
  "name": "Code Pipeline Webhook API",
  "version": "1.0.0",
  "endpoints": [
    {
      "path": "/webhook/trigger",
      "method": "POST",
      "description": "Trigger pipeline"
    },
    {
      "path": "/webhook/status/{webhook_id}",
      "method": "GET",
      "description": "Get webhook status"
    },
    {
      "path": "/pipeline/{pipeline_id}",
      "method": "GET",
      "description": "Get pipeline status"
    },
    {
      "path": "/health",
      "method": "GET",
      "description": "Health check"
    },
    {
      "path": "/docs",
      "method": "GET",
      "description": "API documentation"
    }
  ]
}
```

## API Documentation

Interactive API documentation is available at:
- Swagger UI: `http://localhost:8000/docs`
- ReDoc: `http://localhost:8000/redoc`

## Example Usage

### Using curl
```bash
curl -X POST http://localhost:8000/webhook/trigger \
  -H "Content-Type: application/json" \
  -d '{
    "task": "Fix login page crash",
    "repo_path": ".",
    "branch": "main",
    "dry_run": true,
    "test_command": "npm test",
    "issue_id": "#456",
    "github_repo": "myorg/myrepo"
  }'
```

### Using Python
```python
import requests

payload = {
    "task": "Add dark mode toggle",
    "repo_path": "/path/to/repo",
    "branch": "main",
    "dry_run": False,
    "test_command": "pytest tests/ui/",
    "callback_url": "https://webhook.site/your-url"
}

response = requests.post(
    "http://localhost:8000/webhook/trigger",
    json=payload,
    headers={"Content-Type": "application/json"}
)

if response.status_code == 202:
    webhook_id = response.json()["webhook_id"]
    print(f"Pipeline triggered with webhook ID: {webhook_id}")
```

### Using GitHub Actions
```yaml
name: Trigger Code Pipeline
on:
  issues:
    types: [opened]

jobs:
  trigger-pipeline:
    runs-on: ubuntu-latest
    steps:
      - name: Trigger Pipeline
        run: |
          curl -X POST http://your-api-server/webhook/trigger \
            -H "Content-Type: application/json" \
            -d '{
              "task": "${{ github.event.issue.title }}",
              "repo_path": ".",
              "issue_id": "#${{ github.event.issue.number }}",
              "github_repo": "${{ github.repository }}",
              "issue_url": "${{ github.event.issue.html_url }}",
              "metadata": {
                "github_event": "issue_opened",
                "issue_number": ${{ github.event.issue.number }}
              }
            }'
```

## Pipeline Status

Pipeline execution goes through these states:
1. **pending**: Pipeline created but not started
2. **running**: Pipeline execution in progress
3. **completed**: Pipeline finished successfully
4. **failed**: Pipeline failed with error

## Callback Support

If `callback_url` is provided in the request, the API will send a POST request to that URL when the pipeline completes (successfully or with failure). The callback payload is the same as the `/pipeline/{pipeline_id}` response.

## Error Handling

The API returns appropriate HTTP status codes:
- `400 Bad Request`: Invalid request payload
- `404 Not Found`: Resource not found
- `422 Unprocessable Entity`: Validation error
- `500 Internal Server Error`: Server error

Validation errors include detailed messages about what went wrong.

## Configuration

The API can be configured via environment variables:

| Variable | Default | Description |
|----------|---------|-------------|
| `WEBHOOK_HOST` | `0.0.0.0` | Host to bind to |
| `WEBHOOK_PORT` | `8000` | Port to listen on |
| `WEBHOOK_LOG_LEVEL` | `INFO` | Logging level |

Example:
```bash
WEBHOOK_PORT=8080 WEBHOOK_LOG_LEVEL=DEBUG uv run webhook
```

## Architecture

The webhook API:
1. Accepts HTTP requests with pipeline parameters
2. Validates payload using Pydantic models
3. Starts pipeline execution asynchronously
4. Returns immediate response with webhook ID
5. Tracks pipeline status in memory (in production, use a database)
6. Optionally sends callbacks to external URLs
7. Provides status endpoints for monitoring

## Production Considerations

For production use:
1. Add authentication (API keys, JWT tokens)
2. Use a database (PostgreSQL, Redis) for pipeline status storage
3. Implement rate limiting
4. Add request logging and monitoring
5. Use a process manager (systemd, supervisor)
6. Set up SSL/TLS (via reverse proxy like nginx)
7. Implement retry logic for callbacks