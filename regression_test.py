"""
End-to-end regression test suite for AI Interview Simulator.
Tests all features: auth, profile, interview flow, customization,
evaluation, analytics, authorization enforcement.
Run with: backend/venv/Scripts/python.exe regression_test.py
"""
import json
import os
import sys
import time
import uuid
import tempfile
import requests

if hasattr(sys.stdout, 'reconfigure'):
    sys.stdout.reconfigure(encoding='utf-8')

BASE = "http://127.0.0.1:8000/api/v1"
PASS = "\033[92mPASS\033[0m"
FAIL = "\033[91mFAIL\033[0m"
SKIP = "\033[93mSKIP\033[0m"

results = []

def record(feature, test, status, notes=""):
    results.append((feature, test, status, notes))
    icon = {"PASS": "✅", "FAIL": "❌", "SKIP": "⚠️ "}[status]
    print(f"  {icon} [{status}] {feature} » {test}" + (f": {notes}" if notes else ""))

def check(feature, test, condition, success_notes="", fail_notes=""):
    if condition:
        record(feature, test, "PASS", success_notes)
        return True
    else:
        record(feature, test, "FAIL", fail_notes)
        return False

def print_summary():
    print("\n" + "="*70)
    print("REGRESSION TEST RESULTS")
    print("="*70)
    
    total = len(results)
    passed = sum(1 for r in results if r[2] == "PASS")
    failed = sum(1 for r in results if r[2] == "FAIL")
    skipped = sum(1 for r in results if r[2] == "SKIP")
    
    # Print full table
    print(f"\n{'Feature':<28} {'Test':<50} {'Result':<6} {'Notes'}")
    print("-"*130)
    for feature, test, status, notes in results:
        icon = "✅" if status == "PASS" else ("❌" if status == "FAIL" else "⚠️ ")
        print(f"{feature:<28} {test:<50} {icon} {status:<4} {notes[:60]}")
    
    print(f"\n{'='*70}")
    print(f"TOTAL : {total}")
    print(f"PASSED: {passed}")
    print(f"FAILED: {failed}")
    print(f"SKIPPED: {skipped}")
    print(f"{'='*70}")
    
    if failed > 0:
        print("\nFAILED TESTS:")
        for feature, test, status, notes in results:
            if status == "FAIL":
                print(f"  ❌ {feature} » {test}: {notes}")

# ─────────────────────────────────────────────────────────────
# 1. HEALTH CHECKS
# ─────────────────────────────────────────────────────────────
print("\n── 1. Health Checks ──────────────────────────────────")
try:
    r = requests.get("http://127.0.0.1:8000/health", timeout=5)
    check("Health", "GET /health returns 200", r.status_code == 200, f"status={r.status_code}, body={r.json()}")
    check("Health", "/health body has status=ok", r.json().get("status") == "ok")
except Exception as e:
    record("Health", "GET /health", "FAIL", str(e))

try:
    r = requests.get(f"{BASE}/health", timeout=5)
    check("Health", "GET /api/v1/health returns 200", r.status_code == 200, f"status={r.status_code}")
except Exception as e:
    record("Health", "GET /api/v1/health", "FAIL", str(e))

# ─────────────────────────────────────────────────────────────
# 2. AUTHENTICATION — REGISTRATION
# ─────────────────────────────────────────────────────────────
print("\n── 2. Registration ───────────────────────────────────")
uid = uuid.uuid4().hex[:8]
TEST_EMAIL = f"regtest_{uid}@example.com"
TEST_PW = "TestPass@123"
TEST_NAME = "Reg Tester"

try:
    r = requests.post(f"{BASE}/auth/register", json={"email": TEST_EMAIL, "password": TEST_PW, "full_name": TEST_NAME}, timeout=5)
    check("Auth", "Register new user → 201", r.status_code == 201, f"status={r.status_code}")
    body = r.json()
    check("Auth", "Register response has id", "id" in body)
    check("Auth", "Register response has email", body.get("email") == TEST_EMAIL)
    check("Auth", "Register response has full_name", body.get("full_name") == TEST_NAME)
except Exception as e:
    record("Auth", "Register", "FAIL", str(e))

