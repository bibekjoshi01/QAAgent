import type { Metadata } from "next";
import { Space_Grotesk } from "next/font/google";
import { AppProviders } from "@/components/providers/app-providers";
import "./globals.css";
import { SiteFooter } from "@/components/public/site-footer";
import SiteHeader from "@/components/public/site-header";

const spaceGrotesk = Space_Grotesk({ subsets: ["latin"] });

export const metadata: Metadata = {
  title: "QA Agent Control",
  description: "Autonomous QA agent observability console"
};

export default function RootLayout({ children }: Readonly<{ children: React.ReactNode }>) {
  return (
    <html lang="en">
      <body className={spaceGrotesk.className}>
        <div className="flex min-h-screen relative flex-col bg-[var(--surface-bg)] text-[var(--surface-fg)]">
          <AppProviders>
            <SiteHeader />
            {children}
            <SiteFooter />
          </AppProviders>
        </div>
      </body>
    </html>
  );
}
