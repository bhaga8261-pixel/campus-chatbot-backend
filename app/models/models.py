from typing import Annotated, Optional, List, Dict, Any
from datetime import datetime
from pydantic import BaseModel, Field, BeforeValidator, ConfigDict, EmailStr

# Custom type to convert MongoDB ObjectId to string
PyObjectId = Annotated[str, BeforeValidator(str)]

# --- USER SCHEMAS ---
class UserBase(BaseModel):
    name: str = Field(..., min_length=2, max_length=50)
    email: EmailStr
    role: str = Field(default="student", pattern="^(student|admin)$")

class UserCreate(UserBase):
    password: str = Field(..., min_length=6)

class UserLogin(BaseModel):
    email: EmailStr
    password: str

class UserResponse(UserBase):
    id: PyObjectId = Field(alias="_id")
    created_at: datetime = Field(default_factory=datetime.utcnow)

    model_config = ConfigDict(
        populate_by_name=True,
        arbitrary_types_allowed=True
    )

# --- DOCUMENT SCHEMAS ---
class DocumentBase(BaseModel):
    title: str
    filename: str

class DocumentCreate(DocumentBase):
    uploaded_by: PyObjectId

class DocumentResponse(DocumentBase):
    id: PyObjectId = Field(alias="_id")
    uploaded_by: PyObjectId = Field(alias="uploadedBy")
    uploaded_at: datetime = Field(alias="uploadedAt")

    model_config = ConfigDict(
        populate_by_name=True,
        arbitrary_types_allowed=True
    )

# --- DOCUMENT CHUNK SCHEMAS ---
class DocumentChunk(BaseModel):
    id: Optional[PyObjectId] = Field(alias="_id", default=None)
    document_id: PyObjectId = Field(alias="documentId")
    chunk: str
    embedding: List[float]
    page: int
    metadata: Dict[str, Any] = Field(default_factory=dict)

    model_config = ConfigDict(
        populate_by_name=True,
        arbitrary_types_allowed=True
    )

# --- CHAT SCHEMAS ---
class ChatQuestion(BaseModel):
    question: str = Field(..., min_length=1)

class ChatResponse(BaseModel):
    id: PyObjectId = Field(alias="_id")
    user_id: PyObjectId = Field(alias="userId")
    question: str
    answer: str
    timestamp: datetime
    sources: List[Dict[str, Any]] = Field(default_factory=list) # e.g. [{"document_name": "...", "page": 1}]

    model_config = ConfigDict(
        populate_by_name=True,
        arbitrary_types_allowed=True
    )

# --- NOTICE SCHEMAS ---
class NoticeCreate(BaseModel):
    title: str = Field(..., min_length=3)
    description: str = Field(..., min_length=5)

class NoticeResponse(NoticeCreate):
    id: PyObjectId = Field(alias="_id")
    created_at: datetime = Field(alias="createdAt")

    model_config = ConfigDict(
        populate_by_name=True,
        arbitrary_types_allowed=True
    )

# --- EVENT SCHEMAS ---
class EventCreate(BaseModel):
    title: str = Field(..., min_length=3)
    date: datetime
    description: str = Field(..., min_length=5)

class EventResponse(EventCreate):
    id: PyObjectId = Field(alias="_id")

    model_config = ConfigDict(
        populate_by_name=True,
        arbitrary_types_allowed=True
    )

# --- FAQ SCHEMAS ---
class FAQCreate(BaseModel):
    question: str = Field(..., min_length=5)
    answer: str = Field(..., min_length=5)

class FAQResponse(FAQCreate):
    id: PyObjectId = Field(alias="_id")

    model_config = ConfigDict(
        populate_by_name=True,
        arbitrary_types_allowed=True
    )

# --- JWT TOKEN SCHEMAS ---
class Token(BaseModel):
    access_token: str
    token_type: str
    role: str
    name: str

class TokenData(BaseModel):
    email: Optional[str] = None
    role: Optional[str] = None
