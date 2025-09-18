"""Main GitHub Analysis Agent using LangGraph and LangChain."""

import asyncio
import logging
from typing import Any, Dict, List, Optional

from langchain.schema import BaseMessage, HumanMessage, AIMessage, SystemMessage
from langchain_openai import ChatOpenAI
from langgraph.graph import StateGraph, END
from langgraph.checkpoint.memory import MemorySaver

from ..core.config import get_settings
from ..core.models import (
    AgentState, 
    AnalysisType, 
    AnalysisResult, 
    GitHubRepository, 
    MessageRole
)
from ..core.context_manager import ContextManager
from ..utils.validators import validate_github_url, extract_github_info
from .mcp_client import MCPClient

logger = logging.getLogger(__name__)


class GitHubAnalysisAgent:
    """Main agent for GitHub repository analysis."""
    
    def __init__(self):
        self.settings = get_settings()
        self.llm = ChatOpenAI(
            model=self.settings.openai_model,
            temperature=self.settings.openai_temperature,
            api_key=self.settings.openai_api_key
        )
        self.context_manager = ContextManager()
        self.mcp_client = MCPClient()
        self.workflow = None
        self._initialized = False
    
    async def initialize(self) -> bool:
        """Initialize the agent and its components."""
        if self._initialized:
            return True
        
        try:
            # Initialize MCP client
            mcp_success = await self.mcp_client.initialize()
            if not mcp_success:
                logger.warning("MCP client initialization failed, continuing with limited functionality")
            
            # Build workflow graph
            self.workflow = self._build_workflow()
            
            self._initialized = True
            logger.info("GitHub Analysis Agent initialized successfully")
            return True
        
        except Exception as e:
            logger.error(f"Failed to initialize GitHub Analysis Agent: {str(e)}")
            return False
    
    def _build_workflow(self) -> StateGraph:
        """Build the LangGraph workflow."""
        # Create state graph
        workflow = StateGraph(AgentState)
        
        # Add nodes
        workflow.add_node("validate_input", self._validate_input_node)
        workflow.add_node("analyze_repository", self._analyze_repository_node)
        workflow.add_node("generate_response", self._generate_response_node)
        workflow.add_node("manage_context", self._manage_context_node)
        
        # Set entry point
        workflow.set_entry_point("validate_input")
        
        # Add edges
        workflow.add_edge("validate_input", "analyze_repository")
        workflow.add_edge("analyze_repository", "generate_response")
        workflow.add_edge("generate_response", "manage_context")
        workflow.add_edge("manage_context", END)
        
        # Compile workflow
        memory = MemorySaver()
        return workflow.compile(checkpointer=memory)
    
    async def _validate_input_node(self, state: AgentState) -> AgentState:
        """Validate and parse user input."""
        logger.info("Validating input...")
        
        try:
            # Validate repository URL
            if not validate_github_url(state.repository_url):
                state.add_error("Invalid GitHub repository URL")
                return state
            
            # Extract repository information
            repo_info = extract_github_info(state.repository_url)
            if not repo_info:
                state.add_error("Could not extract repository information from URL")
                return state
            
            # Create repository object
            state.repository = GitHubRepository.from_url(state.repository_url)
            
            # Mark step as completed
            state.mark_step_completed("validate_input")
            
            logger.info(f"Input validated successfully for {state.repository.full_name}")
            return state
        
        except Exception as e:
            error_msg = f"Error validating input: {str(e)}"
            logger.error(error_msg)
            state.add_error(error_msg)
            return state
    
    async def _analyze_repository_node(self, state: AgentState) -> AgentState:
        """Analyze the GitHub repository using MCP client."""
        logger.info(f"Analyzing repository: {state.repository.full_name}")
        
        try:
            # Get repository structure and information
            repo_data = await self.mcp_client.get_repository_structure(
                state.repository.owner,
                state.repository.name
            )
            
            # Store MCP response
            state.mcp_responses.append({
                "action": "get_repository_structure",
                "data": repo_data,
                "timestamp": asyncio.get_event_loop().time()
            })
            
            # Create analysis result
            analysis_result = AnalysisResult(
                repository=state.repository,
                analysis_type=state.analysis_type,
                summary="Repository analysis completed",
                details=repo_data,
                findings=[],
                recommendations=[]
            )
            
            state.current_analysis = analysis_result
            state.analysis_history.append(analysis_result)
            
            # Mark step as completed
            state.mark_step_completed("analyze_repository")
            
            logger.info(f"Repository analysis completed for {state.repository.full_name}")
            return state
        
        except Exception as e:
            error_msg = f"Error analyzing repository: {str(e)}"
            logger.error(error_msg)
            state.add_error(error_msg)
            return state
    
    async def _generate_response_node(self, state: AgentState) -> AgentState:
        """Generate analysis response using LLM."""
        logger.info("Generating response...")
        
        try:
            # Prepare context for LLM
            system_prompt = self._create_system_prompt(state)
            user_prompt = self._create_user_prompt(state)
            
            # Create messages
            messages = [
                SystemMessage(content=system_prompt),
                HumanMessage(content=user_prompt)
            ]
            
            # Get response from LLM
            response = await self.llm.ainvoke(messages)
            response_content = response.content
            
            # Add messages to state
            state.add_message(MessageRole.SYSTEM, system_prompt)
            state.add_message(MessageRole.USER, user_prompt)
            state.add_message(MessageRole.ASSISTANT, response_content)
            
            # Update analysis result with LLM response
            if state.current_analysis:
                state.current_analysis.summary = response_content
            
            # Mark step as completed
            state.mark_step_completed("generate_response")
            
            logger.info("Response generated successfully")
            return state
        
        except Exception as e:
            error_msg = f"Error generating response: {str(e)}"
            logger.error(error_msg)
            state.add_error(error_msg)
            return state
    
    async def _manage_context_node(self, state: AgentState) -> AgentState:
        """Manage context length and summarize if needed."""
        logger.info("Managing context...")
        
        try:
            # Check and manage context
            managed_state = await self.context_manager.manage_context(state)
            
            # Mark step as completed
            managed_state.mark_step_completed("manage_context")
            
            logger.info("Context management completed")
            return managed_state
        
        except Exception as e:
            error_msg = f"Error managing context: {str(e)}"
            logger.error(error_msg)
            state.add_error(error_msg)
            return state
    
    def _create_system_prompt(self, state: AgentState) -> str:
        """Create system prompt based on analysis type."""
        base_prompt = f"""You are an expert GitHub repository analyst. Your task is to analyze the provided repository data and generate a comprehensive {state.analysis_type.value} report.

Repository: {state.repository.full_name}
Analysis Type: {state.analysis_type.value}

Provide a detailed, professional analysis based on the repository data provided."""
        
        # Add custom system prompt if provided
        if state.system_prompt:
            base_prompt += f"\n\nAdditional Instructions: {state.system_prompt}"
        
        return base_prompt
    
    def _create_user_prompt(self, state: AgentState) -> str:
        """Create user prompt with repository data."""
        prompt_parts = []
        
        # Add user prompt if provided
        if state.user_prompt:
            prompt_parts.append(f"User Request: {state.user_prompt}")
        
        # Add repository data
        if state.mcp_responses:
            prompt_parts.append("Repository Data:")
            for response in state.mcp_responses:
                prompt_parts.append(f"- {response['action']}: {response['data']}")
        
        return "\n\n".join(prompt_parts)
    
    async def analyze(self, 
                     repository_url: str,
                     analysis_type: AnalysisType = AnalysisType.SUMMARY,
                     system_prompt: str = "",
                     user_prompt: str = "") -> AgentState:
        """Main analysis method."""
        if not self._initialized:
            await self.initialize()
        
        # Create initial state
        initial_state = AgentState(
            repository_url=repository_url,
            analysis_type=analysis_type,
            system_prompt=system_prompt,
            user_prompt=user_prompt
        )
        
        try:
            # Run workflow
            config = {"configurable": {"thread_id": "analysis_session"}}
            result = await self.workflow.ainvoke(initial_state, config=config)
            
            return result
        
        except Exception as e:
            logger.error(f"Error during analysis: {str(e)}")
            initial_state.add_error(f"Analysis failed: {str(e)}")
            return initial_state
    
    async def close(self):
        """Clean up resources."""
        if self.mcp_client:
            await self.mcp_client.close()