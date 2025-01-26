"use client";
import { useState, useEffect } from 'react';
import { useRouter } from 'next/navigation';

export default function SetupPage() {
    const router = useRouter();
    const [folderName, setFolderName] = useState('');
    const [hasFolder, setHasFolder] = useState<boolean | null>(null);
    const [error, setError] = useState('');
    const [isLoading, setIsLoading] = useState(false);

    // Check if setup is already completed
    useEffect(() => {
        const checkSetup = async () => {
            try {
                const response = await fetch('http://localhost:8000/check-setup');
                const data = await response.json();
                if (data.is_setup) {
                    router.push('/');
                }
            } catch (error) {
                console.error('Error checking setup:', error);
            }
        };
        checkSetup();
    }, []);

    const handleSubmit = async () => {
        try {
            setIsLoading(true);
            setError('');
            
            if (!folderName.trim()) {
                setError('Please enter a folder name');
                return;
            }

            const response = await fetch('http://localhost:8000/setup-folder', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                },
                body: JSON.stringify({ folder_name: folderName }),
            });

            if (response.ok) {
                router.push('/');
            } else {
                const data = await response.json();
                setError(data.detail || 'Failed to save folder settings');
            }
        } catch (error) {
            console.error('Error saving folder:', error);
            setError('Failed to save settings');
        } finally {
            setIsLoading(false);
        }
    };

    if (hasFolder === null) {
        return (
            <div className="min-h-screen flex items-center justify-center bg-gray-50">
                <div className="max-w-md w-full space-y-8 p-8 bg-white rounded-lg shadow-lg">
                    <h2 className="text-2xl font-bold text-center">Welcome to Newsletter Summarizer!</h2>
                    <p className="text-center text-gray-600">Do you have a Gmail folder for newsletters?</p>
                    <div className="flex justify-center space-x-4">
                        <button
                            onClick={() => setHasFolder(true)}
                            className="bg-blue-500 text-white px-6 py-2 rounded-md hover:bg-blue-600 transition-colors"
                        >
                            Yes
                        </button>
                        <button
                            onClick={() => setHasFolder(false)}
                            className="bg-blue-500 text-white px-6 py-2 rounded-md hover:bg-blue-600 transition-colors"
                        >
                            No
                        </button>
                    </div>
                </div>
            </div>
        );
    }

    return (
        <div className="min-h-screen flex items-center justify-center bg-gray-50">
            <div className="max-w-md w-full space-y-8 p-8 bg-white rounded-lg shadow-lg">
                <h2 className="text-2xl font-bold text-center">
                    {hasFolder ? 'Enter Folder Name' : 'Create a Folder'}
                </h2>
                
                {!hasFolder && (
                    <div className="bg-blue-50 p-4 rounded-md">
                        <h3 className="font-semibold mb-2">Quick Instructions:</h3>
                        <ol className="list-decimal list-inside space-y-2 text-sm">
                            <li>Open Gmail</li>
                            <li>On the left sidebar, scroll down and click "Create new label"</li>
                            <li>Enter a name for your newsletter folder</li>
                            <li>Click Create</li>
                            <li>Move your newsletter emails to this folder</li>
                        </ol>
                    </div>
                )}

                <div className="space-y-4">
                    <input
                        type="text"
                        placeholder="Enter your folder name"
                        value={folderName}
                        onChange={(e) => setFolderName(e.target.value)}
                        className="w-full p-2 border rounded-md"
                    />
                    
                    {error && (
                        <div className="text-red-600 text-sm">
                            {error}
                        </div>
                    )}

                    <button
                        onClick={handleSubmit}
                        disabled={isLoading}
                        className={`w-full bg-blue-500 text-white px-4 py-2 rounded-md hover:bg-blue-600 transition-colors ${
                            isLoading ? 'opacity-50 cursor-not-allowed' : ''
                        }`}
                    >
                        {isLoading ? 'Saving...' : 'Continue'}
                    </button>
                </div>
            </div>
        </div>
    );
} 