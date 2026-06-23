# =============================================================================
# pipeline.py — Pipeline Orchestrator
# =============================================================================
# Orchestrates all 6 stages of the AI App Generator pipeline:
#
#   Stage 1: Intent Extraction    (LLM call)
#   Stage 2: System Design        (LLM call)
#   Stage 3: Schema Generation    (LLM call)
#   Stage 4: Validation           (Pure Python)
#   Stage 5: Repair               (Pure Python, loop until valid or max retries)
#   Stage 6: Execution Simulation (Pure Python + SQLite)
#
# The orchestrator:
#   - Tracks timing for each stage
#   - Handles errors gracefully (returns partial results on failure)
#   - Runs repair loop up to max_repair_iterations
#   - Saves metrics to SQLite after each run
#
# Input:  Raw user prompt + configured LLM client
# Output: PipelineResult with all stage outputs
# =============================================================================

import time
import logging
from typing import Optional, Callable

from backend.llm_client import LLMClient
from backend.schemas import PipelineResult
from backend.intent_extractor import extract_intent
from backend.system_designer import design_system
from backend.schema_generator import generate_schemas
from backend.validator import validate_schema
from backend.repair_engine import repair_schema
from backend.simulator import simulate_execution
from backend.database import save_pipeline_run

logger = logging.getLogger(__name__)


def run_pipeline(
    prompt: str,
    llm_client: LLMClient,
    max_repair_iterations: int = 3,
    progress_callback: Optional[Callable[[str, int], None]] = None,
) -> PipelineResult:
    """
    Run the complete AI App Generator pipeline.
    
    Executes all 6 stages sequentially, with a repair loop between
    stages 4 and 5 that retries until validation passes or the
    maximum number of repair iterations is reached.
    
    Args:
        prompt: The natural language application description
        llm_client: Configured LLM client instance
        max_repair_iterations: Max times to retry repair (default: 3)
        progress_callback: Optional function called with (stage_name, stage_number)
                          to report progress (used by Streamlit UI)
        
    Returns:
        PipelineResult: Complete results from all stages
        
    Example:
        >>> client = LLMClient(provider="gemini", api_key="...")
        >>> result = run_pipeline("Build a CRM with login and contacts", client)
        >>> print(result.success)  # True
        >>> print(result.execution_result.app_ready)  # True
    """
    logger.info(f"Starting pipeline for prompt: '{prompt[:80]}...'")
    pipeline_start = time.time()
    
    # Initialize the result with the prompt
    result = PipelineResult(prompt=prompt)
    stage_times = {}
    
    def _notify(stage_name: str, stage_num: int):
        """Helper to call the progress callback if provided."""
        if progress_callback:
            progress_callback(stage_name, stage_num)
    
    try:
        # =================================================================
        # STAGE 1: Intent Extraction
        # =================================================================
        _notify("Intent Extraction", 1)
        stage_start = time.time()
        
        intent = extract_intent(prompt, llm_client)
        result.intent = intent
        stage_times["intent"] = round(time.time() - stage_start, 2)
        
        logger.info(f"  Stage 1 took {stage_times['intent']}s")
        
        # =================================================================
        # STAGE 2: System Design
        # =================================================================
        _notify("System Design", 2)
        stage_start = time.time()
        
        design = design_system(intent, llm_client)
        result.design = design
        stage_times["design"] = round(time.time() - stage_start, 2)
        
        logger.info(f"  Stage 2 took {stage_times['design']}s")
        
        # =================================================================
        # STAGE 3: Schema Generation
        # =================================================================
        _notify("Schema Generation", 3)
        stage_start = time.time()
        
        app_schema = generate_schemas(intent, design, llm_client)
        result.app_schema = app_schema
        stage_times["schema"] = round(time.time() - stage_start, 2)
        
        logger.info(f"  Stage 3 took {stage_times['schema']}s")
        
        # =================================================================
        # STAGE 4 + 5: Validation → Repair Loop
        # =================================================================
        _notify("Validation", 4)
        stage_start = time.time()
        
        validation_report = validate_schema(app_schema)
        result.validation_report = validation_report
        stage_times["validation"] = round(time.time() - stage_start, 2)
        
        logger.info(f"  Stage 4 took {stage_times['validation']}s — valid={validation_report.is_valid}")
        
        # Repair loop: if validation fails, attempt repair and re-validate
        repair_iteration = 0
        total_repair_time = 0.0
        
        while not validation_report.is_valid and repair_iteration < max_repair_iterations:
            repair_iteration += 1
            _notify(f"Repair (iteration {repair_iteration})", 5)
            stage_start = time.time()
            
            logger.info(f"  Repair iteration {repair_iteration}/{max_repair_iterations}")
            
            # Run repair engine
            repaired_schema, repair_report = repair_schema(app_schema, validation_report)
            result.repair_report = repair_report
            result.app_schema = repaired_schema
            app_schema = repaired_schema
            
            # Re-validate
            validation_report = validate_schema(app_schema)
            result.validation_report = validation_report
            
            iteration_time = round(time.time() - stage_start, 2)
            total_repair_time += iteration_time
            
            logger.info(
                f"  Repair iteration {repair_iteration} took {iteration_time}s — "
                f"valid={validation_report.is_valid}, repairs={repair_report.repair_count}"
            )
        
        stage_times["repair"] = round(total_repair_time, 2)
        
        # If validation still fails after all repair attempts, log a warning
        if not validation_report.is_valid:
            logger.warning(
                f"  Schema still invalid after {max_repair_iterations} repair attempts. "
                f"Proceeding to simulation with warnings."
            )
        
        # =================================================================
        # STAGE 6: Execution Simulation
        # =================================================================
        _notify("Execution Simulation", 6)
        stage_start = time.time()
        
        execution_result = simulate_execution(app_schema)
        result.execution_result = execution_result
        stage_times["simulation"] = round(time.time() - stage_start, 2)
        
        logger.info(f"  Stage 6 took {stage_times['simulation']}s — ready={execution_result.app_ready}")
        
        # =================================================================
        # FINALIZE
        # =================================================================
        result.success = True
        result.stage_times = stage_times
        result.processing_time_seconds = round(time.time() - pipeline_start, 2)
        
        logger.info(
            f"Pipeline complete: success={result.success}, "
            f"total_time={result.processing_time_seconds}s"
        )
        
    except Exception as e:
        # Handle any stage failure — return partial results
        result.success = False
        result.error_message = str(e)
        result.processing_time_seconds = round(time.time() - pipeline_start, 2)
        result.stage_times = stage_times
        
        logger.error(f"Pipeline failed: {str(e)}", exc_info=True)
    
    # Save run metrics to the database
    try:
        save_pipeline_run(result)
    except Exception as e:
        logger.warning(f"Failed to save pipeline run to database: {str(e)}")
    
    return result
