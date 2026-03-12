#!/usr/bin/env python3
"""Test script to verify callback URL functionality."""

import json
import threading
import time
from http.server import HTTPServer, BaseHTTPRequestHandler
from typing import Any

import requests


class CallbackHandler(BaseHTTPRequestHandler):
    """Simple HTTP server to receive callbacks."""

    received_callbacks: list[dict[str, Any]] = []

    def do_POST(self) -> None:
        """Handle POST requests (callbacks)."""
        content_length = int(self.headers.get("Content-Length", 0))
        post_data = self.rfile.read(content_length)
        data = json.loads(post_data.decode("utf-8"))

        print(f"Callback received: {json.dumps(data, indent=2)}")
        self.received_callbacks.append(data)

        self.send_response(200)
        self.send_header("Content-Type", "application/json")
        self.end_headers()
        self.wfile.write(json.dumps({"status": "ok"}).encode("utf-8"))

    def log_message(self, format: str, *args: Any) -> None:
        """Suppress default logging."""
        pass


def start_test_server(port: int = 9999) -> HTTPServer:
    """Start a test HTTP server to receive callbacks."""
    server = HTTPServer(("localhost", port), CallbackHandler)
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    print(f"Test callback server started on http://localhost:{port}")
    return server


def test_callback_feature() -> None:
    """Test the callback URL feature."""
    # Start test server
    server = start_test_server(9999)

    # Give server time to start
    time.sleep(1)

    # Clear any previous callbacks
    CallbackHandler.received_callbacks.clear()

    # Test data
    test_payload = {
        "task": "Test callback feature",
        "repo_path": "/tmp/test_repo",
        "branch": "main",
        "dry_run": True,  # Use dry_run to avoid actual pipeline execution
        "callback_url": "http://localhost:9999/callback",
    }

    print(f"Sending test request with callback_url: {test_payload['callback_url']}")

    try:
        # Send request to webhook API
        response = requests.post(
            "http://localhost:8000/webhook/trigger",
            json=test_payload,
            headers={"Content-Type": "application/json"},
            timeout=10,
        )

        print(f"Response status: {response.status_code}")
        if response.status_code == 202:
            print(f"Response: {response.json()}")
        else:
            print(f"Error: {response.text}")

        # Wait for callback (should be quick with dry_run=True)
        print("Waiting for callback...")
        time.sleep(3)

        # Check if callback was received
        if CallbackHandler.received_callbacks:
            print(
                f"\n✓ Callback received! Total callbacks: {len(CallbackHandler.received_callbacks)}"
            )
            for i, callback in enumerate(CallbackHandler.received_callbacks, 1):
                print(f"\nCallback {i}:")
                print(f"  Status: {callback.get('status')}")
                print(f"  Result: {callback.get('result', 'N/A')}")
                print(f"  Error: {callback.get('error', 'N/A')}")
        else:
            print("\n✗ No callback received")

    except requests.exceptions.ConnectionError:
        print("✗ Could not connect to webhook API. Is it running?")
        print("  Start it with: uv run webhook")
    except Exception as e:
        print(f"✗ Error: {e}")
    finally:
        # Cleanup
        server.shutdown()
        print("\nTest server stopped")


if __name__ == "__main__":
    print("Testing callback URL feature...")
    test_callback_feature()
