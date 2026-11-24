export type User = {
  code: string; name: string; ring: string; team: string; bale_id?: string;
  is_coach: boolean; is_admin: boolean; is_ring_leader: boolean;
  is_workgroup_manager: boolean; is_concerned_member: boolean;
};
export type Attendance = { status: string; percent?: number | null; ring?: string; checked?: string; peers?: { name: string; percent: number | null }[] };
export type Growth = {
  day: string; dateJalali: string; sport: number; reading: number; publish?: boolean;
  skillTitle?: string; learned?: string; practice?: string; responsibility?: string;
  leisure?: string; proof?: string; proofName?: string; userId?: string; userName?: string; ring?: string; group?: string;
};
export type Post = {
  id: string; authorId: string; name: string; title: string; text: string; type: string;
  coachPost: boolean; createdAt: string; avatar?: string; image?: string; video?: string; file?: string;
  fileName?: string; likes: number; liked: boolean; recommended: boolean; trending: boolean; bookmarked: boolean; comments: number;
  location?: string; ring?: string; group?: string; people?: string[];
};
export type Form = { id: string; title: string; team: string; questions: string[] };
export type AppState = {
  growth: Growth[]; stats: { posts: number; growth: number; followers: number; following: number };
  following: string[]; preferences: { avatar?: string; personalStatus?: { sportPlan: string; currentBook: string } };
  programPeople: {code: string; name: string; ring: string; team: string}[]; directory: User[]; messages: { id: string; text: string; name: string; date: string; seen: boolean }[];
  archive: { id: string; label: string; body: string; created: string }[];
  notifications: { kind: string; count: number }[];
  ringGrades: Record<string, number>; groupGrades: Record<string, number>;
  landing: { id: string; team: string; title: string; body: string }[];
  forms: Form[]; answers: { form_id: string; answers: string[] }[];
};
let csrf = '';

export async function api<T>(path: string, method = 'GET', body?: unknown): Promise<T> {
  const headers: Record<string, string> = {};
  if (method !== 'GET') headers['X-CSRFToken'] = csrf;
  const isFile = body instanceof FormData;
  if (body && !isFile) headers['Content-Type'] = 'application/json';
  const response = await fetch('/api/' + path, {
    method, headers, credentials: 'same-origin', cache: 'no-store', signal: AbortSignal.timeout(45000),
    body: body ? isFile ? body : JSON.stringify(body) : undefined,
  });
  const data = await response.json().catch(() => ({ detail: 'پاسخ سرور دریافت نشد.' }));
  if (!response.ok) {
    const message = typeof data.detail === 'string' ? data.detail : Object.values(data).flat().join(' ');
    throw new Error(message || 'درخواست انجام نشد. دوباره تلاش کنید.');
  }
  if (data.csrf) csrf = data.csrf;
  return data;
}
export async function upload(file: File | undefined, purpose: string) {
  if (!file?.size) return null;
  if (file.size > 10 * 1024 * 1024) throw new Error('حداکثر حجم فایل ۱۰ مگابایت است.');
  const form = new FormData();
  form.append('file', file);
  return api<{ url: string; medium: string }>('files/upload/' + purpose + '/', 'POST', form);
}
export const fa = (value: number) => new Intl.NumberFormat('fa-IR').format(value);
export const dateLabel = (value: string) => new Date(value).toLocaleDateString('fa-IR');
export function today() {
  return new Intl.DateTimeFormat('en-CA', { timeZone: 'Asia/Tehran', year: 'numeric', month: '2-digit', day: '2-digit' }).format(new Date());
}
