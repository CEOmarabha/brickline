import { ExternalLink } from "lucide-react";
import { Badge } from "@/components/ui/badge";
import { CONFIDENCE_LABEL, CONTACT_SOURCE_LABEL } from "@/lib/contact-labels";
import type { ContactField } from "@/lib/contacts";
import { dateLabel } from "@/lib/format";
import { isHttpUrl } from "@/lib/pipeline";
import { cn } from "@/lib/utils";

/** The suggested value; a website is shown as a link, and only http(s) URLs ever become links. */
export function ContactValue({ field, kind }: { field: ContactField; kind: "website" | "text" }) {
  if (kind === "website" && isHttpUrl(field.value)) {
    return (
      <a
        href={field.value}
        target="_blank"
        rel="noopener noreferrer nofollow"
        className="inline-flex items-center gap-1 break-all text-primary underline-offset-4 hover:underline"
      >
        {field.value.replace(/^https?:\/\//i, "")} <ExternalLink className="size-3 shrink-0" />
      </a>
    );
  }
  return <span className="break-all">{field.value}</span>;
}

/** Source label with a link to the page or record it came from (when there is one), match strength and date. */
export function SourceLine({ field, className }: { field: ContactField; className?: string }) {
  const sources = [field.source, ...(field.alsoFoundIn ?? [])];
  return (
    <div className={cn("flex flex-wrap items-center gap-x-1.5 gap-y-0.5 text-xs text-muted-foreground", className)}>
      <span>{sources.map((s) => CONTACT_SOURCE_LABEL[s]).join(" + ")}</span>
      {field.sourceUrl && isHttpUrl(field.sourceUrl) && (
        <a
          href={field.sourceUrl}
          target="_blank"
          rel="noopener noreferrer nofollow"
          className="inline-flex items-center gap-0.5 text-primary underline-offset-4 hover:underline"
        >
          source <ExternalLink className="size-3" />
        </a>
      )}
      <span aria-hidden>·</span>
      <span>{dateLabel(field.retrievedAt)}</span>
      <Badge variant="outline" className={field.confidence === "high" ? "border-emerald-500/30 text-emerald-700" : "text-amber-700"}>
        {CONFIDENCE_LABEL[field.confidence]}
      </Badge>
    </div>
  );
}