# Duplicate registration
try:
    r = requests.post(f"{BASE}/auth/register", json={"email": TEST_EMAIL, "password": TEST_PW, "full_name": TEST_NAME}, timeout=5)
    check("Auth", "Duplicate register → 400", r.status_code == 400, f"status={r.status_code}")
except Exception as e:
    record("Auth", "Duplicate register", "FAIL", str(e))

# ─────────────────────────────────────────────────────────────
# 3. AUTHENTICATION — LOGIN
# ─────────────────────────────────────────────────────────────
print("\n── 3. Login & JWT ────────────────────────────────────")
TOKEN = None
try:
    r = requests.post(f"{BASE}/auth/login", data={"username": TEST_EMAIL, "password": TEST_PW}, timeout=5)
    check("Auth", "Login → 200", r.status_code == 200, f"status={r.status_code}")
    body = r.json()
    TOKEN = body.get("access_token")
    check("Auth", "Login returns access_token", bool(TOKEN))
    check("Auth", "Login returns token_type=bearer", body.get("token_type") == "bearer")
except Exception as e:
    record("Auth", "Login", "FAIL", str(e))

# Wrong password
try:
    r = requests.post(f"{BASE}/auth/login", data={"username": TEST_EMAIL, "password": "WrongPass999"}, timeout=5)
    check("Auth", "Login with wrong password → 400", r.status_code == 400, f"status={r.status_code}")
except Exception as e:
    record("Auth", "Wrong password login", "FAIL", str(e))

# Unauthenticated access
try:
    r = requests.get(f"{BASE}/interviews/", timeout=5)
    check("Auth", "Unauthenticated request → 401/403", r.status_code in (401, 403), f"status={r.status_code}")
except Exception as e:
    record("Auth", "Unauthenticated access", "FAIL", str(e))

if not TOKEN:
    print("\n  ⛔ No token — remaining tests will be BLOCKED.")
    for label in ["Profile", "Interview Customization", "Interview Flow", "Evaluation", "Analytics", "Authorization"]:
        record(label, "All tests", "SKIP", "No auth token available")
    # Print summary and exit
    print_summary()
    sys.exit(1)

HEADERS = {"Authorization": f"Bearer {TOKEN}"}

# ─────────────────────────────────────────────────────────────
# 4. PROFILE — GET /auth/me
# ─────────────────────────────────────────────────────────────
print("\n── 4. Profile — GET /auth/me ─────────────────────────")
try:
    r = requests.get(f"{BASE}/auth/me", headers=HEADERS, timeout=5)
    check("Profile", "GET /auth/me → 200", r.status_code == 200, f"status={r.status_code}")
    body = r.json()
    check("Profile", "/auth/me returns email", body.get("email") == TEST_EMAIL)
    check("Profile", "/auth/me returns full_name", body.get("full_name") == TEST_NAME)
    check("Profile", "/auth/me returns id", "id" in body)
    check("Profile", "/auth/me returns is_active=true", body.get("is_active") is True)
except Exception as e:
    record("Profile", "GET /auth/me", "FAIL", str(e))

# ─────────────────────────────────────────────────────────────
# 5. PROFILE — UPDATE NAME
# ─────────────────────────────────────────────────────────────
print("\n── 5. Profile — Update Name ──────────────────────────")
NEW_NAME = "Updated Tester"
try:
    r = requests.put(f"{BASE}/auth/me", json={"full_name": NEW_NAME}, headers=HEADERS, timeout=5)
    check("Profile", "PUT /auth/me update name → 200", r.status_code == 200, f"status={r.status_code}")
    body = r.json()
    check("Profile", "Name updated in response", body.get("full_name") == NEW_NAME)
    # Verify persistence via GET
    r2 = requests.get(f"{BASE}/auth/me", headers=HEADERS, timeout=5)
    check("Profile", "Name persists after GET /auth/me", r2.json().get("full_name") == NEW_NAME)
except Exception as e:
    record("Profile", "PUT /auth/me name update", "FAIL", str(e))

# ─────────────────────────────────────────────────────────────
# 6. PROFILE — PASSWORD CHANGE VALIDATION
# ─────────────────────────────────────────────────────────────
print("\n── 6. Profile — Password Change Validation ───────────")

