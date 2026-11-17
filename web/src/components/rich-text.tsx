import Link from "next/link";
import { Fragment, type ReactNode } from "react";

/**
 * Minimal, safe markdown for assistant replies: paragraphs, "- " lists, **bold**, and [text](/internal)
 * links. Builds React elements (no HTML injection); only same-site paths starting with a single "/" become links
 * ("//host" and "/\host" can point to another site).
 */
export function RichText({ text }: { text: string }) {
  const blocks: ReactNode[] = [];
  let list: string[] = [];
  const flush = () => {
    if (list.length) {
      blocks.push(
        <ul key={`ul-${blocks.length}`} className="my-1.5 list-disc space-y-1 pl-5">
          {list.map((item, i) => (
            <li key={i}>{inline(item)}</li>
          ))}
        </ul>,
      );
      list = [];
    }
  };
  for (const line of text.split("\n")) {
    const m = line.match(/^\s*[-*]\s+(.*)$/);
    if (m) {
      list.push(m[1]);
      continue;
    }
    flush();
    if (line.trim()) {
      blocks.push(
        <p key={`p-${blocks.length}`} className="my-1.5">
          {inline(line)}
        </p>,
      );
    }
  }
  flush();
  return <>{blocks}</>;
}

function inline(s: string): ReactNode[] {
  const out: ReactNode[] = [];
  const re = /\*\*([^*]+)\*\*|\[([^\]]+)\]\(([^)\s]+)\)/g;
  let last = 0;
  let m: RegExpExecArray | null;
  while ((m = re.exec(s))) {
    if (m.index > last) out.push(s.slice(last, m.index));
    if (m[1] !== undefined) {
      out.push(<strong key={m.index}>{m[1]}</strong>);
    } else {
      const href = m[3];
      const safe = /^\/(?![/\\])/.test(href);
      out.push(
        safe ? (
          <Link key={m.index} href={href} className="font-medium text-primary underline-offset-2 hover:underline">
            {m[2]}
          </Link>
        ) : (
          <Fragment key={m.index}>{m[2]}</Fragment>
        ),
      );
    }
    last = m.index + m[0].length;
  }
  if (last < s.length) out.push(s.slice(last));
  return out;
}
