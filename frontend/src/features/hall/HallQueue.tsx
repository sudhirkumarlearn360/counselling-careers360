import { useQueryClient } from "@tanstack/react-query";
import { useState } from "react";
import { api, ApiError } from "../../api/client";
import { useHall } from "../../api/hooks";
import type { HallRow } from "../../api/types";
import { Dialog, StatusPill, errText, useToast } from "../../app/ui";
import { streamName } from "../../lib/format";
import { useHallCentre } from "./useHallCentre";

const CAN_REQUEUE = ["no_show", "released", "done"];

export function HallQueue() {
  const { centreId, picker } = useHallCentre();
  const [q, setQ] = useState("");
  const [tab, setTab] = useState<number | null>(null); // persists while working elsewhere in the list
  const { data, isLoading } = useHall(centreId, q.trim(), tab);
  const qc = useQueryClient();
  const toast = useToast();
  const [moving, setMoving] = useState<HallRow | null>(null);
  const [confirm, setConfirm] = useState<{ message: string; counsellorId: number } | null>(null);

  const refresh = () => qc.invalidateQueries({ queryKey: ["hall"] });
  async function move(row: HallRow, counsellorId: number, confirmed = false) {
    try {
      await api.post(`hall/students/${row.id}/move`, { counsellor_id: counsellorId, confirm: confirmed });
      toast(`${row.token} moved. The token stays ${row.token}.`);
      setMoving(null);
      setConfirm(null);
      refresh();
    } catch (e) {
      if (e instanceof ApiError && e.code === "needs_confirmation") setConfirm({ message: e.message, counsellorId });
      else toast(errText(e), true);
    }
  }
  async function requeue(row: HallRow) {
    try {
      await api.post(`hall/students/${row.id}/requeue`);
      toast(`${row.token} is back in the queue.`);
      refresh();
    } catch (e) {
      toast(errText(e), true);
    }
  }

  return (
    <>
      <h1>Hall queue</h1>
      {picker}
      {isLoading && <p role="status">Loading…</p>}
      {data && (
        <>
          <div className="stats-row">
            <div className="kpi"><div className="n">{data.header.waiting}</div><div className="l">waiting</div></div>
            <div className="kpi"><div className="n" style={{ color: data.header.late ? "var(--rose)" : undefined }}>{data.header.late}</div><div className="l">past the {data.header.wait_promise_min}-min promise</div></div>
          </div>
          <div className="toolbar">
            <input
              className="input" type="search" aria-label="Search students" placeholder="Search name, mobile or token"
              value={q} onChange={(e) => setQ(e.target.value)}
            />
            {q.trim() && <span role="status">{data.count} {data.count === 1 ? "result" : "results"}</span>}
          </div>
          <div className="tabs" role="tablist" aria-label="Counsellors">
            {data.tabs.map((t) => (
              <button
                key={t.key} role="tab" className="tab" aria-selected={!q.trim() && tab === t.counsellor_id}
                onClick={() => { setTab(t.counsellor_id); setQ(""); }}
              >
                {t.label} <span className="pill">{t.count}</span>
                {t.late > 0 && <span className="late" aria-label={`${t.late} late`}>{t.late} late</span>}
              </button>
            ))}
          </div>
          {data.rows.length === 0 ? (
            <div className="card">
              {q.trim() ? (
                <p>No match for “{q.trim()}”. Try the last four digits of their mobile.</p>
              ) : (
                <p>No one in the hall yet — tokens appear here as students scan in.</p>
              )}
            </div>
          ) : (
            <div className="card table-wrap">
              <table className="t">
                <thead>
                  <tr><th>Token</th><th>Name</th><th>Counsellor</th><th>Stream</th><th>Mobile</th><th>Waited</th><th>Status</th><th /></tr>
                </thead>
                <tbody>
                  {data.rows.map((r) => (
                    <tr key={r.id} className={r.late ? "late" : ""}>
                      <td><b>{r.token}</b></td>
                      <td>{r.name}</td>
                      <td>{r.counsellor.name} · {r.counsellor.desk}</td>
                      <td>{streamName(r.stream)}</td>
                      <td>{r.mobile}</td>
                      <td>{r.waited_min == null ? "—" : `${r.waited_min} min`}</td>
                      <td>
                        <StatusPill status={r.status} />
                        {r.late && <span className="pill bad"> late</span>}
                        {r.consent_pending && <span className="pill warn"> consent pending</span>}
                        {r.alert_failed && <span className="pill bad" title={r.alert_failed_message}> alert failed</span>}
                      </td>
                      <td>
                        {r.status === "waiting" && <button className="btn sm" onClick={() => setMoving(r)}>Move</button>}
                        {CAN_REQUEUE.includes(r.status) && <button className="btn sm" onClick={() => requeue(r)}>Requeue</button>}
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          )}
        </>
      )}

      {moving && data && (
        <Dialog title={`Move ${moving.token}`} onClose={() => { setMoving(null); setConfirm(null); }}>
          {confirm ? (
            <>
              <div className="notice">{confirm.message}</div>
              <div className="actions">
                <button className="btn" onClick={() => setConfirm(null)}>Cancel</button>
                <button className="btn primary" onClick={() => move(moving, confirm.counsellorId, true)}>Move anyway</button>
              </div>
            </>
          ) : (
            <>
              <p className="muted">Pick a counsellor. Their current queue length is shown.</p>
              <div style={{ display: "grid", gap: "0.5rem" }}>
                {data.tabs
                  .filter((t) => t.counsellor_id != null && t.counsellor_id !== moving.counsellor.id)
                  .map((t) => (
                    <button key={t.key} className="btn" onClick={() => move(moving, t.counsellor_id as number)}>
                      {t.label} — {t.count} in queue
                    </button>
                  ))}
              </div>
              <div className="actions"><button className="btn" onClick={() => setMoving(null)}>Cancel</button></div>
            </>
          )}
        </Dialog>
      )}
    </>
  );
}
