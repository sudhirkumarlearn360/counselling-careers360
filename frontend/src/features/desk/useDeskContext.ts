import { useParams } from "react-router-dom";

/** Inside /console/desk/:counsellorId/* an ops lead works that counsellor's desk (CQ-5). */
export function useDeskContext(): { asCounsellor: number | undefined; base: string } {
  const { counsellorId } = useParams();
  const asCounsellor = counsellorId ? Number(counsellorId) : undefined;
  return { asCounsellor, base: asCounsellor ? `/console/desk/${asCounsellor}` : "/console" };
}
