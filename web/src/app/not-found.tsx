import Link from "next/link";
import { buttonVariants } from "@/components/ui/button";

export default function NotFound() {
  return (
    <div className="mx-auto max-w-md py-24 text-center">
      <h1 className="text-xl font-semibold">That page isn&apos;t here</h1>
      <p className="mt-2 text-sm text-muted-foreground">
        The lead may have aged out of this week&apos;s data, or the link is mistyped.
      </p>
      <Link href="/leads" className={`${buttonVariants()} mt-6`}>
        Back to leads
      </Link>
    </div>
  );
}
