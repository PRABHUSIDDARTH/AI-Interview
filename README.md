# AI-Powered Resume-Driven Interview Simulator

A production-ready, full-stack AI platform that simulates realistic technical, HR, behavioral, and mixed interview practice sessions. Candidates receive personalized questions dynamically grounded in their uploaded resume and target job description, practice with speech-to-text voice input and question narration, and receive evidence-based evaluations, performance analytics, and exportable PDF reports.

---

## 1. Project Overview

### What the System Does
The **AI Interview Simulator** provides an end-to-end, interactive environment for job seekers to prepare for interviews. It ingests a candidate's PDF resume, extracts candidate skills, allows focus selection, and generates customized technical, HR, behavioral, or mixed interview sessions. Answers are evaluated across five key scoring dimensions, and follow-up questions dynamically adapt in difficulty based on candidate performance.

### Who It Is For
- **Software Engineers & Technical Candidates** preparing for role-specific interviews (Frontend, Backend, DevOps, Data, Full-Stack).
- **Job Seekers & Graduates** practicing behavioral and HR responses with real-time AI feedback.
- **Career Switchers** looking to identify knowledge gaps against specific job descriptions.

### Why It Is Useful & Key Differentiation
Unlike basic AI prompt wrappers or static question banks, this platform:
- **Grounds questions in candidate context:** Uses text extracted directly from the candidate's resume and target job description rather than arbitrary templates.
- **Enforces factual AI responses via Hybrid RAG:** Grounded with a curated offline technical knowledge retrieval engine (`LocalKnowledgeRetriever`) to eliminate unsupported hallucinated questions.
- **Evaluates with multi-dimensional scoring:** Evaluates responses across correctness, relevance, technical depth, and communication quality rather than relying on response length.
- **Adapts interview progression dynamically:** Uses an adaptive decision engine (`AdaptiveDecisionEngine`) to escalate difficulty on strong answers or offer reinforcement on weak/irrelevant responses.

---

## 2. Problem Statement

Traditional interview preparation suffers from significant structural limitations:
1. **Generic Question Repositories:** Static question lists fail to reflect a candidate's actual resume or target job requirements.
2. **Lack of Instant, Actionable Feedback:** Mock interviews with peers are difficult to schedule, inconsistent, and often lack objective scoring.
3. **No Adaptive Progression:** Fixed question sequences do not adjust when a candidate struggles or easily answers initial questions.
4. **Isolated Analytics:** Candidates rarely track performance trends, topic strengths, or weak areas over time.

---

## 3. Proposed Solution & End-to-End System Flow

```text
Resume Upload (PDF)
        ↓
Text & Skill Extraction (pdfminer.six)
        ↓
Skill Focus Selection (User Choice)
        ↓
Knowledge Retrieval (LocalKnowledgeRetriever - RAG)
        ↓
Personalized Question Generation (Gemini / OpenAI / Mock)
        ↓
Interactive Interview Room (Voice Input / Timed Mode)
        ↓
Evidence-Based Answer Evaluation (Multi-dimensional Scoring)
        ↓
Adaptive Decision Engine (Escalate / Clarify / Reinforce)
        ↓
Final Evaluation & PDF Report Export (html2canvas & jsPDF)
        ↓
AI Coach & Analytics (Strict User Data Isolation)
```

---

## 4. Key Features

