/** The student check-in link of a centre (what the QR on the student page opens): an "Open Link" button, full URL on hover. */
export function StudentLink({ url, compact = false }: { url: string; compact?: boolean }) {
  return (
    <div className={compact ? "studentlink compact" : "kvrow studentlink"}>
      <span>Student check-in link</span>
      <b>
        <a
          className="btn sm linktip"
          href={url}
          target="_blank"
          rel="noopener noreferrer"
          title={url}
          data-url={url}
          aria-label={`Open Link: ${url} (new tab)`}
        >
          Open Link ↗
        </a>
      </b>
    </div>
  );
}
