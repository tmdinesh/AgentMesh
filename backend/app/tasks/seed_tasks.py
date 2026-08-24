from typing import List, Dict
from sqlalchemy.orm import Session
from app.models.task import Task

DEFAULT_TASKS: List[Dict[str, str]] = [
    # --- Category 1: Reasoning ---
    {
        "id": "reasoning_01_knights_knaves",
        "category": "Reasoning",
        "title": "Knights and Knaves Island Logic",
        "question": (
            "On an island, Knights always tell the truth and Knaves always lie.\n"
            "You meet two inhabitants, Alex and Blair.\n"
            "Alex says: 'At least one of us is a Knave.'\n"
            "What are Alex and Blair? Explain the logical deduction clearly and state their identities."
        ),
        "expected_answer": (
            "Alex is a Knight, and Blair is a Knave.\n"
            "Reasoning: If Alex were a Knave, his statement ('At least one of us is a Knave') would be false, meaning both are Knights, which contradicts Alex being a Knave. Therefore, Alex must be a Knight and telling the truth. Since his statement is true and Alex is a Knight, Blair must be the Knave."
        ),
        "evaluation_criteria": "Alex must be identified as a Knight and Blair as a Knave, with the contradiction proof correctly derived.",
        "difficulty": "Medium"
    },
    {
        "id": "reasoning_02_river_crossing",
        "category": "Reasoning",
        "title": "Fox, Goose, and Bag of Grain River Crossing",
        "question": (
            "A farmer needs to cross a river with a fox, a goose, and a bag of grain.\n"
            "The boat can only carry the farmer and one item at a time.\n"
            "If left unattended together:\n"
            "- The fox will eat the goose.\n"
            "- The goose will eat the grain.\n"
            "Provide the minimal step-by-step sequence of river crossings so all three arrive safely on the other side."
        ),
        "expected_answer": (
            "Minimum 7 steps:\n"
            "1. Farmer takes Goose across (leaving Fox and Grain).\n"
            "2. Farmer returns alone.\n"
            "3. Farmer takes Fox across.\n"
            "4. Farmer brings Goose back.\n"
            "5. Farmer takes Grain across (leaving Goose).\n"
            "6. Farmer returns alone.\n"
            "7. Farmer takes Goose across.\n"
            "All items are now across safely."
        ),
        "evaluation_criteria": "The exact 7-trip sequence must be described without ever leaving Fox+Goose or Goose+Grain unattended.",
        "difficulty": "Easy"
    },
    {
        "id": "reasoning_03_scheduling_constraint",
        "category": "Reasoning",
        "title": "Conference Room Resource Scheduling",
        "question": (
            "Four teams (Alpha, Beta, Gamma, Delta) need to reserve a single meeting room between 9:00 AM and 1:00 PM (1-hour slots: 9-10, 10-11, 11-12, 12-1).\n"
            "Constraints:\n"
            "1. Alpha must meet strictly before Beta.\n"
            "2. Gamma cannot meet in the 9-10 slot or the 12-1 slot.\n"
            "3. Delta must meet immediately after Beta.\n"
            "Assign each team to an exact 1-hour time slot."
        ),
        "expected_answer": (
            "Alpha: 9:00 AM - 10:00 AM\n"
            "Gamma: 10:00 AM - 11:00 AM\n"
            "Beta: 11:00 AM - 12:00 PM\n"
            "Delta: 12:00 PM - 1:00 PM\n"
            "Deduction: Delta is immediately after Beta, so Beta and Delta occupy consecutive slots (either 10-11 & 11-12, or 11-12 & 12-1). Since Alpha must precede Beta, Beta cannot be 9-10 or 10-11 (if Beta was 10-11, Delta would be 11-12, leaving Alpha at 9-10 and Gamma at 12-1, but Gamma cannot be 12-1). Hence Beta is 11-12, Delta is 12-1, Gamma is 10-11, and Alpha is 9-10."
        ),
        "evaluation_criteria": "Alpha: 9-10, Gamma: 10-11, Beta: 11-12, Delta: 12-1.",
        "difficulty": "Hard"
    },

    # --- Category 2: Question Answering ---
    {
        "id": "qa_01_space_telescope",
        "category": "Question Answering",
        "title": "James Webb vs Hubble Orbital & Spectral Physics",
        "question": (
            "Compare the James Webb Space Telescope (JWST) and the Hubble Space Telescope across three specific dimensions:\n"
            "1. Primary orbital location (e.g., LEO vs Lagrange point).\n"
            "2. Primary electromagnetic wavelength bands observed.\n"
            "3. Primary mirror diameter in meters.\n"
            "State the exact facts for both telescopes."
        ),
        "expected_answer": (
            "1. Orbital Location: Hubble orbits in Low Earth Orbit (~540 km altitude); JWST orbits the Sun-Earth Lagrange Point 2 (L2) (~1.5 million km from Earth).\n"
            "2. Wavelength Bands: Hubble primarily observes ultraviolet, visible, and near-infrared (0.1 to 1.0+ micrometers); JWST primarily observes near-infrared and mid-infrared (0.6 to 28 micrometers).\n"
            "3. Primary Mirror Diameter: Hubble is 2.4 meters; JWST is 6.5 meters."
        ),
        "evaluation_criteria": "Accurately state LEO (~540km) vs Sun-Earth L2 (1.5M km), UV/Visible vs Infrared (NIR/MIR), and 2.4m vs 6.5m mirror sizes.",
        "difficulty": "Medium"
    },
    {
        "id": "qa_02_distributed_consensus",
        "category": "Question Answering",
        "title": "Raft vs Paxos Distributed Consensus Protocol",
        "question": (
            "In distributed systems, what is the fundamental structural difference between the Multi-Paxos and Raft consensus algorithms regarding leader election and log replication, and why was Raft designed as an alternative to Paxos?"
        ),
        "expected_answer": (
            "1. Structural difference: Raft decomposes consensus into distinct, explicit subproblems: Leader Election, Log Replication, and Safety (strong leader invariant with sequential append-only log index). Multi-Paxos is symmetric and allows logs to have gaps filled out-of-order via separate slot consensus instances.\n"
            "2. Motivation: Raft was explicitly designed by Ongaro and Ousterhout for understandability and easier formal implementation compared to the conceptual complexity and underspecified operational details of Multi-Paxos."
        ),
        "evaluation_criteria": "Mentions Raft's decomposed strong leader / strict log ordering vs Paxos slot consensus/log gaps, and design goal of understandability.",
        "difficulty": "Medium"
    },

    # --- Category 3: Decision/Summary ---
    {
        "id": "decision_01_cloud_triage",
        "category": "Decision/Summary",
        "title": "E-Commerce Database Incident Triage & Migration Decision",
        "question": (
            "Scenario: An e-commerce platform during Black Friday experiences database CPU spikes at 99%, read replica replication lag of 45 seconds, and checkout latency exceeding 12 seconds.\n"
            "Team proposals:\n"
            "Option A: Immediate live schema optimization and index rebuild.\n"
            "Option B: Implement aggressive redis caching on product catalog reads and route non-critical queries away from the primary DB.\n"
            "Option C: Trigger an emergency failover to a larger unindexed replica.\n"
            "Which option should the team execute immediately during peak traffic, and why are the other two dangerous?"
        ),
        "expected_answer": (
            "Selected Decision: Option B (Implement aggressive Redis caching on product catalog reads and query offloading).\n"
            "Justification:\n"
            "- Option B directly relieves the primary database read pressure, which is causing CPU exhaustion and replica lag, with minimal risk of locking.\n"
            "- Option A is dangerous because index rebuilds and schema alterations take heavy table/metadata locks and spike I/O, worsening downtime during peak traffic.\n"
            "- Option C is dangerous because failing over to an unindexed replica will cause table scans, immediately crushing the new primary."
        ),
        "evaluation_criteria": "Selects Option B. Explicitly identifies the table lock / I/O penalty of Option A and full table scan / unindexed collapse of Option C.",
        "difficulty": "Medium"
    },
    {
        "id": "decision_02_clinical_policy",
        "category": "Decision/Summary",
        "title": "Hospital Emergency Department Triage Protocol",
        "question": (
            "A hospital ED is at 130% capacity. Three critical patients arrive simultaneously:\n"
            "Patient 1: 52-year-old with acute crushing retrosternal chest pain radiating to left arm, SpO2 96%, ECG shows ST-segment elevation.\n"
            "Patient 2: 24-year-old with closed compound fracture of femur, severe pain, distal pulses intact, vital signs stable.\n"
            "Patient 3: 70-year-old with fever of 39.2C, productive cough, BP 85/50 mmHg (hypotensive, refractory to initial oral fluids), altered mental state.\n"
            "Determine the immediate triage priority order (1st, 2nd, 3rd) according to Emergency Severity Index (ESI) principles and state the emergency clinical intervention for each."
        ),
        "expected_answer": (
            "Priority Order:\n"
            "1. Co-Priority / Immediate 1st Tier: Patient 1 (STEMI) & Patient 3 (Septic Shock / Sepsis with organ dysfunction & hypotension).\n"
            "   - Patient 1: ESI Level 1/2 - Immediate Cath Lab activation / STEMI protocol & aspirin/heparin/antiplatelet.\n"
            "   - Patient 3: ESI Level 1/2 - Immediate IV fluid resuscitation, blood cultures, broad-spectrum IV antibiotics, and vasopressors for septic shock.\n"
            "2. Patient 2 (Femur fracture): ESI Level 3 - Analgesia, immobilization/splinting, neurovascular monitoring, orthopedic consultation (vital signs stable, limb perfusion intact).\n"
            "Summary: Patient 1 (STEMI) and Patient 3 (Septic Shock) take immediate top priority over stable orthopedic injury."
        ),
        "evaluation_criteria": "Prioritizes STEMI (Pt 1) and Septic Shock (Pt 3) over stable femur fracture (Pt 2) with respective clinical interventions stated.",
        "difficulty": "Hard"
    }
]


def seed_default_tasks(db: Session):
    """Seed benchmark tasks if database is empty."""
    count = db.query(Task).count()
    if count == 0:
        for t in DEFAULT_TASKS:
            task_obj = Task(
                id=t["id"],
                category=t["category"],
                title=t["title"],
                question=t["question"],
                expected_answer=t["expected_answer"],
                evaluation_criteria=t["evaluation_criteria"],
                difficulty=t.get("difficulty", "Medium")
            )
            db.add(task_obj)
        db.commit()