- **Resume Upload & Parsing:** Ingests PDF resumes (up to 2 MiB) using `pdfminer.six`, extracting skill profiles, technologies, and inferred job roles.
- **Interactive Skill Selection:** Candidates can explicitly choose which extracted skills to emphasize during the session.
- **Customized Setup:** Configure interview type (Technical, HR, Mixed, Behavioral), experience level (Beginner, Intermediate, Advanced), difficulty (Easy, Medium, Hard), language (English, Spanish, French, German, etc.), and question count (3, 5, 10, 15).
- **Target Job Description Context:** Paste target job descriptions (up to 2,000 characters) to align questions with real job postings.
- **Hybrid RAG Knowledge Grounding:** Uses 15 domain-specific technical knowledge modules (Python, React, Docker, FastAPI, PostgreSQL, JavaScript, Node.js, CSS, AWS, Git, Java, MongoDB, Spring, TypeScript, Fallback) to ground technical questions.
- **Resilient AI Provider Infrastructure:** Supports Google Gemini (`gemini-2.5-flash` by default), OpenAI (`gpt-4o-mini` by default; override either with `AI_MODEL`), and an automatic offline `MockProvider` fallback if API quotas or keys are unavailable.
- **Voice System:** Integrated browser-native Speech-to-Text (`webkitSpeechRecognition`) for hands-free answer input and Text-to-Speech (`window.speechSynthesis`) for question narration.
- **Evidence-Based Evaluation:** Multi-dimensional feedback scoring each answer from 0.0 to 10.0 across Overall Score, Correctness, Relevance, Technical Depth, and Communication Quality, complete with key strengths and weaknesses.
- **Adaptive Question Flow:** Dynamically calculates next-question difficulty based on recent answer performance (e.g., strong answers trigger deeper questions, weak answers trigger reinforcement questions).
- **Performance Analytics Dashboard:** Aggregated metrics, score trends over time, top strengths, weak topics, and session history.
- **RAG AI Coach:** Interactive candidate assistant providing personalized recommendations, topic mastery summaries, weak-topic practice questions, and isolated chat.
- **Exportable PDF Reports:** Professional client-side PDF export generated using `html2canvas` and `jspdf`.
- **Security & User Isolation:** JWT authentication (`python-jose`), password hashing (`passlib` with `bcrypt`), protected frontend routes, password reset workflow, and strict database ownership filtering.

---

## 5. System Architecture

```text
                                  +---------------------------------------+
                                  |             React Frontend            |
                                  |  (Vite, Tailwind, Recharts, jsPDF)    |
                                  +-------------------+-------------------+
                                                      |
                                                      | HTTP / REST API (Axios + JWT)
                                                      v
                                  +-------------------+-------------------+
                                  |          FastAPI Backend              |
                                  |        (Uvicorn ASGI Server)          |
                                  +-------------------+-------------------+
                                                      |
         +--------------------------------------------+--------------------------------------------+
         |                                            |                                            |
         v                                            v                                            v
+------------------+                       +--------------------+                       +----------------------+
|  Auth & Security |                       |  Interview Engine  |                       |   AI & RAG Services  |
|  (JWT / Bcrypt)  |                       | (Session State &   |                       | (Gemini/OpenAI/Mock  |
+--------+---------+                       |    Adaptation)     |                       | LocalKnowledgeRAG)   |
         |                                 +----------+---------+                       +----------+-----------+
         |                                            |                                            |
         +--------------------------------------------+--------------------------------------------+
                                                      |
                                                      v
                                  +-------------------+-------------------+
                                  |          SQLAlchemy ORM               |
                                  |     (SQLite / PostgreSQL Engine)      |
                                  +---------------------------------------+
```

### Architectural Component Responsibilities

1. **Frontend Layer (`frontend/src`)**: Single Page Application built with React 18 and Vite. Handles user interaction, voice input/narration, interview state transitions, charts rendering, and PDF report generation.
2. **API Routing Layer (`backend/app/api/v1`)**: Exposes REST endpoints for Authentication (`auth.py`), Interviews (`interviews.py`), AI Coach (`coach.py`), and System Health (`health.py`). Validates requests via Pydantic schemas.
3. **Core Services Layer (`backend/app/services`)**:
   - `InterviewEngine`: Orchestrates session creation, question progression, score aggregation, and adaptive state transitions.
   - `AIProvider`: Manages LLM client integration (Gemini, OpenAI) with prompt construction and mock fallback logic.
   - `LocalKnowledgeRetriever`: Implements hybrid RAG retrieval from curated JSON domain records.
   - `RAGCoachService`: Handles user-isolated analytics aggregation, coaching summaries, and topic practice.
   - `ResumeParserService`: Handles PDF text parsing via `pdfminer.six` and skill extraction.
4. **Data Layer (`backend/app/models` & `backend/app/core`)**: SQLAlchemy ORM models (`User`, `InterviewSession`) with database configuration supporting SQLite (`sqlite:///./sql_app.db`) and PostgreSQL.

