"use client";
import { useEffect, useState, useCallback } from 'react';
import { useRouter } from 'next/navigation';

export default function LoginPage() {
    const router = useRouter();
    const [authStatus, setAuthStatus] = useState<string>('checking');
    const [error, setError] = useState<string>('');

    const checkAuthStatus = useCallback(async () => {
        try {
            const response = await fetch('http://localhost:8000/check-auth');
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

    const handleLogin = async () => {
        try {
            window.location.href = 'http://localhost:8000/auth/gmail';
        } catch (error) {
            console.error('Error during login:', error);
            setError('Failed to initiate login');
        }
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
        <div className="min-h-screen flex items-center justify-center bg-gray-50">
            <div className="max-w-md w-full space-y-8 p-8 bg-white rounded-lg shadow-lg">
                <div className="text-center">
                    <h2 className="mt-6 text-3xl font-extrabold text-gray-900">
                        Newsletter Summarizer
                    </h2>
                    <p className="mt-2 text-sm text-gray-600">
                        Sign in with your Gmail account to continue
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
