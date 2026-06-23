# =============================================================================
# validator.py — Stage 4: Validation Engine
# =============================================================================
# Pure Python validation — NO LLM calls. This stage is deterministic and fast.
#
# Validates the generated FullAppSchema for:
#   1. Schema completeness (tables have columns, endpoints have fields, etc.)
#   2. Cross-layer consistency:
#      - UI data_source → API endpoint paths
#      - API fields → Database columns
#      - UI/API roles → Auth schema roles
#      - Business rule entities → Database tables
#      - Foreign keys → valid table references
#
# Input:  FullAppSchema (from Stage 3 or Stage 5 after repair)
# Output: ValidationReport (is_valid, issues list, pass/fail counts)
# =============================================================================

import logging
from typing import List, Set
from backend.schemas import (
    FullAppSchema,
    ValidationReport,
    ValidationIssue,
    SeverityLevel,
)

logger = logging.getLogger(__name__)


def validate_schema(schema: FullAppSchema) -> ValidationReport:
    """
    Validate the full application schema for completeness and consistency.
    
    Runs all validation checks and produces a detailed report listing
    every issue found, categorized by severity (error, warning, info).
    
    The schema is considered valid only if there are NO error-level issues.
    Warnings and info-level issues are reported but don't block the pipeline.
    
    Args:
        schema: The FullAppSchema to validate
        
    Returns:
        ValidationReport: Detailed validation results
        
    Example:
        >>> report = validate_schema(full_schema)
        >>> print(report.is_valid)       # True/False
        >>> print(report.checks_passed)  # 15
        >>> print(report.checks_failed)  # 2
    """
    logger.info("Stage 4: Running validation engine")
    
    issues: List[ValidationIssue] = []
    checks_passed = 0
    checks_failed = 0
    
    # -------------------------------------------------------------------------
    # CHECK 1: Database schema completeness
    # -------------------------------------------------------------------------
    logger.info("  Check 1: Database schema completeness")
    
    # 1a. Every table must have at least one column
    for i, table in enumerate(schema.database.tables):
        if len(table.columns) == 0:
            issues.append(ValidationIssue(
                severity=SeverityLevel.ERROR,
                layer="database",
                message=f"Table '{table.name}' has no columns",
                field_path=f"database.tables[{i}].columns",
            ))
            checks_failed += 1
        else:
            checks_passed += 1
        
        # 1b. Every table should have a primary key
        has_pk = any(col.primary_key for col in table.columns)
        if not has_pk:
            issues.append(ValidationIssue(
                severity=SeverityLevel.WARNING,
                layer="database",
                message=f"Table '{table.name}' has no primary key column",
                field_path=f"database.tables[{i}]",
            ))
            checks_failed += 1
        else:
            checks_passed += 1
    
    # -------------------------------------------------------------------------
    # CHECK 2: Foreign key validity
    # -------------------------------------------------------------------------
    logger.info("  Check 2: Foreign key validity")
    
    # Collect all table names for reference checking
    table_names: Set[str] = {t.name for t in schema.database.tables}
    
    # Build a map of table_name -> set of column names
    table_columns: dict = {}
    for table in schema.database.tables:
        table_columns[table.name] = {col.name for col in table.columns}
    
    for i, table in enumerate(schema.database.tables):
        for j, col in enumerate(table.columns):
            if col.foreign_key:
                # Parse "table_name.column_name" format
                parts = col.foreign_key.split(".")
                if len(parts) != 2:
                    issues.append(ValidationIssue(
                        severity=SeverityLevel.ERROR,
                        layer="database",
                        message=f"Invalid foreign key format '{col.foreign_key}' in {table.name}.{col.name}. "
                                f"Expected 'table_name.column_name'",
                        field_path=f"database.tables[{i}].columns[{j}].foreign_key",
                    ))
                    checks_failed += 1
                else:
                    ref_table, ref_col = parts
                    if ref_table not in table_names:
                        issues.append(ValidationIssue(
                            severity=SeverityLevel.ERROR,
                            layer="database",
                            message=f"Foreign key in {table.name}.{col.name} references non-existent "
                                    f"table '{ref_table}'",
                            field_path=f"database.tables[{i}].columns[{j}].foreign_key",
                        ))
                        checks_failed += 1
                    elif ref_col not in table_columns.get(ref_table, set()):
                        issues.append(ValidationIssue(
                            severity=SeverityLevel.WARNING,
                            layer="database",
                            message=f"Foreign key in {table.name}.{col.name} references non-existent "
                                    f"column '{ref_col}' in table '{ref_table}'",
                            field_path=f"database.tables[{i}].columns[{j}].foreign_key",
                        ))
                        checks_failed += 1
                    else:
                        checks_passed += 1
    
    # -------------------------------------------------------------------------
    # CHECK 3: API schema completeness
    # -------------------------------------------------------------------------
    logger.info("  Check 3: API schema completeness")
    
    for i, endpoint in enumerate(schema.api.endpoints):
        # 3a. POST/PUT endpoints should have request fields
        if endpoint.method in ("POST", "PUT") and len(endpoint.request_fields) == 0:
            issues.append(ValidationIssue(
                severity=SeverityLevel.WARNING,
                layer="api",
                message=f"Endpoint {endpoint.method} {endpoint.path} has no request fields",
                field_path=f"api.endpoints[{i}].request_fields",
            ))
            checks_failed += 1
        else:
            checks_passed += 1
        
        # 3b. GET endpoints should have response fields
        if endpoint.method == "GET" and len(endpoint.response_fields) == 0:
            issues.append(ValidationIssue(
                severity=SeverityLevel.WARNING,
                layer="api",
                message=f"Endpoint GET {endpoint.path} has no response fields",
                field_path=f"api.endpoints[{i}].response_fields",
            ))
            checks_failed += 1
        else:
            checks_passed += 1
    
    # -------------------------------------------------------------------------
    # CHECK 4: UI → API consistency (data sources must match endpoints)
    # -------------------------------------------------------------------------
    logger.info("  Check 4: UI → API consistency")
    
    # Collect all API endpoint paths
    api_paths: Set[str] = {ep.path for ep in schema.api.endpoints}
    
    for i, page in enumerate(schema.ui.pages):
        for j, component in enumerate(page.components):
            if component.data_source:
                # Normalize: strip trailing slashes, check if path exists
                data_src = component.data_source.rstrip("/")
                # Check exact match or if the data source is a sub-path of an endpoint
                path_matched = any(
                    data_src == p or data_src.startswith(p) or p.startswith(data_src)
                    for p in api_paths
                )
                if not path_matched:
                    issues.append(ValidationIssue(
                        severity=SeverityLevel.ERROR,
                        layer="cross-layer",
                        message=f"UI component '{component.label}' on page '{page.name}' references "
                                f"API endpoint '{component.data_source}' which does not exist",
                        field_path=f"ui.pages[{i}].components[{j}].data_source",
                    ))
                    checks_failed += 1
                else:
                    checks_passed += 1
    
    # -------------------------------------------------------------------------
    # CHECK 5: Role consistency (UI/API roles must exist in Auth schema)
    # -------------------------------------------------------------------------
    logger.info("  Check 5: Role consistency")
    
    # Collect all defined roles from auth schema (case-insensitive comparison)
    auth_role_names: Set[str] = {
        r.role_name.lower() for r in schema.auth.roles
    }
    
    # Check API endpoint roles
    for i, endpoint in enumerate(schema.api.endpoints):
        for role in endpoint.allowed_roles:
            if role.lower() not in auth_role_names:
                issues.append(ValidationIssue(
                    severity=SeverityLevel.ERROR,
                    layer="cross-layer",
                    message=f"API endpoint {endpoint.method} {endpoint.path} references role "
                            f"'{role}' which is not defined in auth schema",
                    field_path=f"api.endpoints[{i}].allowed_roles",
                ))
                checks_failed += 1
            else:
                checks_passed += 1
    
    # Check UI page roles
    for i, page in enumerate(schema.ui.pages):
        for role in page.allowed_roles:
            if role.lower() not in auth_role_names:
                issues.append(ValidationIssue(
                    severity=SeverityLevel.ERROR,
                    layer="cross-layer",
                    message=f"UI page '{page.name}' references role '{role}' "
                            f"which is not defined in auth schema",
                    field_path=f"ui.pages[{i}].allowed_roles",
                ))
                checks_failed += 1
            else:
                checks_passed += 1
    
    # -------------------------------------------------------------------------
    # CHECK 6: Business rules reference valid entities
    # -------------------------------------------------------------------------
    logger.info("  Check 6: Business rules entity references")
    
    # Table names (case-insensitive)
    table_names_lower: Set[str] = {t.name.lower() for t in schema.database.tables}
    
    for i, rule in enumerate(schema.business_rules.rules):
        for entity in rule.entities_involved:
            # Check if entity matches a table name (case-insensitive, singular/plural)
            entity_lower = entity.lower()
            # Try exact match, plural, and singular forms
            matched = (
                entity_lower in table_names_lower
                or entity_lower + "s" in table_names_lower
                or entity_lower.rstrip("s") in table_names_lower
            )
            if not matched:
                issues.append(ValidationIssue(
                    severity=SeverityLevel.WARNING,
                    layer="cross-layer",
                    message=f"Business rule '{rule.name}' references entity '{entity}' "
                            f"which does not match any database table",
                    field_path=f"business_rules.rules[{i}].entities_involved",
                ))
                checks_failed += 1
            else:
                checks_passed += 1
    
    # -------------------------------------------------------------------------
    # CHECK 7: UI page completeness
    # -------------------------------------------------------------------------
    logger.info("  Check 7: UI page completeness")
    
    for i, page in enumerate(schema.ui.pages):
        if len(page.components) == 0:
            issues.append(ValidationIssue(
                severity=SeverityLevel.ERROR,
                layer="ui",
                message=f"Page '{page.name}' has no components",
                field_path=f"ui.pages[{i}].components",
            ))
            checks_failed += 1
        else:
            checks_passed += 1
    
    # -------------------------------------------------------------------------
    # CHECK 8: Auth schema completeness
    # -------------------------------------------------------------------------
    logger.info("  Check 8: Auth schema completeness")
    
    for i, role_def in enumerate(schema.auth.roles):
        if len(role_def.permissions) == 0:
            issues.append(ValidationIssue(
                severity=SeverityLevel.WARNING,
                layer="auth",
                message=f"Role '{role_def.role_name}' has no permissions defined",
                field_path=f"auth.roles[{i}].permissions",
            ))
            checks_failed += 1
        else:
            checks_passed += 1
    
    # -------------------------------------------------------------------------
    # BUILD FINAL REPORT
    # -------------------------------------------------------------------------
    
    # Schema is valid only if there are NO error-level issues
    error_count = sum(1 for issue in issues if issue.severity == SeverityLevel.ERROR)
    is_valid = error_count == 0
    
    report = ValidationReport(
        is_valid=is_valid,
        issues=issues,
        checks_passed=checks_passed,
        checks_failed=checks_failed,
    )
    
    logger.info(
        f"Stage 4 complete: valid={is_valid}, "
        f"passed={checks_passed}, failed={checks_failed}, "
        f"errors={error_count}, warnings={len(issues) - error_count}"
    )
    
    return report
