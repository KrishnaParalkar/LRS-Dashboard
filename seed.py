"""
Course Seed Data Generator
Generates realistic xAPI statements for 30 users with varied outcomes:
- SOP_ALIGNED - passed on 1st attempt
- SOP_INCONSISTENT → retry → SOP_ALIGNED (passed on 2nd attempt)  
- SOP_INCONSISTENT → retry → SOP_INCONSISTENT (failed after 2 attempts)
- SOP_DEVIATION - immediate failure

Flow: Course Start → 3 DPs → 3 GMs → Assessment → Result
"""

import os
import httpx
import json
import random
import uuid
import datetime
import base64
import argparse
from dotenv import load_dotenv

load_dotenv()

parser = argparse.ArgumentParser(description="Generate and send xAPI statements.")
parser.add_argument("--target", choices=["ralph", "sqllrs"], default="ralph", help="The target LRS to send statements to.")
args = parser.parse_args()

# --- CONFIG ---
if args.target == "sqllrs":
    LRS_ENDPOINT = "http://127.0.0.1:8080/xapi/statements"
    API_KEY = "admin"
    API_SECRET = "admin"
else:
    LRS_ENDPOINT = os.getenv("LRS_PUBLIC_URL", "http://127.0.0.1:8100") + "/xAPI/statements"
    API_KEY = os.getenv("LRS_API_KEY", "ralph")
    API_SECRET = os.getenv("LRS_API_SECRET", "secret")

CONTEXT_BASE = "https://example.ai/context/"
COURSE_ID = "SEC-AWARE-01"
COURSE_NAME = "Cybersecurity: Phishing Defense & Data Protection"

# --- VERB IDs ---
VERBS = {
    "initialized": "http://adlnet.gov/expapi/verbs/initialized",
    "responded": "http://adlnet.gov/expapi/verbs/responded",
    "experienced": "http://adlnet.gov/expapi/verbs/experienced",
    "scored": "http://adlnet.gov/expapi/verbs/scored",
    "classified": "http://id.tincanapi.com/verb/classified",
    "completed": "http://adlnet.gov/expapi/verbs/completed",
    "played": "https://w3id.org/xapi/video/verbs/played",
    "paused": "https://w3id.org/xapi/video/verbs/paused",
}

# --- DP CONFIG (3 Decision Points from Storyboard) ---
# DP1: The Urgent Email (Phishing Awareness)
# DP2: The Unknown USB (Physical Security)
# DP3: The Phone Call (Social Engineering)
DP_CONFIG = [
    {
        "id": "DP1",
        "activityId": "dp1-phishing",
        "name": "The Urgent Invoice Email",
        "context": "Email Inbox",
        "choices": {
            "A": "CLICK_LINK",      # Risky: Clicking the link to 'check'
            "B": "REPORT_PHISH",    # Correct: Using the report button
        },
        "sopChoice": "B"  # Correct SOP-aligned choice
    },
    {
        "id": "DP2",
        "activityId": "dp2-usb",
        "name": "The Unlabelled USB Drive",
        "context": "Office Lobby",
        "choices": {
            "A": "PLUG_IN",         # Risky: Checking the contents
            "B": "HAND_TO_SEC",     # Correct: Handing it to Security
        },
        "sopChoice": "B"  # Correct SOP-aligned choice
    },
    {
        "id": "DP3",
        "activityId": "dp3-phone",
        "name": "IT Support Verification Call",
        "context": "Phone / Desk",
        "choices": {
            "A": "GIVE_PASSWORD",   # Risky: Providing credentials over phone
            "B": "VERIFY_IDENTITY", # Correct: Asking for callback ticket
        },
        "sopChoice": "B"  # Correct SOP-aligned choice
    },
]

