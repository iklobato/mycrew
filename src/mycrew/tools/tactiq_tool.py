"""Tactiq API Tool for fetching meeting details and asking AI questions."""

import logging
import time
from typing import Any

import requests
from crewai.tools import BaseTool
from pydantic import BaseModel, Field

from mycrew.settings import get_settings

logger = logging.getLogger(__name__)

GRAPHQL_URL = "https://api2.tactiq.io/api/2/graphql"
USER_AGENT = "mycrew (https://github.com/iklobato/mycrew)"
POLL_INTERVAL = 2  # seconds
MAX_POLL_ATTEMPTS = 30


class TactiqToolInput(BaseModel):
    """Input schema for TactiqTool."""

    meeting_id: str = Field(
        ...,
        description="Tactiq meeting ID to fetch information from",
    )
    question: str = Field(
        default="",
        description="Optional question to ask the Tactiq AI about the meeting",
    )


class TactiqTool(BaseTool):
    """Tool for interacting with Tactiq API to get meeting details and ask AI questions."""

    name: str = "TactiqMeetingTool"
    description: str = (
        "Fetch meeting details and ask AI questions from Tactiq. "
        "Use to get implementation context from meeting transcripts, "
        "decisions, and action items. First call without a question to get "
        "meeting details, then call with a question to ask AI about specifics."
    )
    args_schema: type[BaseModel] = TactiqToolInput

    def __init__(self, **kwargs):
        """Initialize with token from settings."""
        super().__init__(**kwargs)
        self._token = None
        self._session = None

    @property
    def token(self) -> str:
        """Get token from settings."""
        if self._token is None:
            self._token = get_settings().tactiq_token.strip()
        return self._token

    @property
    def session(self) -> requests.Session:
        """Get configured requests session."""
        if self._session is None:
            self._session = requests.Session()
            self._session.headers.update(
                {
                    "Authorization": f"Bearer {self.token}",
                    "User-Agent": USER_AGENT,
                    "Content-Type": "application/json",
                    "Accept": "*/*",
                }
            )
        return self._session

    def _run(self, meeting_id: str, question: str = "") -> str:
        """Fetch meeting details or ask AI question."""
        if not self.token:
            return "Error: TACTIQ_TOKEN not configured. Set TACTIQ_TOKEN environment variable."

        if not meeting_id:
            return "Error: meeting_id is required."

        # Get meeting details first
        meeting_data = self._get_meeting(meeting_id)

        if not meeting_data:
            return f"Error: Could not fetch meeting with ID: {meeting_id}"

        # If no question, return meeting summary
        if not question:
            return self._format_meeting_summary(meeting_data)

        # Ask AI question about the meeting
        ai_answer = self._ask_ai(meeting_id, question)
        return self._format_ai_response(meeting_data, question, ai_answer)

    def _get_meeting(self, meeting_id: str) -> dict[str, Any] | None:
        """Fetch meeting details via GraphQL."""
        query = """
        query GetMeeting($meetingId: ID!) {
            meeting(id: $meetingId) {
                id
                title
                platform
                participants {
                    name
                    email
                }
                duration
                speechDuration
                created
                transcripts {
                    ... on TactiqMeetingTranscriptLink {
                        externalId
                        externalLink
                    }
                }
                aiOutputs {
                    id
                    prompt
                    content {
                        ... on MeetingAIOutputTypeString {
                            text
                        }
                    }
                    promptTitle
                    finishReason
                }
                searchHighlights {
                    type
                    highlight
                }
            }
        }
        """

        variables = {"meetingId": meeting_id}

        try:
            response = self.session.post(
                GRAPHQL_URL,
                json={
                    "operationName": "GetMeeting",
                    "variables": variables,
                    "query": query,
                },
                timeout=30,
            )
            response.raise_for_status()
            data = response.json()

            if "errors" in data:
                error_msg = data["errors"][0].get("message", "Unknown error")
                logger.error("Tactiq GraphQL errors: %s", error_msg)
                return None

            meeting = data.get("data", {}).get("meeting")
            return meeting

        except requests.RequestException as e:
            logger.error("Failed to fetch meeting: %s", e)
            return None

    def _ask_ai(self, meeting_id: str, question: str) -> str | None:
        """Ask AI about the meeting and poll for response."""
        # First, get the agent run details to trigger AI interaction
        query = """
        query LoadAgentRunDetails($input: LoadAgentRunDetailsInput!) {
            loadAgentRunDetails(input: $input) {
                agentRun {
                    id
                    status
                    finishReason
                    conversationHistory {
                        ... on AgentConversationHistoryItemUser {
                            content
                        }
                        ... on AgentConversationHistoryItemAssistant {
                            content
                            quickReplies
                        }
                        ... on AgentConversationHistoryItemToolCall {
                            toolName
                            toolCallId
                            arguments
                            intent
                        }
                    }
                }
            }
        }
        """

        # First try to get existing AI outputs
        meeting_data = self._get_meeting(meeting_id)
        if meeting_data and meeting_data.get("aiOutputs"):
            for output in meeting_data["aiOutputs"]:
                if output.get("promptTitle") or output.get("prompt"):
                    content = output.get("content", {})
                    if isinstance(content, dict) and content.get("text"):
                        return content["text"]

        # Poll for agent run details
        variables = {"input": {"agentRunId": meeting_id}}

        try:
            for attempt in range(MAX_POLL_ATTEMPTS):
                response = self.session.post(
                    GRAPHQL_URL,
                    json={
                        "operationName": "LoadAgentRunDetails",
                        "variables": variables,
                        "query": query,
                    },
                    timeout=30,
                )
                response.raise_for_status()
                data = response.json()

                if "errors" in data:
                    error_msg = data["errors"][0].get("message", "Unknown error")
                    logger.error("Tactiq GraphQL errors: %s", error_msg)
                    return None

                agent_run = (
                    data.get("data", {}).get("loadAgentRunDetails", {}).get("agentRun")
                )
                if agent_run:
                    status = agent_run.get("status")
                    finish_reason = agent_run.get("finishReason")

                    # Check if completed
                    if finish_reason == "COMPLETED":
                        # Get the latest assistant message
                        history = agent_run.get("conversationHistory", [])
                        for item in reversed(history):
                            if (
                                item.get("__typename")
                                == "AgentConversationHistoryItemAssistant"
                            ):
                                content = item.get("content")
                                if content:
                                    return content

                    # Check for pending user input
                    if status == "PENDING_USER_INPUT":
                        # Need to provide input
                        return "Waiting for user input in meeting"

                time.sleep(POLL_INTERVAL)

            return "Timeout waiting for AI response"

        except requests.RequestException as e:
            logger.error("Failed to ask AI: %s", e)
            return None

    def _format_meeting_summary(self, meeting: dict[str, Any]) -> str:
        """Format meeting details into a readable summary."""
        lines = ["## Meeting Details", ""]

        # Title
        title = meeting.get("title", "Untitled Meeting")
        lines.append(f"**Title:** {title}")

        # Platform
        platform = meeting.get("platform", "Unknown")
        lines.append(f"**Platform:** {platform}")

        # Duration
        duration = meeting.get("duration", 0)
        speech_duration = meeting.get("speechDuration", 0)
        lines.append(
            f"**Duration:** {duration} minutes ({speech_duration} seconds speech)"
        )

        # Participants
        participants = meeting.get("participants", [])
        if participants:
            names = [p.get("name", p.get("email", "Unknown")) for p in participants]
            lines.append(f"**Participants:** {', '.join(names)}")

        lines.append("")

        # Search Highlights
        highlights = meeting.get("searchHighlights", [])
        if highlights:
            lines.append("## Key Highlights")
            for h in highlights[:10]:  # Limit to 10
                highlight_type = h.get("type", "general")
                text = h.get("highlight", "")
                lines.append(f"- [{highlight_type}] {text}")
            lines.append("")

        # AI Outputs
        ai_outputs = meeting.get("aiOutputs", [])
        if ai_outputs:
            lines.append("## AI Outputs")
            for output in ai_outputs:
                prompt_title = output.get("promptTitle", output.get("prompt", ""))
                content = output.get("content", {})
                if isinstance(content, dict):
                    text = content.get("text", "")
                    if text:
                        lines.append(f"### {prompt_title}")
                        lines.append(text[:1000])  # Limit length
                        lines.append("")
            lines.append("")

        return "\n".join(lines)

    def _format_ai_response(
        self, meeting: dict[str, Any], question: str, answer: str | None
    ) -> str:
        """Format AI answer with context."""
        lines = ["## Tactiq AI Answer", ""]

        if answer is None:
            lines.append("Could not retrieve AI answer for this question.")
            lines.append("")
            lines.append(
                "The meeting may not have AI outputs or the question may not have been answered yet."
            )
            return "\n".join(lines)

        lines.append(f"**Question:** {question}")
        lines.append("")
        lines.append("**Answer:**")
        lines.append(answer)

        return "\n".join(lines)
