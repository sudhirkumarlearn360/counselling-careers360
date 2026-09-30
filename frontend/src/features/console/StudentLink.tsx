/** The student check-in link of a centre (what the QR on the student page opens), with an Open button. */
export function StudentLink({ url, compact = false }: { url: string; compact?: boolean }) {
  return (
    <div className={compact ? "studentlink compact" : "kvrow studentlink"}>
      <span>Student check-in link</span>
      <b>
        <span className="url">{url}</span>{" "}
        <a className="btn sm" href={url} target="_blank" rel="noopener noreferrer" aria-label={`Open student page ${url} in a new tab`}>
          Open ↗
        </a>
      </b>
    </div>
  );
}
