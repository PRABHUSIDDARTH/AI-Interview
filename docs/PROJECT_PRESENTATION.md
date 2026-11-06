# AI Interview Simulator — Project Presentation & Viva Defense Guide

A comprehensive architectural overview and presentation guide designed for project reviewers, interviewers, hackathon judges, and academic defense.

---

## 1. Project Title

**AI-Powered Resume-Driven Interview Simulator with Hybrid RAG Knowledge Grounding & Adaptive Progression**

---

## 2. Executive Summary & Value Proposition

The **AI Interview Simulator** is a production-grade web platform built to solve the core limitations of traditional interview preparation. By ingesting a job seeker's PDF resume and target job description, the system creates highly tailored, role-specific technical, HR, behavioral, and mixed interview practice sessions. 

Using an offline **Hybrid RAG Knowledge Retrieval Engine** (`LocalKnowledgeRetriever`), the platform eliminates LLM hallucinations by grounding questions in standard software engineering domain records. Candidate responses are evaluated across 5 quantitative scoring dimensions, and an **Adaptive Decision Engine** dynamically adjusts question difficulty in real time.

---

## 3. The Problem: Limitations of Current Preparation Tools

1. **Generic Question Repositories:** Standard platforms serve identical static questions to every candidate regardless of their specific resume, projects, or skill set.
2. **Superficial Feedback:** Existing automated tools evaluate answers primarily based on response length or simple keyword matching rather than technical correctness and conceptual depth.
3. **Static Difficulty Progression:** Traditional mock tests maintain fixed question order, failing to challenge strong candidates or support candidates struggling on fundamental concepts.
4. **Lack of Continuous Insights:** Job seekers rarely receive longitudinal analytics showing topic mastery trends or targeted weak-area remediation.

---

## 4. Proposed Solution & Key Innovations

| Feature | Generic Prompt Wrapper | AI Interview Simulator (Our System) |
| :--- | :--- | :--- |
| **Question Source** | Unbounded LLM generation | Grounded in PDF Resume + Job Description + Hybrid RAG |
| **Factual Reliability** | Prone to hallucinations | 15 Curated Domain Knowledge Modules (`LocalKnowledgeRetriever`) |
| **Answer Evaluation** | Pass/Fail or basic summary | 5-Dimensional Evidence Scoring (0.0 - 10.0) + Specific Feedback |
| **Interview Flow** | Fixed question sequence | Dynamic `AdaptiveDecisionEngine` (Escalate / Clarify / Reinforce) |
| **Voice Interaction** | Text only | Browser-native Speech-to-Text (STT) + Text-to-Speech (TTS) |
| **Candidate Coaching** | None | Personalized RAG AI Coach with Database User Isolation |
| **Exportable Artifacts**| None | Formatted Client-Side PDF Evaluation Reports (`html2canvas` + `jspdf`) |

---

## 5. System Architecture & Component Interaction

```text
                                  +---------------------------------------+
                                  |             React Frontend            |
                                  |  (Vite, Tailwind, Recharts, jsPDF)    |
                                  +-------------------+-------------------+
                                                      |
                                                      | REST API (Axios + JWT Bearer)
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
| (JWT / Bcrypt)   |                       | (Session State &   |                       | (Gemini/OpenAI/Mock  |
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

---

## 6. Core Technology Stack

- **Frontend:** React 18, Vite, Tailwind CSS, Lucide React Icons, Recharts, Axios, `html2canvas`, `jspdf`, Web Speech API (`webkitSpeechRecognition`, `window.speechSynthesis`).
- **Backend:** FastAPI, Python 3.11, Pydantic v2, SQLAlchemy ORM, Uvicorn ASGI Server.
- **Authentication:** JWT tokens (`python-jose`), password hashing (`passlib` with `bcrypt`).
- **Resume Processing:** `pdfminer.six` PDF text extraction.
- **AI Infrastructure:** Multi-provider adapter supporting Google Gemini (`gemini-2.5-flash` by default), OpenAI (`gpt-4o-mini` by default; override either with `AI_MODEL`), and offline `MockProvider`.
- **Knowledge RAG:** `LocalKnowledgeRetriever` with 15 domain knowledge modules.
- **Containerization:** Multi-stage Dockerfiles (`backend/Dockerfile`, `frontend/Dockerfile`), Nginx production static serving (`nginx.conf`), Docker Compose (`docker-compose.yml`).

---

## 7. AI & Hybrid RAG Workflow

1. **Text Extraction:** Ingests candidate PDF resume via `pdfminer.six`, extracting skill keywords and profile summary.
2. **Skill Normalization & Knowledge Lookup:** Candidate skill selection triggers `LocalKnowledgeRetriever`, which normalizes skill names (e.g. `react.js` → `react`, `postgres` → `postgresql`).
3. **Domain Record Filtering:** Loads domain records from `backend/app/data/knowledge/<skill>.json` matching the session difficulty band (`beginner`, `intermediate`, `advanced`).
4. **Prompt Context Injection:** Formats topic concepts, common mistakes, and standard references directly into the LLM system prompt.
5. **Grounded Question Generation:** LLM generates conceptual and practical questions constrained by retrieved domain records.

---

## 8. Multi-Dimensional Evidence-Based Evaluation

Every answer is evaluated across 5 quantitative dimensions:
- **Overall Score (`0.0 - 10.0`)**: Comprehensive quality rating.
- **Correctness (`0.0 - 10.0`)**: Accuracy of technical statements.
- **Relevance (`0.0 - 10.0`)**: Direct alignment with the asked question.
- **Technical Depth (`0.0 - 10.0`)**: Terminology usage and underlying mechanism explanation.
- **Communication Quality (`0.0 - 10.0`)**: Structure, conciseness, and clarity.

*Relevance Gate Guard:* Irrelevant answers (e.g., answering a Python question with historical trivia) receive low relevance scores (`< 3.0`), lowering the overall score and triggering a re-test follow-up question.

---

## 9. Adaptive Progression Flow

The `AdaptiveDecisionEngine` monitors candidate performance across questions:
- **Score >= 7.5 (Strong):** Escalates difficulty (e.g. Medium → Hard) and targets architectural or edge-case concepts.
- **5.0 <= Score < 7.5 (Moderate):** Maintains difficulty and issues targeted clarification follow-ups.
- **Score < 5.0 (Weak):** Provides constructive hint and issues fundamental reinforcement question.

---

## 10. Empirical Verification & Results

- **Backend Pytest Suite:** 110 Unit Tests executed — **110 Passed (100%)**
- **End-to-End Regression Suite (`regression_test.py`):** 123 E2E Assertions executed — **123 Passed (100%)**
- **Frontend Production Build:** `npm run build` executed cleanly — **0 compilation errors**
