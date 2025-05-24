from crewai.knowledge.source.base_knowledge_source import BaseKnowledgeSource
from pydantic import Field
from typing import Dict, Any
import json
from pathlib import Path

class SegmentKnowledgeSource(BaseKnowledgeSource):
    """Loader that chunks audience segments JSON for CrewAI context."""

    file_path: Path = Field(description="Path to segment JSON file")

    def __init__(self, **kwargs):
        root_path = Path(__file__).resolve().parents[1]
        segments_path = root_path / "segments.json"

        print(f"[DEBUG] FORCED segments.json path: {segments_path.resolve()}")
        kwargs["file_path"] = segments_path

        super().__init__(**kwargs)

    def load_content(self) -> Dict[Any, str]:
        try:
            print(f"[DEBUG] Loading segments from: {self.file_path.resolve()}")  # safe absolute path

            with self.file_path.open("r", encoding="utf-8") as f:
                segments = json.load(f)

            chunks = {}
            for segment in segments:
                name = segment.get("name")
                formatted = self._format(segment)
                if name and formatted:
                    chunks[name] = formatted

            print(f"[DEBUG] Loaded {len(chunks)} segments.")
            return chunks

        except Exception as e:
            raise ValueError(f"Failed to load segments JSON: {str(e)}")


    def validate_content(self, content: Any) -> str:
        return str(content)

    def add(self) -> None:
        content = self.load_content()
        for _, chunk in content.items():
            self.chunks.append(chunk)
        self._save_documents()

    def _format(self, seg: dict) -> str:
        demographics = seg.get("demographics", {})
        criteria = seg.get("segmentCriteria", {}).get("filters", {})
        return f"""
Name: {seg.get("name")}
Taxonomy: {seg.get("taxonomyId")}
Graph: {seg.get("identityGraphName")}
Age Range: {demographics.get("age_range")}
Income Level: {demographics.get("income_level")}
Location Type: {demographics.get("location_type")}
Recency: {criteria.get("recency")}
Quality Score: {criteria.get("quality_score")}
CPM: {seg.get("cpm")}
Confidence: {seg.get("taxonomyAttributes", {}).get("confidence")}
Estimated Reach: {seg.get("estReach")}
Data Source: {seg.get("dataSource")}
"""
