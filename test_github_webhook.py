#!/usr/bin/env python
"""Test the GitHub webhook integration."""

import json
import os
import sys
from pathlib import Path

# Add src to path
sys.path.insert(0, str(Path(__file__).parent / "src"))

from code_pipeline.webhook import (
    verify_github_signature,
    extract_pipeline_params_from_github,
    IssueAssignedHandler,
    PRCommentCreatedHandler,
)


def test_signature_verification():
    """Test GitHub signature verification."""
    print("Testing signature verification...")

    # Test data
    secret = "mysecret"
    payload = b'{"test": "data"}'

    # Create a valid signature
    import hmac
    import hashlib

    hash_object = hmac.new(
        secret.encode("utf-8"), msg=payload, digestmod=hashlib.sha256
    )
    valid_signature = "sha256=" + hash_object.hexdigest()

    # Set environment variable
    os.environ["GITHUB_WEBHOOK_SECRET"] = secret

    try:
        # Test valid signature
        verify_github_signature(payload, valid_signature)
        print("  ✓ Valid signature passes")

        # Test invalid signature
        try:
            verify_github_signature(payload, "sha256=invalid")
            print("  ✗ Invalid signature should fail")
            return False
        except Exception:
            print("  ✓ Invalid signature fails as expected")

        # Test missing signature when secret is set
        try:
            verify_github_signature(payload, "")
            print("  ✗ Missing signature should fail when secret is set")
            return False
        except Exception:
            print("  ✓ Missing signature fails when secret is set")

        # Test no secret configured (should pass without verification)
        os.environ.pop("GITHUB_WEBHOOK_SECRET", None)
        verify_github_signature(payload, "")
        print("  ✓ No verification when secret not configured")

        return True

    except Exception as e:
        print(f"  ✗ Signature verification test failed: {e}")
        return False


def test_payload_extraction():
    """Test extracting pipeline parameters from GitHub payload."""
    print("\nTesting payload extraction...")

    # Sample GitHub issue assignment payload
    sample_payload = {
        "action": "assigned",
        "issue": {
            "number": 123,
            "title": "Fix login page bug",
            "html_url": "https://github.com/owner/repo/issues/123",
            "body": "The login page crashes when submitting empty form.",
            "labels": [{"name": "bug"}, {"name": "high-priority"}],
        },
        "repository": {
            "full_name": "owner/repo",
            "name": "repo",
            "owner": {"login": "owner"},
        },
        "assignee": {"login": "developer1", "id": 456},
        "sender": {"login": "project-manager", "id": 789},
    }

    try:
        params = extract_pipeline_params_from_github(sample_payload, "issues")

        # Check extracted parameters
        expected = {
            "task": "Fix login page bug",
            "repo_path": ".",
            "issue_id": "#123",
            "github_repo": "owner/repo",
            "issue_url": "https://github.com/owner/repo/issues/123",
            "dry_run": False,  # Default from env
            "branch": "main",  # Default from env
        }

        all_good = True
        for key, expected_value in expected.items():
            actual_value = params.get(key)
            if actual_value != expected_value:
                print(f"  ✗ {key}: expected {expected_value!r}, got {actual_value!r}")
                all_good = False
            else:
                print(f"  ✓ {key}: {actual_value!r}")

        # Check metadata
        metadata = params.get("metadata", {})
        if "github_issue_body" in metadata:
            print(
                f"  ✓ Issue body included in metadata ({len(metadata['github_issue_body'])} chars)"
            )
        else:
            print("  ✗ Issue body not in metadata")
            all_good = False

        return all_good

    except Exception as e:
        print(f"  ✗ Payload extraction test failed: {e}")
        return False


