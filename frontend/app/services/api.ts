import axios from "axios";

// Base URL pointing to your backend API
const API_BASE_URL = "http://127.0.0.1:8000";

// Define interfaces for the response types
interface Email {
    id: number;
    sender: string;
    subject: string;
}

interface SummaryResponse {
    summary: string;
}

/**
 * Fetch emails by sender or subject.
 * @param query The search query for emails.
 * @returns List of matching emails (id, sender, subject).
 */
export const searchEmails = async (query: string): Promise<Email[]> => {
    try {
        const response = await axios.get(`${API_BASE_URL}/search-emails/`, {
            params: { query },
        });
        // Ensure we're returning an array
        return Array.isArray(response.data) ? response.data : [];
    } catch (error) {
        console.error("Error fetching emails:", error);
        throw error;
    }
};

/**
 * Summarize the email content by email ID.
 * @param emailId The ID of the email to summarize.
 * @returns Summarized content of the email.
 */
export const summarizeEmail = async (emailId: number): Promise<string> => {
    try {
        const response = await axios.get<SummaryResponse>(`${API_BASE_URL}/summarize-email/`, {
            params: { email_id: emailId },
        });
        // Return just the summary string from the response
        return response.data.summary || '';
    } catch (error) {
        console.error("Error summarizing email:", error);
        throw error;
    }
};
