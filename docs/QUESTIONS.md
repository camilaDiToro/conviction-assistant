# Open questions for Decade

Questions still pending — not yet answered by the project owner. Answered ones are in `ASSUMPTIONS.md`.

---

## Product & use case

1. **Should the assistant ever proactively cite *adjacent* convictions the user didn't ask about but should know?** Affects whether retrieval should over-fetch and whether the agent loop has a "related context" step.

## Question types & evaluation

2. **Will the test questions be in Portuguese, English, or Spanish — and what's the mix?** Tests multilingual coverage. Spanish is in scope per `ASSUMPTIONS.md`, but corpus is currently PT/EN only.
3. **Do you have an internal definition of "good citation"?** Just any source quote, or specific criteria (most relevant passage, no over-citation, etc.).
4. **How will you grade — human review, LLM-as-judge, or both?** Helps align the eval framework with the actual grading.

## API surface & integration

5. **What's the expected payload shape on the `POST /chat` endpoint?** Custom JSON or OpenAI-compatible chat completions.

---

## Five questions I would prioritize if time is short tomorrow

1. **Adjacent-convictions behavior** — proactive cross-citation or strict scope?
2. **Grading method** — human, LLM-as-judge, or both? Drives eval framework choice.
3. **"Good citation" definition** — affects verifier strictness and golden-set rubric.
4. **Test-question language mix** — PT / EN / ES split for the eval suite.
5. **`POST /chat` payload shape** — custom or OpenAI-compatible.
