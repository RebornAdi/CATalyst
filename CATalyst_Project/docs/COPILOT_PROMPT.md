# Prompt for GitHub Copilot / Claude Code / Antigravity

You are working on the CATalyst Caterpillar Hackathon 2026 project.

Read the entire repository before changing anything.

Goal: turn this scaffold into a polished, runnable hackathon prototype without breaking the existing module contracts.

Architecture:
- Module 1: simulated machine telemetry on port 8001.
- Module 2: risk + machine health + Link Analyzer on port 8002.
- Module 3: AI Orchestrator + Scheduler + Coach on port 8003.
- Module 4: React operator app on port 5173.

Rules:
1. Keep the four modules independently runnable on separate laptops.
2. Communicate across modules through HTTP JSON APIs, not shared Python imports.
3. Preserve the JSON contract in docs/INTEGRATION_CONTRACT.md.
4. Keep the simulated telemetry wording honest.
5. Do not claim correlation proves causation.
6. Keep confidence heuristic and explainable.
7. Do not introduce a database unless it is genuinely needed.
8. Make the local version work without paid cloud infrastructure.
9. If an LLM is added, keep a deterministic fallback so the demo works without an API key.
10. Keep the React interface sparse, operator-focused and demo-friendly.
11. Add tests for the Module 2 analysis rules.
12. Add a simple health-check view or status indicator if useful.
13. Do not over-engineer the MVP.

High-value improvements to implement:
- stronger scenario simulation with a normal, harsh-load and recovery state
- clean evidence cards
- explain-this flow
- simple scheduler/coach response
- optional LLM adapter behind an environment variable
- robust error handling when another module is offline
- tests and README updates

Before finishing:
- run Python syntax/tests
- run the React production build
- verify all ports and endpoints
- report exactly what changed
- do not hide errors or silently remove functionality
