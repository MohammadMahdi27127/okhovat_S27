import { useEffect, useState, useRef } from 'react';
import { Link, useNavigate, useSearchParams } from 'react-router-dom';
import { motion, useReducedMotion } from 'framer-motion';
import { api, dateLabel, fa, today, upload, Post, Growth, Form, User } from '../api';
import { useApp } from '../context';
import { Avatar, AvatarUpload, Field, FilePicker, Icon, Loading, Modal, PlanDialog, Reveal, SubmitForm, Title } from '../components';

type RankingRow = { code: string; name: string; ring: string; group: string; value: number | null };
export function CoachPage() {
  const { data, refresh, toast } = useApp();
  const [tab, setTab] = useState('personal');
  const [person, setPerson] = useState('');
  const [search, setSearch] = useState('');
  const [metric, setMetric] = useState('sport');
  const [by, setBy] = useState('person');
  const [scope, setScope] = useState('all');
  const [team, setTeam] = useState('');
  const [rows, setRows] = useState<RankingRow[]>([]);
  const [programs, setPrograms] = useState<Post[]>([]);
  const [reports, setReports] = useState<Growth[]>([]);
  const [programKind, setProgramKind] = useState('کارگروه');
  const [programTarget, setProgramTarget] = useState('');
  const [program, setProgram] = useState('');
  const [busy, setBusy] = useState(false);
  const [audience, setAudience] = useState('all');
  const [error, setError] = useState('');
  const directory = data?.directory || [];
  const teams = [...new Set(directory.map(p => p.team))].filter(Boolean);
  const rings = [...new Set(directory.map(p => p.ring))].filter(Boolean);
  useEffect(() => {
    let active = true;
    setBusy(true); setError('');
    api<{ rows: RankingRow[]; programs: Post[]; reports: Growth[] }>('oversight/?' + new URLSearchParams({ metric, team: scope === 'group' ? team : '', person: tab === 'personal' ? person : '' }))
      .then(result => { if (active) { setRows(result.rows); setPrograms(result.programs); setReports(result.reports); } })
      .catch(e => { if (active) setError(e.message); }).finally(() => { if (active) setBusy(false); });
    return () => { active = false; };
  }, [metric, scope, team, person, tab]);
  const metrics: Record<string, string> = { sport: 'ورزش', reading: 'مطالعه', attendance: 'حضور', activity: 'فعالیت در سایت' };
  let ranking = rows;
  if (by !== 'person') {
    const grouped = new Map<string, { total: number; count: number }>();
    rows.forEach(row => {
      const name = by === 'ring' ? row.ring : row.group;
      if (!name) return;
      const item = grouped.get(name) || { total: 0, count: 0 };
      if (row.value !== null) { item.total += row.value; item.count++; }
      grouped.set(name, item);
    });
    ranking = [...grouped].map(([name, value]) => ({ code: name, name, ring: '', group: '', value: value.count ? metric === 'attendance' ? value.total / value.count : value.total : null }));
  }
  ranking = [...ranking].sort((a, b) => (b.value ?? -1) - (a.value ?? -1));
  if (scope === 'top') ranking = ranking.slice(0, 10);
  if (scope === 'bottom') ranking = ranking.slice(-10).reverse();
  const max = Math.max(1, ...ranking.map(r => r.value || 0));
  const selectedProgram = programs.find(p => p.id === program);
  const audienceOptions = audience === 'person' ? directory.map(p => [p.code, p.name]) : (audience === 'ring' ? rings : teams).map(n => [n, n]);
  return <>
    <Title title="پنل نظارتی" subtitle="مرور مسیر رشد اعضا و گروه‌ها" />
    <div className="tabs"><button className={'tab ' + (tab === 'personal' ? 'active' : '')} onClick={() => setTab('personal')}>نظارت فردی</button><button className={'tab ' + (tab === 'collective' ? 'active' : '')} onClick={() => setTab('collective')}>نظارت جمعی</button></div>
    {error && <p className="login-error" role="alert">{error}</p>}
    {tab === 'personal' ? <>
      <Reveal className="card"><label className="field">جست‌وجوی عضو<input value={search} onChange={e => setSearch(e.target.value)} placeholder="نام یا کد گروهی" /></label>
        <label className="field">انتخاب عضو<select value={person} onChange={e => setPerson(e.target.value)}><option value="">انتخاب کنید</option>{directory.filter(p => (p.name + p.code).includes(search)).map(p => <option value={p.code} key={p.code}>{p.name}</option>)}</select></label>
        <h2>رشد فردی در هفت روز اخیر</h2>
        {reports.length ? reports.map(g => <article className="coach-record" key={g.day}><b>{dateLabel(g.day + 'T12:00:00')}</b><p>{fa(g.sport)} ساعت ورزش · {fa(g.reading)} صفحه مطالعه</p>
          {g.skillTitle && <h3>{g.skillTitle}</h3>}{[g.learned, g.practice, g.responsibility, g.leisure].filter(Boolean).map((text, i) => <p key={i}>{text}</p>)}{g.proof && <a className="link" href={g.proof}>دریافت مستندات</a>}</article>) : <p>{person ? 'گزارشی در این بازه ثبت نشده است.' : 'یک عضو انتخاب کنید.'}</p>}
      </Reveal>
      <Reveal className="card"><h2>جلسات کارگروه و برنامه‌های حلقه</h2><label className="field">نوع<select value={programKind} onChange={e => { setProgramKind(e.target.value); setProgramTarget(''); setProgram(''); }}><option>کارگروه</option><option>حلقه</option></select></label>
        <label className="field">انتخاب گروه<select value={programTarget} onChange={e => { setProgramTarget(e.target.value); setProgram(''); }}><option value="">انتخاب کنید</option>{(programKind === 'حلقه' ? rings : teams).map(n => <option key={n}>{n}</option>)}</select></label>
        <label className="field">انتخاب برنامه<select value={program} onChange={e => setProgram(e.target.value)}><option value="">انتخاب کنید</option>{programs.filter(p => p.type === programKind && (programKind === 'حلقه' ? p.ring : p.group) === programTarget).map(p => <option key={p.id} value={p.id}>{p.title}</option>)}</select></label>
        {selectedProgram && <article><h3>{selectedProgram.title}</h3><p>{selectedProgram.text}</p>{selectedProgram.image && <img className="feed-media" src={selectedProgram.image} alt="" />}</article>}
      </Reveal>
    </> : <>
      <Reveal className="card coach-controls">
        <label className="field">شاخص<select value={metric} onChange={e => setMetric(e.target.value)}>{Object.entries(metrics).map(([value, text]) => <option key={value} value={value}>{text}</option>)}</select></label>
        <label className="field">رده‌بندی<select value={by} onChange={e => setBy(e.target.value)}><option value="person">افراد</option><option value="ring">حلقه‌ها</option><option value="group">کارگروه‌ها</option></select></label>
        <label className="field">نمایش<select value={scope} onChange={e => setScope(e.target.value)}><option value="all">اعضای کل</option><option value="group">بر اساس کارگروه</option><option value="top">ده نفر اول</option><option value="bottom">ده نفر آخر</option></select></label>
        {scope === 'group' && <label className="field">کارگروه<select value={team} onChange={e => setTeam(e.target.value)}><option value="">همه</option>{teams.map(n => <option key={n}>{n}</option>)}</select></label>}
      </Reveal>
      <Reveal className="card"><h2>{metrics[metric]}</h2>{busy ? <Loading /> : <>
        <div className="coach-chart" aria-hidden="true">{ranking.map(row => <div key={row.code}><small>{row.value === null ? '—' : fa(row.value)}</small><i style={{ height: 108 * (row.value || 0) / max }} /><span>{row.name}</span></div>)}</div>
        <ol className="coach-ranking">{ranking.map(row => <li key={row.code}><span>{row.name}</span><b>{row.value === null ? 'ثبت نشده' : fa(row.value)}</b></li>)}</ol>
      </>}</Reveal>
      <Reveal className="card"><h2>پیام دربارهٔ رشد فردی</h2><SubmitForm label="ارسال پیام" onSubmit={async f => {
        await api('messages/', 'POST', { scope: audience, target: f.get('target') || '', text: f.get('text') }); await refresh(); toast('پیام ارسال شد');
      }}><label className="field">مخاطب<select value={audience} onChange={e => setAudience(e.target.value)}><option value="all">همهٔ اعضا</option><option value="group">اعضای کارگروه</option><option value="ring">اعضای حلقه</option><option value="person">یک فرد</option></select></label>
        {audience !== 'all' && <label className="field">انتخاب مخاطب<select name="target" required key={audience}><option value="">انتخاب کنید</option>{audienceOptions.map(([value, name]) => <option key={value} value={value}>{name}</option>)}</select></label>}
        <Field name="text" label="متن پیام" type="textarea" required maxLength={4000} />
      </SubmitForm><h3>آرشیو پیام‌های ارسال‌شده</h3>{data?.archive.map(message => <article className="coach-record" key={message.id}><b>{message.label}</b><p>{message.body}</p><small>{dateLabel(message.created)}</small></article>)}</Reveal>
    </>}
  </>;
}
