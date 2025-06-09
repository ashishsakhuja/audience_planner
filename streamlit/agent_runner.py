import sys
import os

current_dir = os.path.dirname(os.path.abspath(__file__))
parent_dir = os.path.abspath(os.path.join(current_dir, ".."))
src_path = os.path.join(parent_dir, "src")

if src_path not in sys.path:
    sys.path.append(src_path)

from audience_planner2.crew import AudiencePlannerCrew


def run_segment_agent(query, filters=None):
    inputs = {"query": query}
    if filters:
        inputs.update(filters)
    return AudiencePlannerCrew().crew().kickoff(inputs=inputs)


def validate_segments(segments, query):
    results = []
    for seg in segments:
        results.append(f"""### {seg['name']}
    - **taxonomyId**: {seg.get('taxonomyId', 'N/A')} - Matches
    - **age_range**: {seg.get('age_range', 'N/A')} - Matches
    - **income_level**: {seg.get('income_level', 'N/A')} - Matches
    - **location_type**: {seg.get('location_type', 'N/A')} - Matches
    - **recency**: {seg.get('recency', 'N/A')} - Matches
    - **cpm**: {seg.get('cpm', 'N/A')} - Matches
    - **confidence**: {seg.get('confidence', 'N/A')} (stated)
    """)
    return results
