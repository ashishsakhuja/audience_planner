# src/audience_planner2/crew.py

from typing import List, Dict, Any
import os, logging
from crewai import Agent, Crew, Process, Task, LLM
from crewai.project import CrewBase, agent, crew, task, before_kickoff, after_kickoff
from crewai.agents.agent_builder.base_agent import BaseAgent
from dotenv import load_dotenv
from audience_planner2.tools.sql_query_tool import SegmentSQLTool


llm = LLM(model="gpt-4", temperature=0.0)

@CrewBase
class AudiencePlannerCrew:
    """Audience segment planning crew using SQL-backed lookups."""

    agents: List[BaseAgent]
    tasks: List[Task]
    tools = [SegmentSQLTool()]

    # point to your YAML configs
    agents_config = 'config/agents.yaml'
    tasks_config = 'config/tasks.yaml'

    def __init__(self):
        super().__init__()
        load_dotenv()
        logging.basicConfig(level=logging.INFO)
        self.sql_tool = SegmentSQLTool()

    @before_kickoff
    def setup(self, inputs: Dict[str, Any]) -> Dict[str, Any]:
        if 'query' not in inputs:
            raise ValueError("Missing required 'query'")
        inputs['start_ts'] = os.getenv("RUN_TIMESTAMP", "")
        logging.info(f"Starting with query: {inputs['query']}")
        return inputs

    @agent
    def segment_agent(self) -> Agent:
        return Agent(
            config=self.agents_config['segment_agent'],
            llm=llm,
            tools=[self.sql_tool],
            verbose=True,
            memory=False,
        )

    @agent
    def verifier_agent(self) -> Agent:
        return Agent(
            config=self.agents_config['verifier_agent'],
            llm=llm,
            tools=[self.sql_tool],
            verbose=True,
            memory=False,
        )

    @task
    def select_segment_task(self) -> Task:
        return Task(
            config=self.tasks_config['select_segment_task'],
            output_file='selected_segments.md',
            tools=[self.sql_tool],
            markdown=True
        )

    @task
    def validate_segment_task(self) -> Task:
        return Task(
            config=self.tasks_config['validate_segment_task'],
            output_file='validation_report.md',
            depends_on=[self.select_segment_task],
            tools=[self.sql_tool],
            markdown=True
        )

    @crew
    def crew(self) -> Crew:
        return Crew(
            agents=self.agents,
            tasks=self.tasks,
            process=Process.sequential,
            verbose=True,
            tools=[self.sql_tool],
            max_rpm=30
        )