def test_invalid_payloads():
    """Test handling of invalid payloads."""
    print("\nTesting invalid payload handling...")

    test_cases = [
        ("Missing issue", {"repository": {"full_name": "owner/repo"}}),
        ("Missing repository", {"issue": {"title": "Test", "number": 1}}),
        (
            "Empty issue title",
            {
                "issue": {"title": "", "number": 1},
                "repository": {"full_name": "owner/repo"},
            },
        ),
        (
            "Missing repo full_name",
            {"issue": {"title": "Test", "number": 1}, "repository": {}},
        ),
    ]

    all_good = True
    for name, payload in test_cases:
        try:
            extract_pipeline_params_from_github(payload, "issues")
            print(f"  ✗ {name}: Should have raised exception")
            all_good = False
        except Exception as e:
            print(f"  ✓ {name}: Correctly raised {type(e).__name__}")

    return all_good


def test_event_handler_abstraction():
    """Test the GitHub event handler abstraction."""
    print("\nTesting event handler abstraction...")

    try:
        # Test IssueAssignedHandler
        issue_payload = {
            "issue": {
                "number": 123,
                "title": "Fix login bug",
                "html_url": "https://github.com/owner/repo/issues/123",
                "body": "Login fails on mobile",
            },
            "repository": {"full_name": "owner/repo"},
        }

        issue_handler = IssueAssignedHandler(issue_payload, "owner/repo")
        issue_params = issue_handler.get_pipeline_params()

        assert issue_params["task"] == "Fix login bug"
        assert issue_params["issue_id"] == "#123"
        assert issue_params["github_repo"] == "owner/repo"
        print("  ✓ IssueAssignedHandler works correctly")

        # Test PRCommentCreatedHandler
        pr_comment_payload = {
            "comment": {
                "id": 456,
                "html_url": "https://github.com/owner/repo/pull/42#issuecomment-456",
                "body": "Add error handling",
                "user": {"login": "reviewer"},
            },
            "pull_request": {
                "number": 42,
                "title": "Auth middleware",
                "body": "Adds authentication",
                "html_url": "https://github.com/owner/repo/pull/42",
            },
            "repository": {"full_name": "owner/repo"},
        }

        pr_handler = PRCommentCreatedHandler(pr_comment_payload, "owner/repo")
        pr_params = pr_handler.get_pipeline_params()

        assert (
            "Address PR comment on 'Auth middleware': Add error handling"
            in pr_params["task"]
        )
        assert pr_params["issue_id"] == "PR#42"
        assert pr_params["github_repo"] == "owner/repo"
        print("  ✓ PRCommentCreatedHandler works correctly")

        # Test validation
        try:
            invalid_handler = IssueAssignedHandler({}, "owner/repo")
            invalid_handler.validate()
            print("  ✗ Should fail validation with empty payload")
            return False
        except Exception:
            print("  ✓ Validation fails correctly for invalid payload")

        return True

    except Exception as e:
        print(f"  ✗ Event handler abstraction test failed: {e}")
        return False


def test_pr_comment_extraction():
    """Test extracting pipeline parameters from PR comment payload."""
    print("\nTesting PR comment payload extraction...")

    # Sample GitHub PR comment payload
    sample_payload = {
        "action": "created",
        "comment": {
            "id": 123456789,
            "html_url": "https://github.com/owner/repo/pull/42#issuecomment-123456789",
            "body": "This function needs better error handling. Can you add try-catch blocks?",
            "user": {"login": "code-reviewer"},
        },
        "pull_request": {
            "number": 42,
            "title": "Add user authentication middleware",
            "body": "This PR adds JWT-based authentication middleware.",
            "html_url": "https://github.com/owner/repo/pull/42",
        },
        "repository": {
            "full_name": "owner/repo",
            "name": "repo",
            "owner": {"login": "owner"},
        },
        "sender": {"login": "code-reviewer"},
    }

    try:
        params = extract_pipeline_params_from_github(
            sample_payload, "pull_request_review_comment"
        )

        # Check extracted parameters
        expected_task_start = "Address PR comment on 'Add user authentication middleware': This function needs better error handling"
        actual_task = params.get("task", "")

        if not actual_task.startswith(expected_task_start[:50]):
            print(
                f"  ✗ Task mismatch: expected to start with {expected_task_start[:50]!r}, got {actual_task[:50]!r}"
            )
            return False
        else:
            print(f"  ✓ Task: {actual_task[:80]}...")

        # Check other parameters
        checks = [
            ("issue_id", "PR#42"),
            ("github_repo", "owner/repo"),
            ("dry_run", False),
            ("branch", "main"),
        ]

        all_good = True
        for key, expected_value in checks:
            actual_value = params.get(key)
            if actual_value != expected_value:
                print(f"  ✗ {key}: expected {expected_value!r}, got {actual_value!r}")
                all_good = False
            else:
                print(f"  ✓ {key}: {actual_value!r}")

        # Check metadata
        metadata = params.get("metadata", {})
        required_metadata = [
            "github_comment_body",
            "github_pr_title",
            "github_pr_number",
            "github_comment_author",
        ]

        for key in required_metadata:
            if key not in metadata:
                print(f"  ✗ Missing metadata key: {key}")
                all_good = False
            else:
                print(f"  ✓ Metadata {key}: present")

        return all_good

    except Exception as e:
        print(f"  ✗ PR comment extraction test failed: {e}")
        return False


