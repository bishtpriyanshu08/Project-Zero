# 🤖 AI App Generator MVP

A multi-stage pipeline that converts natural language application requirements into structured, validated application schemas. Think of it as a **compiler for app generation**.

## 🏗️ Architecture

```
Natural Language Prompt
  → Stage 1: Intent Extraction      (LLM)
  → Stage 2: System Design          (LLM)
  → Stage 3: Schema Generation      (LLM)
  → Stage 4: Validation Engine      (Python)
  → Stage 5: Repair Engine          (Python)
  → Stage 6: Execution Simulator    (Python)
  → Executable Application Configuration
```

### Pipeline Stages

| Stage | Name | Engine | Description |
|-------|------|--------|-------------|
| 1 | Intent Extraction | LLM | Extracts app name, features, roles, entities from natural language |
| 2 | System Design | LLM | Generates workflows, permissions, architecture |
| 3 | Schema Generation | LLM | Produces 5 schema layers (DB, API, UI, Auth, Business Rules) |
| 4 | Validation | Python | 8 categories of checks including cross-layer consistency |
| 5 | Repair | Python | Targeted fixes for validation failures (no full regeneration) |
| 6 | Simulation | Python | Verifies schemas are executable (includes SQLite DDL test) |

### Generated Schema Layers

1. **Database Schema** — Tables, columns, relationships, foreign keys
2. **API Schema** — REST endpoints, methods, request/response fields
3. **UI Schema** — Pages, components, routes, role-based access
4. **Auth Schema** — Authentication method, roles, permissions
5. **Business Rules** — Constraints, conditions, entity relationships

## 📁 Project Structure

```
├── backend/
│   ├── __init__.py              # Package initialization
│   ├── schemas.py               # All Pydantic models (data contracts)
│   ├── llm_client.py            # LLM abstraction (Gemini + OpenAI)
│   ├── intent_extractor.py      # Stage 1: Intent Extraction
│   ├── system_designer.py       # Stage 2: System Design
│   ├── schema_generator.py      # Stage 3: Schema Generation
│   ├── validator.py             # Stage 4: Validation Engine
│   ├── repair_engine.py         # Stage 5: Repair Engine
│   ├── simulator.py             # Stage 6: Execution Simulator
│   ├── pipeline.py              # Pipeline Orchestrator
│   └── database.py              # SQLite persistence for metrics
├── frontend/
│   └── app.py                   # Streamlit UI
├── tests/
│   └── sample_prompts.py        # 20 evaluation prompts (10 normal + 10 edge cases)
├── data/                        # SQLite database (auto-created)
├── requirements.txt
└── README.md
```

## 🚀 Setup Instructions

### Prerequisites

- **Python 3.10+** (3.11 or 3.12 recommended)
- **API Key**: Either a Google Gemini API key or an OpenAI API key

### Installation

1. **Clone or navigate to the project directory:**

```bash
cd "Ai Internship project"
```

2. **Create a virtual environment:**

```bash
python -m venv venv
```

3. **Activate the virtual environment:**

```bash
# Windows
venv\Scripts\activate

# macOS/Linux
source venv/bin/activate
```

4. **Install dependencies:**

```bash
pip install -r requirements.txt
```

### Get an API Key