---

## 6. Frontend Architecture

### Page Components & Structure

| Page File | Route | Description |
| :--- | :--- | :--- |
| `LoginPage.jsx` | `/login` | User authentication form with JWT token storage |
| `RegisterPage.jsx` | `/register` | User registration with full name, email, and password validation |
| `ForgotPasswordPage.jsx` | `/forgot-password` | Initiates password reset flow |
| `ResetPasswordPage.jsx` | `/reset-password` | Completes password reset using secure token |
| `DashboardPage.jsx` | `/dashboard` | Main dashboard displaying metrics, recent sessions, and quick launch |
| `InterviewSetupPage.jsx` | `/interview/setup` | Resume upload, skill extraction/selection, and interview customization |
| `InterviewRoomPage.jsx` | `/interview/room/:id` | Live interview room with question display, voice STT, TTS narration, and countdown timer |
| `InterviewEvaluationPage.jsx` | `/interview/evaluation/:id` | Detailed multi-dimensional evaluation report with client-side PDF export |
| `AnalyticsPage.jsx` | `/analytics` | Aggregated candidate performance charts (Recharts) and topic trends |
| `AICoachPage.jsx` | `/coach` | AI Coach dashboard, topic summaries, practice questions, and isolated coach chat |
| `ProfilePage.jsx` | `/profile` | Candidate profile details and password update form |

### Custom React Hooks
- **`useAuth.js`**: Provides global authentication state, token management, login, logout, and user profile updates via React Context.
- **`useSpeechRecognition.js`**: Wraps the browser-native `webkitSpeechRecognition` API for real-time speech-to-text input with interim transcripts and error handling.

---

## 7. Backend Architecture

### Directory Structure & Responsibilities

```text
backend/app/
├── api/
│   ├── v1/
│   │   ├── auth.py          # User registration, login, profile, password reset
│   │   ├── coach.py         # AI Coach summary, recommendations, topics, chat
│   │   ├── health.py        # Service health check endpoint
│   │   └── interviews.py    # Session creation, resume extraction, Q&A flow, analytics
│   └── deps.get_db          # FastAPI dependency injection for DB session & auth user
├── core/
│   ├── config.py            # Environment settings, CORS origins, JWT config
│   ├── database.py          # SQLAlchemy engine, session maker, wait_for_db retry helper
│   ├── migration.py         # Idempotent auto-migration script for missing columns
│   └── security.py          # Password hashing (bcrypt) and JWT token creation/verification
├── models/
│   ├── user.py              # User SQLAlchemy model
│   └── interview_session.py # InterviewSession SQLAlchemy model
├── schemas/
│   ├── auth.py              # Pydantic schemas for authentication
│   ├── coaching.py          # Pydantic schemas for AI Coach
│   └── interview.py         # Pydantic schemas for interviews & evaluations
├── services/
│   ├── ai.py                # LLM integration (Gemini, OpenAI, Mock fallback)
│   ├── interview_engine.py  # Interview execution logic & adaptive decision engine
│   ├── rag_coach.py         # User-isolated analytics & coaching service
│   ├── resume_parser.py     # Resume skill parser
│   └── knowledge/           # Local knowledge retrieval engine (RAG)
└── utils/
    └── pdf_extractor.py     # PDF text extraction wrapper using pdfminer.six
```

---

## 8. AI & RAG Pipeline

```text
Candidate Resume (PDF)
        ↓
pdfminer.six Text Extraction
        ↓
Skill Profile & Focus Selection
        ↓
LocalKnowledgeRetriever (15 Curated Skill Modules)
        ↓
Difficulty & Experience Banding Filter (Beginner / Intermediate / Advanced)
        ↓
Grounded Prompt Assembly (LLM System Prompt + Knowledge Context)
        ↓
Gemini / OpenAI / Mock Execution
        ↓
Question Generation / Multi-Dimensional Answer Evaluation
        ↓
Adaptive Decision Engine (Score evaluation → Difficulty adjustment)
```

