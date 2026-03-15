# PayVerify — Complete Project

Two deployable packages:

| Folder | What | Deploy to |
|---|---|---|
| `frontend/` | Next.js UI (Landing + Verify + Admin) | Vercel |
| `backend/` | FastAPI + Groq + Supabase | Railway |

## Quick start order

1. `backend/` → deploy to Railway first, get your URL
2. `frontend/` → set `NEXT_PUBLIC_API_URL` to that Railway URL, deploy to Vercel
3. Install HTTP SMS app on admin phone, point it at Railway URL
4. Done ✅

See `backend/README.md` and `frontend/README.md` for full setup guides.
