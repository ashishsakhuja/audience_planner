from crewai.knowledge.source.base_knowledge_source import BaseKnowledgeSource
from pydantic import Field
from typing import Dict, List, Any
import json
from pathlib import Path

class SegmentKnowledgeSource(BaseKnowledgeSource):
    """Loader that chunks audience segments JSON for CrewAI context."""

    file_path: Path = Field(description="Path to segment JSON file")

    def __init__(self, **kwargs):
        root_path = Path(__file__).resolve().parents[1]
        segments_path = root_path / "segments2.json"

        print(f"[DEBUG] FORCED segments2.json path: {segments_path.resolve()}")
        kwargs["file_path"] = segments_path

        super().__init__(**kwargs)

    def load_content(self) -> List[str]:
        try:
            print(f"[DEBUG] Loading segments from: {self.file_path.resolve()}")

            with self.file_path.open("r", encoding="utf-8") as f:
                segments = json.load(f)

            texts = []
            for segment in segments:
                formatted = self._format(segment)
                if formatted:
                    texts.append(formatted)

            print(f"[DEBUG] Returning {len(texts)} string chunks to CrewAI.")
            return texts

        except Exception as e:
            raise ValueError(f"Failed to load segments JSON: {str(e)}")

    def validate_content(self, content: Any) -> bool:
        return isinstance(content, str)

    def add(self) -> None:
        content = self.load_content()
        for value in content:  # each value is a formatted string
            if isinstance(value, str):
                self.chunks.append(value)
            else:
                print(f"[ERROR] Skipped non-str chunk: {type(value)}")
        self._save_documents()

    def _format(self, seg: dict) -> str:
        demographics = seg.get("demographics", {})
        criteria = seg.get("segmentCriteria", {}).get("filters", {})
        return f"""
Name: {seg.get("name")}
Taxonomy ID: {seg.get("taxonomyId")} # UUID - DO NOT GUESS
Graph: {seg.get("identityGraphName")}
Age Range: {demographics.get("age_range")}
Income Level: {demographics.get("income_level")}
Location Type: {demographics.get("location_type")}
Recency: {criteria.get("recency")}
Quality Score: {criteria.get("quality_score")}
CPM: {seg.get("cpm")}
CPM Cap: {seg.get("cpmCap")}
Confidence: {seg.get("taxonomyAttributes", {}).get("confidence")}
Category: {seg.get("taxonomyAttributes", {}).get("category")}
programmaticMediaPct: {seg.get("programmaticMediaPct")}
advertiserDirectPct: {seg.get("advertiserDirectPct")}
Estimated Reach: {seg.get("estReach")}
Data Source: {seg.get("dataSource")}
Segment size: {seg.get("size")}
"""