"""Tests for file operations - real file I/O to temp directories."""

import subprocess
from pathlib import Path

import pytest


@pytest.mark.unit
class TestFileOperations:
    """Tests for real file operations using temp directories."""

    def test_file_writer_creates_file(self, tmp_path):
        """Test that file writer creates file in correct location."""
        from mycrew.tools.repo_file_writer_tool import RepoFileWriterTool

        tool = RepoFileWriterTool(repo_path=str(tmp_path))

        # Create a new file
        content = "def new_feature():\n    return True\n"
        tool._run("src/new_feature.py", content)

        # Verify file was created
        file_path = tmp_path / "src" / "new_feature.py"
        assert file_path.exists(), f"File should exist at {file_path}"

    def test_write_to_nested_directory(self, tmp_path):
        """Test writing to nested directory creates parents."""
        from mycrew.tools.repo_file_writer_tool import RepoFileWriterTool

        tool = RepoFileWriterTool(repo_path=str(tmp_path))

        # Write to deeply nested path
        content = "nested content\n"
        tool._run("deeply/nested/path/file.txt", content)

        # Verify nested directories were created
        file_path = tmp_path / "deeply" / "nested" / "path" / "file.txt"
        assert file_path.exists()
        assert file_path.read_text() == content
