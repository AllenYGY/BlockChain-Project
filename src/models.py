from pydantic import BaseModel, Field
from typing import List, Optional
from datetime import datetime
import uuid

class Author(BaseModel):
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    name: str
    public_key: str
    token_balance: float = 0.0
    created_at: datetime = Field(default_factory=datetime.now)
    
class Paper(BaseModel):
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    title: str
    authors: List[str]  # List of author IDs
    citations: List[str] = []  # List of cited paper IDs
    created_at: datetime = Field(default_factory=datetime.now)
    
class Citation(BaseModel):
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    citing_paper_id: str
    cited_paper_id: str
    created_at: datetime = Field(default_factory=datetime.now)
    
class TokenTransaction(BaseModel):
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    author_id: str
    amount: float
    transaction_type: str  # "MINT" or "BURN"
    reason: str
    created_at: datetime = Field(default_factory=datetime.now) 