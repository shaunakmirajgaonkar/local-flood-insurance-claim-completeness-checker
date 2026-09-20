import pandas as pd
import pytest

from analytics import (
    REQUIRED_COLUMNS,
    add_screening_columns,
    classify_completeness,
    compact_report_table,
    markdown_table,
    scenario_score,
    validate_columns,
)


def sample_df():
    return pd.read_csv("data/sample_flood_claims.csv")


def test_sample_scores_are_bounded_and_classified():
    df = add_screening_columns(sample_df())
    assert df["claim_completeness_score"].between(0, 100).all()
    assert df["claim_completeness_class"].notna().all()


def test_classification_boundaries():
    assert classify_completeness(95) == "Ready for submission review"
    assert classify_completeness(80) == "Mostly complete"
    assert classify_completeness(60) == "Evidence gaps"
    assert classify_completeness(40) == "Major gaps"


def test_missing_columns_raise_clear_error():
    with pytest.raises(ValueError, match="Missing required columns"):
        validate_columns(pd.DataFrame({"claim_id": ["x"]}))


def test_scenario_improves_with_added_evidence():
    base = add_screening_columns(sample_df())
    improved = scenario_score(sample_df(), photo_change=3, receipt_change=2, description_change=15, add_repair_estimate=True, add_inventory=True)
    assert improved["claim_completeness_score"].mean() >= base["claim_completeness_score"].mean()


def test_report_and_markdown_export_are_dependency_free():
    df = add_screening_columns(sample_df())
    report = compact_report_table(df)
    assert "claim_completeness_score" in report.columns
    md = markdown_table(report.head(3))
    assert "| claim_id |" in md
    assert "| --- |" in md