def test_manual_trigger_model():
    """Test the manual trigger request model."""
    print("\nTesting manual trigger model...")

    from code_pipeline.webhook import TriggerRequest
    from pydantic import ValidationError

    try:
        # Test valid request
        req = TriggerRequest(task="Test task")
        assert req.task == "Test task"
        assert req.repo_path == "."
        assert req.branch == "main"
        assert req.dry_run is False
        print("  ✓ Valid request with defaults")

        # Test with all fields
        req = TriggerRequest(
            task="Another task",
            repo_path="/tmp",
            branch="develop",
            dry_run=True,
            test_command="pytest",
            issue_id="#456",
            github_repo="owner/repo",
        )
        assert req.task == "Another task"
        assert req.repo_path == "/tmp"
        assert req.branch == "develop"
        assert req.dry_run is True
        assert req.test_command == "pytest"
        assert req.issue_id == "#456"
        assert req.github_repo == "owner/repo"
        print("  ✓ Valid request with all fields")

        # Test missing required field
        try:
            TriggerRequest()
            print("  ✗ Should require 'task' field")
            return False
        except ValidationError:
            print("  ✓ Missing 'task' raises ValidationError")

        return True

    except Exception as e:
        print(f"  ✗ Manual trigger model test failed: {e}")
        return False


def main():
    """Run all tests."""
    print("=" * 60)
    print("GitHub Webhook Integration Tests")
    print("=" * 60)

    # Set default environment for tests
    os.environ["DEFAULT_DRY_RUN"] = "false"
    os.environ["DEFAULT_BRANCH"] = "main"

    tests = [
        ("Signature Verification", test_signature_verification),
        ("Payload Extraction", test_payload_extraction),
        ("Invalid Payloads", test_invalid_payloads),
        ("Event Handler Abstraction", test_event_handler_abstraction),
        ("PR Comment Extraction", test_pr_comment_extraction),
        ("Manual Trigger Model", test_manual_trigger_model),
    ]

    results = []
    for test_name, test_func in tests:
        print(f"\n{test_name}:")
        try:
            success = test_func()
            results.append((test_name, success))
        except Exception as e:
            print(f"  ✗ Test crashed: {e}")
            results.append((test_name, False))

    # Summary
    print("\n" + "=" * 60)
    print("Test Summary:")
    print("=" * 60)

    passed = 0
    total = len(results)

    for test_name, success in results:
        status = "✓ PASS" if success else "✗ FAIL"
        print(f"{status}: {test_name}")
        if success:
            passed += 1

    print(f"\n{passed}/{total} tests passed")

    if passed == total:
        print("\n✅ All tests passed!")
        return 0
    else:
        print("\n❌ Some tests failed")
        return 1


if __name__ == "__main__":
    sys.exit(main())
