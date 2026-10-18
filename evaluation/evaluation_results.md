# Evaluation Results Summary

Document your team's evaluation results below.

## Summary Overview

- **Date of Evaluation:** YYYY-MM-DD
- **Model Evaluated:** (e.g., `llama3.2`)
- **Total Test Cases Executed:** 0
- **Passed:** 0
- **Failed:** 0
- **Pass Rate:** 0%

## Performance by Category

| Category | Total Cases | Passed | Failed | Pass Rate |
| :--- | :---: | :---: | :---: | :---: |
| Successful Cases | 0 | 0 | 0 | 0% |
| Difficult Cases | 0 | 0 | 0 | 0% |
| Failure / Edge Cases | 0 | 0 | 0 | 0% |

## Key Findings & Failure Analysis

### What worked well
- Observation 1
- Observation 2

### Observed failure modes
- Description of case where the system failed and why.

## Action Items & Improvements
- [ ] Planned fix or enhancement based on evaluation findings.

## Assignment Analysis Accuracy Evaluation - 11 October 2026

**Model:** qwen3:4b  
**Test cases:** 4  
**Method:** Automated structured-output checks followed by manual accuracy review.

### Initial Results

| Case | Category | Manual Status |
|---|---|---|
| Assignment 01 - Python Data Analysis | Successful | Partial |
| Assignment 02 - AI Ethics Essay | Successful | Pass |
| Assignment 03 - Group Project | Difficult | Partial |
| Assignment 04 - Empty Description | Failure / Edge | Pass (with caveat) |

### Key Findings

- All four cases returned structured output successfully.
- The model generally identified relevant task types, skills, and topics.
- Exact string matching caused false mismatches for equivalent terms such as `research_essay` and `essay`.
- Some relevant concepts appeared under topics instead of skills.
- For ambiguous assignments, the model estimated workload and difficulty without sufficient supporting details.
- For empty descriptions, the model avoided inventing skills and topics but still assigned an unsupported difficulty label.
- The second automated evaluation run produced partial results for both successful cases. Assignment 01 passed task type, difficulty, workload, and topics checks, but failed skills matching. Assignment 02 passed difficulty and workload checks, but failed task type, skills, and topics matching. Manual review identified several semantically equivalent terms that the strict evaluator did not recognize. These mismatches were retained rather than changing evaluation criteria solely to increase the pass rate.

### Prompt Improvement and Re-evaluation - 11 October 2026

The initial prompt revision caused a regression: the Python programming assignment was incorrectly classified as unknown. After refining the instructions to distinguish clear, vague, and missing assignment descriptions, the model correctly analysed the Python task again.

The final evaluation produced two automatic partial results and two cases requiring manual review. Manual assessment found that the Python assignment met the expected requirements despite terminology differences. The AI ethics essay remained partially successful because its 4-hour workload estimate was below the predefined range. The vague group project still produced unsupported difficulty and workload estimates, while the empty-description case returned a conservative fallback.

**Conclusion:** The revised prompt improved handling of clearly specified assignments and preserved structured output, but further work is needed to represent uncertainty and evaluate ambiguous assignments reliably.

### Recommended Improvements

- Normalize underscores and equivalent terminology in the automated evaluator.
- Improve prompt instructions for incomplete assignment descriptions.
- Distinguish model-estimated workload and difficulty from confirmed assignment facts.
- Expand the evaluation dataset before making general accuracy claims.