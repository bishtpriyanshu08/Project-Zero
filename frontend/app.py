# =============================================================================
# app.py — Streamlit Frontend for AI App Generator
# =============================================================================
# Main user interface for the AI App Generator MVP.
#
# Layout:
#   - Sidebar: API key input, provider selection, settings
#   - Main area: Prompt input, Generate button, pipeline progress
#   - Tabbed output: One tab per pipeline stage
#   - Bottom: Metrics dashboard and run history
#
# Run with: streamlit run frontend/app.py
# =============================================================================

import sys
import os
import json
import time
import logging

# Add the project root to Python path so we can import backend modules
# This is needed because Streamlit runs from the frontend/ directory
PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if PROJECT_ROOT not in sys.path:
    sys.path.insert(0, PROJECT_ROOT)

# pyrefly: ignore [missing-import]
import streamlit as st

from backend.llm_client import LLMClient
from backend.pipeline import run_pipeline
from backend.database import get_metrics, get_run_history
from tests.sample_prompts import NORMAL_PROMPTS, EDGE_CASE_PROMPTS, ALL_PROMPTS

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# =============================================================================
# PAGE CONFIGURATION
# =============================================================================

st.set_page_config(
    page_title="AI App Generator",
    page_icon="🤖",
    layout="wide",
    initial_sidebar_state="expanded",
)

# =============================================================================
# CUSTOM CSS — Clean, professional styling
# =============================================================================

st.markdown("""
<style>
    /* Main header styling */
    .main-header {
        font-size: 2.2rem;
        font-weight: 700;
        color: #1a1a2e;
        margin-bottom: 0.2rem;
    }
    .sub-header {
        font-size: 1rem;
        color: #6c757d;
        margin-bottom: 1.5rem;
    }
    
    /* Stage indicator badges */
    .stage-badge {
        display: inline-block;
        padding: 0.25rem 0.75rem;
        border-radius: 1rem;
        font-size: 0.8rem;
        font-weight: 600;
        margin-right: 0.5rem;
        margin-bottom: 0.5rem;
    }
    .stage-success { background-color: #d4edda; color: #155724; }
    .stage-error { background-color: #f8d7da; color: #721c24; }
    .stage-pending { background-color: #e2e3e5; color: #383d41; }
    
    /* Metric card styling */
    .metric-container {
        background: #f8f9fa;
        border-radius: 0.5rem;
        padding: 1rem;
        border: 1px solid #e9ecef;
    }
    
    /* JSON display */
    .json-display {
        background: #1e1e1e;
        border-radius: 0.5rem;
        padding: 1rem;
        overflow-x: auto;
    }
    
    /* Pipeline stage cards */
    .stTabs [data-baseweb="tab-list"] {
        gap: 0.5rem;
    }
    .stTabs [data-baseweb="tab"] {
        padding: 0.5rem 1rem;
        border-radius: 0.5rem 0.5rem 0 0;
    }
</style>
""", unsafe_allow_html=True)


# =============================================================================
# SESSION STATE INITIALIZATION
# =============================================================================

def init_session_state():
    """Initialize Streamlit session state variables."""
    defaults = {
        "pipeline_result": None,     # Last pipeline result
        "is_running": False,         # Whether pipeline is currently running
        "current_stage": "",         # Current pipeline stage name
        "current_stage_num": 0,      # Current stage number (1-6)
    }
    for key, value in defaults.items():
        if key not in st.session_state:
            st.session_state[key] = value

init_session_state()


# =============================================================================
# SIDEBAR — Configuration
# =============================================================================