# --- GM CONFIG (3 Guided Missions from Storyboard) ---
# GM1: Reporting a Suspicious Link
# GM2: Securing Your Home Office
# GM3: Handling Sensitive Customer Data
GM_CONFIG = [
    {
        "id": "GM1",
        "name": "Identifying Suspicious Links",
        "context": "Digital Communications",
        "choices": {
            "A": "IGNORE",          # Neutral: Doing nothing
            "B": "HOVER_CHECK",     # Good: Checking the URL
            "C": "REPORT_IT",       # Correct: Reporting to IT
        },
        "correctChoice": "C"
    },
    {
        "id": "GM2",
        "name": "Home Office Security Setup",
        "context": "Remote Work",
        "choices": {
            "A": "PUBLIC_WIFI",     # Risky: Using unencrypted wifi
            "B": "VPN_ALWAYS",      # Correct: Using company VPN
            "C": "PERSONAL_LAPTOP", # Risky: Using unmanaged device
        },
        "correctChoice": "B"
    },
    {
        "id": "GM3",
        "name": "Data Privacy Protocols",
        "context": "Customer Support",
        "choices": {
            "A": "SEND_VIA_CHAT",   # Risky: Sharing PII in unencrypted chat
            "B": "ENCRYPTED_PORTAL",# Correct: Using secure portal
            "C": "EMAIL_PLAIN",     # Risky: Sending plain text email
        },
        "correctChoice": "B"
    },
]

# --- HELPER: Auth Header ---
def get_auth_header():
    creds = f"{API_KEY}:{API_SECRET}"
    b64_creds = base64.b64encode(creds.encode()).decode()
    return {"Authorization": f"Basic {b64_creds}", "X-Experience-API-Version": "1.0.3", "Content-Type": "application/json"}

# --- HELPER: Generate User ---
ROLES = ["Frontline Staff", "Supervisor", "Manager"]
LOCATIONS = ["Site A", "Site B", "Site C", "Warehouse", "Main Office"]

def generate_user(i):
    # Expanded list of roles and departments for better filtering
    roles = ["Surgeon", "Physician", "Nurse", "Executive", "IT Admin", "Support Staff"]
    depts = ["Surgery", "Emergency", "Administration", "Information Technology", "Customer Success"]
    
    return {
        "name": f"User {i:03d}",
        "mbox": f"mailto:user{i:03d}@example.com",
        "role": random.choices(roles, weights=[10, 20, 10, 10, 20, 30])[0],
        "dept": random.choice(depts),
        "location": random.choice(LOCATIONS),
        "attempt_id": str(uuid.uuid4()),
    }

# --- HELPER: Build Statement ---
def build_statement(user, verb, object_id, object_name, result=None, attempt=1, timestamp=None):
    stmt = {
        "id": str(uuid.uuid4()),
        "actor": {
            "name": user["name"],
            "mbox": user["mbox"],
        },
        "verb": {
            "id": VERBS[verb],
            "display": {"en-US": verb}
        },
        "object": {
            "id": f"https://example.ai/{object_id}",
            "definition": {"name": {"en-US": object_name}}
        },
        "context": {
            "extensions": {
                f"{CONTEXT_BASE}course_id": COURSE_ID,
                f"{CONTEXT_BASE}attempt_id": user["attempt_id"],
                f"{CONTEXT_BASE}attempt_count": attempt,
                f"{CONTEXT_BASE}role": user["role"],
                f"{CONTEXT_BASE}dept": user["dept"],
                f"{CONTEXT_BASE}location": user["location"],
            }
        },
        "timestamp": timestamp or datetime.datetime.utcnow().isoformat() + "Z"
    }
    if result:
        stmt["result"] = result
    return stmt

