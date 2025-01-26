"use client";
import { useState } from "react";
import { searchEmails, summarizeEmail } from "./services/api";

export default function HomePage() {
    const [query, setQuery] = useState("");
    const [emails, setEmails] = useState<any[]>([]);
    const [selectedEmail, setSelectedEmail] = useState<number | null>(null);
    const [summary, setSummary] = useState("");
    const [isSearching, setIsSearching] = useState(false);
    const [isSummarizing, setIsSummarizing] = useState(false);
    const [searchError, setSearchError] = useState<string | null>(null);
    const [summaryError, setSummaryError] = useState<string | null>(null);

    const handleSearch = async () => {
        try {
            setIsSearching(true);
            setSearchError(null);
            const response = await searchEmails(query);
            setEmails(response.emails || []);
        } catch (error) {
            console.error("Error fetching emails:", error);
            setSearchError("Failed to fetch emails. Please try again.");
        } finally {
            setIsSearching(false);
        }
    };

    const handleSummarize = async (emailId: number) => {
        try {
            setSelectedEmail(emailId);
            setIsSummarizing(true);
            setSummaryError(null);
            const response = await summarizeEmail(emailId);
            setSummary(response.summary);
        } catch (error) {
            console.error("Error summarizing email:", error);
            setSummaryError("Failed to generate summary. Please try again.");
        } finally {
            setIsSummarizing(false);
        }
    };

    return (
        <div className="min-h-screen flex flex-col items-center justify-center bg-gray-50 dark:bg-gray-900 p-8">
            <h1 className="text-3xl font-bold text-gray-900 dark:text-white mb-6">
                Newsletter Summarizer
            </h1>
            <input
                type="text"
                placeholder="Search emails by sender or subject..."
                value={query}
                onChange={(e) => setQuery(e.target.value)}
                maxLength={100}
                className="border p-2 rounded w-full max-w-md mb-4"
            />
            <button
                onClick={handleSearch}
                disabled={isSearching}
                className={`bg-blue-500 text-white px-4 py-2 rounded-md ${
                    isSearching ? 'opacity-50 cursor-not-allowed' : ''
                }`}
            >
                {isSearching ? 'Searching...' : 'Search Emails'}
            </button>

            {searchError && (
                <div className="mt-4 text-red-600 bg-red-100 p-3 rounded-md">
                    {searchError}
                </div>
            )}

            {isSearching && (
                <div className="mt-4 text-gray-600 dark:text-gray-400">
                    Loading emails...
                </div>
            )}

            <ul className="mt-6 w-full max-w-md space-y-2">
                {emails.map((email) => (
                    <li
                        key={email.id}
                        onClick={() => !isSummarizing && handleSummarize(email.id)}
                        className={`cursor-pointer p-4 bg-gray-100 dark:bg-gray-800 rounded-md shadow-sm ${
                            isSummarizing && selectedEmail === email.id ? 'opacity-50' : ''
                        }`}
                    >
                        <strong>{email.subject}</strong>
                        <p className="text-sm text-gray-600 dark:text-gray-400">{email.sender}</p>
                        {isSummarizing && selectedEmail === email.id && (
                            <p className="text-sm text-blue-500 mt-2">Generating summary...</p>
                        )}
                        {summaryError && selectedEmail === email.id && (
                            <p className="text-sm text-red-600 mt-2">{summaryError}</p>
                        )}
                    </li>
                ))}
            </ul>

            {summary && selectedEmail && (
                <div className="mt-8 p-6 bg-white dark:bg-gray-800 rounded-lg shadow-lg w-full max-w-md">
                    <h2 className="text-lg font-semibold mb-4">Summary</h2>
                    <p>{summary}</p>
                </div>
            )}
        </div>
    );
}
