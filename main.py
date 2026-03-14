from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles

from app.routes import psychology_router, neuroscience_router, letter_router, astrology_router, comprehensive_router, history_router
from app.auth import auth_router
from app.database import init_db
import os


@asynccontextmanager
async def lifespan(app: FastAPI):
    # Create database tables on startup
    await init_db()
    yield

from fastapi.security import OAuth2PasswordBearer
from fastapi.openapi.models import OAuthFlows as OAuthFlowsModel
from fastapi.openapi.models import OAuthFlowPassword

app = FastAPI(
    title="Mental Health Assessment API",
    description="API for psychology, neuroscience, letter science, astrology assessments, and comprehensive AI video generation",
    version="1.5.0",
    docs_url="/docs",
    redoc_url="/redoc",
    lifespan=lifespan,
    swagger_ui_init_oauth={
        "usePkceWithAuthorizationCodeGrant": True,
        "clientId": "your_client_id",
    },
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(auth_router)
app.include_router(psychology_router)
app.include_router(neuroscience_router)
app.include_router(letter_router)
app.include_router(astrology_router)
app.include_router(comprehensive_router)
app.include_router(history_router)

# Serve generated media files (audio/video)
os.makedirs("videos", exist_ok=True)
app.mount("/media", StaticFiles(directory="videos"), name="media")


@app.get("/")
async def root():
    """API root endpoint"""
    return {
        "message": "Mental Health Assessment API with AI Video Generation",
        "version": "1.4.0",
        "endpoints": {
            "psychology": {
                "get_questions": "GET /psychology",
                "submit_answers": "POST /psychology/submit",
                "generate_video": "POST /psychology/generate-video"
            },
            "neuroscience": {
                "get_questions": "GET /neuroscience/questions",
                "submit_answers": "POST /neuroscience/submit"
            },
            "letter": {
                "analyze": "POST /letter/analyze",
                "dictionary": "GET /letter/dictionary"
            },
            "astrology": {
                "analyze": "POST /astrology/analyze",
                "generate_video": "POST /astrology/generate-video"
            },
            "comprehensive": {
                "submit_all": "POST /comprehensive/submit",
                "generate_video": "POST /comprehensive/generate-video"
            },
            "documentation": "/docs"
        }
    }


@app.get("/health")
async def health_check():
    """Health check endpoint"""
    return {"status": "healthy"}


if __name__ == "__main__":
    import uvicorn
    import os
    port = int(os.environ.get("PORT", 8000))
    uvicorn.run(app, host="0.0.0.0", port=port)
