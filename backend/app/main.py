from fastapi import FastAPI

from app.api.routes import router as api_router


def create_app() -> FastAPI:
    app = FastAPI(
        title="TCG Predictor API",
        version="0.1.0",
        description="Backend API for TCG / sports card market prediction MVP.",
    )

    app.include_router(api_router, prefix="/api")

    return app


app = create_app()


@app.get("/health", tags=["system"])
def health_check() -> dict:
    return {"status": "ok"}

