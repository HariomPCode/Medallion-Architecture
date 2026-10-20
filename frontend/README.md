# Finance Complaints Medallion — Frontend

The web user interface for the Finance Complaints Medallion platform. Built with Next.js App Router, TypeScript (strict mode), Tailwind CSS, Vitest, React Testing Library, MSW, and vitest-axe.

## Technology Stack

- **Framework:** [Next.js](https://nextjs.org/) (App Router, React 18, `src`-less structure)
- **Language:** [TypeScript](https://www.typescriptlang.org/) (Strict checking enabled)
- **Styling:** [Tailwind CSS](https://tailwindcss.com/) with `tailwindcss-animate`
- **Component Foundations:** [shadcn/ui](https://ui.shadcn.com/) conventions (`components.json`, `lib/utils.ts`)
- **Icons & Visuals:** [Lucide React](https://lucide.dev/), [Recharts](https://recharts.org/)
- **Data Management:** [@tanstack/react-query](https://tanstack.com/query), [@tanstack/react-table](https://tanstack.com/table)
- **API Typing:** [openapi-typescript](https://openapi-ts.dev/)
- **Testing:** [Vitest](https://vitest.dev/), [React Testing Library](https://testing-library.com/docs/react-testing-library/intro/), [MSW](https://mswjs.io/) (deterministic mocking), [vitest-axe](https://github.com/chaance/vitest-axe) (accessibility)
- **Runtime:** Node.js Active LTS (pinned via `.nvmrc`)

## Prerequisites

- **Node.js:** Node.js 22 LTS (as pinned in `.nvmrc`).
- **npm:** npm 10+.

Ensure your active Node.js version matches `.nvmrc`:

```bash
nvm use
# or
node -v
```

## Installation

Install project dependencies reproducibly using `npm ci`:

```bash
cd frontend
npm ci
```

For first-time or local development setups where `package-lock.json` is updated:

```bash
npm install
```

## Environment Configuration

Configuration variables are defined in `.env.example`:

```bash
cp .env.example .env.local
```

### Environment Variables

| Variable | Scope | Description |
| :--- | :--- | :--- |
| `BACKEND_BASE_URL` | Server-only (BFF) | URL of the backend FastAPI service (e.g. `http://localhost:8000`). Never exposed to browser bundles. |
| `INTERNAL_API_KEY` | Server-only (BFF) | Pre-shared secret injected by Next.js BFF proxy into `X-Internal-Key` headers for backend requests. Never exposed to browser bundles. |
| `NEXT_PUBLIC_APP_NAME` | Client / Browser | Public application branding title. Safe for client exposure. |

> [!CAUTION]
> **Security Boundary:** Never prefix backend credentials, `INTERNAL_API_KEY`, Azure OpenAI keys, or storage credentials with `NEXT_PUBLIC_`. All backend communication flows through Next.js server route handlers (BFF proxy pattern).

## Available Scripts

All scripts are executed from the `frontend/` directory:

| Command | Action |
| :--- | :--- |
| `npm run dev` | Starts the Next.js development server at `http://localhost:3000`. |
| `npm run build` | Compiles the production build into `.next/`. |
| `npm run start` | Runs the compiled production server. |
| `npm run lint` | Runs Next.js ESLint checks (`next lint`). |
| `npm run typecheck` | Runs the TypeScript compiler check without emitting output (`tsc --noEmit`). |
| `npm test` | Runs the Vitest test suite once with coverage support. |
| `npm run test:watch` | Starts Vitest in interactive watch mode. |
| `npm run gen:api` | Regenerates TypeScript API schemas from `docs/openapi.json`. |

## Testing Infrastructure

The testing setup integrates four pillars:

1. **Vitest:** Fast ESM-native test runner running in a simulated DOM environment (`jsdom`).
2. **React Testing Library:** User-centric DOM testing utilities ensuring components render and behave accessibly.
3. **MSW (Mock Service Worker):** Intercepts network requests at the transport level for deterministic API simulation without hitting live services.
4. **vitest-axe:** Automated accessibility assertion library ensuring WCAG 2.1 compliance (`expect(results).toHaveNoViolations()`).

Run all tests:

```bash
npm test
```

## Continuous Integration

The frontend CI workflow is located at `.github/workflows/frontend-ci.yml`. On every push and pull request touching `frontend/**`:

1. Installs Node.js matching `.nvmrc`.
2. Runs `npm ci`.
3. Validates linting: `npm run lint`.
4. Validates typing: `npm run typecheck`.
5. Executes automated tests: `npm test`.
6. Builds production bundle: `npm run build`.
