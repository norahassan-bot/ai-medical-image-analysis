import "./globals.css";
import type { Metadata } from "next";
import AppShell from "@/components/AppShell";
import { LanguageProvider } from "@/lib/i18n";
import { AuthProvider } from "@/lib/auth/AuthContext";

export const metadata: Metadata = {
  title: "تحليل الصور الطبية بالذكاء الاصطناعي ودعم القرار السريري",
  description:
    "Next-generation clinical imaging diagnostics and decision support platform powered by FastAPI, PyTorch, and Next.js.",
};

export default function RootLayout({
  children,
}: {
  children: React.ReactNode;
}) {
  return (
    <html lang="ar" dir="rtl">
      <body className="bg-[#F8FAFC] text-[#172033] min-h-screen antialiased selection:bg-medPink-100 selection:text-medPink-900">
        <LanguageProvider>
          <AuthProvider>
            <AppShell>{children}</AppShell>
          </AuthProvider>
        </LanguageProvider>
      </body>
    </html>
  );
}