# Wrong current password
try:
    r = requests.put(f"{BASE}/auth/me", json={"current_password": "WrongOld!", "new_password": "NewPass@999"}, headers=HEADERS, timeout=5)
    check("Profile", "Wrong current_password → 400", r.status_code == 400, f"status={r.status_code}, detail={r.json().get('detail')}")
except Exception as e:
    record("Profile", "Wrong current_password", "FAIL", str(e))

# new_password without current_password
try:
    r = requests.put(f"{BASE}/auth/me", json={"new_password": "NewPass@999"}, headers=HEADERS, timeout=5)
    check("Profile", "new_password without current_password → 400", r.status_code == 400, f"status={r.status_code}")
except Exception as e:
    record("Profile", "Missing current_password", "FAIL", str(e))

# Valid password change
NEW_PW = "NewPass@777"
try:
    r = requests.put(f"{BASE}/auth/me", json={"current_password": TEST_PW, "new_password": NEW_PW}, headers=HEADERS, timeout=5)
    check("Profile", "Valid password change → 200", r.status_code == 200, f"status={r.status_code}")
    # Verify old password no longer works
    r2 = requests.post(f"{BASE}/auth/login", data={"username": TEST_EMAIL, "password": TEST_PW}, timeout=5)
    check("Profile", "Old password rejected after change → 400", r2.status_code == 400)
    # Verify new password works
    r3 = requests.post(f"{BASE}/auth/login", data={"username": TEST_EMAIL, "password": NEW_PW}, timeout=5)
    check("Profile", "New password accepted → 200", r3.status_code == 200)
    if r3.status_code == 200:
        TOKEN = r3.json().get("access_token", TOKEN)
        HEADERS = {"Authorization": f"Bearer {TOKEN}"}
except Exception as e:
    record("Profile", "Password change flow", "FAIL", str(e))

# PUT /auth/me without auth
try:
    r = requests.put(f"{BASE}/auth/me", json={"full_name": "Hacker"}, timeout=5)
    check("Profile", "PUT /auth/me without token → 401/403", r.status_code in (401, 403), f"status={r.status_code}")
except Exception as e:
    record("Profile", "Unauthenticated PUT /auth/me", "FAIL", str(e))

# ─────────────────────────────────────────────────────────────
# 7. INTERVIEW CUSTOMIZATION — start 3 interviews with different types
# ─────────────────────────────────────────────────────────────
print("\n── 7. Interview Customization ────────────────────────")

SESSION_IDS = {}
INTERVIEW_CONFIGS = [
    {"label": "Technical/Easy/3q",  "interview_type": "Technical",  "job_role": "Python Developer",      "experience_level": "Intermediate", "difficulty": "Easy",   "question_count": "3"},
    {"label": "HR/Medium/3q",       "interview_type": "HR",         "job_role": "Product Manager",       "experience_level": "Beginner",     "difficulty": "Medium", "question_count": "3"},
    {"label": "Mixed/Hard/3q",      "interview_type": "Mixed",      "job_role": "Full Stack Engineer",   "experience_level": "Advanced",     "difficulty": "Hard",   "question_count": "3"},
    {"label": "Behavioral/Easy/3q", "interview_type": "Behavioral", "job_role": "Data Analyst",          "experience_level": "Intermediate", "difficulty": "Easy",   "question_count": "3"},
]

for cfg in INTERVIEW_CONFIGS:
    label = cfg["label"]
    try:
        data = {k: v for k, v in cfg.items() if k != "label"}
        r = requests.post(f"{BASE}/interviews/start", data=data, headers=HEADERS, timeout=30)
        ok = r.status_code == 201
        check("Interview Customization", f"Start interview ({label}) → 201", ok, f"status={r.status_code}" + ("" if ok else f", body={r.text[:200]}"))
        if ok:
            body = r.json()
            sid = body.get("session_id")
            SESSION_IDS[label] = sid
            check("Interview Customization", f"({label}) returns session_id", bool(sid))
            q = body.get("question")
            check("Interview Customization", f"({label}) returns first question", bool(q and q.get("text")), f"q={q}")
    except Exception as e:
        record("Interview Customization", f"Start ({label})", "FAIL", str(e))

