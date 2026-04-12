# Leakage Prevention and Split Enforcement (IP-14)

## Scope

Implemented in:
- `backend/services/features/leakage.py`

Provides:
- point-in-time (PIT) no-lookahead feature validation
- deterministic chronological train/validation/test split enforcement
- sensitive-field masking for research artifacts before persistence

## Usage

Run:

```bash
python tests/usage/utils/usage_leakage_prevention.py
```

The usage script demonstrates:
- `validate_no_lookahead_features(...)`
- `enforce_time_split(...)` with configurable gap
- `mask_research_artifact(...)` for safe artifact output
