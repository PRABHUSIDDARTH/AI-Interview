# AI Interview Simulator — Technology Stack Specification

A comprehensive technical inventory documenting every technology, framework, library, and tool actually utilized in the **AI Interview Simulator** codebase.

---

## 1. Frontend Technologies

### React 18 (`react`, `react-dom`)
- **WHAT:** A declarative, component-based JavaScript library for building user interfaces.
- **WHY:** Enables reactive state management, modular component architecture, and fast virtual DOM rendering necessary for live interview countdowns and real-time speech transcription.
- **WHERE USED:** Core SPA UI layer in `frontend/src/`.

### Vite (`vite`, `@vitejs/plugin-react`)
- **WHAT:** Next-generation frontend build tooling and development server.
- **WHY:** Provides near-instantaneous Hot Module Replacement (HMR) during development and optimized Rollup asset bundling for production.
- **WHERE USED:** Build configuration in `frontend/vite.config.js` and `frontend/package.json`.

### Tailwind CSS (`tailwindcss`, `autoprefixer`, `postcss`)
- **WHAT:** A utility-first CSS framework.
- **WHY:** Enables responsive, modern UI design, custom glassmorphism effects, score badges, and dark/light color schemes without writing verbose custom CSS files.
- **WHERE USED:** Global styling in `frontend/src/index.css` and component class strings.

### Lucide React Icons (`lucide-react`)
- **WHAT:** A clean, consistent icon library for React applications.
- **WHY:** Enhances user experience with clear visual cues for microphone state, audio playback, metrics, score indicators, and navigation links.
- **WHERE USED:** UI components across `frontend/src/components/`, `pages/`, and `layouts/`.

### Recharts (`recharts`)
- **WHAT:** A composable charting library built with React components.
- **WHY:** Renders responsive performance trend line charts, score radar charts, and topic mastery bar charts on the analytics dashboard.
- **WHERE USED:** `frontend/src/pages/AnalyticsPage.jsx` and `DashboardPage.jsx`.

### Axios (`axios`)
- **WHAT:** Promise-based HTTP client for browser and Node.js.
- **WHY:** Handles API requests to the FastAPI backend, automatically appending JWT Bearer tokens via request interceptors and managing 401 redirect logic via response interceptors.
- **WHERE USED:** API client service wrapper in `frontend/src/services/api.js`.

### Client-Side PDF Generation (`html2canvas`, `jspdf`)
- **WHAT:** Libraries for rendering DOM elements into canvas graphics and converting canvas images into multi-page PDF documents.
- **WHY:** Generates formatted evaluation reports directly inside the user's browser without requiring server-side PDF rendering software or extra network overhead.
- **WHERE USED:** `frontend/src/pages/InterviewEvaluationPage.jsx`.

---

## 2. Backend Technologies

### FastAPI (`fastapi`)
- **WHAT:** A high-performance, asynchronous Web framework for building APIs with Python 3.11+.
- **WHY:** Automatic OpenAPI documentation, native async support, low latency execution, and built-in request validation via Pydantic.
- **WHERE USED:** Backend application entrypoint in `backend/app/main.py` and routers in `backend/app/api/v1/`.

### Uvicorn (`uvicorn[standard]`)
- **WHAT:** A lightning-fast ASGI web server implementation for Python.
- **WHY:** Serves the FastAPI application asynchronously in both local development and production Docker containers.
- **WHERE USED:** Application launcher in `backend/app/main.py` and container execution in `backend/Dockerfile`.

### Pydantic v2 (`pydantic`, `pydantic-settings`)
- **WHAT:** Data validation and settings management using Python type annotations.
- **WHY:** Enforces strict request/response schema validation, automatic type conversion, and environment variable parsing with defaults.
- **WHERE USED:** Request/response DTO schemas in `backend/app/schemas/` and settings in `backend/app/core/config.py`.

### SQLAlchemy 2.0 (`sqlalchemy`)
- **WHAT:** Python SQL toolkit and Object Relational Mapper (ORM).
- **WHY:** Abstracts database queries, manages model relationships, supports engine pooling (`pool_pre_ping`), and ensures multi-database support (SQLite/PostgreSQL).
- **WHERE USED:** Database engine setup in `backend/app/core/database.py` and ORM models in `backend/app/models/`.

---

## 3. Database & Migrations

