# =============================================================================
# schemas.py — Pydantic Data Models (Single Source of Truth)
# =============================================================================
# Every piece of data flowing through the pipeline is defined here.
# These models serve as:
#   1. LLM output contracts (response_schema for Gemini API)
#   2. Validation targets (Pydantic enforces types and required fields)
#   3. Documentation (field descriptions explain what each field means)
#
# The models are organized by pipeline stage:
#   - Stage 1: IntentResult
#   - Stage 2: SystemDesign
#   - Stage 3: FullAppSchema (Database, API, UI, Auth, Business Rules)
#   - Stage 4: ValidationReport
#   - Stage 5: RepairReport
#   - Stage 6: ExecutionResult
#   - Pipeline: PipelineResult (wraps all stages)
# =============================================================================

# pyrefly: ignore [missing-import]
from pydantic import BaseModel, Field
from typing import List, Optional
from enum import Enum


# =============================================================================
# STAGE 1: Intent Extraction Models
# =============================================================================

class IntentResult(BaseModel):
    """
    Output of Stage 1 — Intent Extraction.
    
    Captures the core intent from a natural language application description:
    what kind of app, what features, who uses it, and what data it manages.
    """
    app_name: str = Field(
        ...,
        description="A short, descriptive name for the application (e.g., 'CRM System')"
    )
    app_type: str = Field(
        ...,
        description="Category of application (e.g., 'Web Application', 'Mobile App', 'SaaS Platform')"
    )
    features: List[str] = Field(
        ...,
        min_length=1,
        description="List of features the app should have (e.g., ['login', 'dashboard', 'contacts'])"
    )
    roles: List[str] = Field(
        ...,
        min_length=1,
        description="User roles in the system (e.g., ['admin', 'user', 'manager'])"
    )
    entities: List[str] = Field(
        ...,
        min_length=1,
        description="Data entities / domain objects (e.g., ['User', 'Contact', 'Invoice'])"
    )
    business_requirements: List[str] = Field(
        default_factory=list,
        description="High-level business rules or constraints extracted from the prompt"
    )
    assumptions: List[str] = Field(
        default_factory=list,
        description="Assumptions made when the prompt was vague or incomplete"
    )


# =============================================================================
# STAGE 2: System Design Models
# =============================================================================

class Permission(BaseModel):
    """A single permission mapping: which role can perform which action on which resource."""
    role: str = Field(..., description="The user role (e.g., 'admin')")
    resource: str = Field(..., description="The resource being accessed (e.g., 'Contact')")
    actions: List[str] = Field(
        ...,
        description="Allowed actions (e.g., ['create', 'read', 'update', 'delete'])"
    )


class SystemDesign(BaseModel):
    """
    Output of Stage 2 — System Design.
    
    Expands the extracted intent into a structured system architecture
    with entities, roles, workflows, and permissions.
    """
    entities: List[str] = Field(
        ...,
        min_length=1,
        description="Refined list of data entities for the application"
    )
    roles: List[str] = Field(
        ...,
        min_length=1,
        description="Refined list of user roles"
    )
    workflows: List[str] = Field(
        ...,
        min_length=1,
        description="Key user workflows (e.g., 'User Login', 'Create Contact', 'Generate Report')"
    )
    permissions: List[Permission] = Field(
        ...,
        min_length=1,
        description="Permission matrix mapping roles to resources and actions"
    )
    architecture: str = Field(
        ...,
        description="High-level architecture description (e.g., 'Three-tier web application with REST API')"
    )


# =============================================================================
# STAGE 3: Schema Generation Models
# =============================================================================

# ----- Database Schema -----

class Column(BaseModel):
    """A single column in a database table."""
    name: str = Field(..., description="Column name (e.g., 'id', 'email', 'created_at')")
    data_type: str = Field(..., description="SQL data type (e.g., 'INTEGER', 'VARCHAR(255)', 'TIMESTAMP')")
    primary_key: bool = Field(default=False, description="Whether this column is the primary key")
    nullable: bool = Field(default=True, description="Whether this column can be NULL")
    foreign_key: Optional[str] = Field(
        default=None,
        description="Foreign key reference in format 'table_name.column_name', or null if not a FK"
    )


class Table(BaseModel):
    """A single database table with its columns."""
    name: str = Field(..., description="Table name (e.g., 'users', 'contacts')")
    columns: List[Column] = Field(
        ...,
        min_length=1,
        description="List of columns in this table"
    )


