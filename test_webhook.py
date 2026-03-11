#!/usr/bin/env python
"""Test script for webhook API."""

import json
import subprocess
import sys
import time
from pathlib import Path

import requests


def test_webhook_api():
    """Test the webhook API with a sample payload."""

    # Sample payload
    payload = {
        "task": "Add a simple hello world function to main.py",
        "repo_path": ".",
        "branch": "main",
        "from_scratch": False,
        "max_retries": 2,
        "dry_run": True,  # Don't actually commit
        "test_command": "python -c 'print(\"Test passed\")'",
        "issue_id": "#123",
        "github_repo": "test/example",
        "issue_url": "https://github.com/test/example/issues/123",
        "docs_url": "",
        "serper_enabled": False,
        "serper_n_results": 5,
        "callback_url": "http://localhost:8080/callback",  # This won't exist, but that's OK
        "metadata": {"source": "test_script", "priority": "low"},
    }

    print("Testing webhook API...")
    print(f"Payload: {json.dumps(payload, indent=2)}")

    try:
        # Send POST request to webhook endpoint
        response = requests.post(
            "http://localhost:8000/webhook/trigger",
            json=payload,
            headers={"Content-Type": "application/json"},
            timeout=10,
        )

        print(f"\nResponse Status: {response.status_code}")
        print(f"Response Body: {json.dumps(response.json(), indent=2)}")

        if response.status_code == 202:
            print("\n✅ Webhook API test passed!")
            webhook_id = response.json().get("webhook_id")
            print(f"Webhook ID: {webhook_id}")

            # Try to get status
            time.sleep(1)
            status_response = requests.get(
                f"http://localhost:8000/webhook/status/{webhook_id}", timeout=10
            )
            print(f"\nStatus Response: {status_response.status_code}")
            if status_response.status_code == 200:
                print(f"Status: {json.dumps(status_response.json(), indent=2)}")

            return True
        else:
            print(f"\n❌ Webhook API test failed with status {response.status_code}")
            return False

    except requests.exceptions.ConnectionError:
        print("\n❌ Could not connect to webhook API. Is it running?")
        print("Start it with: uv run webhook")
        return False
    except Exception as e:
        print(f"\n❌ Error testing webhook API: {e}")
        return False


def test_health_check():
    """Test health check endpoint."""
    try:
        response = requests.get("http://localhost:8000/health", timeout=5)
        print(f"\nHealth Check: {response.status_code}")
        print(f"Response: {response.json()}")
        return response.status_code == 200
    except Exception as e:
        print(f"\n❌ Health check failed: {e}")
        return False


def main():
    """Run webhook API tests."""
    print("=" * 60)
    print("Code Pipeline Webhook API Test")
    print("=" * 60)

    # Check if webhook API is running
    print("\n1. Testing health check...")
    if not test_health_check():
        print("\n⚠️  Webhook API might not be running.")
        print("Start it in another terminal with:")
        print("  cd /Users/iklo/crew/code_pipeline")
        print("  uv run webhook")
        print("\nThen run this test again.")
        return

    print("\n2. Testing webhook trigger endpoint...")
    test_webhook_api()

    print("\n" + "=" * 60)
    print("Test complete!")
    print("=" * 60)


if __name__ == "__main__":
    main()
