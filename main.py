#!/usr/bin/env python3
"""Main entry point for GitHub Analysis Agent."""

import asyncio
import logging
import os
import sys
from typing import Optional

from dotenv import load_dotenv

# Add src to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'src'))

from src.core.config import get_settings
from src.core.models import AnalysisType
from src.agents.github_agent import GitHubAnalysisAgent
from src.utils.validators import validate_github_url

# Load environment variables
load_dotenv()

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler(sys.stdout),
        logging.FileHandler('github_agent.log')
    ]
)

logger = logging.getLogger(__name__)


async def main():
    """Main function to run the GitHub Analysis Agent."""
    print("🤖 GitHub Analysis Agent")
    print("=" * 50)
    
    # Initialize settings
    try:
        settings = get_settings()
        logger.info("Settings loaded successfully")
    except Exception as e:
        logger.error(f"Failed to load settings: {e}")
        print("❌ Error: Failed to load configuration. Please check your .env file.")
        return
    
    # Initialize agent
    agent = GitHubAnalysisAgent()
    
    try:
        print("🔄 Initializing agent...")
        success = await agent.initialize()
        if not success:
            print("❌ Failed to initialize agent")
            return
        
        print("✅ Agent initialized successfully\n")
        
        # Interactive mode
        await interactive_mode(agent)
        
    except KeyboardInterrupt:
        print("\n👋 Goodbye!")
    except Exception as e:
        logger.error(f"Unexpected error: {e}")
        print(f"❌ Unexpected error: {e}")
    finally:
        await agent.close()


async def interactive_mode(agent: GitHubAnalysisAgent):
    """Interactive mode for the agent."""
    print("📋 Available Analysis Types:")
    for analysis_type in AnalysisType:
        print(f"   • {analysis_type.value}")
    print()
    
    while True:
        try:
            # Get repository URL
            repo_url = input("🔗 Enter GitHub repository URL (or 'quit' to exit): ").strip()
            
            if repo_url.lower() in ['quit', 'exit', 'q']:
                break
            
            if not repo_url:
                continue
            
            # Validate URL
            if not validate_github_url(repo_url):
                print("❌ Invalid GitHub repository URL. Please try again.\n")
                continue
            
            # Get analysis type
            analysis_input = input("📊 Analysis type (summary/security/code_review/documentation/dependencies/custom) [summary]: ").strip().lower()
            analysis_type = AnalysisType.SUMMARY
            
            if analysis_input:
                try:
                    analysis_type = AnalysisType(analysis_input)
                except ValueError:
                    print(f"❌ Unknown analysis type '{analysis_input}'. Using 'summary'.\n")
            
            # Get optional prompts
            system_prompt = input("🔧 System prompt (optional): ").strip()
            user_prompt = input("💬 User prompt (optional): ").strip()
            
            print("\n🔄 Analyzing repository...")
            
            # Run analysis
            result = await agent.analyze(
                repository_url=repo_url,
                analysis_type=analysis_type,
                system_prompt=system_prompt,
                user_prompt=user_prompt
            )
            
            # Display results
            await display_results(result)
            
        except KeyboardInterrupt:
            print("\n👋 Goodbye!")
            break
        except Exception as e:
            logger.error(f"Error in interactive mode: {e}")
            print(f"❌ Error: {e}\n")


async def display_results(state):
    """Display analysis results."""
    print("\n" + "=" * 60)
    print("📊 ANALYSIS RESULTS")
    print("=" * 60)
    
    if state.repository:
        print(f"📁 Repository: {state.repository.full_name}")
        print(f"🔍 Analysis Type: {state.analysis_type.value}")
        print(f"⏰ Completed Steps: {', '.join(state.completed_steps)}")
        print()
    
    if state.errors:
        print("❌ ERRORS:")
        for error in state.errors:
            print(f"   • {error}")
        print()
    
    if state.current_analysis and state.current_analysis.summary:
        print("📋 ANALYSIS SUMMARY:")
        print("-" * 40)
        print(state.current_analysis.summary)
        print()
    
    if state.current_analysis and state.current_analysis.findings:
        print("🔍 KEY FINDINGS:")
        for i, finding in enumerate(state.current_analysis.findings, 1):
            print(f"   {i}. {finding}")
        print()
    
    if state.current_analysis and state.current_analysis.recommendations:
        print("💡 RECOMMENDATIONS:")
        for i, rec in enumerate(state.current_analysis.recommendations, 1):
            print(f"   {i}. {rec}")
        print()
    
    # Display token usage if available
    if state.total_tokens > 0:
        print(f"🔢 Token Usage: {state.total_tokens:,} tokens")
        if state.context_summarized:
            print("📝 Context was summarized due to token limit")
        print()
    
    print("=" * 60 + "\n")


async def batch_mode(repositories: list, analysis_type: AnalysisType = AnalysisType.SUMMARY):
    """Batch processing mode for multiple repositories."""
    agent = GitHubAnalysisAgent()
    
    try:
        await agent.initialize()
        
        results = []
        for repo_url in repositories:
            print(f"Analyzing {repo_url}...")
            result = await agent.analyze(
                repository_url=repo_url,
                analysis_type=analysis_type
            )
            results.append(result)
        
        return results
    
    finally:
        await agent.close()


def cli_mode():
    """Command line interface mode."""
    import argparse
    
    parser = argparse.ArgumentParser(description="GitHub Repository Analysis Agent")
    parser.add_argument("url", help="GitHub repository URL")
    parser.add_argument(
        "-t", "--type", 
        choices=[t.value for t in AnalysisType],
        default="summary",
        help="Analysis type"
    )
    parser.add_argument("-s", "--system-prompt", help="System prompt")
    parser.add_argument("-u", "--user-prompt", help="User prompt")
    parser.add_argument("-v", "--verbose", action="store_true", help="Verbose output")
    
    args = parser.parse_args()
    
    if args.verbose:
        logging.getLogger().setLevel(logging.DEBUG)
    
    async def run_cli():
        agent = GitHubAnalysisAgent()
        try:
            await agent.initialize()
            
            result = await agent.analyze(
                repository_url=args.url,
                analysis_type=AnalysisType(args.type),
                system_prompt=args.system_prompt or "",
                user_prompt=args.user_prompt or ""
            )
            
            await display_results(result)
        
        finally:
            await agent.close()
    
    asyncio.run(run_cli())


if __name__ == "__main__":
    if len(sys.argv) > 1:
        # CLI mode if arguments provided
        cli_mode()
    else:
        # Interactive mode
        asyncio.run(main())