import { Link } from "react-router-dom";
import { useHallCentre } from "../hall/useHallCentre";
import { BoardView } from "./HallBoard";

/** The hall board inside the console (front desk and ops), plus a link to open it full-screen. */
export function ConsoleBoard() {
  const { slug, picker } = useHallCentre();
  return (
    <>
      <h1>Hall board</h1>
      {picker}
      {slug ? (
        <>
          <p><Link className="btn sm" to={`/board/${slug}`} target="_blank">Open full-screen on the hall display</Link></p>
          <div style={{ borderRadius: "var(--r-l)", overflow: "hidden" }}><BoardView slug={slug} /></div>
        </>
      ) : (
        <div className="card"><p>No live centre to show.</p></div>
      )}
    </>
  );
}
