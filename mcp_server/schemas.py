from typing import List, Optional
from pydantic import BaseModel, Field, field_validator
import re

# Used for NewsItem
ISO_DATETIME_REGEX = r'^\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}(\.\d+)?(Z|[+-]\d{2}:\d{2})?$'

class TopicInsert(BaseModel):
    name: str
    source: Optional[str] = "agent"

class ContrastPairUpdate(BaseModel):
    id: int
    item1: Optional[str] = None
    item2: Optional[str] = None
    vector_embedding: Optional[str] = None

class TopicUpdate(BaseModel):
    id: int
    name: Optional[str] = None
    source: Optional[str] = None
    vector_embedding: Optional[str] = None

class ContrastPairRating(BaseModel):
    pair_id: int
    rating: int

class NewsItem(BaseModel):
    data_response: dict
    start_date: str = Field(..., pattern=ISO_DATETIME_REGEX)
    end_date: str = Field(..., pattern=ISO_DATETIME_REGEX)
    search_type: Optional[str] = None
    news_source: Optional[str] = None

class PairStringInput(BaseModel):
    pair_string: str = Field(
        ...,
        pattern=r"^.+ vs .+$",
        description="A string in the format 'Item1 vs Item2'"
    )
