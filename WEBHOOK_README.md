# Code Pipeline Webhook

**Extremely simple** webhook API for triggering code pipeline crews, with **GitHub integration** for issue assignment events.

## Features

- **Two endpoints**: Manual trigger + GitHub webhook
- **GitHub integration**: Processes `issues` events with `assigned` action
- **Signature verification**: HMAC SHA-256 validation for security
- **Simple & synchronous**: No async complexity, no callbacks, no status tracking
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

Trigger pipeline manually with custom parameters.

```bash
curl -X POST http://localhost:8000/webhook/trigger \
  -H "Content-Type: application/json" \
  -d '{
    "task": "Fix login bug",
    "repo_path": ".",
    "branch": "main",
    "dry_run": true,
    "test_command": "pytest",
    "issue_id": "#123",
    "github_repo": "owner/repo"
  }'
```

**Required field**: `task`  
**Optional fields**: `repo_path`, `branch`, `dry_run`, `test_command`, `issue_id`, `github_repo`

### 2. GitHub Webhook
**POST** `/github/webhook`

Process GitHub webhook events. Only handles `issues` events with `assigned` action.

**GitHub Webhook Configuration:**
- **Payload URL**: `https://your-server/github/webhook`
- **Content type**: `application/json`
- **Secret**: Set `GITHUB_WEBHOOK_SECRET` environment variable
- **Events**: Select "Issues" → "Let me select individual events" → Check "Assigned"

**What it does:**
1. Verifies HMAC SHA-256 signature (if secret configured)
2. Checks event type is `issues` and action is `assigned`
3. Extracts: issue title → task, issue number → issue_id, repo full_name → github_repo
4. Triggers pipeline with extracted parameters

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
- ❌ Other issue actions (`opened`, `closed`, `labeled`, etc.)
- ❌ Other GitHub events (`push`, `pull_request`, etc.)

### Payload Mapping
GitHub payload → Pipeline parameters:
- `issue.title` → `task`
- `issue.number` → `issue_id` (formatted as `#123`)
- `repository.full_name` → `github_repo`
- `issue.html_url` → `issue_url`
- `issue.body` → Included in metadata (truncated to 2000 chars)

### Security
- **Signature verification**: Uses `X-Hub-Signature-256` header
- **Event filtering**: Only processes `issues`/`assigned`
- **Input validation**: Checks required fields exist
- **Error handling**: Returns appropriate HTTP status codes

## Example GitHub Payflow Flow

1. **Issue created** on GitHub: "Fix login page crash"
2. **Issue assigned** to developer
3. **GitHub sends webhook** to `/github/webhook`
4. **Webhook extracts**: task="Fix login page crash", issue_id="#456", github_repo="owner/repo"
5. **Pipeline triggers** with these parameters
6. **AI agents** analyze, plan, implement, review
7. **Result**: Code changes committed to branch

## Testing

### Manual Testing
```bash
# Test manual endpoint
curl -X POST http://localhost:8000/webhook/trigger \
  -H "Content-Type: application/json" \
  -d '{"task": "Test task"}'

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

# Configure GitHub webhook to: https://your-ngrok-url.ngrok.io/github/webhook
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
http POST http://localhost:8000/github/webhook \
  X-GitHub-Event:issues \
  X-Hub-Signature-256:sha256=$(echo -n "$(cat test_payload.json)" | openssl dgst -sha256 -hmac "test_secret" | cut -d' ' -f2) \
  < test_payload.json
```

## Error Responses

| Status | Meaning |
|--------|---------|
| `200` | Success or ignored (non-issue events) |
| `400` | Bad request (missing/invalid fields) |
| `401` | Invalid signature |
| `404` | Not found (health check only) |
| `500` | Internal server error |

## Architecture

**Simple & Synchronous:**
- No async complexity
- No background jobs
- No status tracking
- No callbacks
- No database

**Just:**
1. Receive HTTP request
2. Validate & extract parameters
3. Run pipeline (blocks until complete)
4. Return response

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

To add support for more GitHub events:

1. Add new condition in `/github/webhook` endpoint:
```python
if action == "opened":
    # Handle issue opened
elif action == "labeled":
    # Handle issue labeled
```

2. Create extraction function for that event type
3. Update documentation

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
- Pipeline runs synchronously (blocks)
- GitHub expects response within 10 seconds
- Consider timeouts for long-running pipelines