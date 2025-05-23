from crewai import Agent, Task, Crew, Process
from crewai.project import CrewBase, agent, task, crew
from crewai.knowledge.source.json_knowledge_source import JSONKnowledgeSource
import os
from dotenv import load_dotenv
import yaml
import json
from pathlib import Path

load_dotenv()

current_file = os.path.abspath(__file__)
project_root = os.path.dirname(os.path.dirname(current_file))


def load_valid_segment_names(knowledge_dir):
    valid_names = set()
    json_files = list(Path(knowledge_dir).rglob("*.json"))

    for path in json_files:
        with open(path, "r", encoding="utf-8") as f:
            try:
                data = json.load(f)
                if isinstance(data, dict):
                    if "name" in data:
                        valid_names.add(data["name"])
                elif isinstance(data, list):
                    for entry in data:
                        if isinstance(entry, dict) and "name" in entry:
                            valid_names.add(entry["name"])
            except json.JSONDecodeError:
                print(f"[WARNING] Skipping invalid JSON file: {path}")
            except Exception as e:
                print(f"[ERROR] Unexpected issue in file {path}: {e}")
    return sorted(valid_names)


@CrewBase
class AudiencePlannerCrew:
    def __init__(self, input_values=None):
        super().__init__()
        self.input_values = input_values or {}

        base_path = os.path.dirname(__file__)
        with open(os.path.join(base_path, "config", "agents.yaml"), "r", encoding="utf-8") as f:
            self.agents_config = yaml.safe_load(f)
        with open(os.path.join(base_path, "config", "tasks.yaml"), "r", encoding="utf-8") as f:
            self.tasks_config = yaml.safe_load(f)

        self.knowledge_path = os.path.abspath(
            os.path.join(base_path, "..", "..", "knowledge", "Acxiom-Real-Identity")
        )
        self.valid_segment_names = load_valid_segment_names(self.knowledge_path)
        print("[DEBUG] Valid Segment Names:", self.valid_segment_names[:5])
        print(f"[DEBUG] Total valid segment names loaded: {len(self.valid_segment_names)}")
        self.input_values["valid_segment_names"] = self.valid_segment_names

        self.json_knowledge_source = JSONKnowledgeSource(
            file_paths=list(Path(self.knowledge_path).rglob("*.json"))
        )

        print(f"[DEBUG] JSON files loaded into knowledge source: {len(self.json_knowledge_source.file_paths)}")
        for f in self.json_knowledge_source.file_paths[:5]:
            print(f"[DEBUG] → {os.path.basename(f)}")

    @agent
    def segment_agent(self) -> Agent:
        return Agent(
            config=self.agents_config["segment_agent"],
            verbose=True,
            input_values={"valid_segment_names": self.valid_segment_names},
            knowledge_source=[self.json_knowledge_source]
        )

    @agent
    def enrichment_agent(self) -> Agent:
        return Agent(
            config=self.agents_config["enrichment_agent"],
            verbose=True,
            knowledge_source=[self.json_knowledge_source]
        )

    @agent
    def verification_agent(self) -> Agent:
        return Agent(
            config=self.agents_config["verification_agent"],
            verbose=True,
            knowledge_source=[self.json_knowledge_source]
        )

    @task
    def find_audience_segment(self) -> Task:
        return Task(
            config=self.tasks_config["find_audience_segment"],
            input_values={"valid_segment_names": self.valid_segment_names}
        )

    @task
    def enrich_segments(self) -> Task:
        return Task(
            config=self.tasks_config["enrich_segments"]
        )

    @task
    def validate_enriched_segments(self) -> Task:
        return Task(config=self.tasks_config["validate_enriched_segments"])

    @crew
    def crew(self) -> Crew:
        return Crew(
            agents=self.agents,
            tasks=[
                self.find_audience_segment(),
                self.enrich_segments(),
                self.validate_enriched_segments()
            ],
            process=Process.sequential,
            verbose=True,
            knowledge_sources=[self.json_knowledge_source],
            input_values=self.input_values
        )