class DatabaseSchema(BaseModel):
    """Complete database schema with all tables."""
    tables: List[Table] = Field(
        ...,
        min_length=1,
        description="All database tables for the application"
    )


# ----- API Schema -----

class APIField(BaseModel):
    """A single field in an API request or response."""
    name: str = Field(..., description="Field name (e.g., 'email', 'password')")
    field_type: str = Field(..., description="Data type (e.g., 'string', 'integer', 'boolean')")
    required: bool = Field(default=True, description="Whether this field is required")


class Endpoint(BaseModel):
    """A single API endpoint."""
    path: str = Field(..., description="URL path (e.g., '/api/contacts')")
    method: str = Field(..., description="HTTP method (e.g., 'GET', 'POST', 'PUT', 'DELETE')")
    description: str = Field(default="", description="What this endpoint does")
    request_fields: List[APIField] = Field(
        default_factory=list,
        description="Fields expected in the request body"
    )
    response_fields: List[APIField] = Field(
        default_factory=list,
        description="Fields returned in the response"
    )
    auth_required: bool = Field(default=True, description="Whether authentication is required")
    allowed_roles: List[str] = Field(
        default_factory=list,
        description="Roles allowed to access this endpoint (empty = all authenticated users)"
    )


class APISchema(BaseModel):
    """Complete API schema with all endpoints."""
    endpoints: List[Endpoint] = Field(
        ...,
        min_length=1,
        description="All API endpoints for the application"
    )


# ----- UI Schema -----

class UIComponent(BaseModel):
    """A single UI component on a page."""
    component_type: str = Field(
        ...,
        description="Type of component (e.g., 'form', 'table', 'chart', 'button', 'card', 'navbar')"
    )
    label: str = Field(..., description="Display label or title for the component")
    data_source: Optional[str] = Field(
        default=None,
        description="API endpoint this component fetches data from (e.g., '/api/contacts')"
    )


class Page(BaseModel):
    """A single page in the application UI."""
    name: str = Field(..., description="Page name (e.g., 'Dashboard', 'Login', 'Contact List')")
    route: str = Field(..., description="URL route (e.g., '/dashboard', '/login')")
    components: List[UIComponent] = Field(
        ...,
        min_length=1,
        description="UI components on this page"
    )
    requires_auth: bool = Field(default=True, description="Whether the page requires authentication")
    allowed_roles: List[str] = Field(
        default_factory=list,
        description="Roles allowed to view this page (empty = all authenticated users)"
    )


class UISchema(BaseModel):
    """Complete UI schema with all pages."""
    pages: List[Page] = Field(
        ...,
        min_length=1,
        description="All pages in the application"
    )


# ----- Auth Schema -----

class RoleDefinition(BaseModel):
    """Definition of a single role and its permissions."""
    role_name: str = Field(..., description="Name of the role (e.g., 'admin', 'user')")
    permissions: List[str] = Field(
        ...,
        description="List of permissions for this role (e.g., ['read:contacts', 'write:contacts'])"
    )


class AuthSchema(BaseModel):
    """Complete authentication and authorization schema."""
    auth_method: str = Field(
        default="email_password",
        description="Authentication method (e.g., 'email_password', 'oauth', 'jwt')"
    )
    roles: List[RoleDefinition] = Field(
        ...,
        min_length=1,
        description="All role definitions with their permissions"
    )


# ----- Business Rules Schema -----

class BusinessRule(BaseModel):
    """A single business rule or constraint."""
    name: str = Field(..., description="Short name for the rule (e.g., 'Premium Feature Access')")
    description: str = Field(..., description="Detailed description of the rule")
    conditions: List[str] = Field(
        ...,
        description="Conditions that trigger this rule (e.g., ['user.subscription == premium'])"
    )
    entities_involved: List[str] = Field(
        ...,
        description="Entities this rule applies to (e.g., ['User', 'Subscription'])"
    )


class BusinessRulesSchema(BaseModel):
    """Complete business rules schema."""
    rules: List[BusinessRule] = Field(
        default_factory=list,
        description="All business rules for the application"
    )


# ----- Combined Full App Schema (Stage 3 output) -----

class FullAppSchema(BaseModel):
    """
    Output of Stage 3 — Schema Generation.
    
    The complete application schema combining all five layers:
    database, API, UI, authentication, and business rules.
    """
    database: DatabaseSchema = Field(..., description="Database schema with tables and columns")
    api: APISchema = Field(..., description="API schema with endpoints")
    ui: UISchema = Field(..., description="UI schema with pages and components")
    auth: AuthSchema = Field(..., description="Authentication and authorization schema")
    business_rules: BusinessRulesSchema = Field(..., description="Business rules and constraints")