def render_sidebar():
    """Render the sidebar with API configuration and settings."""
    with st.sidebar:
        st.markdown("## ⚙️ Configuration")
        
        # LLM Provider selection
        provider = st.selectbox(
            "LLM Provider",
            options=["gemini", "openai"],
            index=0,
            help="Choose your LLM provider. Gemini is recommended for structured output.",
        )
        
        # API Key input
        api_key = st.text_input(
            "API Key",
            type="password",
            help="Enter your Gemini or OpenAI API key",
            placeholder="Enter your API key here...",
        )
        
        # Model selection
        if provider == "gemini":
            model_options = ["gemini-2.5-flash", "gemini-2.5-pro", "gemini-2.0-flash"]
        else:
            model_options = ["gpt-4o-mini", "gpt-4o", "gpt-4-turbo"]
        
        model_name = st.selectbox(
            "Model",
            options=model_options,
            index=0,
            help="Choose the specific model to use",
        )
        
        st.divider()
        
        # Advanced settings
        st.markdown("### 🔧 Advanced")
        max_repairs = st.slider(
            "Max Repair Iterations",
            min_value=1,
            max_value=5,
            value=3,
            help="Maximum number of times the repair engine will attempt to fix validation issues",
        )
        
        st.divider()
        
        # Sample prompts
        st.markdown("### 📝 Sample Prompts")
        
        prompt_category = st.radio(
            "Category",
            options=["Normal", "Edge Cases"],
            horizontal=True,
        )
        
        if prompt_category == "Normal":
            prompts = NORMAL_PROMPTS
        else:
            prompts = EDGE_CASE_PROMPTS
        
        selected_sample = st.selectbox(
            "Load a sample prompt",
            options=["— Select —"] + [p["name"] for p in prompts],
        )
        
        sample_prompt = ""
        if selected_sample != "— Select —":
            sample_prompt = next(
                p["prompt"] for p in prompts if p["name"] == selected_sample
            )
        
        return provider, api_key, model_name, max_repairs, sample_prompt


# =============================================================================
# MAIN AREA — Pipeline Input & Output
# =============================================================================

def render_header():
    """Render the main page header."""
    st.markdown('<p class="main-header">🤖 AI App Generator</p>', unsafe_allow_html=True)
    st.markdown(
        '<p class="sub-header">'
        'Convert natural language application requirements into structured, '
        'validated application schemas.'
        '</p>',
        unsafe_allow_html=True,
    )


def render_prompt_input(sample_prompt: str) -> str:
    """Render the prompt input area and return the current prompt."""
    # Use sample prompt if one was selected, otherwise use existing value
    default_value = sample_prompt if sample_prompt else ""
    
    prompt = st.text_area(
        "📋 Describe your application",
        value=default_value,
        height=120,
        placeholder=(
            "Example: Build a CRM with login, contacts, dashboard, "
            "role-based access and premium subscriptions..."
        ),
        help="Describe the application you want to generate. Be as specific or as vague as you like!",
    )
    return prompt


