import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.routes.sms import router as sms_router
from app.routes.verify import router as verify_router
from app.routes.admin import router as admin_router

# ── Logging ───────────────────────────────────────────────────────────────────
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
)
logger = logging.getLogger(__name__)


# ── Startup / shutdown ────────────────────────────────────────────────────────
@asynccontextmanager
async def lifespan(app: FastAPI):
    logger.info("School Payment Verification API starting up")
    yield
    logger.info("Shutting down")


# ── App ───────────────────────────────────────────────────────────────────────
app = FastAPI(
    title="School Payment Verification",
    description="SMS-based payment verification for Pakistani schools via Easypaisa, JazzCash, and Meezan.",
    version="1.0.0",
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],   # tighten to your frontend domain in production
    allow_methods=["*"],
    allow_headers=["*"],
)

# ── Routes ────────────────────────────────────────────────────────────────────
app.include_router(sms_router,    prefix="/api/v1")
app.include_router(verify_router, prefix="/api/v1")
app.include_router(admin_router,  prefix="/api/v1")


@app.get("/health", tags=["Health"])
def health():
    return {"status": "ok", "service": "school-payments"}
