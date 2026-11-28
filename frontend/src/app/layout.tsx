import type { Metadata, Viewport } from "next";
import "./globals.css";
import { Toaster } from "@/components/ui/toaster";

export const metadata: Metadata = {
  title: "ARK OMNITEK — Phosphor Console",
  description:
    "Unified RAKSHA defence console: citizen defence applications and infrastructure defence rings behind one phosphor interface.",
  icons: {
    icon:
      "data:image/svg+xml," +
      encodeURIComponent(
        `<svg xmlns='http://www.w3.org/2000/svg' viewBox='0 0 32 32'><rect width='32' height='32' rx='7' fill='#050607'/><path d='M16 6 25 21h-4.6L16 13.4 11.6 21H7L16 6Z' fill='#79C4B7'/><circle cx='16' cy='24' r='2' fill='#DAD1B9'/></svg>`,
      ),
  },
};

export const viewport: Viewport = {
  themeColor: "#050607",
};

export default function RootLayout({
  children,
}: Readonly<{
  children: React.ReactNode;
}>) {
  return (
    <html lang="en" className="dark" suppressHydrationWarning>
      <body className="antialiased bg-background text-foreground min-h-screen flex flex-col">
        {children}
        <Toaster />
      </body>
    </html>
  );
}
