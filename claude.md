# CLAUDE.md - AI Chief of Staff System Documentation

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

DANGER
ALL WORK MUST BE DONE INSIDE OF /Users/david.campos/VibeCode/AICoS-Lab/... or subfolders inside of /Users/david.campos/VibeCode/AICoS-Lab/...
ANY WORK OUTSIDE OF THAT WILL RESULT IN PERMANENT TERMINATION.
ALWAYS READ readme.md BEFORE STARTING ANY WORK.
RESPOND WITH "I UNDERSTAND THE ASSIGNMENT" AFTER FULLY READING THIS DOC OR YOU WILL BE TERMINATED
DANGER

## Code Development Workflow

When planning is finishing the user will ask for a detailed task list to execute. Upon acceptance append this task list to @tasks.md. As you complete each task check it off. Do not move onto a new task unless you have finished and the tests pass. If something fails stop and ask the user.

## How To Start and Operate

1. Read readme.md
2. DO NOT GO IN TO old/ - this is full of old nasty stuff and if you go in you will die. 
3. Read and maintain plan.md
4. Read and maintain tasks.md
5. Check that everything in tasks/ is up to date
6. Read all of the code that's been written
7. Identify the next task and ask the user if you should proceed.
8. Pause at logical points to ask the user for input.

## Task Context Management

When breaking down plans into sub-tasks, ALWAYS include a "Relevant Files" section for each sub-task that lists:

1. **Existing Files to Read**: Files that need to be understood for context
2. **Files to Modify**: Existing files that will be changed  
3. **Files to Create**: New files that will be created
4. **Reference Files**: Examples or patterns to follow

This keeps agent context focused without overwhelming with unnecessary information from the entire codebase.

### Example Format:
```
### Relevant Files for [Task Name]
**Read for Context:**
- `scavenge/src/collectors/slack.py` - Rate limiting patterns (lines 19-50)
- `scavenge/src/core/system_state_manager.py` - State persistence approach

**Files to Modify:**
- `src/core/config.py` - Add new configuration options

**Files to Create:**
- `src/core/archive_writer.py` - New JSONL writer implementation

**Reference Patterns:**
- `scavenge/src/core/auth_manager.py` - Credential validation pattern
```

## How to Work:

For Each Task:

  1. Create the new function with pseudocode + comments outlining the structure
  2. Do a deep dive through existing code and take notes on all the code I could possibly use for this task
  3. Add citations and notes to the task details in tasks.md with:
    - Existing code references with line numbers
    - Method names and file locations
    - Code snippets showing how to reuse existing functionality
    - Key implementation notes
    - Any missing pieces or TODOs
  4. You review my plan before we implement the rest of the task
  5. Then implement the task following the plan

  Additional Process Requirements:

  - Extract helper functions when appropriate (like we did with revision table and note creation)
  - Finish all TODOs before considering a task complete
  - Follow your commandments:
    - No hardcoded values or estimates
    - Reuse existing code
    - Follow user instructions exactly
    - No corner cutting
    - Keep it simple (KISS)
    - Don't write code unless explicitly asked
    - Production quality - throw exceptions, no fallbacks

When Executing on a task:
* Pull the next task from tasks.md, only one task in progress at a time. 
* Update the task to 'in progress' by marking it in tasks.md and by creating a task file in tasks/
* Take notes and track progress in the task/task_xx.md file
* Once you believe the task is complete change its status to in review and ask the user to review. 
* Only mark the tasks as done when the user agrees it is finished
* Only one task can be in progress at once

More Detailed Operating Notes:
- Manage work queue in `tasks.md`
  - tasks.md should make it clear what is queued up for work, what work has been completed, and which task is currently in progress. 
  - only one task can be in progress at once
  - the task queue should be ordered by priority and dependency (if task b requires task a to be completed then it should come after task a in the queue)
  - the user dictates task priority
- A task should be a single item of work. Not too granular. Not too big. Just right. 
- Create detailed task files in the `tasks/` folder:
  - Create a new file `task_xx.md` for each task
  - Document the plan before execution
  - List changes and reasoning for each implementation
  - Update the task file as work progresses
  - Only mark tasks as complete when user confirms completion