# Test job description (optional field)
try:
    data = {
        "interview_type": "Technical",
        "job_role": "Backend Engineer",
        "experience_level": "Advanced",
        "difficulty": "Hard",
        "question_count": "3",
        "job_description": "Build scalable REST APIs using FastAPI and PostgreSQL.",
    }
    r = requests.post(f"{BASE}/interviews/start", data=data, headers=HEADERS, timeout=30)
    check("Interview Customization", "With job_description → 201", r.status_code == 201, f"status={r.status_code}")
    if r.status_code == 201:
        SESSION_IDS["JD"] = r.json().get("session_id")
except Exception as e:
    record("Interview Customization", "With job_description", "FAIL", str(e))

# Test resume PDF upload
try:
    # Create a minimal valid PDF in-memory
    pdf_content = b"""%PDF-1.4
1 0 obj<</Type/Catalog/Pages 2 0 R>>endobj
2 0 obj<</Type/Pages/Kids[3 0 R]/Count 1>>endobj
3 0 obj<</Type/Page/MediaBox[0 0 612 792]/Parent 2 0 R/Contents 4 0 R/Resources<</Font<</F1 5 0 R>>>>>>endobj
4 0 obj<</Length 44>>stream
BT /F1 12 Tf 100 700 Td (Python Developer Resume) Tj ET
endstream endobj
5 0 obj<</Type/Font/Subtype/Type1/BaseFont/Helvetica>>endobj
xref
0 6
0000000000 65535 f
0000000009 00000 n
0000000058 00000 n
0000000115 00000 n
0000000274 00000 n
0000000370 00000 n
trailer<</Size 6/Root 1 0 R>>
startxref
441
%%EOF"""
    data = {
        "interview_type": "Technical",
        "job_role": "Python Developer",
        "experience_level": "Intermediate",
        "difficulty": "Medium",
        "question_count": "3",
    }
    files = {"resume": ("resume.pdf", pdf_content, "application/pdf")}
    r = requests.post(f"{BASE}/interviews/start", data=data, files=files, headers=HEADERS, timeout=30)
    check("Interview Customization", "Resume PDF upload → 201", r.status_code == 201, f"status={r.status_code}" + ("" if r.status_code == 201 else f", body={r.text[:300]}"))
    if r.status_code == 201:
        SESSION_IDS["Resume"] = r.json().get("session_id")
except Exception as e:
    record("Interview Customization", "Resume PDF upload", "FAIL", str(e))

# Test non-PDF file rejection
try:
    data = {"interview_type": "Technical", "job_role": "Dev", "experience_level": "Intermediate", "difficulty": "Easy", "question_count": "3"}
    files = {"resume": ("bad.txt", b"Not a PDF", "text/plain")}
    r = requests.post(f"{BASE}/interviews/start", data=data, files=files, headers=HEADERS, timeout=10)
    check("Interview Customization", "Non-PDF resume → 400", r.status_code == 400, f"status={r.status_code}")
except Exception as e:
    record("Interview Customization", "Non-PDF rejection", "FAIL", str(e))

# Test oversized PDF rejection (>2 MiB)
try:
    big_pdf = b"%PDF-1.4\n" + b"x" * (2 * 1024 * 1024 + 1)
    data = {"interview_type": "Technical", "job_role": "Dev", "experience_level": "Intermediate", "difficulty": "Easy", "question_count": "3"}
    files = {"resume": ("big.pdf", big_pdf, "application/pdf")}
    r = requests.post(f"{BASE}/interviews/start", data=data, files=files, headers=HEADERS, timeout=10)
    check("Interview Customization", "Oversized PDF → 400", r.status_code == 400, f"status={r.status_code}")
except Exception as e:
    record("Interview Customization", "Oversized PDF rejection", "FAIL", str(e))

# Test job_description length > 2000 chars
try:
    data = {"interview_type": "Technical", "job_role": "Dev", "experience_level": "Intermediate", "difficulty": "Easy", "question_count": "3", "job_description": "A" * 2001}
    r = requests.post(f"{BASE}/interviews/start", data=data, headers=HEADERS, timeout=10)
    check("Interview Customization", "JD > 2000 chars → 400", r.status_code == 400, f"status={r.status_code}")
