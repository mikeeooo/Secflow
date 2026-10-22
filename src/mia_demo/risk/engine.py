"""Transparent policy over calibrated anomaly ranks and explicit rules."""

from mia_demo.schemas import FeatureRow, RiskResult


def decide(score: float, verify_threshold: float = 60, block_threshold: float = 85) -> str:
    return "Block" if score >= block_threshold else "Verify" if score >= verify_threshold else "Permit"


def rule_evidence(row: FeatureRow) -> tuple[float, list[dict]]:
    reasons: list[dict] = []
    conditions = [
        ("HIGH_ATTEMPT_VELOCITY", row.outgoing_attempts_5m >= 5, 0.4, f"{row.outgoing_attempts_5m} cereri anterioare în 5 minute"),
        ("NEW_DEVICE_NEW_RECIPIENT", row.device_is_new == 1 and row.recipient_is_new == 1, 0.3, "Dispozitiv și destinatar fără istoric anterior"),
        ("AMOUNT_ABOVE_PERSONAL_BASELINE", row.history_count_30d >= 10 and row.amount_to_sender_median_30d > 5, 0.3, f"Sumă de {row.amount_to_sender_median_30d:.1f} ori peste mediana personală"),
        ("RECENT_INFLOW_RAPID_OUTFLOW", row.unique_senders_1h >= 5 and row.incoming_amount_1h > 0 and row.amount_to_recent_inflow >= 0.8, 0.4, f"{row.unique_senders_1h} expeditori și {row.incoming_amount_1h:.2f} MDL primiți în ultima oră"),
    ]
    for code, active, weight, detail in conditions:
        if active:
            reasons.append({"code": code, "weight": weight, "detail": detail})
    return min(1.0, sum(r["weight"] for r in reasons)), reasons


def assess(row: FeatureRow, bundle, verify_threshold: float = 60, block_threshold: float = 85) -> RiskResult:
    model_scores = bundle.score(row)
    rule_score, reasons = rule_evidence(row)
    if model_scores["if_percentile"] >= 0.95:
        reasons.append({"code": "GLOBAL_ANOMALY", "detail": "Abatere globală ridicată față de referința de calibrare"})
    if model_scores["lof_percentile"] >= 0.95:
        reasons.append({"code": "LOCAL_DENSITY_ANOMALY", "detail": "Densitate locală neobișnuită față de vecini"})
    model_rank = 0.6 * model_scores["if_percentile"] + 0.4 * model_scores["lof_percentile"]
    score = round(100 * (0.7 * model_rank + 0.3 * rule_score), 2)
    return RiskResult(score=score, decision=decide(score, verify_threshold, block_threshold), reasons=reasons, if_percentile=model_scores["if_percentile"], lof_percentile=model_scores["lof_percentile"], rule_score=rule_score, model_version=bundle.version)
