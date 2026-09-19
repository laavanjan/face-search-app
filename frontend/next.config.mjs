/** @type {import('next').NextConfig} */
const backend = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000";

const nextConfig = {
  async rewrites() {
    return [
      { source: "/api/:path*", destination: `${backend}/:path*` },
      { source: "/photos/:path*", destination: `${backend}/photos/:path*` },
    ];
  },
};

export default nextConfig;
