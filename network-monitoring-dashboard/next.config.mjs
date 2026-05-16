import { fileURLToPath } from 'url';
import path from 'path';

const projectDir = path.dirname(fileURLToPath(import.meta.url));

/** @type {import('next').NextConfig} */
const nextConfig = {
  typescript: {
    ignoreBuildErrors: true,
  },
  images: {
    unoptimized: true,
  },
  output: 'standalone',
  turbopack: {
    root: projectDir,
  },
}

export default nextConfig
