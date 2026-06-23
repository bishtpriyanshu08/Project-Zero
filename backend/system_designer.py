# =============================================================================
# system_designer.py — Stage 2: System Design
# =============================================================================
# Takes the extracted intent (Stage 1 output) and expands it into a full
# system design: refined entities, roles, workflows, permissions matrix,
# and architecture description.
#
# This stage bridges the gap between "what the user wants" (intent) and
# "how to build it" (schemas). It creates the architectural blueprint.
#
# Input:  IntentResult (from Stage 1)
# Output: SystemDesign (entities, roles, workflows, permissions, architecture)
# =============================================================================

import logging
from backend.llm_client import LLMClient
from backend.schemas import IntentResult, SystemDesign

logger = logging.getLogger(__name__)

# System prompt for the system design LLM call
SYSTEM_DESIGN_PROMPT = """You are an expert software architect designing application systems.

Your task is to create a comprehensive system design based on extracted application intent.

DESIGN RULES:
1. **entities**: Refine and expand the entity list. Add supporting entities needed for the features.
   - Example: If "login" is a feature, ensure "User" and "Session" entities exist.
   - Example: If "payments" is a feature, add "Payment", "Invoice", "Transaction" entities.
   - Always include a "User" entity.

2. **roles**: Refine roles with clear hierarchy. Ensure at least "admin" and "user" exist.

3. **workflows**: Create specific user workflows for each major feature.
   - Format: "<Action> <Object>" (e.g., "User Login", "Create Contact", "Generate Report")
   - Include CRUD workflows for each major entity.
   - Include authentication workflows (login, register, logout).
   - Include at least 5 workflows.

4. **permissions**: Create a detailed permission matrix.
   - Each permission maps a role to a resource and allowed actions.
   - Actions should be from: ["create", "read", "update", "delete", "manage"]
   - Admin should have the most permissions.
   - Every entity should have at least one permission entry.

5. **architecture**: Describe the technical architecture in 1-2 sentences.
   - Example: "Three-tier web application with React frontend, REST API backend, and PostgreSQL database."

IMPORTANT:
- Be comprehensive — missing workflows or permissions will cause validation failures later.
- Every entity should appear in at least one permission entry.
- Every role should appear in at least one permission entry."""


def design_system(intent: IntentResult, llm_client: LLMClient) -> SystemDesign:
    """
    Generate a system design from the extracted intent.
    
    Takes the output of Stage 1 and creates an architectural blueprint
    including refined entities, workflows, permission matrices, and
    a high-level architecture description.
    
    Args:
        intent: The IntentResult from Stage 1 (intent extraction)
        llm_client: Configured LLM client instance
        
    Returns:
        SystemDesign: Validated Pydantic model with the system design
        
    Example:
        >>> design = design_system(intent_result, client)
        >>> print(design.workflows)   # ["User Login", "Create Contact", ...]
        >>> print(design.permissions) # [Permission(role="admin", ...), ...]
    """
    logger.info(f"Stage 2: Designing system for '{intent.app_name}'")
    
    # Serialize the intent to provide as context to the LLM
    intent_json = intent.model_dump_json(indent=2)
    
    user_message = f"""Based on the following extracted application intent, create a comprehensive system design.

EXTRACTED INTENT:
{intent_json}

Design the system with:
1. Refined and expanded entity list
2. Clear role hierarchy  
3. Detailed user workflows for each feature
4. Comprehensive permission matrix (role → resource → actions)
5. High-level architecture description"""
    
    # Call the LLM with structured output
    result = llm_client.generate_structured(
        prompt=user_message,
        response_model=SystemDesign,
        system_prompt=SYSTEM_DESIGN_PROMPT,
    )
    
    logger.info(
        f"Stage 2 complete: entities={len(result.entities)}, "
        f"roles={len(result.roles)}, workflows={len(result.workflows)}, "
        f"permissions={len(result.permissions)}"
    )
    
    return result
