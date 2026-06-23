# =============================================================================
# repair_engine.py — Stage 5: Repair Engine
# =============================================================================
# Takes a FullAppSchema that failed validation and repairs ONLY the broken
# parts — does NOT regenerate everything from scratch.
#
# Repair strategies (all pure Python, no LLM):
#   - Missing primary keys  → add "id" column
#   - Invalid foreign keys  → remove the broken reference
#   - Missing API fields    → add stub fields based on context
#   - Role mismatches       → add missing roles to auth schema
#   - Broken data sources   → attempt to match to closest API endpoint
#   - Entity mismatches     → add stub tables for referenced entities
#
# Input:  FullAppSchema + ValidationReport
# Output: Repaired FullAppSchema + RepairReport
# =============================================================================

import logging
from typing import Tuple, Set, Optional, List
from copy import deepcopy
from backend.schemas import (
    FullAppSchema,
    ValidationReport,
    ValidationIssue,
    SeverityLevel,
    RepairReport,
    RepairAction,
    Column,
    Table,
    RoleDefinition,
    APIField,
    Endpoint,
)

logger = logging.getLogger(__name__)


def repair_schema(
    schema: FullAppSchema,
    report: ValidationReport,
) -> Tuple[FullAppSchema, RepairReport]:
    """
    Repair a schema based on the validation report.
    
    Only fixes issues identified by the validator — does not modify
    parts of the schema that passed validation. This targeted approach
    preserves the LLM's good output while fixing specific problems.
    
    Args:
        schema: The FullAppSchema that failed validation
        report: The ValidationReport identifying the issues
        
    Returns:
        Tuple of (repaired FullAppSchema, RepairReport documenting changes)
        
    Example:
        >>> repaired_schema, repair_report = repair_schema(schema, validation_report)
        >>> print(repair_report.repair_count)  # 3
        >>> print(repair_report.repairs_applied[0].action)  # "added_primary_key"
    """
    logger.info(f"Stage 5: Repairing {len(report.issues)} validation issues")
    
    # Deep copy to avoid mutating the original schema
    repaired = FullAppSchema.model_validate(deepcopy(schema.model_dump()))
    repairs: List[RepairAction] = []
    
    # Process each validation issue and attempt repair
    for issue in report.issues:
        # Only repair ERROR and WARNING level issues
        if issue.severity == SeverityLevel.INFO:
            continue
        
        repair = _attempt_repair(repaired, issue)
        if repair:
            repairs.append(repair)
    
    repair_report = RepairReport(
        was_repaired=len(repairs) > 0,
        repair_count=len(repairs),
        repairs_applied=repairs,
    )
    
    logger.info(f"Stage 5 complete: {repair_report.repair_count} repairs applied")
    
    return repaired, repair_report


def _attempt_repair(schema: FullAppSchema, issue: ValidationIssue) -> Optional[RepairAction]:
    """
    Attempt to repair a single validation issue.
    
    Dispatches to the appropriate repair function based on the issue
    layer and message content. Returns None if the issue cannot be
    automatically repaired.
    """
    message_lower = issue.message.lower()
    
    # ----- Database repairs -----
    if "no primary key" in message_lower:
        return _repair_missing_primary_key(schema, issue)
    
    if "foreign key" in message_lower and "non-existent" in message_lower:
        return _repair_broken_foreign_key(schema, issue)
    
    if "has no columns" in message_lower:
        return _repair_empty_table(schema, issue)
    
    # ----- API repairs -----
    if "no request fields" in message_lower:
        return _repair_missing_request_fields(schema, issue)
    
    if "no response fields" in message_lower:
        return _repair_missing_response_fields(schema, issue)
    
    # ----- Cross-layer repairs -----
    if "api endpoint" in message_lower and "does not exist" in message_lower:
        return _repair_missing_data_source(schema, issue)
    
    if "role" in message_lower and "not defined in auth" in message_lower:
        return _repair_missing_role(schema, issue)
    
    if "does not match any database table" in message_lower:
        return _repair_missing_entity_table(schema, issue)
    
    # ----- Auth repairs -----
    if "no permissions defined" in message_lower:
        return _repair_empty_permissions(schema, issue)
    
    # ----- UI repairs -----
    if "has no components" in message_lower:
        return None  # Cannot auto-repair — needs LLM
    
    logger.debug(f"No auto-repair available for: {issue.message}")
    return None


