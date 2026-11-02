# AI Interview Simulator — 5 to 7 Minute Live Demo Script

A step-by-step walkthrough script for presenting the **AI Interview Simulator** to project reviewers, interviewers, hackathon judges, or academic evaluators.

---

## Demo Overview & Schedule

| Step | Time | Demonstration Focus | Key Feature Highlighted |
| :---: | :---: | :--- | :--- |
| **1** | 0:00 - 0:45 | Login & Dashboard Overview | Secure JWT Auth & Candidate Dashboard Metrics |
| **2** | 0:45 - 1:45 | Resume Upload & Skill Extraction | `pdfminer.six` Parsing & Interactive Skill Selection |
| **3** | 1:45 - 2:30 | Interview Setup & Customization | Job Description Context & Hybrid RAG Grounding |
| **4** | 2:30 - 4:00 | Live Interview Room | Voice Input (STT) & Question Narration (TTS) |
| **5** | 4:00 - 5:00 | Evaluation & Adaptive Transition | 5-Dimensional Scoring & `AdaptiveDecisionEngine` |
| **6** | 5:00 - 6:00 | Evaluation Report & PDF Export | Client-side PDF Generation (`html2canvas` + `jspdf`) |
| **7** | 6:00 - 7:00 | Analytics & RAG AI Coach | Candidate Analytics & User-Isolated Coaching Chat |

---

### Step 1: User Login & Dashboard Overview (0:00 - 0:45)

- **WHAT TO SHOW:**
  Open the browser at `http://localhost:3000/login`. Log in with candidate credentials (`candidate@example.com` / `Password@123`). The app navigates to `/dashboard`. Show the metrics cards (Total Interviews, Average Score, Best Score) and recent session list.
- **WHAT TO SAY:**
  *"Welcome to the AI Interview Simulator. We start on the secure candidate dashboard. The platform uses JWT token authentication and bcrypt password hashing. Here candidates immediately see their aggregated metrics, performance trends, and past interview history."*
- **WHY IT MATTERS:**
  Demonstrates enterprise security, user isolation, and clean UI navigation right from launch.

---

### Step 2: Resume Upload & Skill Extraction (0:45 - 1:45)

- **WHAT TO SHOW:**
  Click **"Start New Interview"** to navigate to `/interview/setup`. Click **"Upload Resume (PDF)"** and upload a sample technical resume (`sample_resume.pdf`). The system processes the document and displays extracted skill badges (e.g. `Python`, `FastAPI`, `React`, `Docker`, `PostgreSQL`). Select `Python` and `FastAPI` as focus skills.
- **WHAT TO SAY:**
  *"Instead of serving static, generic questions, our platform parses the candidate's actual PDF resume using `pdfminer.six`. It extracts technologies and allows the candidate to select specific skill badges to focus on during this session."*
- **WHY IT MATTERS:**
  Solves the generic question problem by tailoring the session to the candidate's actual background.

---

### Step 3: Interview Setup & Customization (1:45 - 2:30)

- **WHAT TO SHOW:**
  Configure the interview parameters: Select **Technical Interview**, **Intermediate Experience**, **Medium Difficulty**, **3 Questions**, and paste a target job description into the text area. Click **"Launch Interview Session"**.
- **WHAT TO SAY:**
  *"Candidates can customize interview type, experience level, difficulty, language, and paste target job descriptions. When we click launch, our backend's `LocalKnowledgeRetriever` fetches curated domain knowledge records for Python and FastAPI to ground the AI model and prevent hallucinations."*
- **WHY IT MATTERS:**
  Highlights Hybrid RAG knowledge grounding and multi-parameter session customization.

---

### Step 4: Live Interview Room & Voice Interaction (2:30 - 4:00)

- **WHAT TO SHOW:**
  The app navigates to `/interview/room/:id`. Click the **Speaker Icon** to demonstrate Text-to-Speech (TTS) reading the question aloud. Click **"Start Voice Input"** (Microphone button) and speak an answer (e.g. *"FastAPI uses Pydantic for data validation and Starlette for routing, leveraging Python async def for non-blocking concurrency"*). Show real-time transcript appearing in the text box.
- **WHAT TO SAY:**
  *"In the interactive interview room, we integrate two browser-native voice technologies: Text-to-Speech for question narration and Speech-to-Text for hands-free voice answer input. Candidates can speak naturally just like in a real interview."*
- **WHY IT MATTERS:**
  Simulates a realistic, spoken interview environment without requiring third-party audio API fees.

---

### Step 5: Answer Evaluation & Adaptive Transition (4:00 - 5:00)

- **WHAT TO SHOW:**
  Click **"Submit Answer"**. The UI displays the real-time evaluation card with scores across Overall, Correctness, Relevance, Technical Depth, and Communication Quality, alongside constructive feedback. Click **"Next Question"** to show the `AdaptiveDecisionEngine` serving a deeper follow-up question based on the candidate's strong score.
- **WHAT TO SAY:**
  *"Our evaluation engine rates answers on 5 distinct dimensions from 0 to 10. Notice how answer quality—not length—drives scoring. Because our candidate scored high on FastAPI fundamentals, our `AdaptiveDecisionEngine` automatically escalated difficulty to ask a deeper question."*
- **WHY IT MATTERS:**
  Demonstrates evidence-based multi-dimensional scoring and dynamic real-time interview adaptation.

---

### Step 6: Session Completion & PDF Report Export (5:00 - 6:00)

- **WHAT TO SHOW:**
  Answer the remaining questions to complete the session. The app navigates to `/interview/evaluation/:id`. Scroll through the overall session score ring, strengths, weaknesses, and per-question breakdowns. Click **"Download PDF Report"**. Open the downloaded PDF file showing formatted evaluation output.
- **WHAT TO SAY:**
  *"Upon completing the interview, the candidate receives a comprehensive evaluation summary. Using `html2canvas` and `jspdf`, candidates can export a professional PDF report to keep for their records or review offline."*
- **WHY IT MATTERS:**
  Provides candidates with persistent, exportable artifacts to measure their progress.

---

### Step 7: Analytics & RAG AI Coach (6:00 - 7:00)

- **WHAT TO SHOW:**
  Navigate to `/analytics` to show Recharts performance trend graphs over time and topic mastery lists. Then navigate to `/coach` to show the AI Coach dashboard. Click **"Generate Weak-Topic Practice Question"** and ask a question in the AI Coach chat box.
- **WHAT TO SAY:**
  *"Finally, the candidate can review longitudinal analytics and interact with their personalized RAG AI Coach. The coach tracks candidate weak areas across sessions, generates targeted practice questions, and provides isolated guidance that never leaks data across candidate accounts."*
- **WHY IT MATTERS:**
  Completes the continuous learning loop, reinforcing candidate growth beyond a single interview session.
