import "./globals.css";

export const metadata = {
  title: "DocExtract AI — Document Data Extraction Dashboard",
  description:
    "AI-powered dashboard for extracting structured data from official documents like Aadhaar, PAN Card, Passport and more using Google Gemini.",
};

export default function RootLayout({ children }) {
  return (
    <html lang="en">
      <body>{children}</body>
    </html>
  );
}
