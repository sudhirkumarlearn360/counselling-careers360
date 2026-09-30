import { Navigate, useParams, useSearchParams } from "react-router-dom";
import { usePublicCentre } from "../../api/hooks";
import { CheckInFlow } from "./CheckInFlow";
import { StudentShell } from "./StudentShell";
import { savedToken } from "./schema";

/** `/c/:centreSlug`: the landing page IS the check-in (the short details form is on it). */
export function Landing() {
  const { centreSlug = "" } = useParams();
  const [params] = useSearchParams();
  const key = params.get("new") ? null : savedToken(centreSlug);
  const { data, isLoading, error } = usePublicCentre(centreSlug, !key); // no request when we're about to redirect
  if (key) return <Navigate to={`/t/${key}`} replace />; // back to my live token, not a blank form (CQ-26)

  if (isLoading) return <StudentShell><p role="status">Loading…</p></StudentShell>;
  if (error || !data)
    return (
      <StudentShell>
        <h1>We can't find this centre</h1>
        <p className="muted">Check the code at the entrance, or ask the front desk.</p>
      </StudentShell>
    );
  return <CheckInFlow slug={centreSlug} data={data} />;
}
