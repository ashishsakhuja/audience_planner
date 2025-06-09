from crewai import Agent, Task, Crew, Process, LLM
from knowledge.segment_knowledge_source import SegmentKnowledgeSource
from crewai.project import CrewBase, agent, crew, task
from crewai.agents.agent_builder.base_agent import BaseAgent
from typing import List

# Load your segment knowledge source
segment_knowledge = SegmentKnowledgeSource()

@CrewBase
class AudiencePlannerCrew():
    """Audience segment planning crew"""

    agents: List[BaseAgent]
    tasks: List[Task]

    @agent
    def segment_agent(self) -> Agent:
        return Agent(
            config=self.agents_config['segment_agent'],
            knowledge_sources=[segment_knowledge],
            llm=LLM(model="gpt-4", temperature=0),
            verbose=True,
            memory=False
        )

    @agent
    def verifier_agent(self) -> Agent:
        return Agent(
            config=self.agents_config['verifier_agent'],
            knowledge_sources=[segment_knowledge],
            llm=LLM(model="gpt-4", temperature=0),
            verbose=True,
            memory=False
        )

    @task
    def select_segment_task(self) -> Task:
        return Task(
            config=self.tasks_config['select_segment_task'],
            output_file='selected_segments.md'
        )

    @task
    def validate_segment_task(self) -> Task:
        return Task(
            config=self.tasks_config['validate_segment_task'],
            output_file='validation_report.md',
            depends_on=[self.select_segment_task]
        )

    @crew
    def crew(self) -> Crew:
        return Crew(
            agents=self.agents,
            tasks=self.tasks,
            process=Process.sequential,
            verbose=True,
            knowledge_sources=[segment_knowledge],
            storage_path="./chroma_clean_reset"
        )

