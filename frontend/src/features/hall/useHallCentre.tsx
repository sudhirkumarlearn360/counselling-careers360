import { useState, type ReactNode } from "react";
import { useAuth } from "../../api/auth";
import { useLive } from "../../api/hooks";

/** Reception works their own centre; an ops lead picks among the live centres. */
export function useHallCentre(): { centreId: number | undefined; picker: ReactNode; slug?: string } {
  const { user } = useAuth();
  const live = useLive(user?.role === "ops_lead");
  const [picked, setPicked] = useState<number | undefined>();
  if (user?.role === "reception") return { centreId: user.centre?.id, picker: null, slug: user.centre?.slug };
  const centres = live.data ?? [];
  const id = picked ?? centres[0]?.id;
  const picker = (
    <div className="field" style={{ maxWidth: "22rem" }}>
      <label htmlFor="centre-pick">Centre</label>
      <select id="centre-pick" className="select" value={id ?? ""} onChange={(e) => setPicked(Number(e.target.value))}>
        {centres.length === 0 && <option value="">No live centres</option>}
        {centres.map((c) => (
          <option key={c.id} value={c.id}>{c.city} · {c.venue}</option>
        ))}
      </select>
    </div>
  );
  return { centreId: id, picker, slug: centres.find((c) => c.id === id)?.slug };
}
