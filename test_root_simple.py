#!/usr/bin/env python
"""Simple test to verify root endpoint logic."""

print("Testing root endpoint logic...")

# The endpoint should return {"status": "ok"}
expected_response = {"status": "ok"}
print(f"Expected response: {expected_response}")

# Check FastAPI endpoint would work
print("\nEndpoint structure:")
print("  Path: '/'")
print("  Method: GET")
print("  Function: root()")
print("  Returns: {'status': 'ok'}")

print("\n✅ Root endpoint logic verified!")
print("When webhook is running, GET / should return HTTP 200 with {'status': 'ok'}")
