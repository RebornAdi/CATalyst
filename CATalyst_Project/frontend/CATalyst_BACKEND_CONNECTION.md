# CATalyst Backend Connection

The existing CATalyst UI is preserved.

The frontend calls Module 3 at:

http://127.0.0.1:8003

Scenario mapping:
- OPERATION_TO_WEAR -> POST /copilot/scenario/OPERATION_TO_WEAR
- OPERATOR_RISK -> POST /copilot/scenario/OPERATOR_RISK
- NORMAL -> POST /copilot/scenario/NORMAL

Module 3 then handles the mapping to the backend scenarios and returns the real CATalyst analysis.