# =============================================================================
# Individual Repair Functions
# =============================================================================

def _repair_missing_primary_key(schema: FullAppSchema, issue: ValidationIssue) -> RepairAction:
    """Add an 'id' primary key column to a table that's missing one."""
    # Extract table name from the issue message
    table_name = issue.message.split("'")[1]
    
    for table in schema.database.tables:
        if table.name == table_name:
            # Check if 'id' column exists but isn't marked as PK
            id_col = next((c for c in table.columns if c.name == "id"), None)
            if id_col:
                id_col.primary_key = True
                return RepairAction(
                    layer="database",
                    action="marked_existing_id_as_primary_key",
                    field_path=f"database.tables.{table_name}.columns.id",
                    old_value="primary_key=False",
                    new_value="primary_key=True",
                )
            else:
                # Add a new id column at the beginning
                id_column = Column(
                    name="id",
                    data_type="INTEGER",
                    primary_key=True,
                    nullable=False,
                )
                table.columns.insert(0, id_column)
                return RepairAction(
                    layer="database",
                    action="added_primary_key_column",
                    field_path=f"database.tables.{table_name}.columns",
                    old_value=None,
                    new_value="id INTEGER PRIMARY KEY",
                )
    return None


def _repair_broken_foreign_key(schema: FullAppSchema, issue: ValidationIssue) -> RepairAction:
    """Remove a foreign key that references a non-existent table or column."""
    # Find and nullify the broken foreign key
    for table in schema.database.tables:
        for col in table.columns:
            if col.foreign_key and col.foreign_key in issue.message:
                old_fk = col.foreign_key
                col.foreign_key = None
                return RepairAction(
                    layer="database",
                    action="removed_broken_foreign_key",
                    field_path=f"database.tables.{table.name}.columns.{col.name}.foreign_key",
                    old_value=old_fk,
                    new_value=None,
                )
    return None


def _repair_empty_table(schema: FullAppSchema, issue: ValidationIssue) -> RepairAction:
    """Add default columns to an empty table."""
    table_name = issue.message.split("'")[1]
    
    for table in schema.database.tables:
        if table.name == table_name:
            table.columns = [
                Column(name="id", data_type="INTEGER", primary_key=True, nullable=False),
                Column(name="name", data_type="VARCHAR(255)", nullable=False),
                Column(name="created_at", data_type="TIMESTAMP", nullable=False),
                Column(name="updated_at", data_type="TIMESTAMP", nullable=False),
            ]
            return RepairAction(
                layer="database",
                action="added_default_columns_to_empty_table",
                field_path=f"database.tables.{table_name}.columns",
                old_value="[]",
                new_value="[id, name, created_at, updated_at]",
            )
    return None


def _repair_missing_request_fields(schema: FullAppSchema, issue: ValidationIssue) -> RepairAction:
    """Add stub request fields to a POST/PUT endpoint."""
    for endpoint in schema.api.endpoints:
        check_str = f"{endpoint.method} {endpoint.path}"
        if check_str in issue.message:
            endpoint.request_fields = [
                APIField(name="name", field_type="string", required=True),
                APIField(name="description", field_type="string", required=False),
            ]
            return RepairAction(
                layer="api",
                action="added_stub_request_fields",
                field_path=f"api.endpoints.{endpoint.method}_{endpoint.path}",
                old_value="[]",
                new_value="[name, description]",
            )
    return None


def _repair_missing_response_fields(schema: FullAppSchema, issue: ValidationIssue) -> RepairAction:
    """Add stub response fields to a GET endpoint."""
    for endpoint in schema.api.endpoints:
        if f"GET {endpoint.path}" in issue.message:
            endpoint.response_fields = [
                APIField(name="id", field_type="integer", required=True),
                APIField(name="name", field_type="string", required=True),
                APIField(name="created_at", field_type="string", required=True),
            ]
            return RepairAction(
                layer="api",
                action="added_stub_response_fields",
                field_path=f"api.endpoints.GET_{endpoint.path}",
                old_value="[]",
                new_value="[id, name, created_at]",
            )
    return None


