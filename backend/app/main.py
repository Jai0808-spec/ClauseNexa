from fastapi import FastAPI

from app.routes.contracts import router as contracts_router


app = FastAPI(
    title="ClauseNexa API",
    description="Backend API for ClauseNexa Legal Contract Analysis and Risk Detection System",
    version="0.1.0"
)


@app.get("/")
def root():
    return {
        "message": "ClauseNexa API is running"
    }


@app.get("/health")
def health_check():
    return {
        "status": "healthy"
    }


app.include_router(contracts_router)