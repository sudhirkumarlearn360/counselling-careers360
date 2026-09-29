import { useQuery } from "@tanstack/react-query";
import { api } from "../../api/client";
import type { StudentRecord } from "../../api/types";
import { DetailRow, Dialog, StatusPill } from "../../app/ui";
import { streamName } from "../../lib/format";
import { phase } from "../../lib/phase";

/** The student record. Phase 1 shows only the required details; check-in answers and timing are future phase. */
export function StudentDetailsDialog({ path, onClose }: { path: string; onClose: () => void }) {
  const { data: s } = useQuery({ queryKey: ["student-detail", path], queryFn: async () => (await api.get<StudentRecord>(path)).data });
  return (
    <Dialog title={s ? `${s.name} · ${s.token}` : "Student"} onClose={onClose}>
      {!s ? (
        <p role="status">Loading…</p>
      ) : (
        <>
          <p style={{ marginTop: 0 }}>{phase.studentStatus && <StatusPill status={s.status} />}</p>
          <DetailRow label="Mobile" value={s.mobile} />
          <DetailRow label="Parent's contact" value={s.parent_mobile} />
          <DetailRow label="Email" value={s.email} />
          <DetailRow label="School" value={s.school} />
          <DetailRow label="Stream" value={streamName(s.stream)} />
          <DetailRow label="Class" value={s.klass} />
          <DetailRow label="Course or career" value={s.course} />
          <DetailRow label="Counsellor" value={`${s.counsellor.name} · ${s.counsellor.desk}`} />
          <DetailRow label="Consent" value={s.consent === "given" ? "Given" : "Pending"} />
          {phase.intakeSummary && (
            <>
              <DetailRow label="Entrance exams" value={s.exams.join(", ")} />
              <DetailRow label="Clarity" value={s.clarity} />
              <DetailRow label="Wants help with" value={s.help.join(", ")} />
            </>
          )}
        </>
      )}
      <div className="actions"><button className="btn" onClick={onClose}>Close</button></div>
    </Dialog>
  );
}
