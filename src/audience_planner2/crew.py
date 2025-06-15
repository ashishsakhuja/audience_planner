# src/audience_planner2/crew.py

from typing import List, Dict, Any
import os, logging
from crewai import Agent, Crew, Process, Task, LLM
from crewai.project import CrewBase, agent, crew, task, before_kickoff, after_kickoff
from crewai.agents.agent_builder.base_agent import BaseAgent
from dotenv import load_dotenv
from audience_planner2.tools.sql_query_tool import SegmentSQLTool
from audience_planner2.models import SQLString


llm = LLM(model="gpt-4.1-mini", temperature=0.0)

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
        import re
        if 'query' not in inputs:
            raise ValueError("Missing required 'query'")
        query = inputs['query']
        if not isinstance(query, str):
            raise ValueError("'query' must be a string")
        query = query.strip()
        if not query:
            raise ValueError("'query' cannot be empty or just whitespace")
        if len(query) > 500:
            raise ValueError("Query too long (max 500 characters)")
        if not re.match(r"^[A-Za-z0-9\s\.,;:'\"?!\-]", query):
            raise ValueError("Query contains invalid characters")

        # everything’s safe—assign back and proceed
        inputs['query'] = query
        inputs['start_ts'] = os.getenv("RUN_TIMESTAMP", "")
        logging.info(f"Starting with query: {inputs['query']}")
        return inputs

    @agent
    def database_guru(self) -> Agent:
        return Agent(
            config=self.agents_config['database_guru'],
            llm=llm,
            tools=[],
            verbose=True,
            memory=False,
        )

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
    def generate_sql_task(self) -> Task:
        cfg = self.tasks_config['generate_sql_task']
        return Task(
            config=cfg,
            output_pydantic=SQLString,
            markdown=True,
            tools=[]
        )

    @task
    def select_segment_task(self) -> Task:
        cfg = self.tasks_config['select_segment_task']
        return Task(
            config=cfg,
            depends_on=[self.generate_sql_task],
            tools=[self.sql_tool],
            markdown=True
        )

    @task
    def validate_segment_task(self) -> Task:
        cfg = self.tasks_config['validate_segment_task']
        return Task(
            config=cfg,
            prompt=cfg['description'],
            depends_on=[self.select_segment_task],
            tools=[self.sql_tool],
            markdown=True,
            output_file='validation_report.md'
        )

    @crew
    def crew(self) -> Crew:
        return Crew(
            agents=self.agents,
            tasks=self.tasks,
            process=Process.sequential,
            verbose=True,
            tools=[self.sql_tool],
            max_rpm=30,
            pydantic_models=[SQLString]
        )