# --- GENERATE COURSE FLOW ---
def generate_user_flow(user, outcome_type, attempt=1):
    """
    Generate all statements for a user's course attempt.
    outcome_type: "SOP_ALIGNED", "SOP_INCONSISTENT", "SOP_DEVIATION"
    """
    statements = []
    base_time = datetime.datetime.utcnow() - datetime.timedelta(hours=random.randint(1, 72))
    time_offset = 0
    
    def get_timestamp():
        nonlocal time_offset
        time_offset += random.randint(30, 120)  # 30s to 2min between actions
        return (base_time + datetime.timedelta(seconds=time_offset)).isoformat() + "Z"
    
    # 1. Course Start
    statements.append(build_statement(
        user, "initialized", f"course/{COURSE_ID}", COURSE_NAME, 
        attempt=attempt, timestamp=get_timestamp()
    ))
    
    # NEW: Video Interaction (Intro Video)
    video_id = f"video/{COURSE_ID}-intro"
    statements.append(build_statement(
        user, "played", video_id, "Course Introduction Video",
        attempt=attempt, timestamp=get_timestamp()
    ))
    # Add a pause/resume for 30% of users to show interaction friction
    if random.random() < 0.3:
        statements.append(build_statement(
            user, "paused", video_id, "Course Introduction Video",
            attempt=attempt, timestamp=get_timestamp()
        ))
        statements.append(build_statement(
            user, "played", video_id, "Course Introduction Video",
            attempt=attempt, timestamp=get_timestamp()
        ))
    
    statements.append(build_statement(
        user, "completed", video_id, "Course Introduction Video",
        attempt=attempt, timestamp=get_timestamp()
    ))

    # 2. Three Decision Points (DPs)
    for dp in DP_CONFIG:
        choice_keys = list(dp["choices"].keys())
        sop_choice = dp["sopChoice"]
        non_sop_choices = [k for k in choice_keys if k != sop_choice]
        
        # Decide choice based on profile
        if outcome_type == "SOP_ALIGNED":
            choice_key = sop_choice if random.random() < 0.90 else random.choice(non_sop_choices)
        elif outcome_type == "SOP_INCONSISTENT":
            choice_key = sop_choice if random.random() < 0.55 else random.choice(non_sop_choices)
        else:  # SOP_DEVIATION
            choice_key = sop_choice if random.random() < 0.20 else random.choice(non_sop_choices)
        
        choice_value = dp["choices"][choice_key]
        
        # Behavioral metadata: Duration it took to decide
        # ISO8601 Duration: PT15S (15 seconds)
        duration_secs = random.randint(5, 60)
        duration_str = f"PT{duration_secs}S"

        statements.append(build_statement(
            user, "responded", f"interaction/{dp['activityId']}", dp["name"],
            result={
                "response": choice_value,
                "duration": duration_str,
                "success": (choice_key == sop_choice)
            },
            attempt=attempt, timestamp=get_timestamp()
        ))
    
    # 3. Three Guided Missions (GMs)
    for gm in GM_CONFIG:
        # Mission Start
        statements.append(build_statement(
            user, "experienced", f"mission/{gm['id'].lower()}", f"Mission Started: {gm['id']}",
            attempt=attempt, timestamp=get_timestamp()
        ))
        
        # Mission Decision
        choice_keys = list(gm["choices"].keys())
        correct_choice = gm["correctChoice"]
        wrong_choices = [k for k in choice_keys if k != correct_choice]
        
        if outcome_type == "SOP_ALIGNED":
            choice_key = correct_choice if random.random() < 0.85 else random.choice(wrong_choices)
        elif outcome_type == "SOP_INCONSISTENT":
            choice_key = correct_choice if random.random() < 0.55 else random.choice(wrong_choices)
        else:  # SOP_DEVIATION
            choice_key = correct_choice if random.random() < 0.25 else random.choice(wrong_choices)
        
        choice_value = gm["choices"][choice_key]
        is_compliant = choice_key == correct_choice
        outcome = "SOP_COMPLIANT" if is_compliant else "SOP_DEVIATION"
        
        statements.append(build_statement(
            user, "responded", f"mission/{gm['id'].lower()}/decision", f"Mission Decision: {gm['id']}",
            result={"response": choice_value},
            attempt=attempt, timestamp=get_timestamp()
        ))
        
        statements.append(build_statement(
            user, "experienced", f"mission/{gm['id'].lower()}/outcome", f"Mission Outcome: {outcome}",
            result={"response": outcome, "success": is_compliant},
            attempt=attempt, timestamp=get_timestamp()
        ))
    
    # 4. Assessment Result
    if outcome_type == "SOP_ALIGNED":
        score = random.randint(80, 100)
    elif outcome_type == "SOP_INCONSISTENT":
        score = random.randint(60, 79)
    else:  # SOP_DEVIATION
        score = random.randint(20, 59)
    
    scaled = round(score / 100, 2)
    
    statements.append(build_statement(
        user, "scored", "assessment/cyber-security", "Cybersecurity Assessment",
        result={
            "score": {"raw": score, "max": 100, "scaled": scaled},
            "success": outcome_type == "SOP_ALIGNED"
        },
        attempt=attempt, timestamp=get_timestamp()
    ))
    
    # 5. Classification
    statements.append(build_statement(
        user, "classified", f"result/{COURSE_ID}", f"Classification: {outcome_type}",
        result={"response": outcome_type},
        attempt=attempt, timestamp=get_timestamp()
    ))
    
    # 6. Course Complete (only for SOP_ALIGNED)
    if outcome_type == "SOP_ALIGNED":
        statements.append(build_statement(
            user, "completed", f"course/{COURSE_ID}", COURSE_NAME,
            attempt=attempt, timestamp=get_timestamp()
        ))
    
    return statements

