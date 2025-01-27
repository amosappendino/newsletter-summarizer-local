"use client";
import { useEffect, useState } from 'react';
import { useRouter } from 'next/navigation';

interface SearchResult {
    subject: string;
    snippet: string;
}

export default function Home() {
    const router = useRouter();
    const [searchQuery, setSearchQuery] = useState('');
    const [searchResults, setSearchResults] = useState<SearchResult[]>([]);
    const [error, setError] = useState('');

    useEffect(() => {
        const checkAuth = async () => {
            try {
                const response = await fetch(`${process.env.NEXT_PUBLIC_BACKEND_URL}/check-auth`, {
                    credentials: 'include',
                    headers: {
                        'Content-Type': 'application/json',
                    },
                });
                const data = await response.json();
                
                if (data.status === 'unauthenticated') {
                    router.push('/login');
                }
            } catch (error) {
                console.error('Error checking auth status:', error);
                router.push('/login');
            }
        };

        checkAuth();
    }, [router]);

    const handleSearch = async (e: React.FormEvent) => {
        e.preventDefault();
        try {
            const response = await fetch(`${process.env.NEXT_PUBLIC_BACKEND_URL}/search-emails/?query=${encodeURIComponent(searchQuery)}`, {
                credentials: 'include',
                headers: {
                    'Content-Type': 'application/json',
                },
            });
            const data = await response.json();
            setSearchResults(data);
        } catch (error) {
            setError('Failed to search emails');
            console.error('Search error:', error);
        }
    };

    const handleLogout = async () => {
        try {
            await fetch('/api/logout', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                },
            });
            router.push('/login');
        } catch (error) {
            console.error('Logout failed:', error);
        }
    };

    return (
        <div className="min-h-screen bg-gray-50 py-12 px-4 sm:px-6 lg:px-8">
            <div className="max-w-3xl mx-auto">
                <div className="flex justify-between items-center mb-8">
                    <h1 className="text-3xl font-bold text-gray-900">Newsletter Search</h1>
                    <button
                        onClick={handleLogout}
                        className="bg-red-600 text-white px-4 py-2 rounded hover:bg-red-700"
                    >
                        Logout
                    </button>
                </div>

                <form onSubmit={handleSearch} className="mb-8">
                    <div className="flex gap-4">
                        <input
                            type="text"
                            value={searchQuery}
                            onChange={(e) => setSearchQuery(e.target.value)}
                            placeholder="Search your newsletters..."
                            className="flex-1 p-2 border border-gray-300 rounded"
                        />
                        <button
                            type="submit"
                            className="bg-blue-600 text-white px-6 py-2 rounded hover:bg-blue-700"
                        >
                            Search
                        </button>
                    </div>
                </form>

                {error && (
                    <div className="bg-red-100 border border-red-400 text-red-700 px-4 py-3 rounded mb-4">
                        {error}
                    </div>
                )}

                <div className="space-y-4">
                    {searchResults.map((result: SearchResult, index: number) => (
                        <div key={index} className="bg-white p-4 rounded shadow">
                            <h2 className="text-xl font-semibold">{result.subject}</h2>
                            <p className="text-gray-600">{result.snippet}</p>
                        </div>
                    ))}
                </div>
            </div>
        </div>
    );
}
