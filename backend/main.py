from fastapi import FastAPI
from app.api.routes import router
import uvicorn

app = FastAPI(title="Newsletter Summarizer API")

# Include the API routes
app.include_router(router)

@app.get("/")
def read_root():
    return {"message": "Backend is running!"}

if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=8000)
