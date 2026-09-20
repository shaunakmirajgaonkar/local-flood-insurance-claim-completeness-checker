from __future__ import annotations

from dataclasses import dataclass
from typing import Iterable

import numpy as np
import pandas as pd

REQUIRED_COLUMNS = [
    "claim_id",
    "area",
    "flood_date",
    "claim_type",
    "policy_document_present",
    "incident_date_documented",
    "photos_count",
    "receipts_count",
    "repair_estimate_present",
    "ownership_document_present",
    "emergency_expense_records",
    "damaged_item_inventory_complete",
    "damage_description_score",
    "room_damage_records_complete",
    "moisture_documented",
    "mitigation_actions_recorded",
    "local_incident_report_present",
    "witness_details_present",
    "adjuster_contact_recorded",
    "submission_deadline_days_remaining",
]

BOOL_COLUMNS = [
    "policy_document_present",
    "incident_date_documented",
    "repair_estimate_present",
    "ownership_document_present",
    "emergency_expense_records",
    "damaged_item_inventory_complete",
    "room_damage_records_complete",
    "moisture_documented",
    "mitigation_actions_recorded",
    "local_incident_report_present",
    "witness_details_present",
    "adjuster_contact_recorded",
]

NUMERIC_COLUMNS = [
    "photos_count",
    "receipts_count",
    "damage_description_score",
    "submission_deadline_days_remaining",
]


@dataclass(frozen=True)
class Component:
    name: str
    score: float
    weight: float


def _to_bool(series: pd.Series) -> pd.Series:
    if pd.api.types.is_bool_dtype(series):
        return series.fillna(False)
    truthy = {"1", "true", "yes", "y", "present", "complete", "documented"}
    return series.astype(str).str.strip().str.lower().isin(truthy)


def validate_columns(df: pd.DataFrame) -> None:
    missing = [c for c in REQUIRED_COLUMNS if c not in df.columns]
    if missing:
        raise ValueError("Missing required columns: " + ", ".join(missing))


def normalize_data(df: pd.DataFrame) -> pd.DataFrame:
    validate_columns(df)
    out = df.copy()
    out["flood_date"] = pd.to_datetime(out["flood_date"], errors="coerce")
    for col in BOOL_COLUMNS:
        out[col] = _to_bool(out[col])
    for col in NUMERIC_COLUMNS:
        out[col] = pd.to_numeric(out[col], errors="coerce").fillna(0)
    out["damage_description_score"] = out["damage_description_score"].clip(0, 100)
    out["photos_count"] = out["photos_count"].clip(lower=0)
    out["receipts_count"] = out["receipts_count"].clip(lower=0)
    out["submission_deadline_days_remaining"] = out["submission_deadline_days_remaining"].clip(lower=0)
    return out


def classify_completeness(score: float) -> str:
    score = float(score)
    if score >= 90:
        return "Ready for submission review"
    if score >= 75:
        return "Mostly complete"
    if score >= 55:
        return "Evidence gaps"
    return "Major gaps"


def claim_components(row: pd.Series) -> list[Component]:
    photo_component = min(float(row["photos_count"]) / 8.0 * 100.0, 100.0)
    receipt_component = min(float(row["receipts_count"]) / 6.0 * 100.0, 100.0)
    deadline_score = 100.0 if row["submission_deadline_days_remaining"] >= 14 else (
        80.0 if row["submission_deadline_days_remaining"] >= 7 else (
            55.0 if row["submission_deadline_days_remaining"] >= 3 else 25.0
        )
    )
    components = [
        Component("Policy & incident documentation", 100.0 if row["policy_document_present"] and row["incident_date_documented"] else (65.0 if row["policy_document_present"] or row["incident_date_documented"] else 20.0), 0.15),
        Component("Photo evidence", photo_component, 0.12),
        Component("Receipt evidence", receipt_component, 0.10),
        Component("Repair estimate", 100.0 if row["repair_estimate_present"] else 25.0, 0.09),
        Component("Ownership documentation", 100.0 if row["ownership_document_present"] else 30.0, 0.08),
        Component("Emergency expense records", 100.0 if row["emergency_expense_records"] else 30.0, 0.07),
        Component("Damage inventory", 100.0 if row["damaged_item_inventory_complete"] else 30.0, 0.08),
        Component("Damage description", float(row["damage_description_score"]), 0.10),
        Component("Room-by-room records", 100.0 if row["room_damage_records_complete"] else 35.0, 0.06),
        Component("Moisture / mitigation records", 100.0 if row["moisture_documented"] and row["mitigation_actions_recorded"] else (65.0 if row["moisture_documented"] or row["mitigation_actions_recorded"] else 25.0), 0.06),
        Component("Supporting reports / witnesses", 100.0 if row["local_incident_report_present"] and row["witness_details_present"] else (65.0 if row["local_incident_report_present"] or row["witness_details_present"] else 30.0), 0.04),
        Component("Adjuster contact record", 100.0 if row["adjuster_contact_recorded"] else 30.0, 0.02),
        Component("Deadline buffer", deadline_score, 0.03),
    ]
    return components


def score_claim(row: pd.Series) -> float:
    components = claim_components(row)
    return round(sum(c.score * c.weight for c in components), 2)


def add_screening_columns(df: pd.DataFrame) -> pd.DataFrame:
    out = normalize_data(df)
    scores = out.apply(score_claim, axis=1)
    out["claim_completeness_score"] = scores
    out["claim_completeness_class"] = scores.map(classify_completeness)
    out["missing_evidence_count"] = out.apply(missing_evidence_count, axis=1)
    out["dominant_gap"] = out.apply(dominant_gap, axis=1)
    out["review_priority"] = out.apply(review_priority, axis=1)
    return out


