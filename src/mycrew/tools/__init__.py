"""Tools package for mycrew - uses native crewai_tools and custom tactiq tool."""

import os
import requests
from crewai.tools import BaseTool
from crewai_tools import (
    DirectoryReadTool,
    FileReadTool,
    FileWriterTool,
    SerperDevTool,
    EXASearchTool,
    ScrapeWebsiteTool,
    CodeInterpreterTool,
)
from pydantic import Field


class WriteFileTool(BaseTool):
    """Tool for writing content to a file directly on the filesystem."""

    name: str = "write_file"
    description: str = "Write content to a file at the specified path. Creates the file if it doesn't exist."

    def _run(self, file_path: str = "", content: str = "") -> str:
        """Write content to a file."""
        if not file_path:
            return "Error: file_path is required"

        try:
            os.makedirs(os.path.dirname(file_path), exist_ok=True)
            with open(file_path, "w") as f:
                f.write(content)
            return f"Successfully wrote to {file_path}"
        except Exception as e:
            return f"Error writing to {file_path}: {str(e)}"


class TactiqMeetingTool(BaseTool):
    """Tool for fetching meeting context from Tactiq."""

    name: str = "tactiq_meeting"
    description: str = (
        "Fetch meeting details and ask AI questions about meeting context"
    )

    tactiq_token: str = Field(default="")

    def __init__(self, **data):
        super().__init__(**data)
        if not self.tactiq_token:
            self.tactiq_token = os.environ.get("TACTIQ_TOKEN", "")

    def _run(
        self,
        meeting_id: str = "",
        question: str = "",
    ) -> str:
        """Fetch meeting details or ask questions about meeting content."""
        if not self.tactiq_token:
            return "Error: TACTIQ_TOKEN not configured"

        if not meeting_id:
            return "Error: meeting_id is required"

        headers = {
            "Authorization": f"Bearer {self.tactiq_token}",
            "Content-Type": "application/json",
        }

        try:
            if question:
                url = f"https://api.tactiq.io/meetings/{meeting_id}/ask"
                response = requests.post(
                    url,
                    json={"question": question},
                    headers=headers,
                    timeout=30,
                )
            else:
                url = f"https://api.tactiq.io/meetings/{meeting_id}"
                response = requests.get(url, headers=headers, timeout=30)

            if response.status_code == 200:
                return str(response.json())
            else:
                return f"Error: {response.status_code} - {response.text}"
        except Exception as e:
            return f"Error: {str(e)}"


__all__ = [
    "DirectoryReadTool",
    "FileReadTool",
    "FileWriterTool",
    "WriteFileTool",
    "SerperDevTool",
    "EXASearchTool",
    "ScrapeWebsiteTool",
    "CodeInterpreterTool",
    "TactiqMeetingTool",
]
