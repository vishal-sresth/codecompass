---
name: frontend-setup
description: Scaffolds the CodeCompass web app (Next.js in web/) and the FastAPI server skeleton (server/) so both run locally and talk to each other. Use at Stage 5, or when the user says "set up the frontend", "scaffold the app" or "let's set up Next".
---

# Frontend and server setup

## Before starting
1. Read `docs/engineering/engineering-doc.md` and `docs/specs/`. If the stack differs from Next.js (App Router, TypeScript) plus FastAPI, confirm the deviation with the user.
2. Ask the user: create `web/` and `server/` fresh, or use existing folders? Do not overwrite existing files without asking.
3. Check current stable versions (`npm view next version`) and tell the user what you will pin. Do not hard-code versions from memory.

## Steps
1. `server/`: `main.py` with `GET /api/health` returning `{ok: true}` and CORS allowing only `http://localhost:3000`; `requirements.txt`. Do not call Foundry yet.
2. `web/`: Next.js (App Router, TypeScript) with one page and an `app/globals.css`. Read the API address from `NEXT_PUBLIC_API_URL` (default `http://localhost:8000`).
3. App Router rule: page and layout files are Server Components by default. Put anything with `onClick`, state or effects into a file that starts with `"use client"`. Never put event handlers on server components.
4. Show the final folder tree.
5. Start both servers (server on 8000, web on 3000), fetch `/api/health` from the page, and show "server: ok" on screen to prove the wiring.

## Output
A running skeleton: `web/`, `server/`, and a health check visible in the browser.

## Gate
Stop. Show the tree and the running page. Ask before building any feature (Stage 6), and apply `/design-system` to all UI code from the first component.
