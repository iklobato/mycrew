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

echo "Testing root endpoint..."
curl http://localhost:8080/

echo "Testing health endpoint..."
curl http://localhost:8080/health

echo "Testing manual trigger endpoint..."
curl -X POST http://localhost:8080/webhook/trigger \
  -H "Content-Type: application/json" \
  -d '{"task": "Test Docker build"}' \
  --max-time 10

echo "Stopping container..."
docker stop $(docker ps | grep code-pipeline-webhook-test | awk '{print $1}')