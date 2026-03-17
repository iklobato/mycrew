"""Tools package for mycrew - uses native crewai_tools and custom tactiq tool."""

import os
import requests
from crewai.tools import BaseTool
from crewai_tools import (
    DirectoryReadTool,
    FileReadTool,
    SerperDevTool,
    EXASearchTool,
    ScrapeWebsiteTool,
    CodeInterpreterTool,
)
from pydantic import Field


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
    "SerperDevTool",
    "EXASearchTool",
    "ScrapeWebsiteTool",
    "CodeInterpreterTool",
    "TactiqMeetingTool",
]
