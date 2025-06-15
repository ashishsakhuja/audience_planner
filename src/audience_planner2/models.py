from pydantic import BaseModel
from typing import List, Dict, Any


class SQLString(BaseModel):
    sql: str