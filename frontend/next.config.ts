import type { NextConfig } from "next";

const nextConfig: NextConfig = {
    env: {
        NEXT_PUBLIC_BACKEND_URL: 'https://newsletter-summarizer-1081940379388.us-central1.run.app',
        NEXT_PUBLIC_FRONTEND_URL: 'https://newsletter-summarizer-omega.vercel.app'
    },
    async redirects() {
        return [
            {
                source: '/:path*',
                has: [
                    {
                        type: 'host',
                        value: '(?!newsletter-summarizer-omega.vercel.app).*',
                    },
                ],
                destination: 'https://newsletter-summarizer-omega.vercel.app/:path*',
                permanent: true,
            },
        ];
    },
    async rewrites() {
        return [
            {
                source: '/api/:path*',
                destination: 'https://newsletter-summarizer-1081940379388.us-central1.run.app/:path*',
            },
        ];
    },
};

export default nextConfig;