# --- MAIN SEED FUNCTION ---
def seed_els_course(user_count=30):
    print(f"🌱 Seeding Course Data for {user_count} users...")
    print(f"   Target: {LRS_ENDPOINT}")
    
    all_statements = []
    
    # Distribution: 40% SOP_ALIGNED, 30% SOP_INCONSISTENT (various), 30% SOP_DEVIATION
    outcomes = (
        ["ALIGNED_1ST"] * 8 +                    # 8 users: Pass on 1st attempt
        ["INCONSISTENT_RETRY_ALIGNED"] * 6 +     # 6 users: Inconsistent, retry, pass
        ["INCONSISTENT_RETRY_INCONSISTENT"] * 4 + # 4 users: Inconsistent, retry, fail
        ["DEVIATION"] * 12                        # 12 users: Immediate fail
    )
    random.shuffle(outcomes)
    
    for i, outcome in enumerate(outcomes[:user_count], 1):
        user = generate_user(i)
        
        if outcome == "ALIGNED_1ST":
            # Single attempt, pass
            all_statements.extend(generate_user_flow(user, "SOP_ALIGNED", attempt=1))
            
        elif outcome == "INCONSISTENT_RETRY_ALIGNED":
            # First attempt: SOP_INCONSISTENT
            all_statements.extend(generate_user_flow(user, "SOP_INCONSISTENT", attempt=1))
            # Second attempt: SOP_ALIGNED (new attempt ID)
            user["attempt_id"] = str(uuid.uuid4())
            all_statements.extend(generate_user_flow(user, "SOP_ALIGNED", attempt=2))
            
        elif outcome == "INCONSISTENT_RETRY_INCONSISTENT":
            # First attempt: SOP_INCONSISTENT
            all_statements.extend(generate_user_flow(user, "SOP_INCONSISTENT", attempt=1))
            # Second attempt: SOP_INCONSISTENT again (fails permanently)
            user["attempt_id"] = str(uuid.uuid4())
            all_statements.extend(generate_user_flow(user, "SOP_INCONSISTENT", attempt=2))
            
        elif outcome == "DEVIATION":
            # Single attempt, immediate fail
            all_statements.extend(generate_user_flow(user, "SOP_DEVIATION", attempt=1))
    
    # Send all statements
    success_count = 0
    total = len(all_statements)
    
    print(f"\n   Sending {total} statements...")
    
    for i, stmt in enumerate(all_statements, 1):
        try:
            resp = httpx.post(LRS_ENDPOINT, json=stmt, headers=get_auth_header(), timeout=10)
            if resp.status_code == 200:
                success_count += 1
            else:
                print(f"❌ Error: {resp.status_code} - {resp.text[:100]}")
        except Exception as e:
            print(f"❌ Network Error: {e}")
        
        if i % 50 == 0:
            print(f"   ... {i}/{total} sent")
    
    print(f"\n✅ DONE: Successfully seeded {success_count}/{total} statements.")
    print(f"   Users: {user_count}")
    print(f"   Distribution: SOP_ALIGNED={outcomes.count('ALIGNED_1ST')}, INCONSISTENT→ALIGNED={outcomes.count('INCONSISTENT_RETRY_ALIGNED')}, INCONSISTENT→INCONSISTENT={outcomes.count('INCONSISTENT_RETRY_INCONSISTENT')}, DEVIATION={outcomes.count('DEVIATION')}")

if __name__ == "__main__":
    seed_els_course(30)