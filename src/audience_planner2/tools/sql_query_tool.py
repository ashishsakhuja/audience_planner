"""
Segment SQL Query Tool for CrewAI to query DuckDB segments database
"""

import os
import json
import re
import duckdb
from typing import Any, Dict, List
from pydantic import BaseModel, Field
from crewai.tools import BaseTool
from pathlib import Path


class SQLQueryInput(BaseModel):
    """Input schema for SQL Query Tool"""
    query: str = Field(..., description="Natural language or SQL-like filter for segments")


class SegmentSQLTool(BaseTool):
    """Tool for querying your audience segments DuckDB by natural language."""

    name: str = "SegmentSQLTool"
    description: str = """
    SQL-backed lookup of audience segments.  
    The `segments` table has columns:
      - name, iconName, identityGraphName, taxonomyId  
      - datasetIds, quality_score, recency, size  
      - age_range, income_level, location_type  
      - category, confidence, estReach, cpm, cpmCap  
      - programmaticMediaPct, advertiserDirectPct, dataSource, metadata, segmentId  

    You can ask things like:
      • "Give me segments with age_range 18-24 and recency 30_days"  
      • "Show high-quality rural segments"  
      • "List all segments with CPM > 20"  

    The tool will synthesize a SQL `SELECT * FROM segments WHERE …` and return JSON.
    """
    args_schema: type[BaseModel] = SQLQueryInput

    def _run(self, query: str) -> str:
        try:
            sql = self._convert_to_sql(query)
            rows = self._execute_sql(sql)
            return json.dumps(rows, indent=2, default=str)
        except Exception as e:
            return f"Error executing segment query: {e}"

    def _convert_to_sql(self, natural: str) -> str:
        """
        Convert natural‐language filters into SQL on your segments table.
        Handles:
          • OR‐lists for income_level & location_type
          • "all ages" → no age filter
          • "ages over X" / "adults" → numeric lower‐bound on age_range
          • "at least / at most" on recency
        """
        sql = "SELECT * FROM segments"
        conds: List[str] = []
        q = natural.lower()

        # 1) Income: collect any of our known levels
        income_levels = ["low", "medium", "high", "affluent"]
        found_incomes = [lvl for lvl in income_levels if lvl in q]
        if found_incomes and "all income" not in q:
            # build OR‐clause
            ors = " OR ".join(f"income_level = '{lvl}'" for lvl in found_incomes)
            conds.append(f"({ors})")

        # 2) Location: same idea
        locations = ["urban", "suburban", "rural"]
        found_locs = [loc for loc in locations if loc in q]
        if found_locs and "all locations" not in q:
            ors = " OR ".join(f"location_type = '{loc}'" for loc in found_locs)
            conds.append(f"({ors})")

        # 3) Age:
        if "all ages" not in q:
            # numeric “over X”
            m_age = re.search(r"(?:age.*over|over the age of)\s*(\d+)", q)
            if m_age:
                val = int(m_age.group(1))
                conds.append(
                    "CAST(regexp_extract(age_range,'^([0-9]+)',1) AS INTEGER) >= "
                    f"{val}"
                )
            # “adults” → same as age >= 18
            elif "adult" in q:
                conds.append(
                    "CAST(regexp_extract(age_range,'^([0-9]+)',1) AS INTEGER) >= 18"
                )
            else:
                # exact bins like “18-24”
                bins = ["18-24", "25-34", "35-44", "45-54", "55-64"]
                found = [b for b in bins if b in q]
                if found:
                    ors = " OR ".join(f"age_range = '{b}'" for b in found)
                    conds.append(f"({ors})")

        # 4) Recency comparisons (as before)
        m1 = re.search(r"(?:recency\s*)?(at least|>=|>|more than)\s*(\d+)\s*days", q)
        if m1:
            op, days = m1.groups();
            days = int(days)
            operator = ">=" if op in ("at least", ">=", "more than") else ">"
            conds.append(
                f"CAST(REPLACE(recency,'_days','') AS INTEGER) {operator} {days}"
            )
        else:
            m2 = re.search(r"(?:recency\s*)?(at most|<=|<|less than)\s*(\d+)\s*days", q)
            if m2:
                op, days = m2.groups();
                days = int(days)
                operator = "<=" if op in ("at most", "<=", "less than") else "<"
                conds.append(
                    f"CAST(REPLACE(recency,'_days','') AS INTEGER) {operator} {days}"
                )
            else:
                # exact 7_days,30_days,90_days
                for rec in ("7_days", "30_days", "90_days"):
                    if rec in q:
                        conds.append(f"recency = '{rec}'")
                        break

        # 5) CPM / estReach (unchanged)
        m3 = re.search(r"(cpm|estreach)\s*(>=|<=|>|<)\s*([0-9]+)", q)
        if m3:
            col, op, val = m3.groups()
            conds.append(f"{col} {op} {val}")

        # 6) Taxonomy filters (unchanged)
        for cat in ("demo_age", "demo_income", "demo_location", "demo_education"):
            if cat in q:
                conds.append(f"category = '{cat}'")
        for conf in ("high", "medium", "low"):
            if f"{conf} confidence" in q:
                conds.append(f"confidence = '{conf}'")

        # Combine
        if conds:
            sql += " WHERE " + " AND ".join(conds)

        # Default limit
        if "all" not in q:
            sql += " LIMIT 13"

        return sql

    def _execute_sql(self, sql: str) -> List[Dict[str, Any]]:
        db_file = (
            Path(__file__).resolve()
                .parents[3]
                / "knowledge"
                / "segments.duckdb"
        )
        print(f"[DEBUG] Using DB at {db_file}")
        if not db_file.exists():
            raise FileNotFoundError(
                f"Database not found at {db_file!r}; run your setup_database tool first."
            )

        conn = duckdb.connect(str(db_file))
        try:
            cur = conn.execute(sql)
            rows = cur.fetchall()
            cols = [d[0] for d in cur.description]
            return [dict(zip(cols, row)) for row in rows]
        finally:
            conn.close()


# alias if you need the old name
DatasetSQLTool = SegmentSQLTool