### SQLite (`sql_app.db`)
- **WHAT:** Lightweight, zero-configuration file-based SQL database engine.
- **WHY:** Default database for local development, demo sessions, and single-container deployments without requiring external database server administration.
- **WHERE USED:** Default engine configuration in `backend/app/core/database.py`.

### PostgreSQL Support (`psycopg2-binary`)
- **WHAT:** PostgreSQL database driver for Python.
- **WHY:** Allows production deployments to scale seamlessly to external managed database servers (e.g. AWS RDS, Cloud SQL) or containerized PostgreSQL services.
- **WHERE USED:** `backend/requirements.txt` and `docker-compose.yml` (`postgres` profile).

### Idempotent Auto-Migrations (`app/core/migration.py`)
- **WHAT:** Custom Python migration engine using SQLAlchemy `inspect` and `ALTER TABLE`.
- **WHY:** Automatically inspects database tables on application startup and idempotently adds any missing columns without dropping existing user data.
- **WHERE USED:** `backend/app/core/migration.py` and `backend/migrate_db.py`.

---

## 4. AI & Hybrid RAG Layer

### Multi-Provider LLM Client (`app/services/ai.py`)
- **WHAT:** Abstract AI service supporting Google Gemini (`gemini-2.5-flash` by default), OpenAI (`gpt-4o-mini` by default; override either with `AI_MODEL`), and `MockProvider`.
- **WHY:** Guarantees platform availability even if external AI provider credentials expire, hit rate limits, or suffer network timeouts.
- **WHERE USED:** `backend/app/services/ai.py`.

### Local Knowledge RAG Engine (`LocalKnowledgeRetriever`)
- **WHAT:** Offline Retrieval-Augmented Generation (RAG) engine that loads curated JSON technical records.
- **WHY:** Eliminates LLM technical hallucinations by injecting grounded concept definitions, difficulty constraints, and common candidate mistakes into LLM system prompts.
- **WHERE USED:** `backend/app/services/knowledge/retriever.py` and knowledge modules in `backend/app/data/knowledge/` (15 JSON files).

---

## 5. Security & Authentication

### JWT Authentication (`python-jose[cryptography]`)
- **WHAT:** JavaScript Object Signing and Encryption implementation for Python.
- **WHY:** Generates and verifies cryptographically signed JWT access tokens containing candidate claims (`sub: user_id`).
- **WHERE USED:** Security helpers in `backend/app/core/security.py` and auth router `backend/app/api/v1/auth.py`.

### Password Hashing (`passlib[bcrypt]`, `bcrypt==4.0.1`)
- **WHAT:** Password hashing library utilizing the salted Bcrypt algorithm.
- **WHY:** Ensures candidate plaintext passwords are never stored in the database, protecting against database compromise.
- **WHERE USED:** `backend/app/core/security.py`.

---

## 6. Resume Processing & Voice System

### PDF Text Extraction (`pdfminer.six`)
- **WHAT:** A community-maintained PDF extraction tool for Python.
- **WHY:** Extracts layout-aware plaintext from PDF resumes uploaded by candidates for skill parsing.
- **WHERE USED:** `backend/app/utils/pdf_extractor.py` and `backend/app/services/resume_parser.py`.

### Web Speech API (Speech Recognition & Speech Synthesis)
- **WHAT:** Browser-native speech-to-text (`webkitSpeechRecognition`) and text-to-speech (`window.speechSynthesis`) interfaces.
- **WHY:** Enables interactive voice input and question audio narration without external paid audio processing API subscriptions.
- **WHERE USED:** `frontend/src/hooks/useSpeechRecognition.js` and `frontend/src/pages/InterviewRoomPage.jsx`.

---

## 7. Testing & DevOps

### Pytest (`pytest`)
- **WHAT:** Python testing framework.
- **WHY:** Executes 110 automated unit tests for FastAPI routers, authentication logic, interview engines, and RAG services.
- **WHERE USED:** `backend/tests/`.

### End-to-End Regression Suite (`regression_test.py`)
- **WHAT:** Automated Python end-to-end integration test runner.
- **WHY:** Validates 123 assertions across the complete user flow (Registration → Setup → Q&A → Evaluation → Analytics → Coach).
- **WHERE USED:** Root directory `regression_test.py`.

### Docker & Docker Compose
- **WHAT:** Containerization platform and multi-container orchestration.
- **WHY:** Ensures reproducible production builds across any cloud provider or operating system.
- **WHERE USED:** `backend/Dockerfile`, `frontend/Dockerfile`, `frontend/nginx.conf`, and `docker-compose.yml`.