### Hybrid RAG Knowledge Retrieval Implementation
Rather than relying on external vector databases that introduce network latency and dependency overhead, the system uses a high-performance offline retrieval engine (`LocalKnowledgeRetriever` in `app/services/knowledge/retriever.py`).
- **Knowledge Base Location:** `backend/app/data/knowledge/` containing 15 domain JSON files (`python.json`, `react.json`, `fastapi.json`, `postgresql.json`, `docker.json`, `javascript.json`, `nodejs.json`, `css.json`, `aws.json`, `git.json`, `java.json`, `mongodb.json`, `spring.json`, `typescript.json`, `_fallback.json`).
- **Retrieval Process:** When a candidate selects skills, the retriever normalizes skill strings, loads matching JSON topic modules, filters topic records matching the session difficulty band, and injects conceptual constraints directly into the LLM system prompt.
- **Fallback Behavior:** If an unsupported skill is selected, the retriever gracefully falls back to `_fallback.json` containing core software engineering principles.

---

## 9. Evidence-Based Evaluation & Scoring System

The AI evaluation engine rates every submitted answer on a scale from `0.0` to `10.0` across 5 specific metrics:

1. **Overall Score (`0.0 - 10.0`)**: Weighted synthesis of total answer quality.
2. **Correctness (`0.0 - 10.0`)**: Accuracy of technical statements against standard domain concepts.
3. **Relevance (`0.0 - 10.0`)**: Direct alignment with the specific question asked.
4. **Technical Depth (`0.0 - 10.0`)**: Depth of technical explanation, use of appropriate terminology, and underlying mechanism awareness.
5. **Communication Quality (`0.0 - 10.0`)**: Clarity, structure, and conciseness of the response.

### Relevance Gate & Irrelevant Answer Handling
Answer length alone is not treated as quality. The evaluation engine evaluates semantic alignment:
- *Example Question:* "What is polymorphism in Python?"
- *Irrelevant Response:* "Python was created by Guido van Rossum in 1991."
- *Evaluation Output:* Receives a low **Relevance** score (`< 3.0`), lowering the Overall Score and triggering an adaptive follow-up or clarification question.

---

## 10. Adaptive Interview Engine

The `AdaptiveDecisionEngine` (in `app/services/interview_engine.py`) dynamically modifies question selection during a session based on real-time evaluation history:

- **Strong Answer (`Score >= 7.5`)**: System escalates difficulty for the next question, introducing deeper technical concepts or design trade-offs.
- **Partial / Moderate Answer (`5.0 <= Score < 7.5`)**: System maintains difficulty and generates a targeted follow-up or clarification question on missing aspects.
- **Weak Answer (`Score < 5.0`)**: System provides a helpful hint in the feedback and selects a fundamental reinforcement question to test core concepts.
- **Irrelevant Response (`Relevance < 4.0`)**: System flags off-topic responses and re-tests the primary skill concept before progressing.

---

## 11. AI Coach & Data Isolation

The AI Coach service (`RAGCoachService` in `app/services/rag_coach.py`) provides candidates with personalized performance insights:
- **Performance Summaries:** Aggregates average scores across all historical sessions.
- **Topic Mastery:** Categorizes candidates' strengths and weak topics using keyword matching against evaluation history.
- **Practice Question Generator:** Generates custom single-topic practice questions focused on identified weak areas.
- **Strict User Data Isolation:** Implements database-level ownership filtering (`UserInterviewHistoryRetriever`) enforcing `user_id == current_user.id`. Candidates can never access or view another user's session history or coaching data.

---

## 12. Voice System Architecture

Speech input and question narration are cleanly divided into two independent browser-native technologies:

1. **Speech-to-Text (STT - Speech Recognition)**:
   - Handled by `useSpeechRecognition.js` using `window.webkitSpeechRecognition` or `window.SpeechRecognition`.
   - Captures microphone input, converts audio to text in real time, and populates the candidate's answer textarea.
2. **Text-to-Speech (TTS - Speech Synthesis)**:
   - Handled in `InterviewRoomPage.jsx` using `window.speechSynthesis`.
   - Reads AI-generated interview questions aloud upon display, with controls to pause, replay, or mute narration.

---

## 13. Security Architecture

