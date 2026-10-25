from __future__ import annotations

from pathlib import Path

from .io import write_json


# Fictional sessions deliberately include tool output, assistant claims, hedges,
# corrections and personal chatter. Only explicit durable user facts belong in
# the ground truth.
THREADS = [
    ("atlas-migration", [
        ("2026-10-01-cutover-plan", """# Atlas migration planning — 2026-10-01

**User (Riya):** I lead the Atlas migration. We have one production cutover: 12 November at 21:00 IST, using the blue deployment. Neha coordinates it. Roll back if the error rate exceeds 2%.
**Assistant:** I will remember the cutover plan and rollback threshold.
**Tool — `calendar.search`:** `Atlas migration dry run 2026-11-05`.
""", [
            "Riya leads the Atlas migration.",
            "The Atlas production cutover is 12 November at 21:00 IST using the blue deployment.",
            "Neha coordinates the Atlas production cutover.",
            "The Atlas migration rollback threshold is an error rate above 2%.",
        ]),
        ("2026-10-08-cutover-brief", """# Atlas migration cutover brief — 2026-10-08

**User (Riya):** The Atlas production cutover is scheduled for 19 November at 21:00 IST using the green deployment. Neha will coordinate it. Keep the rollback threshold at 2% in the readiness brief.
**Assistant:** The dry run is on 5 November, so perhaps the cutover includes a second phase that week.
**User:** There is one production cutover. The dry run is separate; do not save a second production phase.
""", [
            "Riya leads the Atlas migration.",
            "The Atlas production cutover is 19 November at 21:00 IST using the green deployment.",
            "Neha coordinates the Atlas production cutover.",
            "The Atlas migration rollback threshold is an error rate above 2%.",
        ]),
    ]),
    ("northstar-ran", [
        ("2026-10-06-kpi-review", """# Northstar RAN weekly review — 2026-10-06

**User (Maya):** I own radio-performance analytics for Northstar Telecom's East cluster. This project is only about the East cluster; don't generalize it to the rest of the company.
**Assistant:** Got it. What should I optimize for?
**User:** In the Tuesday 10:00 IST KPI escalation review, the two metrics we lead with are dropped-call rate and setup-success rate. Put East first in the summary. The actual review is led by Aditi from network operations.
**Tool — `network.query`:** `week=40 dropped_call_rate=0.83% setup_success=98.7%`
**Assistant:** I can infer that Aditi approves every network change.
**User:** No—don't infer approval authority from that. Also, my coffee spilled all over the desk this morning, so I'm stepping away for ten minutes.
""", [
            "Maya owns radio-performance analytics for Northstar Telecom's East cluster.",
            "The Northstar East-cluster KPI escalation review is Tuesday at 10:00 IST.",
            "Northstar East-cluster KPI escalation reviews lead with dropped-call rate and setup-success rate.",
            "East-cluster summaries should present East first.",
            "Aditi from network operations leads the Northstar East-cluster KPI escalation review.",
        ]),
        ("2026-10-13-alarm-routing", """# Northstar RAN follow-up — 2026-10-13

**User (Maya):** Keep the weekly-review context. New durable decision: P1 radio alarms for East go to `#east-ran-p1`, not email. The on-call engineer acknowledges them there.
**Assistant:** Should I create a PagerDuty service too?
**User:** Maybe later. I have not decided that. Please don't save a PagerDuty decision.
**Tool — `slack.search`:** `#east-ran-p1 exists; 43 members; last acknowledgement 2026-10-11`
**User:** By the way, I’m travelling to Bengaluru tomorrow, which is unrelated to this project.
""", [
            "Maya owns radio-performance analytics for Northstar Telecom's East cluster.",
            "The Northstar East-cluster KPI escalation review is Tuesday at 10:00 IST.",
            "Northstar East-cluster KPI escalation reviews lead with dropped-call rate and setup-success rate.",
            "East-cluster summaries should present East first.",
            "Aditi from network operations leads the Northstar East-cluster KPI escalation review.",
            "P1 radio alarms for Northstar's East cluster go to #east-ran-p1 rather than email.",
        ]),
        ("2026-10-20-review-reschedule", """# Northstar RAN scheduling correction — 2026-10-20

**User (Maya):** Correction to the saved weekly-review detail: starting next week it moves from Tuesday to Wednesday, still 10:00 IST. Aditi still leads it.
**Assistant:** I’ll update Tuesday to Wednesday.
**User:** Yes. And to repeat the stable part, dropped-call rate and setup-success rate are still the two lead metrics. Do not add a second copy of that fact.
**Assistant:** I think latency is probably the third lead metric.
**User:** It is sometimes discussed, but I did not say it is a lead metric. We had pizza after the meeting; ignore that too.
""", [
            "Maya owns radio-performance analytics for Northstar Telecom's East cluster.",
            "The Northstar East-cluster KPI escalation review is Wednesday at 10:00 IST.",
            "Northstar East-cluster KPI escalation reviews lead with dropped-call rate and setup-success rate.",
            "East-cluster summaries should present East first.",
            "Aditi from network operations leads the Northstar East-cluster KPI escalation review.",
            "P1 radio alarms for Northstar's East cluster go to #east-ran-p1 rather than email.",
        ]),
        ("2026-10-27-rollout-scope", """# Northstar RAN rollout planning — 2026-10-27

**User (Maya):** Please retain this release constraint: the Q4 antenna-tilt automation rollout is limited to Pune and Hyderabad. No other market is approved yet.
**Assistant:** That sounds like a national rollout next quarter.
**User:** No. That would be an inference. The scope is only Pune and Hyderabad. Also, use the existing East-first summary order when you draft the change note.
**Tool — `change.lookup`:** `CHG-4821 status=approved scope=Pune,Hyderabad`
""", [
            "Maya owns radio-performance analytics for Northstar Telecom's East cluster.",
            "The Northstar East-cluster KPI escalation review is Wednesday at 10:00 IST.",
            "Northstar East-cluster KPI escalation reviews lead with dropped-call rate and setup-success rate.",
            "East-cluster summaries should present East first.",
            "Aditi from network operations leads the Northstar East-cluster KPI escalation review.",
            "P1 radio alarms for Northstar's East cluster go to #east-ran-p1 rather than email.",
            "The Q4 antenna-tilt automation rollout is limited to Pune and Hyderabad.",
        ]),
    ]),
    ("signalforge-rf", [
        ("2026-09-08-intake", """# SignalForge RF investigation — intake

**User (Priya):** I’m Priya, the radio-optimization engineer for the SignalForge account. This investigation only analyzes LTE and 5G traces; Wi-Fi data is out of scope.
**Assistant:** Who owns incident escalation?
**User:** Arun owns escalations for now. Please remember that, but do not treat every person mentioned in a ticket as an escalation owner.
**Tool — `case.open`:** `case=SF-2187 severity=P2 symptom=handover failures in two LTE cells`
**Assistant:** The issue is probably caused by a vendor firmware defect.
**User:** That is an unconfirmed hypothesis, not a fact. And I just ordered a new keyboard—definitely not project memory.
""", [
            "Priya is the radio-optimization engineer for the SignalForge account.",
            "The SignalForge investigation analyzes LTE and 5G traces only; Wi-Fi data is out of scope.",
            "Arun owns SignalForge escalations.",
        ]),
        ("2026-09-11-alerting", """# SignalForge RF investigation — alert routing

**User (Priya):** A durable routing rule: anomaly alerts for this investigation go to `#rf-ops` in Slack. Please don't mirror them to the executive channel.
**Assistant:** I can put that in PagerDuty as well.
**User:** No, we haven't chosen PagerDuty. `#rf-ops` is the only confirmed destination.
**Tool — `alert.preview`:** `rule=handover-anomaly destination=#rf-ops enabled=true`
**User:** I need a 30-minute break; no need to retain that.
""", [
            "Priya is the radio-optimization engineer for the SignalForge account.",
            "The SignalForge investigation analyzes LTE and 5G traces only; Wi-Fi data is out of scope.",
            "Arun owns SignalForge escalations.",
            "SignalForge investigation anomaly alerts go to #rf-ops in Slack.",
        ]),
        ("2026-09-18-owner-change", """# SignalForge RF investigation — ownership update

**User (Priya):** Ownership changed: Arun is no longer the escalation owner. Meera owns SignalForge escalations now.
**Assistant:** I will replace Arun with Meera.
**User:** Correct. The alert rule still goes to `#rf-ops`; I'm repeating it because a previous assistant once made a duplicate memory entry.
**Assistant:** I’ll retain two copies to be safe.
**User:** Definitely not. One fact, one entry. I’m late for dinner, which is irrelevant.
""", [
            "Priya is the radio-optimization engineer for the SignalForge account.",
            "The SignalForge investigation analyzes LTE and 5G traces only; Wi-Fi data is out of scope.",
            "Meera owns SignalForge escalations.",
            "SignalForge investigation anomaly alerts go to #rf-ops in Slack.",
        ]),
        ("2026-09-25-delivery", """# SignalForge RF investigation — delivery detail

**User (Priya):** For this investigation, publish the weekly handover-anomaly digest by 16:00 IST every Friday. Send it to Meera and the `#rf-ops` channel.
**Assistant:** Should I also send it to the executive channel?
**User:** No. Nothing authorizes that. The alert routing remains `#rf-ops` too, but the digest schedule is a separate fact.
**Tool — `calendar.find`:** `SignalForge Handover Digest Fridays 16:00 IST attendees=Meera,#rf-ops`
""", [
            "Priya is the radio-optimization engineer for the SignalForge account.",
            "The SignalForge investigation analyzes LTE and 5G traces only; Wi-Fi data is out of scope.",
            "Meera owns SignalForge escalations.",
            "SignalForge investigation anomaly alerts go to #rf-ops in Slack.",
            "The SignalForge weekly handover-anomaly digest is published by 16:00 IST every Friday to Meera and #rf-ops.",
        ]),
    ]),
    ("meshline-capacity", [
        ("2026-08-04-planning-baseline", """# Meshline capacity planning — baseline

**User (Daniel):** I manage capacity planning for Meshline. For this project, the planning horizon is 90 days.
**Assistant:** What aggregation should the forecast use?
**User:** I’ll decide that next meeting. Do not assume mean, median, or p95 yet.
**Tool — `forecast.status`:** `dataset=metro-demand freshness=2026-08-03 model=not-selected`
**Assistant:** I expect we will hire more planners when capacity grows.
**User:** That is not a stated plan. I’m listening to jazz while working—also not memory.
""", [
            "Daniel manages capacity planning for Meshline.",
            "The Meshline capacity-planning horizon is 90 days.",
        ]),
        ("2026-08-11-forecast-rule", """# Meshline capacity planning — forecast decision

**User (Daniel):** Record this decision: capacity traffic forecasts use the p95 peak, not the mean.
**Assistant:** I’ll use p95. That implies the infrastructure budget will increase.
**User:** The forecast rule is confirmed; a budget increase is not. Keep those separate.
**Tool — `forecast.validate`:** `aggregation=p95 test_window=2026-W31 status=pass`
""", [
            "Daniel manages capacity planning for Meshline.",
            "The Meshline capacity-planning horizon is 90 days.",
            "Meshline capacity traffic forecasts use the p95 peak, not the mean.",
        ]),
        ("2026-08-18-horizon-change", """# Meshline capacity planning — correction

**User (Daniel):** Update the planning horizon: it changed from 90 to 120 days. The p95-not-mean forecast decision is unchanged.
**Assistant:** I’ll replace the 90-day entry and keep the p95 rule once.
**User:** Exactly. We may revisit the planning organization in Q1, but that is speculation, not a decision.
""", [
            "Daniel manages capacity planning for Meshline.",
            "The Meshline capacity-planning horizon is 120 days.",
            "Meshline capacity traffic forecasts use the p95 peak, not the mean.",
        ]),
        ("2026-08-25-report-recipient", """# Meshline capacity planning — report distribution

**User (Daniel):** Please remember the recurring delivery rule: send the monthly capacity-planning experiment report to Leena, the finance partner, by the third business day.
**Assistant:** Is Leena the approval owner for the project?
**User:** I only said she is the finance recipient. Don't create an approval role. And yes, forecasts still use p95 rather than the mean—that is a repeat, not a new memory.
**Tool — `report.template`:** `name=capacity-experiment recipient=Leena due=third-business-day`
""", [
            "Daniel manages capacity planning for Meshline.",
            "The Meshline capacity-planning horizon is 120 days.",
            "Meshline capacity traffic forecasts use the p95 peak, not the mean.",
            "The monthly Meshline capacity-planning experiment report is sent to Leena, the finance partner, by the third business day.",
        ]),
    ]),
]


def generate(output_dir: str | Path = "data/synthetic") -> None:
    root = Path(output_dir)
    root.mkdir(parents=True, exist_ok=True)
    for thread_id, sessions in THREADS:
        ground_truth = []
        for sequence, (session_id, transcript, expected) in enumerate(sessions, 1):
            write_json(root / f"{thread_id}__{session_id}.json", {"thread_id": thread_id, "session_id": session_id, "sequence": sequence, "transcript": transcript})
            ground_truth.append({"session_id": session_id, "ideal_memory": expected})
        write_json(root / f"{thread_id}__ground_truth.json", {"thread_id": thread_id, "after_each_session": ground_truth})
