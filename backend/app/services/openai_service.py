import openai
import os
from dotenv import load_dotenv

load_dotenv()
openai.api_key = os.getenv('OPENAI_API_KEY')

async def get_summary(subject: str, body: str) -> str:
    try:
        # Clean up forwarded email content
        cleaned_body = body
        if "---------- Forwarded message ---------" in body:
            # Try to get the actual content after the forwarded header
            parts = body.split("---------- Forwarded message ---------")
            if len(parts) > 1:
                cleaned_body = parts[1].split("\n\n", 1)[1] if "\n\n" in parts[1] else parts[1]

        # Basic encoding error handling
        try:
            cleaned_body = cleaned_body.encode('utf-8').decode('utf-8')
        except UnicodeError:
            return "Error: Unable to process email content due to encoding issues."

        # Truncate email body to roughly 500 tokens
        max_chars = 2000
        truncated_body = cleaned_body[:max_chars] + "..." if len(cleaned_body) > max_chars else cleaned_body

        response = openai.ChatCompletion.create(
            model="gpt-3.5-turbo",
            messages=[
                {"role": "system", "content": "Create a concise summary focusing only on the most important points. If this is a forwarded email, focus on the main content. Maintain the original language of the content."},
                {"role": "user", "content": f"Subject: {subject}\n\nBody:\n{truncated_body}"}
            ],
            max_tokens=150,
            temperature=0.5
        )
        
        return response['choices'][0]['message']['content']
    except Exception as e:
        return f"Error summarizing email: {str(e)}"  # Return error message instead of raising 