def missing_evidence_count(row: pd.Series) -> int:
    checks = [
        not bool(row["policy_document_present"]),
        not bool(row["incident_date_documented"]),
        row["photos_count"] < 3,
        row["receipts_count"] < 2,
        not bool(row["repair_estimate_present"]),
        not bool(row["ownership_document_present"]),
        not bool(row["damaged_item_inventory_complete"]),
        row["damage_description_score"] < 70,
        not bool(row["room_damage_records_complete"]),
        not bool(row["moisture_documented"]),
        not bool(row["mitigation_actions_recorded"]),
    ]
    return int(sum(checks))


def dominant_gap(row: pd.Series) -> str:
    gaps: dict[str, float] = {
        "Photos": max(0.0, 100.0 - min(row["photos_count"] / 8.0 * 100.0, 100.0)),
        "Receipts": max(0.0, 100.0 - min(row["receipts_count"] / 6.0 * 100.0, 100.0)),
        "Damage description": max(0.0, 100.0 - row["damage_description_score"]),
        "Repair estimate": 75.0 if not row["repair_estimate_present"] else 0.0,
        "Ownership document": 70.0 if not row["ownership_document_present"] else 0.0,
        "Damage inventory": 70.0 if not row["damaged_item_inventory_complete"] else 0.0,
        "Room records": 65.0 if not row["room_damage_records_complete"] else 0.0,
        "Moisture / mitigation": 75.0 if not (row["moisture_documented"] and row["mitigation_actions_recorded"]) else 0.0,
    }
    return max(gaps, key=gaps.get)


def review_priority(row: pd.Series) -> str:
    score = float(row["claim_completeness_score"])
    days = float(row["submission_deadline_days_remaining"])
    if score < 55 or days <= 2:
        return "Urgent review"
    if score < 75 or days <= 7:
        return "Priority review"
    return "Routine review"


def evidence_checklist(row: pd.Series) -> pd.DataFrame:
    items = [
        ("Policy document", bool(row["policy_document_present"]), "Confirm the relevant policy document is accessible."),
        ("Flood / incident date", bool(row["incident_date_documented"]), "Record when the loss event occurred."),
        ("Damage photographs", row["photos_count"] >= 3, "Capture clear photos of affected areas and major items."),
        ("Receipts / ownership evidence", row["receipts_count"] >= 2, "Collect available receipts, invoices, or equivalent ownership evidence."),
        ("Repair estimate", bool(row["repair_estimate_present"]), "Keep an itemized repair estimate when available."),
        ("Ownership document", bool(row["ownership_document_present"]), "Keep available ownership / occupancy documentation."),
        ("Expense records", bool(row["emergency_expense_records"]), "Keep records for eligible emergency or temporary expenses."),
        ("Damaged-item inventory", bool(row["damaged_item_inventory_complete"]), "List damaged items with quantity and condition."),
        ("Damage descriptions", row["damage_description_score"] >= 70, "Describe what was damaged, where, and how it was observed."),
        ("Room-by-room records", bool(row["room_damage_records_complete"]), "Record affected rooms or areas consistently."),
        ("Moisture documentation", bool(row["moisture_documented"]), "Record visible moisture or water-impact observations."),
        ("Mitigation record", bool(row["mitigation_actions_recorded"]), "Document reasonable mitigation actions taken."),
        ("Local incident report", bool(row["local_incident_report_present"]), "Attach a locally available incident or authority report when applicable."),
        ("Witness details", bool(row["witness_details_present"]), "Keep relevant witness/contact details where appropriate."),
        ("Adjuster contact", bool(row["adjuster_contact_recorded"]), "Keep a record of claim-related contact."),
    ]
    return pd.DataFrame(items, columns=["Evidence item", "Present / complete", "Suggested record"])


def scenario_score(base: pd.DataFrame, photo_change: float = 0.0, receipt_change: float = 0.0,
                   description_change: float = 0.0, add_repair_estimate: bool = False,
                   add_inventory: bool = False) -> pd.DataFrame:
    out = normalize_data(base).copy()
    out["photos_count"] = (out["photos_count"] + photo_change).clip(lower=0)
    out["receipts_count"] = (out["receipts_count"] + receipt_change).clip(lower=0)
    out["damage_description_score"] = (out["damage_description_score"] + description_change).clip(0, 100)
    if add_repair_estimate:
        out["repair_estimate_present"] = True
    if add_inventory:
        out["damaged_item_inventory_complete"] = True
    return add_screening_columns(out)


def compact_report_table(df: pd.DataFrame, cols: Iterable[str] | None = None, n: int = 10) -> pd.DataFrame:
    scored = add_screening_columns(df) if "claim_completeness_score" not in df.columns else df.copy()
    if cols is None:
        cols = ["claim_id", "area", "claim_completeness_score", "claim_completeness_class", "missing_evidence_count", "dominant_gap", "review_priority"]
    available = [c for c in cols if c in scored.columns]
    return scored[available].sort_values("claim_completeness_score", ascending=False).head(n)


def markdown_table(df: pd.DataFrame) -> str:
    if df.empty:
        return "*(No rows available.)*"
    safe = df.copy()
    for col in safe.columns:
        safe[col] = safe[col].map(lambda v: str(v).replace("|", "\\|").replace("\n", " "))
    header = "| " + " | ".join(map(str, safe.columns)) + " |"
    sep = "| " + " | ".join(["---"] * len(safe.columns)) + " |"
    rows = ["| " + " | ".join(map(str, row)) + " |" for row in safe.itertuples(index=False, name=None)]
    return "\n".join([header, sep, *rows])
