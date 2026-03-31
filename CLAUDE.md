# CLAUDE.md

Behavioral guidelines to reduce common LLM coding mistakes. Merge with project-specific instructions as needed.

**Tradeoff:** These guidelines bias toward caution over speed. For trivial tasks, use judgment.

## 1. Think Before Coding

**Don't assume. Don't hide confusion. Surface tradeoffs.**

Before implementing:
- State your assumptions explicitly. If uncertain, ask. Werify your assumptions or ask for more information
- If multiple interpretations exist, present them - don't pick silently.
- If a simpler approach exists, say so. Push back when warranted.
- If something is unclear, stop. Name what's confusing. Ask.
- Don't speculate. don't say "likely" or "probably". if you have a theory, check it and then reply.

## 2. Simplicity First

**Minimum code that solves the problem. Nothing speculative.**

- No features beyond what was asked.
- No abstractions for single-use code.
- No "flexibility" or "configurability" that wasn't requested.
- No error handling for impossible scenarios.
- If you write 200 lines and it could be 50, rewrite it.

Ask yourself: "Would a senior engineer say this is overcomplicated?" If yes, simplify.

## 3. Surgical Changes

**Touch only what you must. Clean up only your own mess.**

When editing existing code:
- Don't "improve" adjacent code, comments, or formatting.
- Don't refactor things that aren't broken.
- Match existing style, even if you'd do it differently.
- If you notice unrelated dead code, mention it - don't delete it.

When your changes create orphans:
- Remove imports/variables/functions that YOUR changes made unused.
- Don't remove pre-existing dead code unless asked.

The test: Every changed line should trace directly to the user's request.

## 4. Goal-Driven Execution

**Define success criteria. Loop until verified.**

Transform tasks into verifiable goals:
- "Add validation" → "Write tests for invalid inputs, then make them pass"
- "Fix the bug" → "Write a test that reproduces it, then make it pass"
- "Refactor X" → "Ensure tests pass before and after"

For multi-step tasks, state a brief plan:
```
1. [Step] → verify: [check]
2. [Step] → verify: [check]
3. [Step] → verify: [check]
```

Strong success criteria let you loop independently. Weak criteria ("make it work") require constant clarification.

---

## 5. Performance & Caching

**Cache with intent, not by default.**

When implementing caching:
- Use content-addressed keys (SHA256 of content + model) for deterministic invalidation
- Prefer numpy's native format (.npy/.npz) over pickle for numeric data - it's faster and more compact
- Include version metadata with model fingerprints to auto-invalidate stale caches
- Cache at the right granularity (SDG embeddings once per model, activity embeddings per text)

---

## 6. Code Organization

**Files should fit on a screen, not in a book.**

- If a file exceeds ~500 lines, consider modularizing
- Extract pure functions that don't depend on framework state (e.g., Streamlit session)
- Group by feature/domain, not by layer (dashboard/utils.py, not helpers.py)
- Keep framework-specific imports (Streamlit, Flask) at the edges, not in core logic

**When to split:**
- Utilities used in multiple places → extract to shared module
- Constants/configuration → config module
- Pure business logic → separate from UI/rendering code

---

## 7. Bug Prevention Patterns

**Common code smells to catch:**

1. **Duplicate assignments**: Same variable assigned twice without intermediate use

2. **Custom implementations of standard algorithms**:

3. **Missing cache invalidation**:

---

## 8. Project Hygiene & Directory Organization

**A place for everything, and everything in its place.**

Messy projects accumulate technical debt. Keep the root directory clean and organized.

### The .gitignore Rule

**Create `.gitignore` early and keep it comprehensive:**

### Clean Up After Debugging

### The "One Day" Trap

**Don't keep files "just in case":**


**Git is your backup:**

### Verification Checklist

1. **Trace the data flow**: Where does each model's output enter the pipeline?
2. **Verify all components contribute**: Add assertions or logging to confirm each model's scores affect the final result
3. **Compare outputs**: Run both "single model" and "ensemble" modes and verify different outputs
4. **Check the math**: Ensemble scores should be weighted combinations, not just one model's scores
5. **Test with known inputs**: Use inputs where each model gives different predictions to verify combination

### Red Flags


---

## 9. Root cause


No quick fixes. ALways diagnose to the root cause and devise proper solutions. Never apply patches or workarounds unless explicitly asked.

---

**These guidelines are working if:** fewer unnecessary changes in diffs, fewer rewrites due to overcomplication, and clarifying questions come before implementation rather than after mistakes.
