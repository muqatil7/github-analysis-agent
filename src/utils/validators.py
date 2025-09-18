"""Input validation utilities."""

import re
from typing import Optional
from urllib.parse import urlparse

from ..core.models import AnalysisType


def validate_github_url(url: str) -> bool:
    """Validate GitHub repository URL format."""
    if not url or not isinstance(url, str):
        return False
    
    # Parse URL
    try:
        parsed = urlparse(url.strip())
    except Exception:
        return False
    
    # Check basic URL structure
    if not parsed.scheme or not parsed.netloc:
        return False
    
    # Check if it's a GitHub URL
    if parsed.netloc.lower() not in ['github.com', 'www.github.com']:
        return False
    
    # Check path format: /owner/repo
    path = parsed.path.strip('/')
    path_parts = path.split('/')
    
    if len(path_parts) < 2:
        return False
    
    owner, repo = path_parts[0], path_parts[1]
    
    # Validate owner and repo names (GitHub username/org rules)
    if not _is_valid_github_name(owner) or not _is_valid_github_name(repo.replace('.git', '')):
        return False
    
    return True


def _is_valid_github_name(name: str) -> bool:
    """Validate GitHub username/repository name."""
    if not name or len(name) > 39:  # GitHub max length is 39
        return False
    
    # GitHub names can contain alphanumeric characters and hyphens
    # Cannot start or end with hyphen
    pattern = r'^[a-zA-Z0-9]([a-zA-Z0-9-]*[a-zA-Z0-9])?$'
    return bool(re.match(pattern, name))


def validate_analysis_type(analysis_type: str) -> bool:
    """Validate analysis type."""
    if not analysis_type:
        return False
    
    try:
        AnalysisType(analysis_type.lower())
        return True
    except ValueError:
        return False


def sanitize_input(text: str, max_length: int = 10000) -> str:
    """Sanitize user input."""
    if not text:
        return ""
    
    # Strip whitespace and limit length
    sanitized = text.strip()[:max_length]
    
    # Remove potentially harmful characters (basic sanitization)
    # This is a simple approach - for production, consider more robust sanitization
    harmful_patterns = [
        r'<script[^>]*>.*?</script>',  # Script tags
        r'javascript:',  # JavaScript URLs
        r'on\w+\s*=',   # Event handlers
    ]
    
    for pattern in harmful_patterns:
        sanitized = re.sub(pattern, '', sanitized, flags=re.IGNORECASE | re.DOTALL)
    
    return sanitized


def extract_github_info(url: str) -> Optional[dict]:
    """Extract owner, repo, and branch from GitHub URL."""
    if not validate_github_url(url):
        return None
    
    try:
        parsed = urlparse(url.strip())
        path = parsed.path.strip('/')
        path_parts = path.split('/')
        
        owner = path_parts[0]
        repo = path_parts[1].replace('.git', '')
        
        # Extract branch if present in URL (e.g., /tree/branch-name)
        branch = None
        if len(path_parts) > 3 and path_parts[2] == 'tree':
            branch = path_parts[3]
        
        return {
            'owner': owner,
            'repo': repo,
            'branch': branch or 'main',
            'full_name': f"{owner}/{repo}"
        }
    except Exception:
        return None


def validate_system_prompt(prompt: str) -> bool:
    """Validate system prompt."""
    if not prompt or not isinstance(prompt, str):
        return False
    
    # Basic validation - ensure it's not too short or too long
    prompt = prompt.strip()
    if len(prompt) < 10 or len(prompt) > 5000:
        return False
    
    return True