import Link from "next/link";

export default function AuthLayout({ children }: { children: React.ReactNode }) {
  return (
    <div className="flex min-h-screen flex-col items-center justify-center gap-6 px-4 py-8">
      <Link href="/login" className="flex items-center gap-2" aria-label="Bizz AI">
        <span className="flex size-8 items-center justify-center rounded-md bg-primary text-[15px] font-semibold text-primary-foreground">
          B
        </span>
        <span className="text-lg font-semibold tracking-tight">Bizz AI</span>
      </Link>
      <main className="w-full max-w-sm">{children}</main>
    </div>
  );
}
