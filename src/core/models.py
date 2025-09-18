"""Pydantic models for state management and data structures."""

from datetime import datetime
from enum import Enum
from typing import Any, Dict, List, Optional, Union

from pydantic import BaseModel, Field, HttpUrl, validator


class AnalysisType(str, Enum):
    """Types of analysis that can be performed."""
    SUMMARY = "summary"
    SECURITY = "security"
    CODE_REVIEW = "code_review"
    DOCUMENTATION = "documentation"
    DEPENDENCIES = "dependencies"
    CUSTOM = "custom"


class MessageRole(str, Enum):
    """Message roles in conversation."""
    USER = "user"
    ASSISTANT = "assistant"
    SYSTEM = "system"
    TOOL = "tool"


class ConversationMessage(BaseModel):
    """Single message in conversation history."""
    role: MessageRole
    content: str
    timestamp: datetime = Field(default_factory=datetime.now)
    token_count: Optional[int] = None
    metadata: Dict[str, Any] = Field(default_factory=dict)


class GitHubRepository(BaseModel):
    """GitHub repository information."""
    url: HttpUrl
    owner: str
    name: str
    branch: Optional[str] = "main"
    full_name: str = ""
    
    @validator("full_name", always=True)
    def set_full_name(cls, v, values):
        """Set full_name from owner and name."""
        if not v and "owner" in values and "name" in values:
            return f"{values['owner']}/{values['name']}"
        return v
    
    @classmethod
    def from_url(cls, url: str) -> "GitHubRepository":
        """Create repository from GitHub URL."""
        # Parse GitHub URL (https://github.com/owner/repo)
        if not url.startswith("https://github.com/"):
            raise ValueError("Invalid GitHub URL format")
        
        path_parts = url.replace("https://github.com/", "").strip("/").split("/")
        if len(path_parts) < 2:
            raise ValueError("Invalid GitHub URL: missing owner or repository name")
        
        owner, name = path_parts[0], path_parts[1]
        # Remove .git suffix if present
        name = name.replace(".git", "")
        
        return cls(
            url=url,
            owner=owner,
            name=name,
            full_name=f"{owner}/{name}"
        )


class AnalysisResult(BaseModel):
    """Result of repository analysis."""
    repository: GitHubRepository
    analysis_type: AnalysisType
    summary: str
    details: Dict[str, Any] = Field(default_factory=dict)
    findings: List[str] = Field(default_factory=list)
    recommendations: List[str] = Field(default_factory=list)
    timestamp: datetime = Field(default_factory=datetime.now)
    token_usage: Dict[str, int] = Field(default_factory=dict)
    metadata: Dict[str, Any] = Field(default_factory=dict)


class AgentState(BaseModel):
    """State object for LangGraph workflow."""
    # Input data
    repository_url: Optional[str] = None
    analysis_type: AnalysisType = AnalysisType.SUMMARY
    system_prompt: str = ""
    user_prompt: str = ""
    
    # Repository information
    repository: Optional[GitHubRepository] = None
    
    # Conversation history
    messages: List[ConversationMessage] = Field(default_factory=list)
    total_tokens: int = 0
    context_summarized: bool = False
    
    # Analysis results
    current_analysis: Optional[AnalysisResult] = None
    analysis_history: List[AnalysisResult] = Field(default_factory=list)
    
    # MCP interaction data
    mcp_tools: List[Dict[str, Any]] = Field(default_factory=list)
    mcp_responses: List[Dict[str, Any]] = Field(default_factory=list)
    
    # Workflow control
    current_step: str = "start"
    completed_steps: List[str] = Field(default_factory=list)
    errors: List[str] = Field(default_factory=list)
    
    # Metadata
    session_id: Optional[str] = None
    created_at: datetime = Field(default_factory=datetime.now)
    updated_at: datetime = Field(default_factory=datetime.now)
    
    def add_message(self, role: MessageRole, content: str, token_count: Optional[int] = None, **metadata):
        """Add a message to conversation history."""
        message = ConversationMessage(
            role=role,
            content=content,
            token_count=token_count,
            metadata=metadata
        )
        self.messages.append(message)
        if token_count:
            self.total_tokens += token_count
        self.updated_at = datetime.now()
    
    def get_recent_messages(self, count: int = 5) -> List[ConversationMessage]:
        """Get the most recent messages."""
        return self.messages[-count:] if self.messages else []
    
    def mark_step_completed(self, step_name: str):
        """Mark a workflow step as completed."""
        if step_name not in self.completed_steps:
            self.completed_steps.append(step_name)
        self.current_step = step_name
        self.updated_at = datetime.now()
    
    def add_error(self, error_message: str):
        """Add an error to the state."""
        self.errors.append(f"{datetime.now().isoformat()}: {error_message}")
        self.updated_at = datetime.now()
    
    class Config:
        """Pydantic configuration."""
        use_enum_values = True
        validate_assignment = True
        arbitrary_types_allowed = True