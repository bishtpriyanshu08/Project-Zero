# =============================================================================
# simulator.py — Stage 6: Execution Simulator
# =============================================================================
# Simulates application execution by verifying that the final schema
# is structurally sound and could be used to generate a real application.
#
# Simulation checks:
#   1. All schemas re-validate through Pydantic (round-trip test)
#   2. Validation engine reports is_valid=True
#   3. Database schema compiles to valid SQLite DDL
#   4. API routes are well-formed (no duplicates, valid methods)
#   5. UI routes are well-formed (no duplicates)
#
# Input:  FullAppSchema (final, after repair)
# Output: ExecutionResult (status, validation, app_ready, details)
# =============================================================================

import logging
import sqlite3
from typing import List
from backend.schemas import FullAppSchema, ExecutionResult
from backend.validator import validate_schema

logger = logging.getLogger(__name__)


def simulate_execution(schema: FullAppSchema) -> ExecutionResult:
    """
    Simulate the execution of the generated application configuration.
    
    This stage acts as a "dry run" — it doesn't actually deploy anything,
    but verifies that the schema is complete enough to generate a real app.
    
    Args:
        schema: The final FullAppSchema (after any repairs)
        
    Returns:
        ExecutionResult with status, validation result, and details
        
    Example:
        >>> result = simulate_execution(final_schema)
        >>> print(result.status)      # "success"
        >>> print(result.app_ready)   # True
    """
    logger.info("Stage 6: Simulating application execution")
    
    details: List[str] = []
    all_checks_passed = True
    
    # -------------------------------------------------------------------------
    # CHECK 1: Pydantic round-trip validation
    # -------------------------------------------------------------------------
    logger.info("  Simulation check 1: Pydantic round-trip validation")
    try:
        # Serialize to JSON and back — ensures the schema is self-consistent
        json_data = schema.model_dump()
        FullAppSchema.model_validate(json_data)
        details.append("✅ Schema round-trip validation: PASSED")
    except Exception as e:
        details.append(f"❌ Schema round-trip validation: FAILED — {str(e)}")
        all_checks_passed = False
    
    # -------------------------------------------------------------------------
    # CHECK 2: Run validation engine
    # -------------------------------------------------------------------------
    logger.info("  Simulation check 2: Validation engine")
    validation_report = validate_schema(schema)
    if validation_report.is_valid:
        details.append(
            f"✅ Validation engine: PASSED "
            f"({validation_report.checks_passed} checks passed)"
        )
    else:
        error_count = sum(
            1 for i in validation_report.issues
            if i.severity.value == "error"
        )
        details.append(
            f"❌ Validation engine: FAILED "
            f"({error_count} errors, {validation_report.checks_failed} checks failed)"
        )
        all_checks_passed = False
    
    # -------------------------------------------------------------------------
    # CHECK 3: Database DDL compilation (SQLite in-memory)
    # -------------------------------------------------------------------------
    logger.info("  Simulation check 3: SQLite DDL compilation")
    try:
        ddl_statements = _generate_ddl(schema)
        # Try creating all tables in an in-memory SQLite database
        conn = sqlite3.connect(":memory:")
        cursor = conn.cursor()
        for ddl in ddl_statements:
            cursor.execute(ddl)
        conn.close()
        details.append(
            f"✅ Database DDL compilation: PASSED "
            f"({len(schema.database.tables)} tables created in-memory)"
        )
    except Exception as e:
        details.append(f"❌ Database DDL compilation: FAILED — {str(e)}")
        all_checks_passed = False
    
    # -------------------------------------------------------------------------
    # CHECK 4: API route validation
    # -------------------------------------------------------------------------
    logger.info("  Simulation check 4: API route validation")
    api_issues = _validate_api_routes(schema)
    if not api_issues:
        details.append(
            f"✅ API route validation: PASSED "
            f"({len(schema.api.endpoints)} endpoints verified)"
        )
    else:
        for api_issue in api_issues:
            details.append(f"⚠️ API route issue: {api_issue}")
        # Route issues are warnings, not blockers
    
    # -------------------------------------------------------------------------
    # CHECK 5: UI route validation
    # -------------------------------------------------------------------------
    logger.info("  Simulation check 5: UI route validation")
    ui_issues = _validate_ui_routes(schema)
    if not ui_issues:
        details.append(
            f"✅ UI route validation: PASSED "
            f"({len(schema.ui.pages)} pages verified)"
        )
    else:
        for ui_issue in ui_issues:
            details.append(f"⚠️ UI route issue: {ui_issue}")
    
    # -------------------------------------------------------------------------
    # BUILD RESULT
    # -------------------------------------------------------------------------
    status = "success" if all_checks_passed else "failure"
    validation = "passed" if all_checks_passed else "failed"
    
    result = ExecutionResult(
        status=status,
        validation=validation,
        app_ready=all_checks_passed,
        details=details,
    )
    
    logger.info(f"Stage 6 complete: status={status}, app_ready={all_checks_passed}")
    
    return result


