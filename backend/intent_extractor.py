# =============================================================================
# intent_extractor.py — Stage 1: Intent Extraction
# =============================================================================
# Takes a raw natural language prompt describing an application and extracts
# the structured intent: what kind of app, what features, who uses it, etc.
#
# This is the first stage in the pipeline and sets the foundation for all
# subsequent stages. It uses an LLM call with a carefully crafted system
# prompt to ensure comprehensive extraction.
#
# Input:  Raw text prompt (e.g., "Build a CRM with login and contacts")
# Output: IntentResult (app_name, features, roles, entities, etc.)
# =============================================================================

import logging
from backend.llm_client import LLMClient
from backend.schemas import IntentResult

logger = logging.getLogger(__name__)

# System prompt that instructs the LLM on how to extract intent.
# This is the "compiler specification" for Stage 1.
INTENT_EXTRACTION_PROMPT = """You are an expert software architect analyzing application requirements.

Your task is to extract structured intent from a natural language application description.

EXTRACTION RULES:
1. **app_name**: Create a short, descriptive name (2-4 words max). If the user mentions a specific name, use it.
2. **app_type**: Categorize the app (e.g., "Web Application", "Mobile App", "SaaS Platform", "Desktop Application").
3. **features**: Extract ALL mentioned features. Also infer obvious features that weren't explicitly stated.
   - If "login" is mentioned, include "authentication" and "user registration" if not already listed.
   - If "dashboard" is mentioned, include "analytics" if relevant.
4. **roles**: Extract all user roles. If none are mentioned, default to ["admin", "user"].
5. **entities**: Extract all data entities/domain objects. Always include "User" if authentication is mentioned.
6. **business_requirements**: Extract any business rules, constraints, or specific requirements.
7. **assumptions**: If the prompt is vague or incomplete, list the assumptions you made.
   - Example: If no auth method is specified, assume "Email/password authentication will be used".

IMPORTANT:
- Always provide meaningful output even for vague prompts like "build something useful".
- For vague prompts, make reasonable assumptions and document them ALL in the assumptions field.
- Never leave any field empty — provide at least one item in each list.
- Be thorough but concise in your extractions."""


def extract_intent(prompt: str, llm_client: LLMClient) -> IntentResult:
    """
    Extract structured intent from a natural language application description.
    
    This function takes the raw user prompt and uses an LLM to extract:
    - Application name and type
    - Features list
    - User roles
    - Data entities
    - Business requirements
    - Assumptions (for vague prompts)
    
    Args:
        prompt: The natural language application description from the user
        llm_client: Configured LLM client instance
        
    Returns:
        IntentResult: Validated Pydantic model with extracted intent
        
    Example:
        >>> client = LLMClient(provider="gemini", api_key="...")
        >>> result = extract_intent("Build a CRM with login and contacts", client)
        >>> print(result.app_name)  # "CRM System"
        >>> print(result.features)  # ["login", "contacts", "authentication", ...]
    """
    logger.info(f"Stage 1: Extracting intent from prompt ({len(prompt)} chars)")
    
    # Construct the user message with the prompt
    user_message = f"""Analyze the following application requirement and extract the structured intent:

APPLICATION REQUIREMENT:
\"\"\"{prompt}\"\"\"

Extract the app name, type, features, roles, entities, business requirements, and any assumptions you need to make."""
    
    # Call the LLM with structured output
    result = llm_client.generate_structured(
        prompt=user_message,
        response_model=IntentResult,
        system_prompt=INTENT_EXTRACTION_PROMPT,
    )
    
    logger.info(
        f"Stage 1 complete: app_name='{result.app_name}', "
        f"features={len(result.features)}, roles={len(result.roles)}, "
        f"entities={len(result.entities)}, assumptions={len(result.assumptions)}"
    )
    
    return result
