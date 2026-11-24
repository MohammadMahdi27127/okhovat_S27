import { useEffect, useState, useRef } from 'react';
import { Link, useNavigate, useSearchParams } from 'react-router-dom';
import { motion, useReducedMotion } from 'framer-motion';
import { api, dateLabel, fa, today, upload, Post, Growth, Form, User } from '../api';
import { useApp } from '../context';
import { Avatar, AvatarUpload, Field, FilePicker, Icon, Loading, Modal, PlanDialog, Reveal, SubmitForm, Title } from '../components';

export function ProfilePage() {
  const { user, data, attendance, refresh, logout, toast } = useApp();
  const [ranking, setRanking] = useState<{ name: string; attendance: number | null; total: number }[] | null>(null);
  const [rankingBusy, setRankingBusy] = useState(false);
  const [plan, setPlan] = useState(false);
  const [password, setPassword] = useState(false);
  if (!data || !user) return <Loading />;
  const status = data.preferences.personalStatus;
  const error: Record<string, string> = { missing_column: 'ستون درصد حضور در شیت پذیرش پیدا نشد.', unknown_code: 'کد گروهی در شیت پذیرش پیدا نشد یا تکراری است.', unavailable: 'دریافت درصد حضور از شیت پذیرش ممکن نشد.' };
  const percent = (n: number | null | undefined) => n == null ? 'ثبت نشده' : fa(n) + '٪';
  const gradeCard = (kind: 'ring' | 'group', label: string) => {
    const targets = [...new Set(data.directory.map(u => kind === 'ring' ? u.ring : u.team))].filter(Boolean);
    return <Reveal className="card" key={kind}><h2>امتیاز {label}</h2><SubmitForm label={'ثبت امتیاز ' + label} onSubmit={async f => {
      await api('grades/' + kind + '/', 'PUT', { target: f.get('target'), score: Number(f.get('score')) }); await refresh(); toast('امتیاز ذخیره شد');
    }}>
      <label className="field">انتخاب {label}<select name="target" required defaultValue=""><option value="" disabled>انتخاب کنید</option>{targets.map(n => <option key={n}>{n}</option>)}</select></label>
      <label className="field">امتیاز مربی<input name="score" type="number" required min="0" max="10000" step="any" /></label>
    </SubmitForm></Reveal>;
  };
  return <div className="profile-page">
    <div className="profile-page-heading"><h1>{user.is_coach ? user.name : 'پروفایل من'}</h1><button className="iconbtn profile-logout" onClick={() => logout().catch(e => toast(e.message))} aria-label="خروج از حساب"><Icon name="logout" /></button></div>
    {user.is_coach ? <div className="profile-sections">{gradeCard('group', 'کارگروه')}{gradeCard('ring', 'حلقه')}</div> : <>
      <Reveal className="card profile-overview"><div className="profile-identity"><AvatarUpload /><div><h2>{user.name}</h2><p>کد گروهی <b dir="ltr">{user.code}</b></p></div></div>
        <dl className="profile-stat-grid">{([['پست', data.stats.posts], ['دنبال‌کننده', data.stats.followers], ['دنبال‌شونده', data.stats.following], ['گزارش رشد', data.stats.growth]] as const).map(([label, n]) =>
          <div className="profile-stat" key={label}><dt>{label}</dt><dd>{fa(n)}</dd></div>)}</dl>
      </Reveal>
      <div className="profile-sections"><Reveal className="card"><h2>درصد حضور</h2>
        {attendance?.status === 'ok' ? <><p>حضور من <strong>{percent(attendance.percent)}</strong></p><h3>هم‌حلقه‌ای‌ها · {attendance.ring}</h3>
          <ul>{attendance.peers?.map((p, i) => <li key={i}>{p.name} · {percent(p.percent)}</li>)}</ul>
          {attendance.checked && <small>آخرین بررسی {dateLabel(attendance.checked)}</small>}</> : <p>{error[attendance?.status || ''] || 'در ورود بعدی حضور از شیت پذیرش خوانده می‌شود.'}</p>}
      </Reveal>
      <Reveal className="card"><h2>حلقهٔ من · {user.ring || 'تعیین نشده'}</h2>
        <p>امتیاز مربی: {fa(data.ringGrades[user.ring] || 0)}</p>
        <button className="btn soft" disabled={rankingBusy} onClick={async () => {
          setRankingBusy(true); try { setRanking(await api('rankings/')); } catch (e) { toast((e as Error).message); } finally { setRankingBusy(false); }
        }}>{rankingBusy ? 'در حال دریافت…' : 'رده‌بندی حلقه‌ها'}</button>
        {ranking && <ol>{ranking.map(row => <li key={row.name}>{row.name} · {fa(row.total)} امتیاز</li>)}</ol>}
        <p className="muted">امتیاز مربی و میانگین حضور هر کدام با ضریب ۲ محاسبه می‌شوند.</p>
      </Reveal>
      <Reveal className="card"><h2>کارگروه من · {user.team || 'تعیین نشده'}</h2><p>امتیاز مربی: {fa(data.groupGrades[user.team] || 0)}</p>
        <Link className="link" to="/posts/?type=کارگروه">جلسات ثبت‌شدهٔ کارگروه‌ها</Link>
      </Reveal>
      <Reveal className="card"><h2>وضعیت من</h2><div className="status-item"><Icon name="sport" /><div><h3>برنامهٔ ورزشی</h3><p>{status?.sportPlan || 'هنوز ثبت نشده'}</p></div></div>
        <div className="status-item"><Icon name="book" /><div><h3>کتاب در حال مطالعه</h3><p>{status?.currentBook || 'هنوز ثبت نشده'}</p></div></div><button className="btn gold full" onClick={() => setPlan(true)}>ویرایش برنامه و کتاب</button></Reveal>
      <Reveal className="card"><h2>پیام مربی {data.messages.some(m => !m.seen) && <span className="badge">خوانده‌نشده</span>}</h2>
        {data.messages.length ? data.messages.map(m => <article className="coach-record" key={m.id}><strong>{m.name}</strong><p>{m.text}</p><small>{dateLabel(m.date)}</small></article>) : <p>هنوز پیامی نداری.</p>}
        {data.messages.some(m => !m.seen) && <button className="btn soft" onClick={async () => { try { await api('messages/read/', 'POST'); await refresh(); } catch (e) { toast((e as Error).message); } }}>خواندم</button>}
      </Reveal></div>
    </>}
    <div className="profile-tools"><button className="link" onClick={() => setPassword(true)}>تغییر رمز عبور</button>{user.is_admin && <Link className="btn soft" to="/admin/reports/">مدیریت سایت</Link>}</div>
    {plan && <PlanDialog close={() => setPlan(false)} />}
    {password && <Modal title="تغییر رمز عبور" close={() => setPassword(false)}><SubmitForm onSubmit={async f => {
      if (f.get('password') !== f.get('repeat')) throw new Error('تکرار رمز یکسان نیست.');
      await api('password/', 'POST', { current: f.get('current'), password: f.get('password') }); setPassword(false); toast('رمز تغییر کرد');
    }}><Field name="current" label="رمز فعلی" type="password" required /><Field name="password" label="رمز جدید" type="password" required /><Field name="repeat" label="تکرار رمز جدید" type="password" required /></SubmitForm></Modal>}
  </div>;
}
