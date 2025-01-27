"use client";
import { useEffect, useState, useCallback } from 'react';
import { useRouter } from 'next/navigation';

// Verify this URL matches your Cloud Run service
const BACKEND_URL = 'https://newsletter-summarizer-1081940379388.us-central1.run.app';

export default function LoginPage() {
    const router = useRouter();
    const [authStatus, setAuthStatus] = useState<string>('checking');
    const [error, setError] = useState<string>('');

    console.log("Using backend URL:", BACKEND_URL);

    const checkAuthStatus = useCallback(async () => {
        try {
            console.log("Checking auth at:", `${BACKEND_URL}/check-auth`);
            
            const response = await fetch(`${BACKEND_URL}/check-auth`, {
                credentials: 'include',
                headers: {
                    'Content-Type': 'application/json',
                },
            });
            const data = await response.json();
            
            if (data.status === 'authenticated') {
                router.push('/');
            } else {
                setAuthStatus('unauthenticated');
            }
        } catch (error) {
            console.error('Error checking auth status:', error);
            setError('Failed to check authentication status');
            setAuthStatus('error');
        }
    }, [router]);

    useEffect(() => {
        checkAuthStatus();
    }, [checkAuthStatus]);

    const handleLogin = (e: React.MouseEvent) => {
        e.preventDefault(); // Prevent any default behavior
        console.log("Redirecting to:", `${BACKEND_URL}/auth/gmail`);
        window.location.href = `${BACKEND_URL}/auth/gmail`;
    };

    if (authStatus === 'checking') {
        return (
            <div className="min-h-screen flex items-center justify-center bg-gray-50">
                <div className="text-center">
                    Checking authentication status...
                </div>
            </div>
        );
    }

    return (
        <div className="min-h-screen flex items-center justify-center bg-gray-50 py-12 px-4 sm:px-6 lg:px-8">
            <div className="max-w-md w-full space-y-8">
                <div>
                    <h2 className="mt-6 text-center text-3xl font-extrabold text-gray-900">
                        Sign in to your account
                    </h2>
                    <p className="mt-2 text-center text-sm text-gray-600">
                        Use your Gmail account to access the newsletter summarizer
                    </p>
                </div>

                {error && (
                    <div className="bg-red-100 border border-red-400 text-red-700 px-4 py-3 rounded relative" role="alert">
                        <span className="block sm:inline">{error}</span>
                    </div>
                )}

                <div>
                    <button
                        onClick={handleLogin}
                        className="group relative w-full flex justify-center py-2 px-4 border border-transparent text-sm font-medium rounded-md text-white bg-blue-600 hover:bg-blue-700 focus:outline-none focus:ring-2 focus:ring-offset-2 focus:ring-blue-500"
                    >
                        Sign in with Gmail
                    </button>
                </div>
            </div>
        </div>
    );
}