- **Authentication:** JWT tokens signed with `HS256` algorithm via `python-jose`. Tokens are transmitted via `Authorization: Bearer <token>` headers.
- **Password Hashing:** Passwords hashed with `bcrypt` algorithm using `passlib`. Plaintext passwords are never stored.
- **Authorization & Ownership:** All API endpoints inspect `current_user` dependencies. Session queries filter explicitly by `user_id`, preventing unauthorized cross-tenant data access.
- **File Upload Security:** Resume upload endpoint (`/api/v1/interviews/extract-resume` and `/start`) validates file extension (`.pdf`), content-type header (`application/pdf`), maximum file size (`2 MiB`), and PDF magic bytes (`%PDF`).
- **CORS Protection:** Configurable allowed origins enforced via FastAPI `CORSMiddleware`.

---

## 14. Database Schema

```text
+---------------------------------------+         +---------------------------------------+
|                 User                  |         |           InterviewSession            |
+---------------------------------------+         +---------------------------------------+
| id: Integer (PK)                      | 1     * | id: Integer (PK)                      |
| email: String (Unique, Indexed)       |<------->| user_id: Integer (FK -> User.id)     |
| hashed_password: String               |         | job_role: String                      |
| full_name: String                     |         | interview_type: String                |
| reset_token: String (Nullable)        |         | experience_level: String              |
| reset_token_expires: DateTime         |         | difficulty: String                    |
| created_at: DateTime                  |         | question_count: Integer               |
| updated_at: DateTime                  |         | status: String                        |
+---------------------------------------+         | questions: JSON / Text                |
                                                  | evaluations: JSON / Text              |
                                                  | answered_count: Integer               |
                                                  | job_description: Text (Nullable)      |
                                                  | interview_language: String            |
                                                  | resume_skills: Text (JSON List)       |
                                                  | selected_skills: Text (JSON List)     |
                                                  | source_context: Text (JSON)           |
                                                  | resume_profile: Text (JSON)           |
                                                  | adaptive_state: Text (JSON)           |
                                                  | created_at: DateTime                  |
                                                  | updated_at: DateTime                  |
                                                  +---------------------------------------+
```

---

## 15. API Reference

### Authentication Endpoints (`/api/v1/auth`)

| Method | Path | Auth Required | Request Body / Query | Response | Purpose |
| :--- | :--- | :---: | :--- | :--- | :--- |
| `POST` | `/register` | No | `{email, password, full_name}` | `UserResponse (201)` | Register a new user |
| `POST` | `/login` | No | Form Data: `username, password` | `{access_token, token_type} (200)` | Authenticate user & return JWT |
| `GET` | `/me` | Yes | Header: `Bearer <token>` | `UserResponse (200)` | Retrieve current user profile |
| `PUT` | `/me` | Yes | `{full_name, current_password, new_password}` | `UserResponse (200)` | Update user name or password |
| `POST` | `/forgot-password` | No | `{email}` | `{message} (200)` | Initiate password reset |
| `POST` | `/reset-password` | No | `{token, new_password}` | `{message} (200)` | Reset password using token |

### Interview Endpoints (`/api/v1/interviews`)

| Method | Path | Auth Required | Request Body / Query | Response | Purpose |
| :--- | :--- | :---: | :--- | :--- | :--- |
| `POST` | `/extract-resume` | Yes | Multipart: `resume (File)` | `{success, profile} (200)` | Extract skills & profile from PDF |
| `POST` | `/start` | Yes | Form: `interview_type, job_role, ...` | `{session_id, question} (201)` | Create session & get 1st question |
| `GET` | `/{id}` | Yes | Path: `id` | `InterviewSessionResponse (200)` | Fetch interview session details |
| `GET` | `/{id}/next` | Yes | Path: `id` | `{question} (200)` | Fetch current active question |
| `POST` | `/{id}/answer` | Yes | `{answer_text}` | `EvaluationResponse (200)` | Submit answer & get evaluation |
| `GET` | `/{id}/evaluation` | Yes | Path: `id` | `OverallEvaluationResponse (200)` | Fetch complete final evaluation |
| `GET` | `/analytics` | Yes | None | `AnalyticsResponse (200)` | Fetch user aggregated metrics |
| `GET` | `/` | Yes | Query: `skip, limit` | `InterviewSessionListResponse (200)`| List user interview sessions |

