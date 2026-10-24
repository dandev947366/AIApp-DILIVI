
# 🎓 Tutor MCP Server: Available Tools

The Tutor MCP server provides 46 tools for building adaptive, mastery-based learning experiences. The tools are grouped into six main categories:

---

### 🏗️ 1. Domain & Curriculum Management
Tools for creating, managing, and versioning the learning curriculum (domains, concepts, and prerequisites).

*   **`init_domain`**
    *   **Description:** Initialize a learning domain with its concepts and prerequisites. Does not destroy existing progress.
    *   **Required:** `name`, `concepts`, `prerequisites`
*   **`add_concepts`**
    *   **Description:** Add concepts through an immutable curriculum revision without destroying progress. Requires the latest `expected_version`; stale writers are rejected.
    *   **Required:** `domain_id`, `expected_version`, `concepts`, `prerequisites`
*   **`publish_curriculum_revision`**
    *   **Description:** Publish an immutable curriculum revision using optimistic concurrency. Supports rename, update, split, merge, and prerequisite repair.
    *   **Required:** `domain_id`, `expected_version`, `operation`, `source_concept_ids`, `provenance`
*   **`archive_domain`**
    *   **Description:** Archive a domain—it disappears from the dashboard but progress is preserved.
    *   **Required:** `domain_id`
*   **`unarchive_domain`**
    *   **Description:** Reactivate an archived domain with all progress preserved.
    *   **Required:** `domain_id`
*   **`delete_domain`**
    *   **Description:** Remove a domain using an auditable tombstone. Curriculum and evidence are preserved. Requires `confirm=true`.
    *   **Required:** `domain_id`, `confirm`
*   **`set_domain_priority`**
    *   **Description:** Set the learner-controlled priority for an active domain (rank 1 is highest).
    *   **Required:** `domain_id`, `rank`
*   **`mark_domain_high_stakes`**
    *   **Description:** Apply a one-way high-stakes safety classification. Demonstrated claims will require human-reviewed evaluation.
    *   **Required:** `domain_id`
*   **`get_curriculum_snapshot`**
    *   **Description:** Read the latest or a historical immutable curriculum snapshot.
    *   **Required:** `domain_id`
*   **`get_goal_relevance`**
    *   **Description:** Read the stored relevance vector for a domain and list uncovered concepts.
    *   **Required:** `domain_id`
*   **`set_goal_relevance`**
    *   **Description:** Decompose the learner's personal goal against the domain's concepts (0.0 to 1.0).
    *   **Required:** `relevance`
*   **`validate_domain_graph`**
    *   **Description:** Audit the active domain graph deterministically and return structural quality issues.
    *   **Required:** `domain_id`

---

### 🔄 2. Learning Cycle & Routing
Tools for managing the active learning session, routing the next activity, and fetching alerts.

*   **`get_pending_alerts`**
    *   **Description:** Retrieve ALL pending alerts (activity and metacognitive). **Call FIRST each turn.**
    *   **Required:** None
*   **`get_next_activity`**
    *   **Description:** Determine the next optimal activity for the learner (the main tool of the learning cycle).
    *   **Required:** None
*   **`start_learning_session`**
    *   **Description:** Open or resume the learner's durable learning session. Returns the canonical `session_id`.
    *   **Required:** None
*   **`get_learner_context`**
    *   **Description:** Retrieve the full learner context for session start.
    *   **Required:** `domain_id`
*   **`learning_negotiation`**
    *   **Description:** Expose the session plan with rationale. The learner can propose an alternative.
    *   **Required:** `session_id`
*   **`get_autonomy_metrics`**
    *   **Description:** Descriptive learning rates, prediction accuracy, and observation counts.
    *   **Required:** None

---

### 📝 3. Assessments & Evidence
Tools for recording interactions, testing mastery, and managing assessment attempts.

*   **`record_interaction`**
    *   **Description:** Record an observed result and update the learner model (BKT/FSRS).
    *   **Required:** `concept`, `activity_type`, `success`, `response_time_seconds`, `confidence`
*   **`record_learning_event`**
    *   **Description:** Record that an exposure to feedback/instruction occurred once.
    *   **Required:** `event_key`, `domain_id`, `concept`, `kind`
*   **`prepare_assessment_attempt`**
    *   **Description:** Freeze an assessment task and passing rubric before showing it to the learner.
    *   **Required:** `concept`, `activity_type`, `observable`, `rubric_json`