def render_pipeline_output(result):
    """Render the pipeline output in tabs."""
    if result is None:
        st.info("👆 Enter a prompt and click **Generate** to start the pipeline.")
        return
    
    # Show overall status
    if result.success:
        if result.execution_result and result.execution_result.app_ready:
            st.success(
                f"✅ Pipeline completed successfully in {result.processing_time_seconds}s — "
                f"Application is ready!"
            )
        else:
            st.warning(
                f"⚠️ Pipeline completed in {result.processing_time_seconds}s but "
                f"application may have issues."
            )
    else:
        st.error(f"❌ Pipeline failed: {result.error_message}")
    
    # Create tabs for each stage output
    tabs = st.tabs([
        "1️⃣ Intent",
        "2️⃣ Design",
        "3️⃣ DB Schema",
        "4️⃣ API Schema",
        "5️⃣ UI Schema",
        "6️⃣ Auth",
        "7️⃣ Rules",
        "8️⃣ Validation",
        "9️⃣ Repair",
        "🔟 Execution",
        "📦 Full Config",
    ])
    
    # Tab 1: Intent Extraction
    with tabs[0]:
        st.markdown("### Stage 1: Intent Extraction")
        if result.intent:
            _render_stage_time(result, "intent")
            col1, col2 = st.columns(2)
            with col1:
                st.markdown(f"**App Name:** {result.intent.app_name}")
                st.markdown(f"**App Type:** {result.intent.app_type}")
                st.markdown("**Features:**")
                for f in result.intent.features:
                    st.markdown(f"  - {f}")
            with col2:
                st.markdown("**Roles:**")
                for r in result.intent.roles:
                    st.markdown(f"  - {r}")
                st.markdown("**Entities:**")
                for e in result.intent.entities:
                    st.markdown(f"  - {e}")
            
            if result.intent.assumptions:
                st.info("**Assumptions Made:**\n" + "\n".join(
                    f"- {a}" for a in result.intent.assumptions
                ))
            
            with st.expander("📄 Raw JSON"):
                st.json(result.intent.model_dump())
        else:
            st.warning("Stage 1 did not produce output.")
    
    # Tab 2: System Design
    with tabs[1]:
        st.markdown("### Stage 2: System Design")
        if result.design:
            _render_stage_time(result, "design")
            col1, col2 = st.columns(2)
            with col1:
                st.markdown("**Entities:**")
                for e in result.design.entities:
                    st.markdown(f"  - {e}")
                st.markdown("**Roles:**")
                for r in result.design.roles:
                    st.markdown(f"  - {r}")
            with col2:
                st.markdown("**Workflows:**")
                for w in result.design.workflows:
                    st.markdown(f"  - {w}")
            
            st.markdown(f"**Architecture:** {result.design.architecture}")
            
            st.markdown("**Permissions:**")
            perm_data = []
            for p in result.design.permissions:
                perm_data.append({
                    "Role": p.role,
                    "Resource": p.resource,
                    "Actions": ", ".join(p.actions),
                })
            st.table(perm_data)
            
            with st.expander("📄 Raw JSON"):
                st.json(result.design.model_dump())
        else:
            st.warning("Stage 2 did not produce output.")
    
    # Tab 3: Database Schema
    with tabs[2]:
        st.markdown("### Stage 3a: Database Schema")
        if result.app_schema:
            _render_stage_time(result, "schema")
            for table in result.app_schema.database.tables:
                with st.expander(f"📊 Table: {table.name}", expanded=True):
                    col_data = []
                    for col in table.columns:
                        col_data.append({
                            "Column": col.name,
                            "Type": col.data_type,
                            "PK": "✅" if col.primary_key else "",
                            "Nullable": "✅" if col.nullable else "❌",
                            "FK": col.foreign_key or "",
                        })
                    st.table(col_data)
        else:
            st.warning("Stage 3 did not produce output.")
    
    # Tab 4: API Schema
    with tabs[3]:
        st.markdown("### Stage 3b: API Schema")
        if result.app_schema:
            for ep in result.app_schema.api.endpoints:
                method_color = {
                    "GET": "🟢", "POST": "🟡", "PUT": "🟠",
                    "DELETE": "🔴", "PATCH": "🔵"
                }.get(ep.method.upper(), "⚪")
                
                with st.expander(
                    f"{method_color} {ep.method.upper()} {ep.path}",
                    expanded=False,
                ):
                    st.markdown(f"**Description:** {ep.description}")
                    st.markdown(f"**Auth Required:** {'Yes' if ep.auth_required else 'No'}")
                    if ep.allowed_roles:
                        st.markdown(f"**Allowed Roles:** {', '.join(ep.allowed_roles)}")
                    
                    if ep.request_fields:
                        st.markdown("**Request Fields:**")
                        req_data = [{"Field": f.name, "Type": f.field_type, "Required": "✅" if f.required else ""} for f in ep.request_fields]
                        st.table(req_data)
                    
                    if ep.response_fields:
                        st.markdown("**Response Fields:**")
                        res_data = [{"Field": f.name, "Type": f.field_type, "Required": "✅" if f.required else ""} for f in ep.response_fields]
                        st.table(res_data)
        else:
            st.warning("Stage 3 did not produce output.")
    
    # Tab 5: UI Schema
    with tabs[4]:
        st.markdown("### Stage 3c: UI Schema")
        if result.app_schema:
            for page in result.app_schema.ui.pages:
                with st.expander(f"📱 {page.name} ({page.route})", expanded=False):
                    st.markdown(f"**Auth Required:** {'Yes' if page.requires_auth else 'No'}")
                    if page.allowed_roles:
                        st.markdown(f"**Allowed Roles:** {', '.join(page.allowed_roles)}")
                    
                    st.markdown("**Components:**")
                    comp_data = []
                    for comp in page.components:
                        comp_data.append({
                            "Type": comp.component_type,
                            "Label": comp.label,
                            "Data Source": comp.data_source or "—",
                        })
                    st.table(comp_data)
        else:
            st.warning("Stage 3 did not produce output.")
    
    # Tab 6: Auth Schema
    with tabs[5]:
        st.markdown("### Stage 3d: Auth Schema")
        if result.app_schema:
            st.markdown(f"**Auth Method:** {result.app_schema.auth.auth_method}")
            for role in result.app_schema.auth.roles:
                with st.expander(f"👤 {role.role_name}", expanded=True):
                    st.markdown("**Permissions:**")
                    for perm in role.permissions:
                        st.markdown(f"  - `{perm}`")
        else:
            st.warning("Stage 3 did not produce output.")
    
    # Tab 7: Business Rules
    with tabs[6]:
        st.markdown("### Stage 3e: Business Rules")
        if result.app_schema:
            for rule in result.app_schema.business_rules.rules:
                with st.expander(f"📜 {rule.name}", expanded=False):
                    st.markdown(f"**Description:** {rule.description}")
                    st.markdown("**Conditions:**")
                    for c in rule.conditions:
                        st.markdown(f"  - `{c}`")
                    st.markdown(f"**Entities:** {', '.join(rule.entities_involved)}")
        else:
            st.warning("Stage 3 did not produce output.")
    
    # Tab 8: Validation Report
    with tabs[7]:
        st.markdown("### Stage 4: Validation Report")
        if result.validation_report:
            _render_stage_time(result, "validation")
            vr = result.validation_report
            
            col1, col2, col3 = st.columns(3)
            with col1:
                st.metric("Status", "✅ Valid" if vr.is_valid else "❌ Invalid")
            with col2:
                st.metric("Checks Passed", vr.checks_passed)
            with col3:
                st.metric("Checks Failed", vr.checks_failed)
            
            if vr.issues:
                st.markdown("**Issues Found:**")
                for issue in vr.issues:
                    icon = {"error": "❌", "warning": "⚠️", "info": "ℹ️"}.get(issue.severity.value, "")
                    st.markdown(
                        f"{icon} **[{issue.severity.value.upper()}]** [{issue.layer}] "
                        f"{issue.message}"
                    )
                    if issue.field_path:
                        st.caption(f"  Path: `{issue.field_path}`")
            else:
                st.success("No issues found — all checks passed!")
            
            with st.expander("📄 Raw JSON"):
                st.json(vr.model_dump())
        else:
            st.warning("Stage 4 did not produce output.")
    
    # Tab 9: Repair Report
    with tabs[8]:
        st.markdown("### Stage 5: Repair Report")
        if result.repair_report:
            _render_stage_time(result, "repair")
            rr = result.repair_report
            
            col1, col2 = st.columns(2)
            with col1:
                st.metric("Repairs Applied", rr.repair_count)
            with col2:
                st.metric("Was Repaired", "Yes" if rr.was_repaired else "No")
            
            if rr.repairs_applied:
                st.markdown("**Repairs:**")
                for repair in rr.repairs_applied:
                    st.markdown(
                        f"🔧 **[{repair.layer}]** {repair.action}"
                    )
                    if repair.field_path:
                        st.caption(f"  Path: `{repair.field_path}`")
                    if repair.old_value:
                        st.caption(f"  Old: `{repair.old_value}`")
                    if repair.new_value:
                        st.caption(f"  New: `{repair.new_value}`")
            else:
                st.info("No repairs were needed.")
            
            with st.expander("📄 Raw JSON"):
                st.json(rr.model_dump())
        else:
            st.info("No repair was needed — validation passed on the first attempt.")
    
    # Tab 10: Execution Result
    with tabs[9]:
        st.markdown("### Stage 6: Execution Simulation")
        if result.execution_result:
            _render_stage_time(result, "simulation")
            er = result.execution_result
            
            col1, col2, col3 = st.columns(3)
            with col1:
                st.metric("Status", er.status.upper())
            with col2:
                st.metric("Validation", er.validation.upper())
            with col3:
                st.metric("App Ready", "✅ Yes" if er.app_ready else "❌ No")
            
            st.markdown("**Simulation Details:**")
            for detail in er.details:
                st.markdown(f"  {detail}")
            
            # Show the final status JSON
            st.markdown("**Final Status:**")
            st.json({
                "status": er.status,
                "validation": er.validation,
                "app_ready": er.app_ready,
            })
        else:
            st.warning("Stage 6 did not produce output.")
    
    # Tab 11: Full Configuration
    with tabs[10]:
        st.markdown("### 📦 Full Executable Configuration")
        if result.app_schema:
            st.markdown("Complete application schema — copy this JSON to generate your app.")
            
            # Download button
            full_json = result.app_schema.model_dump_json(indent=2)
            st.download_button(
                label="⬇️ Download Full Schema (JSON)",
                data=full_json,
                file_name=f"{result.intent.app_name.lower().replace(' ', '_')}_schema.json" if result.intent else "app_schema.json",
                mime="application/json",
            )
            
            st.json(result.app_schema.model_dump())
        else:
            st.warning("No schema was generated.")