except Exception as e:
    record("Interview Customization", "JD length rejection", "FAIL", str(e))

# ─────────────────────────────────────────────────────────────
# 8. INTERVIEW FLOW — complete a full 3-question interview
# ─────────────────────────────────────────────────────────────
print("\n── 8. Interview Flow ─────────────────────────────────")

COMPLETE_SESSION_ID = SESSION_IDS.get("Technical/Easy/3q")
if not COMPLETE_SESSION_ID:
    record("Interview Flow", "All flow tests", "SKIP", "No Technical session was created")
else:
    # Verify session loads
    try:
        r = requests.get(f"{BASE}/interviews/{COMPLETE_SESSION_ID}", headers=HEADERS, timeout=5)
        check("Interview Flow", "GET /interviews/{id} → 200", r.status_code == 200, f"status={r.status_code}")
        body = r.json()
        check("Interview Flow", "Session has correct job_role", body.get("job_role") == "Python Developer")
        check("Interview Flow", "Session has status=in_progress", body.get("status") == "in_progress")
        check("Interview Flow", "Session has question_count=3", body.get("question_count") == 3)
        check("Interview Flow", "Session answered_count=0", body.get("answered_count") == 0)
    except Exception as e:
        record("Interview Flow", "GET session", "FAIL", str(e))

    # Get next question
    try:
        r = requests.get(f"{BASE}/interviews/{COMPLETE_SESSION_ID}/next", headers=HEADERS, timeout=10)
        check("Interview Flow", "GET /next → 200", r.status_code == 200, f"status={r.status_code}")
        body = r.json()
        q = body.get("question", {})
        check("Interview Flow", "First question has text", bool(q.get("text")))
        check("Interview Flow", "First question has question_id", q.get("question_id") == 1)
    except Exception as e:
        record("Interview Flow", "GET /next Q1", "FAIL", str(e))

    # Submit 3 answers
    EVAL_RESULTS = []
    ANSWERS = [
        "I would use FastAPI with async endpoints, SQLAlchemy for ORM, and PostgreSQL for persistence. I would structure the code with layered architecture: routes, services, models.",
        "I handle errors using try-except blocks, structured logging with contextual information, and proper HTTP status codes in the API responses.",
        "For caching I would use Redis with appropriate TTL values and cache invalidation strategies, combined with database indexes for query optimization."
    ]
    for i, answer in enumerate(ANSWERS, 1):
        try:
            r = requests.post(f"{BASE}/interviews/{COMPLETE_SESSION_ID}/answer", json={"answer": answer}, headers=HEADERS, timeout=15)
            ok = r.status_code == 200
            check("Interview Flow", f"Submit answer Q{i} → 200", ok, f"status={r.status_code}")
            if ok:
                body = r.json()
                ev = body.get("evaluation", {})
                EVAL_RESULTS.append(ev)
                check("Interview Flow", f"Q{i} evaluation has score", isinstance(ev.get("score"), (int, float)), f"score={ev.get('score')}")
                check("Interview Flow", f"Q{i} evaluation has feedback", bool(ev.get("feedback")))
                check("Interview Flow", f"Q{i} evaluation score in 0-10", 0 <= (ev.get("score") or 0) <= 10)
        except Exception as e:
            record("Interview Flow", f"Submit answer Q{i}", "FAIL", str(e))

    # After all answers, verify session is completed
    try:
        r = requests.get(f"{BASE}/interviews/{COMPLETE_SESSION_ID}", headers=HEADERS, timeout=5)
        body = r.json()
        check("Interview Flow", "Session status=completed after all answers", body.get("status") == "completed", f"status={body.get('status')}")
        check("Interview Flow", "Session answered_count=3", body.get("answered_count") == 3)
    except Exception as e:
        record("Interview Flow", "Session completion check", "FAIL", str(e))

    # Submit extra answer on completed session (should be rejected)
    try:
        r = requests.post(f"{BASE}/interviews/{COMPLETE_SESSION_ID}/answer", json={"answer": "extra answer"}, headers=HEADERS, timeout=5)
        check("Interview Flow", "Extra answer on completed session → 400", r.status_code == 400, f"status={r.status_code}")
    except Exception as e:
        record("Interview Flow", "Extra answer rejection", "FAIL", str(e))

