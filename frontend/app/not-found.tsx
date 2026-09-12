import type { Metadata } from "next";
import Link from "next/link";
import { Button } from "@/components/ui/button";
import { EmptyState } from "@/components/ui/empty-state";

export const metadata: Metadata = { title: "Not found" };

export default function NotFound() {
  return (
    <main className="mx-auto flex min-h-[60vh] w-full max-w-md flex-col justify-center px-4">
      <EmptyState
        title="Page not found"
        description="The address is invalid or the record no longer exists. Use navigation to continue."
      />
      <div className="mt-2 text-center">
        <Button variant="secondary" size="sm" asChild>
          <Link href="/overview">Back to overview</Link>
        </Button>
      </div>
    </main>
  );
}
