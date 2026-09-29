import { useParams } from "react-router-dom";
import { useBoard } from "../../api/hooks";
import "../../styles/board.css";

export function BoardView({ slug }: { slug: string }) {
  const { data: b, isLoading, error } = useBoard(slug);
  if (isLoading) return <div className="board"><p role="status">Loading…</p></div>;
  if (error || !b) return <div className="board"><h1>Board unavailable</h1></div>;
  return (
    <div className="board">
      <header>
        <h1>{b.centre.city} · {b.centre.venue}</h1>
        <div className="clock" aria-label="Current time">{b.now}</div>
        <div>{b.total_waiting} waiting</div>
      </header>
      <section className="panels" aria-label="Desks">
        {b.panels.map((p) => (
          <article key={p.desk} className={`panel${p.serving ? "" : " dim"}`}>
            <div className="desk">{p.desk}</div>
            <div className="who">{p.counsellor}</div>
            <div className="serving" aria-label="Now serving">{p.serving ?? "—"}</div>
            {p.line ? (
              <div className="line">{p.line}</div>
            ) : (
              <div className="line">Next: {p.next ?? "—"} · {p.waiting} waiting</div>
            )}
          </article>
        ))}
      </section>
      <section className="recent" aria-label="Recently called">
        <strong>Recently called</strong>
        {b.recently_called.length === 0 ? (
          <span>{b.recently_called_empty}</span>
        ) : (
          b.recently_called.map((t) => <span className="tok" key={t}>{t}</span>)
        )}
      </section>
      <footer>{b.standing_line}</footer>
    </div>
  );
}

export function HallBoard() {
  const { centreSlug = "" } = useParams();
  return <BoardView slug={centreSlug} />;
}