### AI Coach Endpoints (`/api/v1/coach`)

| Method | Path | Auth Required | Request Body / Query | Response | Purpose |
| :--- | :--- | :---: | :--- | :--- | :--- |
| `GET` | `/summary` | Yes | None | `CoachSummaryResponse (200)` | Aggregate coaching metrics |
| `GET` | `/recommendations` | Yes | None | `List[RecommendedInterviewDTO]` | Get recommended practice roles |
| `GET` | `/topics` | Yes | None | `List[TopicMetricDTO]` | Get candidate topic breakdown |
| `POST` | `/practice-question` | Yes | `{topic}` | `PracticeQuestionResponse (200)` | Generate weak-topic question |
| `POST` | `/chat` | Yes | `{message, history}` | `CoachChatResponse (200)` | Interactive AI Coach chat |

---

## 16. Testing & Quality Assurance

### Test Execution Summary

#### 1. Backend Pytest Unit Suite
```bash
cd backend
python -m pytest -q
```
- **Total Unit Tests Executed:** 110
- **Passed:** 110 (100%)
- **Failed:** 0
- **Execution Time:** 18.70s

#### 2. End-to-End Automated Regression Suite
```bash
python regression_test.py
```
- **Total Assertions Executed:** 123
- **Passed:** 123 (100%)
- **Failed:** 0
- **Coverage:** Auth, Profile, Password Reset, Resume Extraction, Skill Selection, Interview Customization, PDF Rejection, Question Generation, Answer Submission, Multi-Dimensional Evaluation, Adaptive Progression, Analytics, AI Coach, Authorization Enforcement.

#### 3. Frontend Production Build Verification
```bash
cd frontend
npm run build
```
- **Status:** Clean Build (`✓ 1058 modules transformed`)

---

## 17. Deployment & Operations

### Local Development Setup

#### Backend Setup:
```bash
cd backend
python -m venv venv
# Windows: venv\Scripts\activate | Linux/macOS: source venv/bin/activate
pip install -r requirements.txt
python -m uvicorn app.main:app --reload --port 8000
```

#### Frontend Setup:
```bash
cd frontend
npm install
npm run dev
```

### Production Containerized Setup (Docker Compose)

```bash
# Build production images
docker compose build

# Launch services in detached mode
docker compose up -d
```

- **Frontend Container:** Served via Nginx on port `3000` (mapped to internal Nginx port 80).
- **Backend Container:** FastAPI app running via Uvicorn on port `8000`.
- **Database Storage:** Persistent SQLite data mounted at `/app/data` (volume `backend_data`), or PostgreSQL container via `docker compose --profile postgres up`.

---

## 18. Troubleshooting Guide

| Problem | Potential Cause | Solution |
| :--- | :--- | :--- |
| **Backend port `8000` already in use** | Another process is bound to port 8000 | Kill process on 8000 (`Stop-Process -Id (Get-NetTCPConnection -LocalPort 8000).OwningProcess`) or set custom port in Uvicorn command. |
| **CORS policy error in browser console** | Frontend origin missing from backend CORS list | Add frontend origin (e.g. `http://localhost:3000`) to `CORS_ORIGINS` in `.env`. |
| **Microphone speech-to-text not capturing** | Browser permission denied or HTTP origin | Grant microphone permissions in browser settings. Note that Web Speech API requires HTTPS or `localhost`. |
| **Database missing column errors** | Schema updated between code versions | Backend automatically runs `run_auto_migrations(engine)` on startup. Alternatively, run `python backend/migrate_db.py`. |
| **AI Question generation fallback to mock** | Invalid or missing `AI_API_KEY`, or an `AI_MODEL` your key can't use | Set `AI_PROVIDER=gemini`, a valid `AI_API_KEY`, and a valid `AI_MODEL` (or leave it empty for the default) in `.env`. Check `GET /health` (the `ai` field) and look for `Falling back to mock output` in the backend log, which includes the HTTP status. |

---

## License

This project is licensed under the [Apache License 2.0](LICENSE).
