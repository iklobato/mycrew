#!/bin/bash
# Test Dockerfile for webhook functionality

echo "Building Docker image..."
docker build -t code-pipeline-webhook-test .

echo "Running container..."
docker run -p 8080:8080 \
  -e GITHUB_WEBHOOK_SECRET="test" \
  -e DEFAULT_DRY_RUN="true" \
  code-pipeline-webhook-test &

echo "Waiting for container to start..."
sleep 5

echo "Testing health endpoint..."
curl http://localhost:8080/health

echo "Testing webhook endpoint..."
curl -X POST http://localhost:8080/webhook \
  -H "Content-Type: application/json" \
  -d '{"issue_url": "https://github.com/owner/repo/issues/1"}' \
  --max-time 10

echo "Stopping container..."
docker stop $(docker ps | grep code-pipeline-webhook-test | awk '{print $1}')