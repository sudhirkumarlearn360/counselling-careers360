import { keepPreviousData, useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { api } from "./client";
import type {
  Board,
  CentreFull,
  CounsellorFull,
  DeskPayload,
  HallPayload,
  Insights,
  LiveCentre,
  OpsStudentRow,
  PublicCentre,
  StudentRecord,
  TokenView,
} from "./types";

export const POLL = { token: 5000, board: 5000, desk: 5000, hall: 5000, landing: 10000 } as const;

// --- public (students, no login) ---------------------------------------------------------------
export const usePublicCentre = (slug: string, enabled = true) =>
  useQuery({
    queryKey: ["public-centre", slug],
    enabled,
    queryFn: async () => (await api.get<PublicCentre>(`public/centres/${slug}`, undefined, false)).data,
    refetchInterval: POLL.landing,
  });

export const useToken = (key: string) =>
  useQuery({
    queryKey: ["token", key],
    queryFn: async () => (await api.get<TokenView>(`public/tokens/${key}`, undefined, false)).data,
    refetchInterval: POLL.token,
    retry: (count, err: any) => err?.status !== 404 && count < 2,
  });

export const useBoard = (slug: string) =>
  useQuery({
    queryKey: ["board", slug],
    queryFn: async () => (await api.get<Board>(`public/board/${slug}`, undefined, false)).data,
    refetchInterval: POLL.board,
  });

// --- hall ---------------------------------------------------------------------------------------
export const useHall = (centreId: number | undefined, q: string, counsellor: number | null) =>
  useQuery({
    queryKey: ["hall", centreId, q, counsellor],
    enabled: centreId != null,
    queryFn: async () =>
      (await api.get<HallPayload>(`hall/centres/${centreId}/queue`, { q, counsellor })).data,
    refetchInterval: POLL.hall,
    placeholderData: keepPreviousData,
  });

export const useHallStudent = (id: number | null) =>
  useQuery({
    queryKey: ["hall-student", id],
    enabled: id != null,
    queryFn: async () => (await api.get<StudentRecord>(`hall/students/${id}`)).data,
  });

// --- desk ---------------------------------------------------------------------------------------
export const useDesk = (asCounsellor?: number, enabled = true) =>
  useQuery({
    queryKey: ["desk", asCounsellor ?? "me"],
    enabled,
    queryFn: async () => (await api.get<DeskPayload>("desk/queue", { as_counsellor: asCounsellor })).data,
    refetchInterval: POLL.desk,
  });

export const useDeskAction = (asCounsellor?: number) => {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: async (a: { path: string; body?: unknown; method?: "POST" | "PATCH" }) =>
      a.method === "PATCH"
        ? api.patch<any>(a.path, a.body, { as_counsellor: asCounsellor })
        : api.post<any>(a.path, a.body, { query: { as_counsellor: asCounsellor } }),
    onSuccess: () => qc.invalidateQueries({ queryKey: ["desk"] }),
  });
};

export const useMyList = <T,>(path: "desk/my-students" | "desk/my-centres", asCounsellor?: number, enabled = true) =>
  useQuery({
    queryKey: [path, asCounsellor ?? "me"],
    enabled,
    queryFn: async () => (await api.get<T[]>(path, { as_counsellor: asCounsellor })).data,
  });

// --- ops ----------------------------------------------------------------------------------------
/** ops_lead only: other roles must never call ops/live (it is a 403 for them). */
export const useLive = (enabled = true) =>
  useQuery({
    queryKey: ["live"],
    enabled,
    queryFn: async () => (await api.get<LiveCentre[]>("ops/live")).data,
    refetchInterval: POLL.desk,
  });
export const useCentres = () =>
  useQuery({ queryKey: ["centres"], queryFn: async () => (await api.get<CentreFull[]>("ops/centres")).data });
export const useCounsellors = () =>
  useQuery({
    queryKey: ["counsellors"],
    queryFn: async () => (await api.get<CounsellorFull[]>("ops/counsellors")).data,
  });
export const useOpsStudents = (params: Record<string, string>) =>
  useQuery({
    queryKey: ["ops-students", params],
    queryFn: async () => {
      const r = await api.get<OpsStudentRow[]>("ops/students", params);
      return { rows: r.data, count: r.count ?? r.data.length, total: r.total ?? r.data.length };
    },
    placeholderData: keepPreviousData,
  });
export const useInsights = (centre: string) =>
  useQuery({
    queryKey: ["insights", centre],
    queryFn: async () => (await api.get<Insights>("ops/insights", { centre })).data,
  });

/** Sidebar counts for the operations lead: live centres, centres, counsellors, students (ops-only endpoints). */
export const useOpsNavCounts = (enabled: boolean) =>
  useQuery({
    queryKey: ["nav-counts", "ops"],
    enabled,
    refetchInterval: 15000,
    queryFn: async () => {
      const [live, centres, counsellors, students] = await Promise.all([
        api.get<LiveCentre[]>("ops/live"),
        api.get<CentreFull[]>("ops/centres"),
        api.get<CounsellorFull[]>("ops/counsellors"),
        api.get<OpsStudentRow[]>("ops/students", { limit: 1 }),
      ]);
      return { live: live.data.length, centres: centres.data.length, counsellors: counsellors.data.length, students: students.total ?? 0 };
    },
  });
