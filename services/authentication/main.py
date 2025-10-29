from fastapi import FastAPI

app = FastAPI()


@app.get("/")
def root():
    """Root endpoint: give a short description and point to /health."""
    return {"message": "Authentication service", "health": "/health"}


@app.get("/health")
def health_check():
    return {"status": "ok"}