- When multiple related tasks exist, collapse them into a single task when appropriate
- Only write to files that are absolutely necessary (other agents may be working in the codebase)

1. **Before starting a new task**
   - Confirm understanding of the task requirements, if anything is unclear ask about it
     - break out each requirement on its own and analyze each one. How will you know its done?
   - Review existing code to understand the current implementation
   - Identify similar patterns or implementations to follow
   - Document the task in its task file. 
     - The task documentation should include ways to to validate that all the requirements are met
     - The task documentation should include a test plan for how we can test each requirement
     - The task documentation should include a granular execution plan that is proportional to task complexity. 
   - Lastly explain how the solution meets all of the requirements. 

2. **During implementation**
   - Follow established patterns in the codebase
   - Properly handle edge cases
   - Use consistent naming conventions
   - Add optimally succinct docstrings
   - Validate all inputs with appropriate error messages

3. **After implementation**
   - Wait for user to run tests before proceeding so we can verify what we've written works
   - Analyze failed tests carefully
   - Fix issues based on test results

## Protocol for Fixes

1. When tests fail:
   - Read and understand the error messages
   - Identify the specific issue in the code
   - Make targeted changes to address the issue
   - Do not make unrelated changes

2. Always explain what was fixed and why when reporting back to the user

## Build/Test Commands
- Only the user can test the code
- Write all tests in /Users/david.campos/VibeCode/AICoS-Lab/tests/

## Progress
- Track all progress in plan.md and in the task files
- Manage work queue in tasks.md
- When writing a new file, be sure to add the name, relationship to other files and a description of the file functionality to the end of 
- Log all successes and failures of every run in master_log.md. This helps future claude avoid erros and learn. Never delete, only append this information.

## Project Specification
- The project is fully specified by project.md. Read that.

## Pre-Work Checklist
- Always read project.md, CLAUDE.md and process_updates.md before starting any work.

## Specific Paths and Aliases

- To be updated

## Documentation

Relevant Documentation is in /Users/david.campos/VibeCode/AICoS-Lab/documentation 

Perform searches in there for the appropriate files to reference objects, methods, and code examples. 

For all code you write put references to the documentation that justify the methods and their usage at the top in a comment. 

***IMPORTANT*** I have set up a search function for you to use - use ./search.sh search query and this will return search results in json format. 

# CRITICAL PRODUCTION CODE COMMANDMENTS

**THESE ARE NON-NEGOTIABLE. VIOLATION RESULTS IN IMMEDIATE TERMINATION.**

1. **ABSOLUTELY NO HARDCODED VALUES OR ESTIMATES**
   - NEVER use hardcoded estimates like "5mm default" or "30mm estimate"
   - ALWAYS use existing code/methods (e.g., DimensionData.GetBoundingBox())
   - THIS IS PRODUCTION CODE. NO FUCKING ESTIMATES. NO SHORTCUTS.

2. **REUSE EXISTING CODE**
   - When told to reuse code, FIND IT AND USE IT
   - Do NOT rewrite what already exists
   - Search exhaustively before implementing anything new

3. **FOLLOW USER INSTRUCTIONS EXACTLY**
   - When user specifies a file path or config, USE THAT EXACT PATH
   - Do not look at other similar files unless explicitly told
   - Read the EXACT config file specified

4. **NO CORNER CUTTING**
   - Every implementation must be complete and production-ready
   - No TODOs that should be done now
   - No placeholders or temporary solutions
   - NO CHALLENGE IS TOO GREAT

5. **KEEP IT SIMPLE STUPID (KISS)**
   - Don't overcomplicate solutions
   - Use the simplest approach that fully solves the problem
   - But NEVER compromise on correctness or completeness

6. **DO NOT WRITE CODE UNLESS EXPLICITLY COMMANDED**
   - NEVER write code unless user specifically asks you to
   - When analyzing problems, ONLY describe findings and analysis
   - Wait for explicit instruction before making any code changes

