from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from google.cloud import storage
import os
import uvicorn
import requests
from dotenv import load_dotenv
from app.api.routes import router

# Load environment variables
load_dotenv()

# Set Google Cloud credentials
credentials_path = "google_secrets.json"
if not os.path.exists(credentials_path):
    raise ValueError(f"Google Cloud credentials file not found: {credentials_path}")

os.environ["GOOGLE_APPLICATION_CREDENTIALS"] = credentials_path

# Initialize Google Cloud Storage client
storage_client = storage.Client()
bucket_name = os.getenv("BUCKET_NAME")
if not bucket_name:
    raise ValueError("BUCKET_NAME environment variable is not set")

bucket = storage_client.bucket(bucket_name)

app = FastAPI(title="Newsletter Summarizer API")

# Configure CORS
origins = [
    "http://localhost:3000",
    "https://newsletter-summarizer-omega.vercel.app",
    # Allow all Vercel preview URLs
    "https://*.vercel.app"
]

app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    allow_origin_regex=r"https://.*\.vercel\.app$",  # This allows all Vercel preview URLs
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include the router
app.include_router(router)

@app.get("/")
def read_root():
    return {"message": "Backend is running!"}

@app.post("/upload")
async def upload_image(image_url: str):
    """Uploads an image from a given URL to Google Cloud Storage."""
    try:
        response = requests.get(image_url)
        if response.status_code != 200:
            raise HTTPException(status_code=400, detail="Failed to fetch image from URL")

        content_type = response.headers.get("content-type", "image/png")
        extension = content_type.split("/")[-1]

        # Generate a unique filename
        blob_name = f"uploads/{os.urandom(8).hex()}.{extension}"
        blob = bucket.blob(blob_name)

        # Upload the image
        blob.upload_from_string(response.content, content_type=content_type)

        # Make the file publicly accessible
        blob.make_public()

        return {"image_url": blob.public_url}

    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0")