def _render_stage_time(result, stage_key: str):
    """Helper to display stage processing time."""
    if stage_key in result.stage_times:
        st.caption(f"⏱️ Processing time: {result.stage_times[stage_key]}s")


# =============================================================================
# METRICS DASHBOARD
# =============================================================================

def render_metrics_dashboard():
    """Render the metrics dashboard at the bottom of the page."""
    st.divider()
    st.markdown("## 📊 Metrics Dashboard")
    
    metrics = get_metrics()
    
    col1, col2, col3, col4, col5 = st.columns(5)
    
    with col1:
        st.metric(
            label="Total Requests",
            value=metrics["total_requests"],
        )
    
    with col2:
        st.metric(
            label="Success Rate",
            value=f"{metrics['success_rate']}%",
        )
    
    with col3:
        st.metric(
            label="Validation Failures",
            value=metrics["validation_failures"],
        )
    
    with col4:
        st.metric(
            label="Total Repairs",
            value=metrics["total_repairs"],
        )
    
    with col5:
        st.metric(
            label="Avg Response Time",
            value=f"{metrics['avg_response_time']}s",
        )
    
    # Run history
    with st.expander("📜 Run History", expanded=False):
        history = get_run_history(limit=10)
        if history:
            for run in history:
                status_icon = "✅" if run["success"] else "❌"
                ready_icon = "🟢" if run["app_ready"] else "🔴"
                st.markdown(
                    f"{status_icon} **{run['prompt']}** — "
                    f"{run['processing_time']}s — "
                    f"Repairs: {run['repair_count']} — "
                    f"Ready: {ready_icon}"
                )
        else:
            st.info("No runs yet. Generate your first application above!")


