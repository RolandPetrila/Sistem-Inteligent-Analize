"""Verification sub-modules extracted from agent_verification.py."""
from backend.agents.verification.scoring import calculate_risk_score
from backend.agents.verification.completeness import check_completeness

__all__ = ["calculate_risk_score", "check_completeness"]
