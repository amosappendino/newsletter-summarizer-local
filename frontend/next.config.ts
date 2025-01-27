import type { NextConfig } from "next";

const nextConfig: NextConfig = {
    env: {
        NEXT_PUBLIC_BACKEND_URL: 'https://newsletter-summarizer-1081940379388.us-central1.run.app',
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