# =============================================================================
# MAIN APPLICATION
# =============================================================================

def main():
    """Main application entry point."""
    # Render sidebar and get configuration
    provider, api_key, model_name, max_repairs, sample_prompt = render_sidebar()
    
    # Render main area
    render_header()
    
    # Prompt input
    prompt = render_prompt_input(sample_prompt)
    
    # Generate button
    col1, col2, col3 = st.columns([1, 1, 4])
    with col1:
        generate_clicked = st.button(
            "🚀 Generate",
            type="primary",
            disabled=st.session_state.is_running,
            use_container_width=True,
        )
    with col2:
        clear_clicked = st.button(
            "🗑️ Clear",
            use_container_width=True,
        )
    
    if clear_clicked:
        st.session_state.pipeline_result = None
        st.rerun()
    
    # Handle Generate button click
    if generate_clicked:
        # Validate inputs
        if not prompt.strip():
            st.error("⚠️ Please enter an application description.")
            return
        
        if not api_key.strip():
            st.error("⚠️ Please enter your API key in the sidebar.")
            return
        
        # Create LLM client
        try:
            llm_client = LLMClient(
                provider=provider,
                api_key=api_key,
                model_name=model_name,
            )
        except Exception as e:
            st.error(f"❌ Failed to initialize LLM client: {str(e)}")
            return
        
        # Run the pipeline with progress display
        st.session_state.is_running = True
        
        # Progress bar
        progress_bar = st.progress(0, text="Starting pipeline...")
        status_text = st.empty()
        
        stage_names = {
            1: "Intent Extraction",
            2: "System Design",
            3: "Schema Generation",
            4: "Validation",
            5: "Repair",
            6: "Execution Simulation",
        }
        
        def progress_callback(stage_name: str, stage_num: int):
            """Update the progress bar as stages complete."""
            progress = min(stage_num / 6, 1.0)
            progress_bar.progress(progress, text=f"Stage {stage_num}: {stage_name}...")
            status_text.markdown(f"⏳ **Running Stage {stage_num}:** {stage_name}")
        
        # Execute pipeline
        result = run_pipeline(
            prompt=prompt,
            llm_client=llm_client,
            max_repair_iterations=max_repairs,
            progress_callback=progress_callback,
        )
        
        # Update state
        st.session_state.pipeline_result = result
        st.session_state.is_running = False
        
        # Clear progress indicators
        progress_bar.progress(1.0, text="Pipeline complete!")
        status_text.empty()
    
    # Render output
    st.divider()
    render_pipeline_output(st.session_state.pipeline_result)
    
    # Render metrics dashboard
    render_metrics_dashboard()


# =============================================================================
# Entry point
# =============================================================================

if __name__ == "__main__":
    main()
