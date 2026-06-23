# =============================================================================
# schema_generator.py — Stage 3: Schema Generation
# =============================================================================
# Takes the intent (Stage 1) and system design (Stage 2) and generates
# five complete schema layers in a single LLM call:
#
#   1. Database Schema  — Tables, columns, relationships, foreign keys
#   2. API Schema       — REST endpoints, methods, request/response fields
#   3. UI Schema        — Pages, components, routes, role-based access
#   4. Auth Schema      — Authentication method, roles, permissions
#   5. Business Rules   — Constraints, conditions, entity relationships
#
# Input:  IntentResult + SystemDesign
# Output: FullAppSchema (all 5 layers combined)
# =============================================================================

import logging
from backend.llm_client import LLMClient
from backend.schemas import IntentResult, SystemDesign, FullAppSchema

logger = logging.getLogger(__name__)

# System prompt for schema generation — the most detailed prompt in the pipeline
SCHEMA_GENERATION_PROMPT = """You are an expert full-stack architect generating complete application schemas.

Your task is to generate five interconnected schema layers that are CONSISTENT with each other.

== DATABASE SCHEMA ==
- Create a table for EACH entity in the system design.
- Every table MUST have an "id" column (INTEGER, primary key).
- Every table MUST have "created_at" and "updated_at" columns (TIMESTAMP).
- Use appropriate data types: INTEGER, VARCHAR(255), TEXT, BOOLEAN, TIMESTAMP, DECIMAL.
- Add foreign key relationships where entities are related.
  - Format foreign_key as "table_name.column_name" (e.g., "users.id").
- The "users" table MUST include: id, email, password_hash, role, created_at, updated_at.

== API SCHEMA ==
- Create CRUD endpoints for each major entity.
  - GET /api/{entity}s — list all (response: list of entity fields)
  - GET /api/{entity}s/{id} — get one
  - POST /api/{entity}s — create new (request: entity fields)
  - PUT /api/{entity}s/{id} — update (request: entity fields)
  - DELETE /api/{entity}s/{id} — delete
- Create auth endpoints: POST /api/auth/login, POST /api/auth/register, POST /api/auth/logout.
- Set auth_required=true for all endpoints except login and register.
- Set allowed_roles based on the permission matrix from the system design.
- Request and response field names MUST match database column names.

== UI SCHEMA ==
- Create pages for each major feature.
- ALWAYS include: Login page (/login), Dashboard page (/dashboard).
- Each page should have relevant components (form, table, chart, card, navbar, button).
- Set data_source on components to the corresponding API endpoint path.
  - Example: A contacts table component should have data_source="/api/contacts".
- Set requires_auth and allowed_roles appropriately.

== AUTH SCHEMA ==
- Set auth_method to "email_password" (or "jwt" if appropriate).
- Create a role definition for EACH role in the system design.
- Permissions format: "action:resource" (e.g., "read:contacts", "write:users", "delete:invoices").

== BUSINESS RULES ==
- Create rules for premium features, role restrictions, data validation, etc.
- Each rule must reference entities that exist in the database schema.
- Include at least 3 business rules.

== CRITICAL CONSISTENCY RULES ==
- Every data_source in UI components must match an API endpoint path.
- Every field in API requests/responses must correspond to a database column.
- Every role in allowed_roles (UI & API) must exist in the auth schema.
- Every entity in business rules must exist as a database table.
- Foreign keys must reference existing tables and columns."""


def generate_schemas(
    intent: IntentResult,
    design: SystemDesign,
    llm_client: LLMClient
) -> FullAppSchema:
    """
    Generate all five schema layers from the intent and system design.
    
    This is the most complex LLM call in the pipeline, producing the
    complete application configuration. The system prompt enforces
    cross-layer consistency to minimize validation failures.
    
    Args:
        intent: The IntentResult from Stage 1
        design: The SystemDesign from Stage 2
        llm_client: Configured LLM client instance
        
    Returns:
        FullAppSchema: All five schema layers (database, API, UI, auth, business rules)
        
    Example:
        >>> schema = generate_schemas(intent, design, client)
        >>> print(len(schema.database.tables))   # Number of tables
        >>> print(len(schema.api.endpoints))     # Number of endpoints
    """
    logger.info(f"Stage 3: Generating schemas for '{intent.app_name}'")
    
    # Serialize both inputs to provide as context
    intent_json = intent.model_dump_json(indent=2)
    design_json = design.model_dump_json(indent=2)
    
    user_message = f"""Generate a complete, consistent application schema based on the following:

== EXTRACTED INTENT ==
{intent_json}

== SYSTEM DESIGN ==
{design_json}

Generate all five schema layers:
1. Database Schema (tables, columns, foreign keys)
2. API Schema (REST endpoints with request/response fields)
3. UI Schema (pages with components)
4. Auth Schema (roles and permissions)
5. Business Rules (constraints and conditions)

IMPORTANT: All layers must be consistent with each other:
- UI data sources → API endpoints
- API fields → Database columns  
- UI/API roles → Auth roles
- Business rule entities → Database tables"""
    
    # Call the LLM with structured output
    result = llm_client.generate_structured(
        prompt=user_message,
        response_model=FullAppSchema,
        system_prompt=SCHEMA_GENERATION_PROMPT,
    )
    
    logger.info(
        f"Stage 3 complete: tables={len(result.database.tables)}, "
        f"endpoints={len(result.api.endpoints)}, "
        f"pages={len(result.ui.pages)}, "
        f"roles={len(result.auth.roles)}, "
        f"rules={len(result.business_rules.rules)}"
    )
    
    return result
