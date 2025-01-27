import { NextResponse } from 'next/server';

export async function POST() {
    try {
        const response = await fetch(`${process.env.NEXT_PUBLIC_BACKEND_URL}/logout`, {
            method: 'POST',
            credentials: 'include',
            headers: {
                'Content-Type': 'application/json',
            },
        });

        return NextResponse.json({ message: 'Logged out successfully' });
    } catch (error) {
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