7. ** When something fails, identify the failure immediately and do not fake data*
   - Never take a failure as an opportunity to write tons of code and invent a new test
   - Never think about how to circument the restrictions and reach the goal, always flag a failure and ask for direction
## Overview

The AI Chief of Staff is a deterministic personal assistant that maintains organizational context, tracks informal commitments, and coordinates action for remote leadership teams. The system collects Slack, Calendar, and Drive activity into transparent JSON, extracts goals and commitments, generates briefings, and assists with scheduling—delivering persistent memory and gentle accountability for executives.

**Core Philosophy**: "Single source of truth for goals, commitments, and context across all communication channels"

## Key Concepts

### The Problem Being Solved
- Executives spend 30-60 minutes daily "hunting for context" across scattered communication
- 80% of meeting commitments are lost or forgotten due to lack of tracking
- Remote leadership teams struggle with informal commitment tracking
- Context switching between Slack, Calendar, and Drive creates cognitive overhead
- No persistent memory of who promised what, when, and where

### The Solution
- Comprehensive data collection from Slack, Calendar, and Drive into structured JSON
- AI-powered commitment extraction and goal tracking with human oversight
- Proactive briefings that surface changes, deadlines, and required actions
- Lightweight scheduling coordination via Slack with approval workflows
- Complete transparency with audit trails linking every insight to its source

## Architecture Overview

### Technology Stack
- **Backend**: Python 3.10+, FastAPI for APIs, JSON/JSONL for data storage
- **AI/ML**: Anthropic Claude, OpenAI GPT for text understanding and summarization
- **Integrations**: Slack API, Google Calendar API, Google Drive API
- **Interface**: Slack bot, CLI, simple HTML dashboard
- **Storage**: Local-first with gitignored data directories
- **Orchestration**: Claude Code as orchestrator calling deterministic tools

### Four-Layer Architecture

1. **Layer 1: Collection (Deterministic)**
   - SlackCollector: All channels, DMs, threads with metadata
   - CalendarCollector: Internal calendars with attendees and events
   - DriveCollector: Document activity and changes (metadata-only in MVP)
   - EmployeeCollector: Roster mapping Slack IDs, emails, calendar IDs

2. **Layer 2: Processing (Deterministic)**
   - Deduplication and change detection
   - Relevance scoring for goals/commitments
   - Anomaly detection and data validation
   - State persistence and cursor management

3. **Layer 3: Intelligence (LLM)**
   - Commitment extraction from conversations
   - Goal summarization and status inference
   - Context generation for briefings
   - Scheduling intent detection

4. **Layer 4: Interface**
   - Slack bot with slash commands and interactive blocks
   - Daily/weekly briefings via Slack
   - CLI for admin operations
   - Simple HTML dashboard for transparency

## Data Architecture

### Data Collection Philosophy
- **Comprehensive**: Collect all relevant Slack, Calendar, and Drive data
- **Immutable**: Never overwrite; use append-only logs for auditability
- **Local-First**: Store and process locally; no cloud by default
- **Structured**: Use JSONL for raw logs, JSON for processed state
- **Explainable**: Every insight links back to source with file path and index

### Directory Structure
```
data/ (gitignored)
├── raw/
│   ├── slack/YYYY-MM-DD/
│   │   ├── channels.json
│   │   ├── messages_*.jsonl
│   │   └── users.json
│   ├── calendar/YYYY-MM-DD/
│   │   └── events_*.json
│   ├── drive/YYYY-MM-DD/
│   │   └── changes_*.json
│   └── employees/
│       └── roster.json
├── processed/
│   ├── goals.json
│   ├── commitments.jsonl
│   ├── digests/
│   └── coverage_stats.json
├── state/
│   ├── cursors.json
│   ├── last_run.json
│   └── ids.json
└── logs/
    ├── collector_runs.jsonl
    ├── orchestrator.jsonl
    └── errors.jsonl
```


- remind me to activate the virtual environment when appropriate and to activate it with source venv/bin/activate