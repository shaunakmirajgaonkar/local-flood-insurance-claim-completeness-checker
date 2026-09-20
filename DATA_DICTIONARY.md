# Data Dictionary

| Column | Meaning |
|---|---|
| claim_id | Local claim identifier |
| area | Household / neighborhood label |
| flood_date | Locally recorded loss-event date |
| claim_type | Claim category |
| policy_document_present | Policy document available |
| incident_date_documented | Event date recorded |
| photos_count | Count of available damage photos |
| receipts_count | Count of receipts/invoices or similar records |
| repair_estimate_present | Repair estimate available |
| ownership_document_present | Ownership/occupancy document available |
| emergency_expense_records | Emergency expense records available |
| damaged_item_inventory_complete | Damaged-item inventory complete |
| damage_description_score | 0–100 completeness of damage narrative |
| room_damage_records_complete | Room-by-room records complete |
| moisture_documented | Moisture/water-impact observations recorded |
| mitigation_actions_recorded | Mitigation actions documented |
| local_incident_report_present | Local incident/authority report available where applicable |
| witness_details_present | Relevant witness details available |
| adjuster_contact_recorded | Claim-related contact record available |
| submission_deadline_days_remaining | Locally supplied days remaining |

Derived columns are described in `doc/SCREENING_METHOD.md`.
