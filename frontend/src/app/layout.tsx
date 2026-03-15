import type { Metadata } from "next";
import "./globals.css";

export const metadata: Metadata = {
  title: "PayVerify — School Fee Verification",
  description:
    "Instant payment verification for school fees via Easypaisa, JazzCash, and Meezan.",
};

export default function RootLayout({
  children,
}: {
  children: React.ReactNode;
}) {
  return (
    <html lang="en">
      <body>{children}</body>
    </html>
  );
}
