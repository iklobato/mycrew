#!/usr/bin/env python
"""Example of using the Code Pipeline Webhook API."""

import asyncio
import json
import sys
from typing import Dict, Any

import httpx


async def trigger_pipeline(
    base_url: str = "http://localhost:8000",
    payload: Dict[str, Any] | None = None,
) -> None:
    """Trigger a pipeline via the webhook API."""

    if payload is None:
        payload = {
            "issue_url": "https://github.com/precisetargetlabs/monarch/issues/836",
            "branch": "main",
            "dry_run": True,
            "test_command": "pytest",
        }

    print("Triggering pipeline...")
    print(f"Payload:\n{json.dumps(payload, indent=2)}")

    try:
        async with httpx.AsyncClient(timeout=30.0) as client:
            # Trigger the pipeline
            response = await client.post(
                f"{base_url}/webhook",
                json=payload,
                headers={"Content-Type": "application/json"},
            )

            if response.status_code == 202:
                data = response.json()
                if data.get("status") == "accepted":
                    print("\n✅ Pipeline triggered successfully!")
                    print(f"Issue: {data.get('issue_url', '')}")
                else:
                    print(f"\n❌ Unexpected response: {data}")
            else:
                print(f"\n❌ Failed to trigger pipeline: {response.status_code}")
                print(f"Response: {response.text}")

    except httpx.ConnectError:
        print(f"\n❌ Could not connect to {base_url}")
        print("Make sure the webhook API is running:")
        print("  uv run webhook")
        sys.exit(1)
    except Exception as e:
        print(f"\n❌ Error: {e}")
        sys.exit(1)


async def check_health(base_url: str = "http://localhost:8000") -> bool:
    """Check if the API is healthy."""
    try:
        async with httpx.AsyncClient(timeout=5.0) as client:
            response = await client.get(f"{base_url}/health")
            if response.status_code == 200:
                data = response.json()
                print(f"✅ API is healthy: {data}")
                return True
            else:
                print(f"❌ API health check failed: {response.status_code}")
                return False
    except Exception as e:
        print(f"❌ Could not connect to API: {e}")
        return False


async def get_api_info(base_url: str = "http://localhost:8000") -> None:
    """Get API information."""
    print("API Endpoints:")
    print("  POST /webhook  - Trigger pipeline (manual or GitHub webhook)")
    print("  GET  /health  - Health check")


async def main():
    """Run the example."""
    base_url = "http://localhost:8000"

    print("=" * 60)
    print("Code Pipeline Webhook API Example")
    print("=" * 60)

    # Check if API is running
    print("\n1. Checking API health...")
    if not await check_health(base_url):
        print("\n⚠️  API is not running. Start it with:")
        print("  cd /path/to/mycrew")
        print("  uv run webhook")
        print("\nThen run this example again.")
        return

    # Get API info
    print("\n2. Getting API information...")
    await get_api_info(base_url)

    # Trigger a pipeline
    print("\n3. Triggering a pipeline...")
    await trigger_pipeline(base_url)

    print("\n" + "=" * 60)
    print("Example complete!")
    print("=" * 60)
    print("\nNext steps:")
    print("1. Check the webhook API logs for pipeline execution")
    print("2. Visit http://localhost:8000/docs for interactive API documentation")
    print("3. Modify the payload in this script for different tasks")


if __name__ == "__main__":
    asyncio.run(main())
