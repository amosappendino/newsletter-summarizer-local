"use client";
import { useState, useEffect } from "react";
import { searchEmails, summarizeEmail } from "./services/api";

// Define types for email data
interface Email {
    id: number;
    sender: string;
    subject: string;
    preview?: string;
    received_at?: string;
    match_type?: string;
}

export default function HomePage() {
    const [query, setQuery] = useState<string>("");
    const [emails, setEmails] = useState<Email[]>([]);
    const [selectedEmail, setSelectedEmail] = useState<number | null>(null);
    const [summary, setSummary] = useState<string>("");
    const [isSearching, setIsSearching] = useState<boolean>(false);
    const [isSummarizing, setIsSummarizing] = useState<boolean>(false);
    const [searchError, setSearchError] = useState<string | null>(null);
    const [summaryError, setSummaryError] = useState<string | null>(null);
    const [isAuthenticated, setIsAuthenticated] = useState<boolean>(false);
    const [isLoading, setIsLoading] = useState<boolean>(true);

    // Add authentication check
    useEffect(() => {
        const checkAuth = async () => {
            try {
                const response = await fetch('http://localhost:8000/check-auth');
                const data = await response.json();
                
                if (data.status === 'unauthenticated') {
                    window.location.href = '/login';
                } else {
                    setIsAuthenticated(true);
                }
            } catch (error) {
                console.error('Error checking auth status:', error);
                window.location.href = '/login';
            } finally {
                setIsLoading(false);
            }
        };

        checkAuth();
    }, []);

    const handleSearch = async () => {
        if (!query.trim()) return;
        
        setIsSearching(true);
        setSearchError(null);
        setEmails([]); // Clear previous results

        try {
            const response = await searchEmails(query);
            if (Array.isArray(response)) {
                setEmails(response);
                if (response.length === 0) {
                    setSearchError("No emails found matching your search.");
                }
            } else {
                console.error("Invalid response format:", response);
                setSearchError("Error fetching emails. Please try again.");
            }
        } catch (error) {
            console.error("Error searching emails:", error);
            setSearchError("Failed to search emails. Please try again.");
        } finally {
            setIsSearching(false);
        }
    };

    const handleSummarize = async (emailId: number) => {
        if (isSummarizing) return;
        
        setSelectedEmail(emailId);
        setSummaryError(null);
        setIsSummarizing(true);

        try {
            const summary = await summarizeEmail(emailId);
            if (summary) {
                setSummary(summary);
            } else {
                setSummaryError("Failed to generate summary.");
            }
        } catch (error) {
            console.error("Error summarizing email:", error);
            setSummaryError("Failed to generate summary. Please try again.");
        } finally {
            setIsSummarizing(false);
        }
    };

    const handleLogout = async () => {
        try {
            const response = await fetch('http://localhost:8000/logout');
            const data = await response.json();
            
            if (response.ok) {
                // Clear local state
                setEmails([]);
                setSummary("");
                setQuery("");
                setIsAuthenticated(false);
                // Redirect to login page
                window.location.href = '/login';
            } else {
                console.error('Logout failed:', data);
            }
        } catch (error) {
            console.error('Error logging out:', error);
        }
    };

    if (isLoading) {
        return (
            <div className="min-h-screen flex items-center justify-center bg-gray-50">
                <div className="text-center text-gray-600">
                    Loading...
                </div>
            </div>
        );
    }

    if (!isAuthenticated) {
        return (
            <div className="min-h-screen flex items-center justify-center bg-gray-50">
                <div className="text-center text-gray-600">
                    Redirecting to login...
                </div>
            </div>
        );
    }

    return (
        <div className="min-h-screen flex flex-col items-center justify-center bg-gray-50 dark:bg-gray-900 p-8">
            <button
                onClick={handleLogout}
                className="absolute top-4 right-4 bg-red-500 text-white px-4 py-2 rounded-md hover:bg-red-600"
            >
                Logout
            </button>

            <h1 className="text-3xl font-bold text-gray-900 dark:text-white mb-6">
                Newsletter Summarizer
            </h1>

            <div className="w-full max-w-md space-y-4">
                <div className="flex space-x-2">
                    <input
                        type="text"
                        placeholder="Search emails by sender or subject..."
                        value={query}
                        onChange={(e) => setQuery(e.target.value)}
                        maxLength={100}
                        className="flex-1 border p-2 rounded"
                    />
                    <button
                        onClick={handleSearch}
                        disabled={isSearching || !query.trim()}
                        className={`bg-blue-500 text-white px-4 py-2 rounded-md ${
                            isSearching || !query.trim() ? 'opacity-50 cursor-not-allowed' : 'hover:bg-blue-600'
                        }`}
                    >
                        {isSearching ? 'Searching...' : 'Search'}
                    </button>
                </div>

                {searchError && (
                    <div className="text-red-600 bg-red-100 p-3 rounded-md">
                        {searchError}
                    </div>
                )}

                {emails.length > 0 && (
                    <ul className="space-y-2">
                        {emails.map((email) => (
                            <li
                                key={email.id}
                                onClick={() => !isSummarizing && handleSummarize(email.id)}
                                className={`cursor-pointer p-4 bg-white dark:bg-gray-800 rounded-md shadow-sm hover:shadow-md transition-shadow ${
                                    isSummarizing && selectedEmail === email.id ? 'opacity-50' : ''
                                }`}
                            >
                                <strong className="block text-gray-900 dark:text-white">{email.subject}</strong>
                                <span className="text-sm text-gray-600 dark:text-gray-400">{email.sender}</span>
                                
                                {isSummarizing && selectedEmail === email.id && (
                                    <p className="text-sm text-blue-500 mt-2">Generating summary...</p>
                                )}
                                {summaryError && selectedEmail === email.id && (
                                    <p className="text-sm text-red-600 mt-2">{summaryError}</p>
                                )}
                            </li>
                        ))}
                    </ul>
                )}

                {summary && selectedEmail && (
                    <div className="mt-8 p-6 bg-white dark:bg-gray-800 rounded-lg shadow-lg">
                        <h2 className="text-lg font-semibold mb-4 text-gray-900 dark:text-white">Summary</h2>
                        <p className="text-gray-700 dark:text-gray-300">{summary}</p>
                    </div>
                )}
            </div>
        </div>
    );
}
