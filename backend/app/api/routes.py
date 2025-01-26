from fastapi import APIRouter, Query, HTTPException
import psycopg2
import os
from dotenv import load_dotenv
import openai

# Load environment variables
load_dotenv()

# Database connection config
DB_CONFIG = {
    'dbname': os.getenv('DB_NAME'),
    'user': os.getenv('DB_USER'),
    'password': os.getenv('DB_PASSWORD'),
    'host': os.getenv('DB_HOST'),
    'port': os.getenv('DB_PORT'),
}

# OpenAI API Key
openai.api_key = os.getenv('OPENAI_API_KEY')

router = APIRouter()

@router.get("/")
def read_root():
    return {"message": "Hello from API"}

def get_email_list(query):
    """Fetch email metadata (id, sender, subject) based on sender or subject query."""
    try:
        conn = psycopg2.connect(**DB_CONFIG)
        cur = conn.cursor()
        cur.execute("SELECT id, sender, subject, received_at FROM emails WHERE sender ILIKE %s OR subject ILIKE %s",
                    (f'%{query}%', f'%{query}%'))
        emails = cur.fetchall()
        cur.close()
        conn.close()
        return [{"id": row[0], "sender": row[1], "subject": row[2], "received_at": row[3]} for row in emails]
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

def get_email_content(email_id):
    """Fetch the content of a specific email by ID."""
    try:
        conn = psycopg2.connect(**DB_CONFIG)
        cur = conn.cursor()
        cur.execute("SELECT body FROM emails WHERE id = %s", (email_id,))
        email_body = cur.fetchone()
        cur.close()
        conn.close()
        if email_body:
            return email_body[0]
        else:
            raise HTTPException(status_code=404, detail="Email not found.")
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

def summarize_content(email_body):
    """Use OpenAI to summarize a single email."""
    prompt = f"Summarize the following email:\n{email_body}"
    response = openai.ChatCompletion.create(
        model="gpt-3.5-turbo",
        messages=[
            {"role": "system", "content": "Summarize the email, keeping key insights with sufficient detail."},
            {"role": "user", "content": prompt}
        ],
        max_tokens=500
    )
    
    summary = response['choices'][0]['message']['content']

    # Extract token usage info from API response
    token_usage = response.get('usage', {})
    input_tokens = token_usage.get('prompt_tokens', 0)
    output_tokens = token_usage.get('completion_tokens', 0)
    total_tokens = token_usage.get('total_tokens', 0)

    # Cost estimation based on model pricing
    cost_per_1k_input = 0.0005  # GPT-3.5-turbo input cost
    cost_per_1k_output = 0.0015  # GPT-3.5-turbo output cost

    input_cost = (input_tokens / 1000) * cost_per_1k_input
    output_cost = (output_tokens / 1000) * cost_per_1k_output
    total_cost = input_cost + output_cost

    print(f"Tokens used - Input: {input_tokens}, Output: {output_tokens}, Total: {total_tokens}")
    print(f"Estimated Cost: ${total_cost:.6f}")

    return summary

@router.get("/search-emails/")
async def search_emails(query: str = Query(..., description="Search emails by sender or subject")):
    emails = get_email_list(query)
    if not emails:
        return {"message": "No emails found for the given query."}
    return {"query": query, "emails": emails}

@router.get("/summarize-email/")
async def summarize_email(email_id: int = Query(..., description="ID of the email to summarize")):
    email_body = get_email_content(email_id)
    summary = summarize_content(email_body)
    return {"email_id": email_id, "summary": summary}
