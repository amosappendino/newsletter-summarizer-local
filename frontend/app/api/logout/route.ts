import { NextResponse } from 'next/server';

export async function GET() {
    try {
        const response = await fetch('http://localhost:8000/logout', {
            method: 'GET',
            credentials: 'include'
        });

        if (!response.ok) {
            throw new Error('Logout failed');
        }

        return NextResponse.json({ message: 'Logged out successfully' });
    } catch (error) {
        console.error('Error during logout:', error);
        return NextResponse.json({ error: 'Failed to logout' }, { status: 500 });
    }
}

const checkAuth = async () => {
    try {
        const response = await fetch(
            `${process.env.NEXT_PUBLIC_BACKEND_URL}/auth/status`,
            {
                credentials: 'include',
                headers: {
                    'Content-Type': 'application/json',
                },
            }
        );
        // Handle response
    } catch (error) {
        console.error('Failed to check authentication status:', error);
    }
};

