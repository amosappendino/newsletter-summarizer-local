import { NextResponse } from 'next/server';

export async function POST() {
    try {
        await fetch(`${process.env.NEXT_PUBLIC_BACKEND_URL}/logout`, {
            method: 'POST',
            credentials: 'include',
            headers: {
                'Content-Type': 'application/json',
            },
        });

        return NextResponse.json({ message: 'Logged out successfully' });
    } catch {
        return NextResponse.json({ error: 'Failed to logout' }, { status: 500 });
    }
}

