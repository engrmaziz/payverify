# PayVerify — Frontend

Next.js 14 frontend for school fee payment verification.
Dark UI, three pages: Landing, Student Verify, Admin Dashboard.

---

## Stack

- **Next.js 14** (App Router)
- **TypeScript**
- **CSS Modules** (zero external UI libraries)
- **Deploy target:** Vercel

---

## Local setup

```bash
# 1. Install dependencies
npm install

# 2. Configure environment
cp .env.local.example .env.local
# Edit .env.local — set your Railway backend URL

# 3. Run dev server
npm run dev
# → http://localhost:3000
```

---

## Pages

| Route | Description |
|---|---|
| `/` | Landing page with how-it-works |
| `/verify` | Student enters TxnID — auto-polls if not found yet |
| `/admin` | Admin login + parse-failed review queue |

---

## Deploy to Vercel (5 minutes)

### Option A — Vercel CLI

```bash
npm i -g vercel
vercel login
vercel
```

Follow the prompts. When asked for environment variables, add:
- `NEXT_PUBLIC_API_URL` → your Railway backend URL
- `NEXT_PUBLIC_ADMIN_KEY` → your admin secret

### Option B — Vercel Dashboard

1. Push this folder to a GitHub repo
2. Go to vercel.com → New Project → Import your repo
3. Add environment variables in Project Settings → Environment Variables:
   - `NEXT_PUBLIC_API_URL` = `https://your-app.up.railway.app`
   - `NEXT_PUBLIC_ADMIN_KEY` = your SMS_WEBHOOK_SECRET from backend
4. Deploy

---

## VS Code setup

Install these extensions for the best experience:
- **ESLint** (`dbaeumer.vscode-eslint`)
- **Prettier** (`esbenp.prettier-vscode`)
- **Tailwind CSS IntelliSense** (not used here, but useful for future)
- **ES7+ React/Redux/React-Native snippets**

Recommended `settings.json`:
```json
{
  "editor.formatOnSave": true,
  "editor.defaultFormatter": "esbenp.prettier-vscode"
}
```

---

## Project structure

```
src/
├── app/
│   ├── layout.tsx        ← root layout, imports global CSS
│   ├── globals.css       ← design tokens + base styles
│   ├── page.tsx          ← landing page
│   ├── page.module.css
│   ├── verify/
│   │   ├── page.tsx      ← student verification
│   │   └── verify.module.css
│   └── admin/
│       ├── page.tsx      ← admin dashboard
│       └── admin.module.css
└── lib/
    └── api.ts            ← typed API client (all fetch calls)
```

---

## Connecting to the backend

All API calls go through `src/lib/api.ts`.
The base URL is `NEXT_PUBLIC_API_URL` from your `.env.local`.

Make sure your FastAPI backend has CORS enabled for your Vercel domain.
In `app/main.py`, update:
```python
allow_origins=["https://your-app.vercel.app"]
```
