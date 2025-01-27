import type { NextConfig } from "next";

const PRODUCTION_DOMAIN = 'newsletter-summarizer-omega.vercel.app';

const nextConfig: NextConfig = {
    env: {
        NEXT_PUBLIC_BACKEND_URL: 'https://newsletter-summarizer-1081940379388.us-central1.run.app',
        NEXT_PUBLIC_FRONTEND_URL: `https://${PRODUCTION_DOMAIN}`
    },
    async redirects() {
        return [
            {
                source: '/:path*',
                has: [
                    {
                        type: 'host',
                        value: `(?!${PRODUCTION_DOMAIN}).*`,
                    },
                ],
                destination: `https://${PRODUCTION_DOMAIN}/:path*`,
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
