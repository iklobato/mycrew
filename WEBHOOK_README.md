# Code Pipeline Webhook

**Extremely simple** webhook API for triggering code pipeline crews, with **GitHub integration** for issue assignment events.

## Features

- **Two endpoints**: Manual trigger + single webhook (provider detected from headers)
- **GitHub integration**: Processes `issues`/`assigned` and `pull_request_review_comment`/`created`
- **Signature verification**: HMAC SHA-256 validation for security
- **Background execution**: Returns 202 Accepted immediately; pipeline runs in background (avoids webhook timeouts)
- **Minimal dependencies**: FastAPI + uvicorn only

## Installation

```bash
uv sync
```

## Running

```bash
# Basic (no GitHub secret)
uv run webhook

# With GitHub webhook secret
GITHUB_WEBHOOK_SECRET=your_secret_token uv run webhook

# With custom port
PORT=8080 uv run webhook
```

## Endpoints

### 1. Manual Trigger
**POST** `/webhook/trigger`

Trigger pipeline manually. Returns **202 Accepted** immediately; pipeline runs in background.

```bash
curl -X POST http://localhost:8000/webhook/trigger \
  -H "Content-Type: application/json" \
  -d '{
    "issue_url": "https://github.com/owner/repo/issues/123",
    "branch": "main",
    "dry_run": true,
    "test_command": "pytest"
  }'
```

**Required field**: `issue_url` (GitHub issue or PR URL)  
**Optional fields**: `branch`, `dry_run`, `test_command`

### 2. Webhook (GitHub)
**POST** `/webhook`

Single webhook endpoint. Provider detected from headers (`X-GitHub-Event` for GitHub). Returns **202 Accepted** immediately; pipeline runs in background.

**GitHub Webhook Configuration:**
- **Payload URL**: `https://your-server/webhook`
- **Content type**: `application/json`
- **Secret**: Set `GITHUB_WEBHOOK_SECRET` environment variable
- **Events**: Select "Issues" → "Let me select individual events" → Check "Assigned"

**What it does:**
1. Detects GitHub from `X-GitHub-Event` header
2. Verifies HMAC SHA-256 signature (if secret configured)
3. Extracts `issue_url` from payload (config-driven: issues/assigned, pull_request_review_comment/created)
4. Queues pipeline in background and returns 202 Accepted immediately

## Environment Variables

| Variable | Default | Description |
|----------|---------|-------------|
| `GITHUB_WEBHOOK_SECRET` | (none) | GitHub webhook secret for signature verification |
| `DEFAULT_DRY_RUN` | `false` | Default dry_run setting for GitHub triggers |
| `DEFAULT_BRANCH` | `main` | Default branch for GitHub triggers |
| `PORT` | `8000` | Port to listen on |
| `HOST` | `0.0.0.0` | Host to bind to |

## GitHub Integration Details

### Supported Events
- ✅ `issues` → `assigned` (issue assigned to someone)
- ✅ `pull_request_review_comment` → `created` (comment on PR)
- ❌ Other issue/PR actions
- ❌ Other GitHub events (`push`, etc.)

### Payload Mapping
GitHub payload → Pipeline parameters (path from `GitHubWebhookEvent` enum config):
- `issue.html_url` or `pull_request.html_url` → `issue_url`
- `branch`, `dry_run` from settings

### Security
- **Signature verification**: Uses `X-Hub-Signature-256` header
- **Event filtering**: Only processes `issues`/`assigned`
- **Input validation**: Checks required fields exist
- **Error handling**: Returns appropriate HTTP status codes

## Example GitHub Payflow Flow

1. **Issue created** on GitHub: "Fix login page crash"
2. **Issue assigned** to developer
3. **GitHub sends webhook** to `/webhook`
4. **Webhook queues** pipeline and returns 202
5. **Pipeline runs** in background with extracted parameters
6. **AI agents** analyze, plan, implement, review
7. **Result**: Code changes committed to branch

## Testing

### Manual Testing
```bash
# Test manual endpoint
curl -X POST http://localhost:8000/webhook/trigger \
  -H "Content-Type: application/json" \
  -d '{"issue_url": "https://github.com/owner/repo/issues/123"}'

# Test health check
curl http://localhost:8000/health
```

### GitHub Webhook Testing
Use [ngrok](https://ngrok.com/) for local testing:

```bash
# Start webhook
GITHUB_WEBHOOK_SECRET=test_secret uv run webhook

# In another terminal
ngrok http 8000

# Configure GitHub webhook to: https://your-ngrok-url.ngrok.io/webhook
```

Or use [httpie](https://httpie.io/) to simulate:

```bash
# Create test payload
echo '{
  "action": "assigned",
  "issue": {
    "number": 123,
    "title": "Test issue",
    "html_url": "https://github.com/owner/repo/issues/123",
    "body": "Test description"
  },
  "repository": {
    "full_name": "owner/repo"
  },
  "assignee": {"login": "testuser"}
}' > test_payload.json

# Send with headers
http POST http://localhost:8000/webhook \
  X-GitHub-Event:issues \
  X-Hub-Signature-256:sha256=$(echo -n "$(cat test_payload.json)" | openssl dgst -sha256 -hmac "test_secret" | cut -d' ' -f2) \
  < test_payload.json
```

## Error Responses

| Status | Meaning |
|--------|---------|
| `200` | Ignored (unsupported event/action) |
| `202` | Accepted — pipeline queued, runs in background |
| `400` | Bad request (missing/invalid fields, unknown provider) |
| `403` | Invalid signature |
| `500` | Internal server error (validation, etc.) |

## Architecture

**Simple & Background:**
- FastAPI BackgroundTasks (no extra dependencies)
- Pipeline runs in thread pool after response sent
- No status tracking, callbacks, or database
- Failures logged (not returned to client)

**Flow:**
1. Receive HTTP request
2. Validate & extract parameters
3. Queue pipeline in background, return 202 immediately
4. Pipeline runs after response sent; errors logged

## Comparison with Previous Version

| Feature | Previous (508 lines) | Current (258 lines) |
|---------|---------------------|---------------------|
| Endpoints | 5+ | 3 |
| Dependencies | FastAPI + uvicorn + httpx | FastAPI + uvicorn |
| Async/await | Yes | No |
| Status tracking | Yes | No |
| Callbacks | Yes | No |
| GitHub integration | No | Yes |
| Code complexity | High | Low |

## Extending

To add support for more GitHub events, add a new member to `GitHubWebhookEvent` in `webhook.py`:

```python
class GitHubWebhookEvent(Enum):
    ...
    ISSUES_OPENED = _EventConfig(
        path=("issue", "html_url"),
        validations=[],
        event="issues",
        action="opened",
    )
```

To add another provider (e.g. GitLab), add an `elif headers.get("x-gitlab-event")` block and a `_handle_gitlab` function.

## Troubleshooting

**Webhook not receiving events:**
- Check GitHub webhook configuration
- Verify `GITHUB_WEBHOOK_SECRET` matches
- Check server logs: `uv run webhook`

**Signature verification fails:**
- Ensure secret is set on both GitHub and server
- Check for trailing whitespace in secret
- Verify payload isn't being modified

**Pipeline not triggering:**
- Check webhook logs for errors
- Verify required fields in GitHub payload
- Check pipeline dependencies/config

**Slow responses:**
- Pipeline runs in background; HTTP response returns 202 immediately
- GitHub expects response within ~10 seconds; this design avoids timeouts