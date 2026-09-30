import { useQueryClient } from "@tanstack/react-query";
import { useState } from "react";
import { api, ApiError } from "../../api/client";
import { useHall } from "../../api/hooks";
import type { HallRow } from "../../api/types";
import { Dialog, StatusPill, errText, useToast } from "../../app/ui";
import { StudentLink } from "../console/StudentLink";
import { StudentDetailsDialog } from "../ops/StudentDetails";
import { fmtMobile, streamName } from "../../lib/format";
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
  const [detailsId, setDetailsId] = useState<number | null>(null);
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
      if (e instanceof ApiError && e.code === "needs_confirmation") {
        setMoving(row);
        setConfirm({ message: e.message, counsellorId });
      }
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
      <div className="pagehead">
        <div>
          <h1>Hall queue</h1>
          <p className="lede">Everyone in the room, split by desk. Search finds anyone from today — including lost slips and missed calls.</p>
        </div>
        {data && data.header.late > 0 && <div className="right"><span className="pill bad">{data.header.late} over {data.header.wait_promise_min} min</span></div>}
      </div>
      {picker}
      {data && <StudentLink url={data.centre.student_url} compact />}
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
            <div className="card empty">
              {q.trim() ? (
                <>
                  <b>No match for “{q.trim()}”.</b>
                  <p style={{ margin: 0 }}>Try the last four digits of their mobile.</p>
                </>
              ) : (
                <p style={{ margin: 0 }}>No one in the hall yet — tokens appear here as students scan in.</p>
              )}
            </div>
          ) : (
            <ul className="qlist" aria-label="Students in the hall">
              {data.rows.map((r) => (
                <li key={r.id} className={`qitem${r.late ? " late" : ""}`}>
                  <span className="num">{r.token}</span>
                  <div className="body">
                    <div className="nm">{r.name}</div>
                    <div className="meta">
                      {r.counsellor.name} · {r.counsellor.desk} · {streamName(r.stream)} · {fmtMobile(r.mobile)}
                      {r.waited_min != null && ` · waiting ${r.waited_min} min`}
                    </div>
                  </div>
                  <div className="act">
                    {r.late && <span className="pill bad">late</span>}
                    {r.consent_pending && <span className="pill warn">consent pending</span>}
                    {r.alert_failed && <span className="pill bad" title={r.alert_failed_message}>alert failed</span>}
                    <StatusPill status={r.status} />
                    {r.status === "waiting" && (
                      <select
                        className="select sel-move" aria-label={`Move ${r.token} to`} value=""
                        onChange={(e) => e.target.value && move(r, Number(e.target.value))}
                      >
                        <option value="">Move to…</option>
                        {data.tabs
                          .filter((tb) => tb.counsellor_id != null && tb.counsellor_id !== r.counsellor.id)
                          .map((tb) => (
                            <option key={tb.key} value={tb.counsellor_id as number}>{tb.label} — {tb.count} in queue</option>
                          ))}
                      </select>
                    )}
                    {CAN_REQUEUE.includes(r.status) && <button className="btn sm" onClick={() => requeue(r)}>Requeue</button>}
                    <button className="btn sm" onClick={() => setDetailsId(r.id)}>Details</button>
                  </div>
                </li>
              ))}
            </ul>
          )}
        </>
      )}

      {confirm && moving && (
        <Dialog title={`Move ${moving.token}`} onClose={() => { setMoving(null); setConfirm(null); }}>
          <div className="notice">{confirm.message}</div>
          <div className="actions">
            <button className="btn" onClick={() => { setMoving(null); setConfirm(null); }}>Cancel</button>
            <button className="btn primary" onClick={() => move(moving, confirm.counsellorId, true)}>Move anyway</button>
          </div>
        </Dialog>
      )}
      {detailsId != null && <StudentDetailsDialog path={`hall/students/${detailsId}`} onClose={() => setDetailsId(null)} />}
    </>
  );
}
