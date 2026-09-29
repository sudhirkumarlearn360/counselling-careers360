import type { ReactNode } from "react";
import "../../styles/student.css";

export function StudentShell({ children, wide = false }: { children: ReactNode; wide?: boolean }) {
  return (
    <div className="stu">
      <div className="stu-top">
        <span className="brand">
          Careers360 <em>counselling</em>
        </span>
      </div>
      <main className={`stu-wrap${wide ? " wide" : ""}`}>{children}</main>
    </div>
  );
}