# ─────────────────────────────────────────────────────────────
# 9. EVALUATION
# ─────────────────────────────────────────────────────────────
print("\n── 9. Evaluation ─────────────────────────────────────")

if COMPLETE_SESSION_ID:
    try:
        r = requests.get(f"{BASE}/interviews/{COMPLETE_SESSION_ID}/evaluation", headers=HEADERS, timeout=10)
        check("Evaluation", "GET /evaluation → 200", r.status_code == 200, f"status={r.status_code}")
        body = r.json()
        check("Evaluation", "Has overall_score", isinstance(body.get("overall_score"), (int, float)), f"score={body.get('overall_score')}")
        check("Evaluation", "overall_score in 0-10", 0 <= (body.get("overall_score") or 0) <= 10)
        check("Evaluation", "Has overall_correctness", body.get("overall_correctness") is not None)
        check("Evaluation", "Has overall_relevance", body.get("overall_relevance") is not None)
        check("Evaluation", "Has overall_technical_depth", body.get("overall_technical_depth") is not None)
        check("Evaluation", "Has overall_communication_quality", body.get("overall_communication_quality") is not None)
        check("Evaluation", "Has feedback string", bool(body.get("feedback")))
        check("Evaluation", "Has strengths list", isinstance(body.get("strengths"), list))
        check("Evaluation", "Has weaknesses list", isinstance(body.get("weaknesses"), list))
        pqe = body.get("per_question_evaluations", [])
        check("Evaluation", "Has per_question_evaluations", isinstance(pqe, list) and len(pqe) == 3, f"len={len(pqe)}")
        check("Evaluation", "per_question_evaluations have scores", all("score" in e for e in pqe))
        check("Evaluation", "Has job_role", body.get("job_role") == "Python Developer")
        check("Evaluation", "Has question_count=3", body.get("question_count") == 3)
        check("Evaluation", "Has answered_count=3", body.get("answered_count") == 3)
    except Exception as e:
        record("Evaluation", "GET /evaluation", "FAIL", str(e))

    # Evaluation on nonexistent session
    try:
        r = requests.get(f"{BASE}/interviews/99999/evaluation", headers=HEADERS, timeout=5)
        check("Evaluation", "Nonexistent session evaluation → 404", r.status_code == 404, f"status={r.status_code}")
    except Exception as e:
        record("Evaluation", "Nonexistent evaluation", "FAIL", str(e))

# ─────────────────────────────────────────────────────────────
# 10. COMPLETE A 2nd AND 3rd INTERVIEW (for analytics)
# ─────────────────────────────────────────────────────────────
print("\n── 10. Complete additional interviews for analytics ──")

def complete_interview(session_id, num_questions=3):
    answers = [
        "This is a comprehensive answer covering the main aspects of the question with technical depth and clear communication.",
        "I would approach this systematically, considering all stakeholders and using data-driven decision making for optimal outcomes.",
        "My experience with this area includes practical implementations and I have resolved similar challenges in production environments.",
    ]
    for i in range(num_questions):
        ans = answers[i % len(answers)]
        r = requests.post(f"{BASE}/interviews/{session_id}/answer", json={"answer": ans}, headers=HEADERS, timeout=15)
        if r.status_code != 200:
            return False
    return True

for label in ["HR/Medium/3q", "Mixed/Hard/3q"]:
    sid = SESSION_IDS.get(label)
    if sid:
        try:
            ok = complete_interview(sid, 3)
            check("Interview Flow", f"Complete {label} interview", ok, f"session_id={sid}")
        except Exception as e:
            record("Interview Flow", f"Complete {label}", "FAIL", str(e))