*   **`submit_assessment_attempt`**
    *   **Description:** Persist the learner's committed response against a previously frozen assessment attempt.
    *   **Required:** `attempt_id`
*   **`cancel_assessment_attempt`**
    *   **Description:** Cancel a prepared or submitted assessment attempt without changing the learner model.
    *   **Required:** `attempt_id`
*   **`check_mastery`**
    *   **Description:** Check whether a concept is ready for the mastery challenge using BKT, evidence diversity, and uncertainty.
    *   **Required:** None
*   **`calibration_check`**
    *   **Description:** Record the learner's self-assessment before an exercise. Returns a `prediction_id`.
    *   **Required:** `predicted_mastery`
*   **`record_calibration_result`**
    *   **Description:** Compare the learner's prediction with the actual result. Updates calibration bias.
    *   **Required:** `prediction_id`, `actual_score`
*   **`feynman_challenge`**
    *   **Description:** Ask the learner to explain a concept whose model estimate reached the deep-evidence threshold.
    *   **Required:** None
*   **`transfer_challenge`**
    *   **Description:** Generate a novel situation to probe transfer outside the training context.
    *   **Required:** None
*   **`record_transfer_result`**
    *   **Description:** Record a legacy, unverified transfer observation for adaptive routing.
    *   **Required:** `context_type`, `score`
*   **`get_metacognitive_mirror`**
    *   **Description:** Return a factual mirror message if a dependency pattern is consolidated over the last 7 days.
    *   **Required:** None
*   **`get_misconceptions`**
    *   **Description:** List misconceptions detected per concept, with status and frequency.
    *   **Required:** None
*   **`record_session_close`**
    *   **Description:** Idempotently close the durable learning session and return structured recap.
    *   **Required:** None

---

### 🧠 4. Learner Modeling, Memory & Preferences
Tools for managing the learner's emotional state, memory, and profile.

*   **`record_affect`**
    *   **Description:** Record the learner's emotional state (energy, confidence, satisfaction).
    *   **Required:** `session_id`
*   **`update_learner_profile`**
    *   **Description:** Update learner-declared preferences (device, objective, language, affect baseline).
    *   **Required:** None
*   **`update_learner_memory`**
    *   **Description:** Write learner memory markdown files for session summaries, notes, or archives.
    *   **Required:** `scope`, `content`
*   **`get_memory_state`**
    *   **Description:** Inspect learner memory file counts, sizes, session bounds, and consolidation lag.
    *   **Required:** None
*   **`read_raw_session`**
    *   **Description:** Read one raw learner memory session by timestamp.
    *   **Required:** `timestamp`
*   **`list_implementation_intentions`**
    *   **Description:** List the learner's if-then practice commitments and their lifecycle state.
    *   **Required:** None
*   **`update_implementation_intention`**
    *   **Description:** Resolve one pending practice commitment as honored, missed, or cancelled.
    *   **Required:** `id`, `status`

---

### 📊 5. Analytics, Dashboards & Snapshots
Tools for retrieving comprehensive state views and decision replays.

*   **`get_dashboard_state`**
    *   **Description:** Return the learning state as structured JSON (per-concept progress, retention alerts, next action).
    *   **Required:** None
*   **`get_olm_snapshot`**
    *   **Description:** Return a transparent snapshot of model estimates and evidence-backed stages (retained, demonstrated, transferred).
    *   **Required:** None
*   **`get_pedagogical_snapshots`**
    *   **Description:** Read stored pedagogical decision snapshots for the authenticated learner.
    *   **Required:** None
*   **`get_decision_replay_summary`**
    *   **Description:** Build an offline replay summary from stored pedagogical snapshots (model deltas, suspicious jumps).
    *   **Required:** None

---

### ⏰ 6. Availability & Notifications
Tools for managing the learner's schedule and sending nudges.

*   **`get_availability_model`**
    *   **Description:** Retrieve learner-owned availability, IANA timezone, weekly windows, and notification consent.
    *   **Required:** None
*   **`update_availability_model`**
    *   **Description:** Replace the authenticated learner's availability and accessibility policy using `expected_version`.
    *   **Required:** `expected_version`, `timezone`, `preferred_windows`, `avg_session_duration_minutes`, `sessions_per_week`, `do_not_disturb`, `notification_consent`, `notification_frequency`, `max_notifications_per_day`, `accessibility_preferences`
*   **`queue_webhook_message`**
    *   **Description:** Queue a nudge message that the scheduler will post to the learner's Discord webhook at the desired window.
    *   **Required:** `kind`, `scheduled_for`