# =============================================================================
# Helper Functions
# =============================================================================

def _generate_ddl(schema: FullAppSchema) -> List[str]:
    """
    Generate SQLite CREATE TABLE statements from the database schema.
    
    Maps common data types to SQLite equivalents and handles
    primary keys, nullable constraints, and foreign keys.
    """
    ddl_statements = []
    
    # Map common SQL types to SQLite types
    type_mapping = {
        "INTEGER": "INTEGER",
        "INT": "INTEGER",
        "BIGINT": "INTEGER",
        "SMALLINT": "INTEGER",
        "VARCHAR": "TEXT",
        "TEXT": "TEXT",
        "BOOLEAN": "INTEGER",       # SQLite stores booleans as integers
        "BOOL": "INTEGER",
        "TIMESTAMP": "TEXT",         # SQLite stores timestamps as text
        "DATETIME": "TEXT",
        "DATE": "TEXT",
        "DECIMAL": "REAL",
        "FLOAT": "REAL",
        "DOUBLE": "REAL",
        "REAL": "REAL",
        "BLOB": "BLOB",
    }
    
    for table in schema.database.tables:
        columns_sql = []
        foreign_keys = []
        
        for col in table.columns:
            # Determine SQLite type
            base_type = col.data_type.split("(")[0].upper().strip()
            sqlite_type = type_mapping.get(base_type, "TEXT")
            
            # Build column definition
            col_def = f'    "{col.name}" {sqlite_type}'
            
            if col.primary_key:
                col_def += " PRIMARY KEY"
            if not col.nullable and not col.primary_key:
                col_def += " NOT NULL"
            
            columns_sql.append(col_def)
            
            # Collect foreign keys
            if col.foreign_key:
                parts = col.foreign_key.split(".")
                if len(parts) == 2:
                    ref_table, ref_col = parts
                    foreign_keys.append(
                        f'    FOREIGN KEY ("{col.name}") REFERENCES "{ref_table}"("{ref_col}")'
                    )
        
        # Combine columns and foreign keys
        all_parts = columns_sql + foreign_keys
        columns_str = ",\n".join(all_parts)
        
        ddl = f'CREATE TABLE IF NOT EXISTS "{table.name}" (\n{columns_str}\n);'
        ddl_statements.append(ddl)
    
    return ddl_statements


def _validate_api_routes(schema: FullAppSchema) -> List[str]:
    """Check for duplicate routes and invalid HTTP methods."""
    issues = []
    valid_methods = {"GET", "POST", "PUT", "DELETE", "PATCH", "HEAD", "OPTIONS"}
    
    # Check for duplicates (same method + path)
    seen_routes = set()
    for endpoint in schema.api.endpoints:
        route_key = f"{endpoint.method.upper()} {endpoint.path}"
        if route_key in seen_routes:
            issues.append(f"Duplicate API route: {route_key}")
        else:
            seen_routes.add(route_key)
        
        # Check method validity
        if endpoint.method.upper() not in valid_methods:
            issues.append(f"Invalid HTTP method '{endpoint.method}' for {endpoint.path}")
    
    return issues


def _validate_ui_routes(schema: FullAppSchema) -> List[str]:
    """Check for duplicate UI routes."""
    issues = []
    seen_routes = set()
    
    for page in schema.ui.pages:
        if page.route in seen_routes:
            issues.append(f"Duplicate UI route: {page.route} (page: {page.name})")
        else:
            seen_routes.add(page.route)
    
    return issues
