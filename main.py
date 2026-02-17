from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from app.routes import psychology_router, neuroscience_router

app = FastAPI(
    title="Mental Health Assessment API",
    description="API for psychology and neuroscience assessments",
    version="1.1.0",
    docs_url="/docs",
    redoc_url="/redoc"
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(psychology_router)
app.include_router(neuroscience_router)


@app.get("/")
async def root():
    """API root endpoint"""
    return {
        "message": "Mental Health Assessment API",
        "version": "1.1.0",
        "endpoints": {
            "psychology": {
                "get_questions": "GET /psychology",
                "submit_answers": "POST /psychology/submit"
            },
            "neuroscience": {
                "get_questions": "GET /neuroscience/questions",
                "submit_answers": "POST /neuroscience/submit"
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
