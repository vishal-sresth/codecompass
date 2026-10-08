# CodeCompass web app

Next.js (App Router, TypeScript) front end for CodeCompass. It only talks to the local API server (`NEXT_PUBLIC_API_URL`, default http://localhost:8000).

- Run: `npm install` then `npm run dev` (port 3000). Start the API first (see the project README).
- Checks: `npm run lint`, `npx tsc --noEmit`, `npm run build`.
- Design tokens: `app/globals.css` (documented in `../docs/design.md`). Behaviour and wording: `../docs/specs/ui-states.md`.
- Project overview, setup and the demo script: see the project `README.md` and `docs/DEMO.md` in the parent folder.
