import type { Metadata } from "next";
import "./globals.css";

export const metadata: Metadata = {
  title: "Routerly — Universal Router Manager",
  description: "A simple, local-first workspace for managing supported network devices.",
};

export default function RootLayout({ children }: Readonly<{ children: React.ReactNode }>) {
  return <html lang="en"><body>{children}</body></html>;
}
