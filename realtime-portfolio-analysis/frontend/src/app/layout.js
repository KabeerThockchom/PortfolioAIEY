import "./globals.css";

export const metadata = {
  title: "Realtime Portfolio Analysis",
  description: "Realtime Portfolio Analysis",
};

export default function RootLayout({ children }) {
  return (
    <html lang="en" suppressHydrationWarning>
      <body className={`antialiased`}>{children}</body>
    </html>
  );
}
