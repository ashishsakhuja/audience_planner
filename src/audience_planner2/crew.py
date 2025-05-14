from crewai import Agent, Task, Crew, Process
from crewai.project import CrewBase, agent, task, crew
from crewai.knowledge.source.json_knowledge_source import JSONKnowledgeSource
import os
from dotenv import load_dotenv
import yaml

load_dotenv()

@CrewBase
class AudiencePlannerCrew:
    def __init__(self, input_values=None):
        super().__init__()
        self.input_values = input_values or {}
        with open("config/agents.yaml", "r") as f:
            self.agents_config = yaml.safe_load(f)

        with open("config/tasks.yaml", "r") as f:
            self.tasks_config = yaml.safe_load(f)

    @agent
    def segment_agent(self) -> Agent:
        return Agent(
            config=self.agents_config["segment_agent"],
            verbose=True
        )

    @task
    def find_audience_segment(self) -> Task:
        return Task(
            config=self.tasks_config["find_audience_segment"]
        )

    @crew
    def crew(self) -> Crew:
        from pathlib import Path

        knowledge_path = os.path.abspath(
            os.path.join(os.path.dirname(__file__), "..", "..", "knowledge", "Acxiom-Real-Identity")
        )
        json_files = list(Path(knowledge_path).rglob("*.json"))
        knowledge_source = JSONKnowledgeSource(file_paths=json_files)

        return Crew(
            agents=self.agents,
            tasks=self.tasks,
            process=Process.sequential,
            verbose=True,
            knowledge_sources=[knowledge_source],
            input_values=self.input_values
        )