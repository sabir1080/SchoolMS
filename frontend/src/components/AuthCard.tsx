import { BrandLogo } from "./BrandLogo";

export function AuthCard({
  title,
  subtitle,
  logo,
  children,
}: {
  title: string;
  subtitle?: string;
  logo?: string;
  children: React.ReactNode;
}) {
  return (
    <main className="flex min-h-screen items-center justify-center px-4 py-10">
      <div className="w-full max-w-sm space-y-4 rounded-2xl bg-white p-6 shadow-sm dark:bg-slate-900">
        <div className="flex items-center gap-3">
          <BrandLogo src={logo} className="h-12 w-12" />
          <div>
          <h1 className="text-2xl font-semibold">{title}</h1>
          {subtitle && <p className="text-sm text-slate-500">{subtitle}</p>}
          </div>
        </div>
        {children}
      </div>
    </main>
  );
}
