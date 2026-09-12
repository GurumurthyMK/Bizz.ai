"use client";

import * as React from "react";
import { useRouter } from "next/navigation";
import { useAuth } from "@/lib/auth";
import { Skeleton } from "@/components/ui/skeleton";

/**
 * Client-side protection for dashboard routes. The middleware already
 * redirects cookie-less visits; this handles invalid/expired sessions by
 * verifying against GET /api/v1/auth/me.
 */
function ProtectedRoute({ children }: { children: React.ReactNode }) {
  const router = useRouter();
  const { user, isReady } = useAuth();

  React.useEffect(() => {
    if (isReady && user == null) {
      router.replace("/login");
    }
  }, [isReady, user, router]);

  if (!isReady || user == null) {
    return (
      <div className="flex flex-col gap-4" aria-label="Checking authentication" role="status">
        <Skeleton className="h-8 w-56" />
        <Skeleton className="h-4 w-96" />
        <Skeleton className="h-40 w-full" />
      </div>
    );
  }
  return <>{children}</>;
}

export { ProtectedRoute };
