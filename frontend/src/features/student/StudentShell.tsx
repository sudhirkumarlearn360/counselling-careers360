import type { ReactNode } from "react";
import "../../styles/student.css";

export function StudentShell({ children, wide = false, bare = false }: { children: ReactNode; wide?: boolean; bare?: boolean }) {
  return (
    <div className="stu">
      <div className="stu-top">
        <span className="brand">
          Careers360 <em>Counselling</em>
        </span>
      </div>
      {bare ? <main>{children}</main> : <main className={`stu-wrap${wide ? " wide" : ""}`}>{children}</main>}
    </div>
  );
}
