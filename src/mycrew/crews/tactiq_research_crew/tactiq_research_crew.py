"""Tactiq Research crew: fetch meeting context and determine if clarification is needed."""

from crewai import Agent, Crew, LLM, Process, Task

from mycrew.llm import ModelMappings
from mycrew.settings import Settings
from mycrew.tools import TactiqMeetingTool


class TactiqResearchCrew:
    """Tactiq Research crew: synthesize meeting context and determine if clarification needed."""

    def __init__(self):
        self.settings = Settings()

    def tactiq_researcher(self) -> Agent:
        return Agent(
            llm=LLM(
                model=ModelMappings.AUXILIARY.value.openrouter_model,
                api_key=self.settings.openrouter_api_key,
            ),
            role="Tactiq Researcher",
            goal="Fetch meeting context and determine if clarification is needed",
            backstory="Expert at synthesizing meeting notes with issue analysis",
            tools=[TactiqMeetingTool()],
        )

    def tactiq_research_task(self) -> Task:
        return Task(
            description="""Fetch meeting context from Tactiq and synthesize with issue analysis and exploration to determine if clarification is still needed.

## Context Provided

### Original Task
{task}

### Issue Analysis
{issue_analysis}

### Exploration Results
{exploration}

### Tactiq Meeting ID
{tactiq_meeting_id}

## Your Process

1. **Fetch Meeting Information**
   Use tactiq_meeting tool with the meeting_id to get meeting details.

2. **Ask Tactiq AI Clarifying Questions**
   For each ambiguity from issue_analysis, ask Tactiq AI for clarification.

3. **Synthesize Information**
   Combine: Issue Analysis + Exploration + Meeting Details + Tactiq AI Answers

4. **Clarification Decision**
   If AI answers resolve ambiguities → sufficient_info: true
   If gaps remain → sufficient_info: false + list unanswered questions

5. **Output**
   Combine all sources into enhanced context for architect or clarifier.

Start by calling tactiq_meeting tool with the meeting_id to get meeting details.""",
            expected_output="A structured document with Meeting Insights, Tactiq AI Answers table, Clarification Decision, and Enhanced Context.",
            agent=self.tactiq_researcher(),
        )

    def crew(self) -> Crew:
        return Crew(
            agents=[self.tactiq_researcher()],
            tasks=[self.tactiq_research_task()],
            process=Process.sequential,
            memory=False,
        )
