import type { Metadata } from 'next'
import { Geist, Geist_Mono } from 'next/font/google'
import { Analytics } from '@vercel/analytics/next'
import { Toaster } from '@/components/ui/toaster'
import './globals.css'

const _geist = Geist({ subsets: ["latin"] });
const _geistMono = Geist_Mono({ subsets: ["latin"] });

export const metadata: Metadata = {
  title: 'Network Traffic Monitoring Dashboard',
  description: 'Intelligent network traffic prediction and anomaly detection dashboard',
  generator: 'v0.app',
  icons: {
    icon: [
      {
        url: '/icon-light-32x32.png',
        media: '(prefers-color-scheme: light)',
      },
      {
        url: '/icon-dark-32x32.png',
        media: '(prefers-color-scheme: dark)',
      },
      {
        url: '/icon.svg',
        type: 'image/svg+xml',
      },
    ],
    apple: '/apple-icon.png',
  },
}

export default function RootLayout({
  children,
}: Readonly<{
  children: React.ReactNode
}>) {
  return (
    <html lang="en" className="dark" suppressHydrationWarning>
      <body className="font-sans antialiased dark relative">
        {/* Background Layer */}
        <div
          className="fixed inset-0 -z-50 bg-cover bg-center bg-no-repeat bg-fixed"
          style={{
            backgroundImage: "url('/assets/background.png')",
            opacity: 0.35,
          }}
        />

        {/* Optional: Dark overlay for better contrast */}
        <div className="fixed inset-0 -z-40 bg-gradient-to-br from-black/40 via-black/20 to-black/40 pointer-events-none" />

        {children}
        <Toaster />
        <Analytics />
      </body>
    </html>
  )
}