def _repair_missing_data_source(schema: FullAppSchema, issue: ValidationIssue) -> RepairAction:
    """Fix a UI component's data_source by finding the closest matching API endpoint."""
    # Extract the bad data source from the message
    parts = issue.message.split("'")
    if len(parts) < 6:
        return None
    
    component_label = parts[1]
    page_name = parts[3]
    bad_source = parts[5]
    
    # Find the closest matching endpoint
    api_paths = [ep.path for ep in schema.api.endpoints]
    closest = _find_closest_path(bad_source, api_paths)
    
    if closest:
        # Update the component's data source
        for page in schema.ui.pages:
            if page.name == page_name:
                for comp in page.components:
                    if comp.label == component_label and comp.data_source == bad_source:
                        comp.data_source = closest
                        return RepairAction(
                            layer="ui",
                            action="fixed_data_source_reference",
                            field_path=f"ui.pages.{page_name}.components.{component_label}.data_source",
                            old_value=bad_source,
                            new_value=closest,
                        )
    
    # If no close match, remove the data source
    for page in schema.ui.pages:
        if page.name == page_name:
            for comp in page.components:
                if comp.label == component_label and comp.data_source == bad_source:
                    comp.data_source = None
                    return RepairAction(
                        layer="ui",
                        action="removed_invalid_data_source",
                        field_path=f"ui.pages.{page_name}.components.{component_label}.data_source",
                        old_value=bad_source,
                        new_value=None,
                    )
    return None


def _repair_missing_role(schema: FullAppSchema, issue: ValidationIssue) -> RepairAction:
    """Add a missing role to the auth schema."""
    # Extract the role name from the message
    parts = issue.message.split("'")
    if len(parts) < 4:
        return None
    
    missing_role = parts[3]
    
    # Check if role already exists (case-insensitive)
    existing = {r.role_name.lower() for r in schema.auth.roles}
    if missing_role.lower() in existing:
        return None
    
    # Add the role with basic read permissions
    schema.auth.roles.append(RoleDefinition(
        role_name=missing_role,
        permissions=["read:all"],
    ))
    
    return RepairAction(
        layer="auth",
        action="added_missing_role",
        field_path=f"auth.roles",
        old_value=None,
        new_value=f"Added role '{missing_role}' with basic read permissions",
    )


def _repair_missing_entity_table(schema: FullAppSchema, issue: ValidationIssue) -> RepairAction:
    """Add a stub table for a business rule entity that doesn't have one."""
    parts = issue.message.split("'")
    if len(parts) < 4:
        return None
    
    entity_name = parts[3].lower()
    
    # Check if table already exists
    existing = {t.name.lower() for t in schema.database.tables}
    if entity_name in existing or entity_name + "s" in existing:
        return None
    
    # Create a stub table
    new_table = Table(
        name=entity_name + "s",
        columns=[
            Column(name="id", data_type="INTEGER", primary_key=True, nullable=False),
            Column(name="name", data_type="VARCHAR(255)", nullable=False),
            Column(name="created_at", data_type="TIMESTAMP", nullable=False),
            Column(name="updated_at", data_type="TIMESTAMP", nullable=False),
        ],
    )
    schema.database.tables.append(new_table)
    
    return RepairAction(
        layer="database",
        action="added_stub_table_for_business_rule_entity",
        field_path=f"database.tables",
        old_value=None,
        new_value=f"Added table '{entity_name}s' with default columns",
    )


def _repair_empty_permissions(schema: FullAppSchema, issue: ValidationIssue) -> RepairAction:
    """Add default permissions to a role with none."""
    role_name = issue.message.split("'")[1]
    
    for role_def in schema.auth.roles:
        if role_def.role_name == role_name:
            role_def.permissions = ["read:all"]
            return RepairAction(
                layer="auth",
                action="added_default_permissions",
                field_path=f"auth.roles.{role_name}.permissions",
                old_value="[]",
                new_value="['read:all']",
            )
    return None


# =============================================================================
# Helper Functions
# =============================================================================

def _find_closest_path(target: str, candidates: List[str]) -> Optional[str]:
    """
    Find the closest matching API path for a data source.
    
    Uses simple string similarity: checks for common segments.
    Example: "/api/contact" would match "/api/contacts"
    """
    target_parts = set(target.strip("/").split("/"))
    
    best_match = None
    best_score = 0
    
    for candidate in candidates:
        candidate_parts = set(candidate.strip("/").split("/"))
        # Count overlapping segments
        overlap = len(target_parts & candidate_parts)
        if overlap > best_score:
            best_score = overlap
            best_match = candidate
    
    # Only return a match if there's meaningful overlap
    return best_match if best_score >= 1 else None
