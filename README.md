# Clinic AI Assistant

This repository is a pre-production work environment for a clinic-focused AI assistant, not just a product snapshot. It contains the application itself, the supporting architecture around booking and scheduling, and the AI-assisted delivery workflow I used to move requirements from idea to verified code on `main`.

The project is being developed toward MVP release, so the repo intentionally shows both product implementation and the working environment used to shape, test, and stabilize that implementation.

Before post-MVP cleanup, this repository is optimized for solo development and CLI-based AI collaboration, not yet for extended team usage. After MVP, the structure should be streamlined to separate product code, workflow artifacts, and supporting development utilities more clearly.

## What This Repo Contains

1. Product code for a FastAPI-based clinic assistant with chat, booking, and scheduling capabilities.
2. A lightweight frontend used to exercise patient-facing flows and interaction patterns.
3. Tenant-driven configuration that keeps business wording and conversation rules outside Python code.
4. Scheduling infrastructure with provider abstraction, mock scheduling support, and Google Calendar integration.
5. Automated tests covering key backend and frontend integration paths.
6. Task and verification artifacts that document how requirements were approved, implemented, reviewed, and prepared for merge.
7. An AI collaboration workflow that I used as a practical developer tool rather than just a code generator.

## Why This Repo Exists

I built this project as both a product and a working engineering system.

The product goal is to support clinic-facing conversational flows such as:
- service discovery
- appointment intent capture
- booking confirmation
- scheduling availability lookup
- contact collection continuity across sessions

The engineering goal is to make delivery structured and repeatable. During MVP development I allowed the repository to grow naturally so I could learn what needed to exist around the product itself: architecture rules, scoped task files, verification checkpoints, testing discipline, and a stable AI-assisted workflow for shipping changes safely.

## How AI Was Used

AI was part of the development workflow throughout this repo.

I used AI to:
- break larger work into smaller prompt-sized implementation units
- compare implementation approaches before coding
- accelerate boilerplate and integration work
- propose and refine regression tests
- help document verification steps and prompt boundaries
- keep changes small enough to review and commit cleanly

The important part is that AI was not used as an autopilot. The repo reflects an increasingly stable process where a requirement is scoped, implemented, technically verified, manually checked when needed, and only then proposed for commit to `main`.

## Implemented

- FastAPI backend with `/chat`, `/config/{tenant}`, `/agent/{tenant}`, and `/health`
- scheduling endpoints for configuration, availability lookup, and booking
- OpenAI-powered response generation through the Responses API
- JSON tenant profiles for conversation rules and business-specific configuration
- lightweight HTML/JS frontend served by the backend
- SQLite-based lead checkpoint persistence
- booking state machine for confirmation, contact collection, and completion
- session-based booking continuity with completed-session rollover
- scheduling orchestration for availability-first requests
- mock scheduling provider for deterministic testing
- Google Calendar scheduling provider for live availability lookup and booking
- integration and regression coverage around booking and scheduling behavior

## Pre-Production Characteristics

This repo is useful to review as a case study because it shows work before final production cleanup.

That means it still includes evidence of:
- evolving repo structure during MVP development
- active task-management and verification documents
- decisions about what belongs in product code versus configuration
- experimentation around frontend shells and scheduling flow handling
- a growing but already stabilized AI-assisted delivery process

If I were preparing the long-term production repo today, I would further separate public product code, internal workflow artifacts, and archived implementation history. I left those layers together during MVP so I could optimize for learning speed and safe iteration first.

## Architecture Principles

- Configuration separation: Python contains logic and orchestration, while wording, triggers, and business-specific content live in tenant JSON.
- Verification before merge: tracked prompts are expected to stop at real execution boundaries so changes can be checked before they move forward.
- Scheduling isolation with integration paths: scheduling can be developed and tested in a controlled way while still connecting back into the main chat flow.
- Multi-tenant direction: the structure is designed so onboarding a new business should be driven primarily by configuration rather than backend rewrites.

## Current State

The system is functional as an MVP-stage clinic assistant, with working chat, booking-state handling, and scheduling support. It is not yet a polished production repository, and that is part of why I use it as a useful engineering case study: it shows how the product and the workflow around it matured together.

Current areas still being improved include:
- broader regression coverage
- stronger repo separation and cleanup ahead of release
- more complete multi-tenant hardening
- frontend/session-state polish
- production-oriented deployment and observability hardening

## Repository Layout

- `clinic-ai-assistant-src/backend/` - backend services, routing, orchestration, config loading, and tests
- `clinic-ai-assistant-src/frontend/` - lightweight frontend and scheduling/chat interaction surfaces
- `clinic-ai-assistant-src/configs/` - supporting configuration assets
- `clinic-ai-assistant-src/AI_sync/` - repository-level coordination and architecture context used during active development
- `clinic-ai-assistant docs/` - task files, planning material, architecture notes, and verification artifacts
- `clinic-ai-assistant-src/lessons_learned_repo/` - separate learning/history support layer outside the live runtime path

## What I Would Improve Next

The next major improvement would be repo structure cleanup for post-MVP life. Right now the repository intentionally acts as both product container and AI-collaboration work environment. After MVP, I would split those responsibilities more clearly so outside contributors could understand the codebase faster without losing the process discipline that helped the project move reliably.

## Why This Is A Good Case Study

This repo shows more than feature implementation. It shows how I think about:
- translating requirements into scoped execution steps
- keeping business wording out of backend logic
- validating higher-risk flows with tests and verification checkpoints
- using AI to improve delivery quality, not only coding speed
- evolving a codebase responsibly while still shipping toward an MVP deadline