**Option A — Google Gemini (Recommended):**
1. Go to [Google AI Studio](https://aistudio.google.com/)
2. Click "Get API Key" → "Create API Key"
3. Copy the key

**Option B — OpenAI:**
1. Go to [OpenAI Platform](https://platform.openai.com/api-keys)
2. Create a new API key
3. Copy the key

## 🖥️ Usage

### Start the Application

```bash
streamlit run frontend/app.py
```

This opens the app in your browser at `http://localhost:8501`.

### Using the App

1. **Enter your API key** in the sidebar
2. **Choose your LLM provider** (Gemini or OpenAI)
3. **Type or select a prompt** describing your application
4. **Click Generate** to run the pipeline
5. **Browse the tabs** to see each stage's output
6. **Download the full schema** as JSON

### Example Prompt

```
Build a CRM with login, contacts, dashboard, role-based access 
and premium subscriptions. Admins can view analytics.
```

## 📊 Evaluation Dataset

The project includes 20 test prompts in `tests/sample_prompts.py`:

### Normal Prompts (10)
- CRM System, E-Commerce Store, Hospital Management, School Portal
- Inventory System, Expense Tracker, Fitness App, Hotel Booking
- Job Portal, Library Management

### Edge Cases (10)
- "Build something useful" (vague)
- "Make an app" (minimal)
- Conflicting requirements, Missing authentication
- Undefined entities, Ambiguous users
- Contradictory permissions, Incomplete payment flow
- Missing workflows, Unclear business rules

## 🔧 Technical Details

### Strict JSON Output

All LLM outputs are validated through Pydantic models:
- Gemini API: Uses `response_schema` parameter for native structured output
- OpenAI API: Uses `response_format` with JSON schema
- Both guarantee valid JSON conforming to predefined schemas

### Validation Checks (Stage 4)

| Check | Description |
|-------|-------------|
| Table Completeness | Every table has columns and a primary key |
| Foreign Key Validity | FKs reference existing tables and columns |
| API Completeness | POST/PUT have request fields, GET has response fields |
| UI → API Consistency | Component data sources match API endpoints |
| Role Consistency | All referenced roles exist in auth schema |
| Business Rule Entities | Referenced entities match database tables |
| Page Completeness | Every page has at least one component |
| Auth Completeness | Every role has defined permissions |

### Repair Strategies (Stage 5)

| Issue | Repair |
|-------|--------|
| Missing primary key | Add `id INTEGER PRIMARY KEY` column |
| Broken foreign key | Remove the invalid reference |
| Empty table | Add default columns (id, name, timestamps) |
| Missing request/response fields | Add stub fields |
| Invalid data source | Match to closest API endpoint |
| Missing role in auth | Add role with basic permissions |
| Missing entity table | Create stub table |

## 📈 Metrics Dashboard

The app tracks and displays:
- **Success Rate**: Percentage of successful pipeline runs
- **Validation Failures**: Count of runs where validation initially failed
- **Total Repairs**: Number of automatic repairs applied
- **Average Response Time**: Mean pipeline execution time
- **Total Requests**: Total number of runs processed

Metrics are persisted in SQLite at `data/app_generator.db`.

## 🧹 Code Quality

- **Modular architecture**: Each stage is an independent module
- **Clean code**: Detailed comments and docstrings
- **Type safety**: Full Pydantic validation on all data
- **Separation of concerns**: LLM calls, validation, repair, and UI are fully decoupled
- **Error handling**: Graceful degradation with partial results on failure
- **Logging**: Comprehensive logging at each pipeline stage

## 🚀 Deployment

### Option 1: Streamlit Community Cloud (Recommended — Free)

1. Push this repo to GitHub
2. Go to [streamlit.io/cloud](https://streamlit.io/cloud)
3. Click **"New app"** → Select your repo
4. Set **Main file path** to: `frontend/app.py`
5. Deploy! 🎉

### Option 2: Vercel (Docker Runtime)

1. Install the [Vercel CLI](https://vercel.com/docs/cli):
   ```bash
   npm install -g vercel
   ```
2. Deploy from the project root:
   ```bash
   vercel --prod
   ```
3. Set environment variables in Vercel dashboard:
   - `STREAMLIT_SERVER_HEADLESS` = `true`

> **Note:** Streamlit apps require a persistent server. For the best Vercel experience, use the included `Dockerfile` with Vercel's Docker runtime.

### Option 3: Docker

```bash
# Build the image
docker build -t ai-app-generator .

# Run the container
docker run -p 8501:8501 ai-app-generator
```

Then visit `http://localhost:8501`.

### Option 4: Railway / Render / Heroku

These platforms auto-detect the `Procfile` and `runtime.txt`:

```bash
# Railway
railway deploy

# Heroku
heroku create && git push heroku main
```

### Environment Variables

| Variable | Description | Default |
|----------|-------------|---------|
| `VERCEL` | Set automatically on Vercel | — |
| `DB_DIR` | Custom path for SQLite database | `./data/` |
| `STREAMLIT_SERVER_PORT` | Port for Streamlit server | `8501` |

## 📝 License

This project is for educational and internship purposes.
