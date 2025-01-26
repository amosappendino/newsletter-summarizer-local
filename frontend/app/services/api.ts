import axios from "axios";

// Base URL pointing to your backend API
const API_BASE_URL = "http://127.0.0.1:8000";

/**
 * Fetch emails by sender or subject.
 * @param query The search query for emails.
 * @returns List of matching emails (id, sender, subject).
 */
export const searchEmails = async (query: string) => {
    try {
        const response = await axios.get(`${API_BASE_URL}/search-emails/`, {
            params: { query },
        });
        return response.data;
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
export const summarizeEmail = async (emailId: number) => {
    try {
        const response = await axios.get(`${API_BASE_URL}/summarize-email/`, {
            params: { email_id: emailId },
        });
        return response.data;
    } catch (error) {
        console.error("Error summarizing email:", error);
        throw error;
    }
};
