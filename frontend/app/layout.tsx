import type { Metadata } from "next";
import "./globals.css";

export const metadata: Metadata = {
  title: "Finance Complaints Medallion",
  description: "Regulatory-intelligence and analytics platform for CFPB financial complaints",
};

export default function RootLayout({
  children,
}: Readonly<{
  children: React.ReactNode;
}>) {
  return (
    <html lang="en">
      <body className="min-h-screen bg-background text-foreground antialiased font-sans">
        {children}
      </body>
    </html>
  );
}
