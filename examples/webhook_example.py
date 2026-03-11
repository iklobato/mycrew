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

    # Default payload if not provided
    if payload is None:
        payload = {
            "task": "Create a simple hello world API endpoint",
            "repo_path": ".",
            "branch": "main",
            "from_scratch": False,
            "max_retries": 2,
            "dry_run": True,  # Don't actually commit
            "test_command": "python -m pytest tests/ -xvs",
            "issue_id": "#999",
            "github_repo": "example/example-repo",
            "issue_url": "https://github.com/example/example-repo/issues/999",
            "docs_url": "",
            "serper_enabled": False,
            "serper_n_results": 5,
            "metadata": {"example": True, "purpose": "demonstration"},
        }

    print("Triggering pipeline...")
    print(f"Payload:\n{json.dumps(payload, indent=2)}")

    try:
        async with httpx.AsyncClient(timeout=30.0) as client:
            # Trigger the pipeline
            response = await client.post(
                f"{base_url}/webhook/trigger",
                json=payload,
                headers={"Content-Type": "application/json"},
            )

            if response.status_code == 202:
                data = response.json()
                webhook_id = data["webhook_id"]
                pipeline_id = data.get("pipeline_id")

                print(f"\n✅ Pipeline triggered successfully!")
                print(f"Webhook ID: {webhook_id}")
                if pipeline_id:
                    print(f"Pipeline ID: {pipeline_id}")
                print(f"Message: {data['message']}")

                # Wait a bit and check status
                await asyncio.sleep(2)

                # Check webhook status
                status_response = await client.get(
                    f"{base_url}/webhook/status/{webhook_id}",
                )

                if status_response.status_code == 200:
                    status_data = status_response.json()
                    print(f"\nWebhook Status: {status_data['status']}")
                    print(f"Status Message: {status_data['message']}")

                    # If we have a pipeline ID, check pipeline status
                    if pipeline_id:
                        pipeline_response = await client.get(
                            f"{base_url}/pipeline/{pipeline_id}",
                        )

                        if pipeline_response.status_code == 200:
                            pipeline_data = pipeline_response.json()
                            print(f"\nPipeline Status: {pipeline_data['status']}")
                            if pipeline_data.get("started_at"):
                                print(f"Started at: {pipeline_data['started_at']}")
                            if pipeline_data.get("completed_at"):
                                print(f"Completed at: {pipeline_data['completed_at']}")
                            if pipeline_data.get("error"):
                                print(f"Error: {pipeline_data['error']}")
                else:
                    print(
                        f"\n⚠️ Could not get webhook status: {status_response.status_code}"
                    )

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
    try:
        async with httpx.AsyncClient(timeout=5.0) as client:
            response = await client.get(base_url)
            if response.status_code == 200:
                data = response.json()
                print("API Information:")
                print(f"Name: {data['name']}")
                print(f"Version: {data['version']}")
                print("\nAvailable Endpoints:")
                for endpoint in data["endpoints"]:
                    print(
                        f"  {endpoint['method']} {endpoint['path']} - {endpoint['description']}"
                    )
            else:
                print(f"Failed to get API info: {response.status_code}")
    except Exception as e:
        print(f"Error getting API info: {e}")


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
        print("  cd /Users/iklo/crew/code_pipeline")
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