# ─────────────────────────────────────────────────────────────
# 11. ANALYTICS
# ─────────────────────────────────────────────────────────────
print("\n── 11. Analytics ─────────────────────────────────────")
try:
    r = requests.get(f"{BASE}/interviews/analytics", headers=HEADERS, timeout=10)
    check("Analytics", "GET /analytics → 200", r.status_code == 200, f"status={r.status_code}")
    body = r.json()
    check("Analytics", "Has total_interviews", isinstance(body.get("total_interviews"), int), f"total={body.get('total_interviews')}")
    check("Analytics", "Has completed_interviews", isinstance(body.get("completed_interviews"), int))
    check("Analytics", "completed_interviews >= 3", (body.get("completed_interviews") or 0) >= 3, f"completed={body.get('completed_interviews')}")
    check("Analytics", "Has average_score (numeric or None)", body.get("average_score") is None or isinstance(body.get("average_score"), (int, float)))
    check("Analytics", "Has best_score", "best_score" in body)
    check("Analytics", "Has latest_score", "latest_score" in body)
    check("Analytics", "Has average_correctness", "average_correctness" in body)
    check("Analytics", "Has average_relevance", "average_relevance" in body)
    check("Analytics", "Has average_technical_depth", "average_technical_depth" in body)
    check("Analytics", "Has average_communication_quality", "average_communication_quality" in body)
    check("Analytics", "Has strengths list", isinstance(body.get("strengths"), list))
    check("Analytics", "Has weaknesses list", isinstance(body.get("weaknesses"), list))
    check("Analytics", "Has trend list", isinstance(body.get("trend"), list))
    check("Analytics", "trend has entries", len(body.get("trend", [])) >= 3, f"len={len(body.get('trend', []))}")
    check("Analytics", "Has recent_interviews list", isinstance(body.get("recent_interviews"), list))
    recent = body.get("recent_interviews", [])
    if recent:
        r0 = recent[0]
        check("Analytics", "recent_interviews item has job_role", "job_role" in r0)
        check("Analytics", "recent_interviews item has score", "score" in r0)
        check("Analytics", "recent_interviews item has date", "date" in r0)
except Exception as e:
    record("Analytics", "GET /analytics", "FAIL", str(e))

# ─────────────────────────────────────────────────────────────
# 12. DASHBOARD — LIST INTERVIEWS
# ─────────────────────────────────────────────────────────────
print("\n── 12. Dashboard — List Interviews ───────────────────")
try:
    r = requests.get(f"{BASE}/interviews/", headers=HEADERS, timeout=5)
    check("Dashboard", "GET /interviews/ → 200", r.status_code == 200, f"status={r.status_code}")
    body = r.json()
    check("Dashboard", "Has interviews list", isinstance(body.get("interviews"), list))
    check("Dashboard", "Has total count", isinstance(body.get("total"), int))
    interviews_list = body.get("interviews", [])
    check("Dashboard", "At least 3 sessions in history", len(interviews_list) >= 3, f"count={len(interviews_list)}")
    if interviews_list:
        s0 = interviews_list[0]
        check("Dashboard", "Session has id", "id" in s0)
        check("Dashboard", "Session has job_role", "job_role" in s0)
        check("Dashboard", "Session has status", "status" in s0)
        check("Dashboard", "Session has question_count", "question_count" in s0)
        check("Dashboard", "Session has answered_count", "answered_count" in s0)
        check("Dashboard", "Session has created_at", "created_at" in s0)
    completed = [s for s in interviews_list if s.get("status") == "completed"]
    check("Dashboard", "Completed sessions visible", len(completed) >= 3, f"completed={len(completed)}")
except Exception as e:
    record("Dashboard", "GET /interviews/", "FAIL", str(e))

# ─────────────────────────────────────────────────────────────
# 13. AUTHORIZATION — Cross-user isolation
# ─────────────────────────────────────────────────────────────
print("\n── 13. Authorization / Cross-User Isolation ──────────")

# Create a second user
uid2 = uuid.uuid4().hex[:8]
EMAIL2 = f"user2_{uid2}@example.com"
PW2 = "SecondUser@456"
TOKEN2 = None

try:
    r = requests.post(f"{BASE}/auth/register", json={"email": EMAIL2, "password": PW2, "full_name": "User Two"}, timeout=5)
    r2 = requests.post(f"{BASE}/auth/login", data={"username": EMAIL2, "password": PW2}, timeout=5)
    TOKEN2 = r2.json().get("access_token")
    check("Authorization", "Second user registered and logged in", bool(TOKEN2))
