"""Token counting utilities using tiktoken."""

import logging
from functools import lru_cache
from typing import Dict, List, Optional

try:
    import tiktoken
except ImportError:
    tiktoken = None
    logging.warning("tiktoken not available, using approximate token counting")

from ..core.config import get_settings

logger = logging.getLogger(__name__)


class TokenCounter:
    """Handles token counting for different models."""
    
    def __init__(self, model_name: Optional[str] = None):
        self.settings = get_settings()
        self.model_name = model_name or self.settings.openai_model
        self._encoding = self._get_encoding()
    
    @lru_cache(maxsize=1)
    def _get_encoding(self):
        """Get tiktoken encoding for the model."""
        if not tiktoken:
            return None
        
        try:
            # Try to get encoding by model name
            return tiktoken.encoding_for_model(self.model_name)
        except KeyError:
            # Fall back to cl100k_base for GPT-4 family
            logger.warning(f"Model {self.model_name} not found, using cl100k_base encoding")
            return tiktoken.get_encoding("cl100k_base")
    
    def count_tokens(self, text: str) -> int:
        """Count tokens in text."""
        if not text:
            return 0
        
        if self._encoding:
            try:
                return len(self._encoding.encode(text))
            except Exception as e:
                logger.warning(f"Error counting tokens with tiktoken: {e}")
        
        # Fallback: approximate token count (roughly 4 characters per token)
        return max(1, len(text) // 4)
    
    def count_messages_tokens(self, messages: List[Dict[str, str]]) -> int:
        """Count tokens in a list of messages."""
        if not messages:
            return 0
        
        total_tokens = 0
        
        for message in messages:
            # Count tokens for role and content
            role = message.get("role", "")
            content = message.get("content", "")
            
            # Add base tokens per message (role, formatting, etc.)
            total_tokens += 4  # Base tokens per message
            total_tokens += self.count_tokens(role)
            total_tokens += self.count_tokens(content)
        
        # Add base tokens for the messages array
        total_tokens += 2
        
        return total_tokens
    
    def estimate_completion_tokens(self, prompt_tokens: int, max_completion_ratio: float = 0.5) -> int:
        """Estimate completion tokens based on prompt length."""
        # Conservative estimate: completion is typically 20-50% of prompt length
        return int(prompt_tokens * max_completion_ratio)
    
    def check_context_limit(self, prompt_tokens: int, completion_tokens: int = 0) -> bool:
        """Check if tokens exceed context limit."""
        total_tokens = prompt_tokens + completion_tokens
        return total_tokens >= self.settings.max_context_tokens
    
    def get_available_tokens(self, used_tokens: int) -> int:
        """Get remaining available tokens."""
        return max(0, self.settings.max_context_tokens - used_tokens)
    
    def truncate_text_by_tokens(self, text: str, max_tokens: int) -> str:
        """Truncate text to fit within token limit."""
        if not text:
            return text
        
        current_tokens = self.count_tokens(text)
        if current_tokens <= max_tokens:
            return text
        
        if not self._encoding:
            # Fallback: truncate by characters (approximate)
            chars_per_token = 4
            max_chars = max_tokens * chars_per_token
            return text[:max_chars] + "..."
        
        # Use tiktoken for precise truncation
        try:
            tokens = self._encoding.encode(text)
            if len(tokens) <= max_tokens:
                return text
            
            truncated_tokens = tokens[:max_tokens]
            truncated_text = self._encoding.decode(truncated_tokens)
            return truncated_text + "..."
        except Exception as e:
            logger.error(f"Error truncating text: {e}")
            # Fallback to character-based truncation
            chars_per_token = 4
            max_chars = max_tokens * chars_per_token
            return text[:max_chars] + "..."
    
    def get_model_limits(self) -> Dict[str, int]:
        """Get token limits for the current model."""
        # Common model limits
        model_limits = {
            "gpt-4o-mini": 128000,
            "gpt-4o": 128000,
            "gpt-4-turbo": 128000,
            "gpt-4": 8192,
            "gpt-3.5-turbo": 16385,
        }
        
        return {
            "max_context": model_limits.get(self.model_name, self.settings.max_context_tokens),
            "configured_max": self.settings.max_context_tokens,
            "summary_threshold": self.settings.summary_token_threshold
        }