import axios from "axios";

// Base URL pointing to your backend API
const API_BASE_URL = process.env.NEXT_PUBLIC_API_URL || "http://127.0.0.1:8000";

// Define interfaces for the response types
interface Email {
    id: number;
    sender: string;
    subject: string;
}

interface SummaryResponse {
    summary: string;
}

// Add new auth-related functions
export const signInWithGoogle = async () => {
    try {
        const response = await axios.get(`${API_BASE_URL}/auth/gmail`);
        // Redirect to Google's auth page
        window.location.href = response.data.auth_url;
    } catch (error) {
        console.error("Error during sign in:", error);
        throw error;
    }
};

export const checkAuth = async () => {
    try {
        const response = await axios.get(`${API_BASE_URL}/check-auth`);
        return response.data.isAuthenticated;
    } catch (error) {
        console.error("Error checking auth status:", error);
        return false;
    }
};

export const logout = async () => {
    try {
        await axios.get(`${API_BASE_URL}/logout`);
        return true;
    } catch (error) {
        console.error("Error during logout:", error);
        throw error;
    }
};

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
        // The backend returns { status, results }, we want the results array
        return response.data.results || [];
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
        const response = await axios.get(`${API_BASE_URL}/summarize-email/`, {
            params: { email_id: emailId },
        });
        // Return just the summary string from the response
        return response.data.summary || '';
    } catch (error) {
        console.error("Error summarizing email:", error);
        // Log more details about the error
        if (axios.isAxiosError(error) && error.response) {
            console.error("Server response:", error.response.data);
        }
        throw error;
    }
};