except Exception as e:
    record("Authorization", "Create second user", "FAIL", str(e))

if TOKEN2 and COMPLETE_SESSION_ID:
    H2 = {"Authorization": f"Bearer {TOKEN2}"}
    try:
        r = requests.get(f"{BASE}/interviews/{COMPLETE_SESSION_ID}", headers=H2, timeout=5)
        check("Authorization", "User2 cannot GET user1's session → 404", r.status_code == 404, f"status={r.status_code}, body={r.text[:100]}")
    except Exception as e:
        record("Authorization", "Cross-user session access", "FAIL", str(e))

    try:
        r = requests.post(f"{BASE}/interviews/{COMPLETE_SESSION_ID}/answer", json={"answer": "hack"}, headers=H2, timeout=5)
        check("Authorization", "User2 cannot answer user1's session → 404", r.status_code == 404, f"status={r.status_code}")
    except Exception as e:
        record("Authorization", "Cross-user answer submit", "FAIL", str(e))

    try:
        r = requests.get(f"{BASE}/interviews/{COMPLETE_SESSION_ID}/evaluation", headers=H2, timeout=5)
        check("Authorization", "User2 cannot GET user1's evaluation → 404", r.status_code == 404, f"status={r.status_code}")
    except Exception as e:
        record("Authorization", "Cross-user evaluation access", "FAIL", str(e))

    try:
        r = requests.get(f"{BASE}/auth/me", headers=H2, timeout=5)
        check("Authorization", "User2 profile is isolated", r.json().get("email") == EMAIL2, f"email={r.json().get('email')}")
    except Exception as e:
        record("Authorization", "Profile isolation", "FAIL", str(e))

# ─────────────────────────────────────────────────────────────
# 14. EDGE CASES
# ─────────────────────────────────────────────────────────────
print("\n── 14. Edge Cases ────────────────────────────────────")

# Interview with no answers → evaluation should 404
try:
    data = {"interview_type": "Technical", "job_role": "Dev", "experience_level": "Intermediate", "difficulty": "Easy", "question_count": "3"}
    r = requests.post(f"{BASE}/interviews/start", data=data, headers=HEADERS, timeout=15)
    if r.status_code == 201:
        new_sid = r.json().get("session_id")
        r2 = requests.get(f"{BASE}/interviews/{new_sid}/evaluation", headers=HEADERS, timeout=5)
        check("Edge Cases", "Evaluation on unanswered session → 404", r2.status_code == 404, f"status={r2.status_code}")
except Exception as e:
    record("Edge Cases", "Unanswered session evaluation", "FAIL", str(e))

# Empty answer submission
try:
    if COMPLETE_SESSION_ID:
        # Use a fresh session
        data = {"interview_type": "Technical", "job_role": "Dev", "experience_level": "Intermediate", "difficulty": "Easy", "question_count": "3"}
        r = requests.post(f"{BASE}/interviews/start", data=data, headers=HEADERS, timeout=15)
        if r.status_code == 201:
            sid = r.json().get("session_id")
            r2 = requests.post(f"{BASE}/interviews/{sid}/answer", json={"answer": ""}, headers=HEADERS, timeout=5)
            # Empty answer is technically allowed by backend (score=0), just verify it doesn't crash
            check("Edge Cases", "Empty answer submission does not 500", r2.status_code != 500, f"status={r2.status_code}")
except Exception as e:
    record("Edge Cases", "Empty answer", "FAIL", str(e))

# Access nonexistent session
try:
    r = requests.get(f"{BASE}/interviews/99999999", headers=HEADERS, timeout=5)
    check("Edge Cases", "Nonexistent session GET → 404", r.status_code == 404, f"status={r.status_code}")
except Exception as e:
    record("Edge Cases", "Nonexistent session", "FAIL", str(e))

# ─────────────────────────────────────────────────────────────
# SUMMARY
# ─────────────────────────────────────────────────────────────
print_summary()
failed = sum(1 for r in results if r[2] == "FAIL")
sys.exit(0 if failed == 0 else 1)
