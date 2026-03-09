# Haven AI Guardrails (Do & Don't)

This document defines the product and implementation contract for all AI-powered features in Haven. Every prompt and post-processing step for mediation, message rewriter, and weekly report must respect these boundaries.

## Do (AI is allowed to)

- **Tone rewriting**: Rephrase attacking or harsh language into "I feel..." / "I need..." style sentences.
- **Repair sentence templates**: Provide non-judgmental, relationship-safe sentence templates for communication.
- **Weekly report insights**: Summarize patterns (e.g. "most frequent conflict trigger situations") without assigning blame or diagnosing.

## Don't (AI must not)

- **Judge who is right or wrong**: Never output verdicts like "you were wrong" or "your partner was at fault."
- **Provide psychological diagnosis**: No clinical or diagnostic language (e.g. "you have anxiety", "your partner is narcissistic").
- **Generate manipulative language**: No output designed to control, guilt-trip, or coerce the other person.

## Implementation

- **Reference in code**: All prompts for mediation, rewriter (`POST /api/cooldown/rewrite-message`), and weekly report MUST reference this document (e.g. in prompt text or in `app/core/prompts`).
- **Location**: `docs/ai-safety/ai-guardrails.md`
- **Related**: `backend/app/services/ai.py`, `backend/app/services/ai_persona.py`, mediation runtime, cooldown rewriter, weekly report job.
