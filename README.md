# AI Study Deadline Assistant

Starter project for the **Development of AI Applications** course final group project.

## Team members

- Member 1 Dmytro Krempovskyy (amk1002944@student.hamk.fi)
- Member 2: Vindya Nukulasooriya (amk1001863@student.hamk.fi)
- Member 3 Lien Pham (amk1002343@student.hamk.fi)
- Member 4: Dan Le (dan23001@student.hamk.fi)

## Problem

### Intended users

University students who manage coursework, assignments, and deadlines through Moodle.

### Problem statement

Students can see when assignments are due, but it can be difficult to decide when they should start working on them.

Different assignments require different amounts of time and effort. Starting too late can lead to rushed work and missed deadlines.

### Why AI is appropriate

Assignment descriptions contain unstructured natural language and can vary significantly between courses.

An LLM can interpret the assignment description, identify the type and complexity of the task, and produce an estimated workload.

Traditional fixed rules would have difficulty handling the different ways assignments are described.

## Solution

The AI Study Deadline Assistant helps students plan when to start their assignments.

The application reads assignment information, uses an AI model to estimate the workload, and calculates a recommended starting time before the deadline.

Example:

Assignment description  
- AI workload estimate  
- Recommended start date  
- Student reminder

## Main user workflow

1. **Get assignment:** The application receives assignment information and its deadline.
2. **Process assignment:** The service layer validates and prepares the assignment description.
3. **AI analysis:** The local LLM analyses the assignment and returns a structured workload estimate.
4. **Planning:** The application calculates a recommended start time using the estimate, deadline, and a safety buffer.
5. **User output:** The student sees the assignment, estimated workload, and recommended start time.

## Architecture

Initial architecture:

![AI Study Deadline Assistant Architecture](docs/DAIA_architecture.svg)

> **Core Architectural Rule:** The user interface does not communicate directly with the model or Ollama. Model interaction passes through the application/service layer.

## Model

- **Model used:** To be decided/tested
- **Selection rationale:** A local Ollama chat model capable of understanding assignment descriptions and producing reliable structured output.

## Additional AI capability

Possible capability:

- [ ] Tools / External integration (planned: Moodle iCal)
- [ ] Memory / Persistent state (possible later extension)
- [ ] Other capabilities if justified later

### Capability justification

The application may integrate with a student's Moodle calendar/iCal feed to obtain assignment information automatically.

This allows the AI component to analyse real assignment descriptions instead of requiring the student to manually copy every assignment into the application.

## Setup

Setup instructions will be updated as the application is developed.

The project is expected to use:

- Python
- Ollama
- Local LLM
- Pydantic
- A suitable user interface
- Moodle iCal integration (planned)

## Evaluation

We will test the application using representative assignment descriptions with different workload levels.

Evaluation can check:

- whether the assignment is interpreted correctly;
- whether the workload estimate is reasonable;
- whether structured output is valid;
- whether the recommended start time is calculated correctly;
- whether the application handles incomplete or unclear assignment information safely.

## Known limitations

- AI workload estimates may be inaccurate.
- Assignment descriptions may not contain enough information for a reliable estimate.
- Actual working time differs between students.
- Moodle/iCal data availability may vary.
- Recommended start times should be treated as planning assistance rather than guaranteed estimates.

## Future improvements

Possible future extensions:

- Telegram notifications
- Student feedback after completing an assignment
- Persistent storage of actual completion times
- Personalized workload estimates
- Natural-language commands such as "What's due this week?"
- Snoozing or rescheduling reminders