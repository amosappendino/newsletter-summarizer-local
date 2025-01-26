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