# =============================================================================
# STAGE 4: Validation Models
# =============================================================================

class SeverityLevel(str, Enum):
    """Severity level for validation issues."""
    ERROR = "error"         # Must be fixed — schema is broken
    WARNING = "warning"     # Should be fixed — schema may have problems
    INFO = "info"           # Informational — optional improvement


class ValidationIssue(BaseModel):
    """A single issue found during validation."""
    severity: SeverityLevel = Field(..., description="How serious this issue is")
    layer: str = Field(
        ...,
        description="Which schema layer has the issue (e.g., 'database', 'api', 'ui', 'auth', 'cross-layer')"
    )
    message: str = Field(..., description="Human-readable description of the issue")
    field_path: str = Field(
        default="",
        description="Dot-notation path to the problematic field (e.g., 'database.tables[0].columns[1].name')"
    )


class ValidationReport(BaseModel):
    """
    Output of Stage 4 — Validation Engine.
    
    Reports all issues found during schema validation,
    including cross-layer consistency checks.
    """
    is_valid: bool = Field(..., description="True if no ERROR-level issues were found")
    issues: List[ValidationIssue] = Field(
        default_factory=list,
        description="All validation issues found"
    )
    checks_passed: int = Field(default=0, description="Number of validation checks that passed")
    checks_failed: int = Field(default=0, description="Number of validation checks that failed")


# =============================================================================
# STAGE 5: Repair Models
# =============================================================================

class RepairAction(BaseModel):
    """A single repair action taken to fix a validation issue."""
    layer: str = Field(..., description="Which schema layer was repaired")
    action: str = Field(..., description="What repair was performed (e.g., 'added_missing_column')")
    field_path: str = Field(default="", description="Dot-notation path to the repaired field")
    old_value: Optional[str] = Field(default=None, description="Previous value (if applicable)")
    new_value: Optional[str] = Field(default=None, description="New value after repair")


class RepairReport(BaseModel):
    """
    Output of Stage 5 — Repair Engine.
    
    Documents all repairs applied to fix validation issues.
    """
    was_repaired: bool = Field(..., description="True if any repairs were applied")
    repair_count: int = Field(default=0, description="Total number of repairs applied")
    repairs_applied: List[RepairAction] = Field(
        default_factory=list,
        description="Detailed list of all repairs"
    )


# =============================================================================
# STAGE 6: Execution Simulation Models
# =============================================================================

class ExecutionResult(BaseModel):
    """
    Output of Stage 6 — Execution Simulator.
    
    Reports whether the final schema is executable and ready for deployment.
    """
    status: str = Field(..., description="Overall status: 'success' or 'failure'")
    validation: str = Field(..., description="Validation status: 'passed' or 'failed'")
    app_ready: bool = Field(..., description="Whether the application configuration is ready")
    details: List[str] = Field(
        default_factory=list,
        description="Additional details about the simulation (errors, warnings, etc.)"
    )


# =============================================================================
# PIPELINE: Combined Result Model
# =============================================================================

class PipelineResult(BaseModel):
    """
    Complete output from the full pipeline run.
    
    Wraps all stage outputs along with metadata about the run itself.
    """
    # Input
    prompt: str = Field(..., description="The original user prompt")
    
    # Stage outputs (Optional because a stage might fail)
    intent: Optional[IntentResult] = Field(default=None, description="Stage 1 output")
    design: Optional[SystemDesign] = Field(default=None, description="Stage 2 output")
    app_schema: Optional[FullAppSchema] = Field(default=None, description="Stage 3 output")
    validation_report: Optional[ValidationReport] = Field(default=None, description="Stage 4 output")
    repair_report: Optional[RepairReport] = Field(default=None, description="Stage 5 output")
    execution_result: Optional[ExecutionResult] = Field(default=None, description="Stage 6 output")
    
    # Metadata
    success: bool = Field(default=False, description="Whether the pipeline completed successfully")
    processing_time_seconds: float = Field(default=0.0, description="Total processing time in seconds")
    stage_times: dict = Field(
        default_factory=dict,
        description="Processing time for each stage (e.g., {'intent': 1.2, 'design': 2.3})"
    )
    error_message: Optional[str] = Field(default=None, description="Error message if pipeline failed")
