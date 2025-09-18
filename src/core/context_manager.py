"""Context length management and conversation summarization."""

import logging
from typing import List, Tuple

from langchain.schema import BaseMessage, HumanMessage, AIMessage, SystemMessage
from langchain_openai import ChatOpenAI

from .config import get_settings
from .models import ConversationMessage, MessageRole, AgentState
from ..utils.token_counter import TokenCounter

logger = logging.getLogger(__name__)


class ContextManager:
    """Manages conversation context and handles token limits."""
    
    def __init__(self):
        self.settings = get_settings()
        self.token_counter = TokenCounter()
        self.llm = ChatOpenAI(
            model=self.settings.openai_model,
            temperature=0.1,
            api_key=self.settings.openai_api_key
        )
    
    def check_context_limit(self, state: AgentState) -> bool:
        """Check if context is approaching token limit."""
        current_tokens = self.calculate_total_tokens(state.messages)
        return current_tokens >= self.settings.summary_token_threshold
    
    def calculate_total_tokens(self, messages: List[ConversationMessage]) -> int:
        """Calculate total tokens in conversation."""
        total = 0
        for message in messages:
            if message.token_count:
                total += message.token_count
            else:
                # Calculate tokens if not already counted
                tokens = self.token_counter.count_tokens(message.content)
                total += tokens
        return total
    
    async def summarize_context(self, state: AgentState) -> AgentState:
        """Summarize conversation context when approaching token limit."""
        if not self.check_context_limit(state):
            return state
        
        logger.info("Context limit approached, summarizing conversation...")
        
        try:
            # Keep the last N messages as specified in settings
            messages_to_keep = state.get_recent_messages(self.settings.keep_last_messages)
            messages_to_summarize = state.messages[:-self.settings.keep_last_messages]
            
            if not messages_to_summarize:
                logger.warning("No messages to summarize")
                return state
            
            # Create summary prompt
            summary_content = self._create_summary_content(messages_to_summarize)
            summary_prompt = self._create_summary_prompt(summary_content)
            
            # Get summary from LLM
            summary_response = await self.llm.ainvoke([HumanMessage(content=summary_prompt)])
            summary_text = summary_response.content
            
            # Create new state with summarized context
            new_state = state.model_copy()
            new_state.messages = []
            
            # Add summary as system message
            summary_tokens = self.token_counter.count_tokens(summary_text)
            new_state.add_message(
                role=MessageRole.SYSTEM,
                content=f"Previous conversation summary: {summary_text}",
                token_count=summary_tokens,
                summarized=True
            )
            
            # Add recent messages
            for message in messages_to_keep:
                new_state.messages.append(message)
            
            # Update token count
            new_state.total_tokens = self.calculate_total_tokens(new_state.messages)
            new_state.context_summarized = True
            
            logger.info(f"Context summarized. Token count reduced from {state.total_tokens} to {new_state.total_tokens}")
            
            return new_state
            
        except Exception as e:
            logger.error(f"Error summarizing context: {str(e)}")
            state.add_error(f"Context summarization failed: {str(e)}")
            return state
    
    def _create_summary_content(self, messages: List[ConversationMessage]) -> str:
        """Create content string from messages for summarization."""
        content_parts = []
        for message in messages:
            role_prefix = {
                MessageRole.USER: "User",
                MessageRole.ASSISTANT: "Assistant",
                MessageRole.SYSTEM: "System",
                MessageRole.TOOL: "Tool"
            }.get(message.role, "Unknown")
            
            content_parts.append(f"{role_prefix}: {message.content}")
        
        return "\n\n".join(content_parts)
    
    def _create_summary_prompt(self, content: str) -> str:
        """Create prompt for conversation summarization."""
        return f"""Please provide a concise but comprehensive summary of the following conversation about GitHub repository analysis. 
Include:
1. Key topics discussed
2. Important findings or insights
3. Any technical details that should be preserved
4. Current context and state of the analysis

Keep the summary focused and preserve important technical information.

Conversation to summarize:
{content}

Summary:"""
    
    def convert_to_langchain_messages(self, messages: List[ConversationMessage]) -> List[BaseMessage]:
        """Convert internal messages to LangChain format."""
        langchain_messages = []
        
        for message in messages:
            if message.role == MessageRole.USER:
                langchain_messages.append(HumanMessage(content=message.content))
            elif message.role == MessageRole.ASSISTANT:
                langchain_messages.append(AIMessage(content=message.content))
            elif message.role == MessageRole.SYSTEM:
                langchain_messages.append(SystemMessage(content=message.content))
            # Tool messages are handled differently in different contexts
        
        return langchain_messages
    
    def should_summarize(self, state: AgentState) -> bool:
        """Determine if context should be summarized."""
        return (
            self.check_context_limit(state) and 
            not state.context_summarized and 
            len(state.messages) > self.settings.keep_last_messages
        )
    
    async def manage_context(self, state: AgentState) -> AgentState:
        """Main context management function."""
        if self.should_summarize(state):
            state = await self.summarize_context(state)
        
        return state