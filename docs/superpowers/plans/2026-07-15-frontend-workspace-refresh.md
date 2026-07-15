# Frontend Workspace Refresh Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Deliver a polished, responsive enterprise knowledge workspace while preserving all current Vue workflows and API contracts.

**Architecture:** Centralize color, spacing, typography, focus, table, dialog, and responsive rules in `global.css`. Keep page behavior inside existing Vue views and limit template changes to semantic structure, icons, empty states, and tool placement.

**Tech Stack:** Vue 3, TypeScript, Element Plus, Element Plus Icons, Vite, CSS.

## Global Constraints

- Do not change backend APIs or frontend data contracts.
- Do not use gradients, decorative orbs, oversized hero typography, nested cards, or viewport-scaled fonts.
- Use Element Plus icons for actions and retain accessible labels/tooltips.
- Preserve desktop and mobile workflows.

### Task 1: Global Design System And Application Shell

**Files:** Modify `frontend/src/styles/global.css`, `frontend/src/App.vue`.

- [ ] Add visual contract tests for required tokens, stable control sizing, and responsive breakpoints.
- [ ] Define neutral, graphite, blue, green, amber, and red semantic tokens.
- [ ] Restyle navigation, product identity, account menu, focus states, Element controls, dialogs, tables, and mobile shell.
- [ ] Verify the frontend build.

### Task 2: Chat Workspace

**Files:** Modify `frontend/src/views/Chat.vue`.

- [ ] Replace emoji identity and action labels with icon-based controls.
- [ ] Remove the duplicate account footer and add compact suggested questions to the empty state.
- [ ] Establish stable conversation rail, readable message rows, source list, tool strip, and bottom composer.
- [ ] Verify sending, stopping, image attachment, source opening, feedback, history switching, and mobile layout.

### Task 3: Login And Operational Pages

**Files:** Modify `frontend/src/views/Login.vue`, `frontend/src/views/Documents.vue`, `frontend/src/views/Evaluation.vue`, `frontend/src/views/Admin/Dashboard.vue`.

- [ ] Align page headers, toolbars, tables, metrics, dialogs, status chips, loading states, and pagination.
- [ ] Keep login compact and product-first with explicit service status.
- [ ] Verify role-gated actions and page-specific workflows remain present.

### Task 4: Visual Verification

**Files:** No production files unless defects are found.

- [ ] Run `npm run build`.
- [ ] Start a frontend preview or rebuild the Nginx-served assets.
- [ ] Capture desktop and mobile screenshots for login, chat, and documents.
- [ ] Check text overflow, control overlap, empty states, responsive navigation, and nonblank rendering.
- [ ] Run `git diff --check` and commit the refresh on `codex/frontend-workspace-refresh`.
