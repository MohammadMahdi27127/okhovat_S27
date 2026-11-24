import { useEffect, useState } from 'react';
import { api, fa, upload, LandingCard, MemberTitle } from './api';
import { useApp } from './context';
import { Icon, Loading, Modal } from './components';

// کارت‌های مجاز هر کارگروه (هم‌راستا با landing_api.py)
export const TEAM_CARDS: Record<string, string[]> = {
  'مالی': ['announcement', 'debtors'],
  'هدایت و برنامه ریزی': ['announcement', 'meeting', 'html'],
  'آموزش': ['announcement'],
  'خدمات': ['announcement', 'image'],
  'علوم اسلامی': ['announcement', 'image'],
  'فرهنگی': ['announcement', 'image'],
  'سازماندهی': ['announcement', 'offenders'],
  'پذیرش': ['announcement', 'wanted'],
  'تربیت بدنی': ['announcement', 'gym_offenders'],
  'تدارکات': ['announcement', 'image'],
};
const CARD_LABEL: Record<string, string> = {
  announcement: 'اطلاعیه', meeting: 'جلسه', image: 'تصویر', html: 'صفحهٔ HTML',
  debtors: 'بدهکاران', wanted: 'وانتد', offenders: 'متخلفین', gym_offenders: 'متخلفین باشگاه',
};
// نگاشت نوع کارت لیستی به نوع عنوان در تاریخچه
const KIND_BY_CARD: Record<string, string> = {
  debtors: 'debtor', wanted: 'wanted', offenders: 'offender', gym_offenders: 'gym_offender',
};
// کارگروه مسئول هر نوع عنوان
const TEAM_BY_KIND: Record<string, string> = {
  debtor: 'مالی', wanted: 'پذیرش', offender: 'سازماندهی', gym_offender: 'تربیت بدنی',
};

function faDateTime(value: string) {
  return new Intl.DateTimeFormat('fa-IR', { dateStyle: 'full', timeStyle: 'short' }).format(new Date(value));
}
function toLocalInput(iso: string) {
  const d = new Date(iso); const pad = (n: number) => String(n).padStart(2, '0');
  return `${d.getFullYear()}-${pad(d.getMonth() + 1)}-${pad(d.getDate())}T${pad(d.getHours())}:${pad(d.getMinutes())}`;
}

export function ImageViewer({ src, close }: { src: string; close: () => void }) {
  return <div className="landing-viewer" role="dialog" aria-modal="true" aria-label="نمایش تمام‌صفحه">
    <button className="landing-viewer-close" onClick={close}><Icon name="arrow" /> بازگشت</button>
    <img src={src} alt="" onClick={close} />
  </div>;
}

function CardBody({ card, openImage, openTitles }: { card: LandingCard; openImage: (src: string) => void; openTitles: (kind: string) => void }) {
  if (card.card_type === 'image' && card.image)
    return <button className="landing-image" onClick={() => openImage(card.image!)} aria-label="نمایش تمام‌صفحه"><img src={card.image} alt={card.title} /></button>;
  if (card.card_type === 'html' && card.html_file)
    return <iframe className="landing-html" src={card.html_file} sandbox="allow-same-origin" title={card.title} loading="lazy" />;
  if (card.card_type === 'meeting')
    return <>
      {card.body && <p className="preserve-lines">{card.body}</p>}
      <p className="landing-meeting"><Icon name="bell" />{card.meeting_at ? faDateTime(card.meeting_at) : 'زمان جلسه ثبت نشده است.'}</p>
    </>;
  const kind = KIND_BY_CARD[card.card_type];
  if (kind)
    return <>
      {card.body && <p className="preserve-lines">{card.body}</p>}
      <button className="btn soft full" onClick={() => openTitles(kind)}>لیست {CARD_LABEL[card.card_type]} هفته</button>
    </>;
  return card.body ? <p className="preserve-lines">{card.body}</p> : null;
}

export function LandingCards() {
  const { user, toast } = useApp();
  const [cards, setCards] = useState<LandingCard[] | null>(null);
  const [image, setImage] = useState<string | null>(null);
  const [titles, setTitles] = useState<{ kind: string; team: string } | null>(null);
  const [editor, setEditor] = useState(false);
  const load = async () => { setCards(await api<LandingCard[]>('landing/cards/')); };
  useEffect(() => { load().catch(e => toast((e as Error).message)); }, []);
  const manager = user && user.is_workgroup_manager && user.team ? user : null;
  return <>
    <div className="sectionhead"><h2>محتوای کارگروه‌ها</h2>
      {manager && <button className="btn soft" onClick={() => setEditor(true)}>مدیریت کارت کارگروه</button>}
    </div>
    {!cards ? <Loading /> : cards.length ? <div className="cards workgroup-cards">
      {cards.map(card => <article className="card landing-card" key={card.id}>
        <div className="landing-head"><span className="tile-icon"><Icon name="users" /></span>
          <div><h3>{card.team}</h3><small>{CARD_LABEL[card.card_type] || card.title}</small></div></div>
        <strong>{card.title}</strong>
        <CardBody card={card} openImage={setImage} openTitles={kind => setTitles({ kind, team: card.team })} />
      </article>)}
    </div> : <div className="card">هنوز کارتی برای کارگروه‌ها منتشر نشده است.</div>}
    {image && <ImageViewer src={image} close={() => setImage(null)} />}
    {titles && <TitleList kind={titles.kind} team={titles.team} close={() => setTitles(null)} />}
    {editor && manager && <LandingManager close={() => setEditor(false)} onSaved={load} />}
  </>;
}

export function TitleList({ kind, team, close }: { kind: string; team: string; close: () => void }) {
  const { user, data, toast } = useApp();
  const [rows, setRows] = useState<MemberTitle[] | null>(null);
  const [history, setHistory] = useState<Record<string, number>>({});
  const [view, setView] = useState<string | null>(null);
  const isManager = !!user && user.is_workgroup_manager && user.team === TEAM_BY_KIND[kind];
  const load = async () => {
    const current = await api<MemberTitle[]>('landing/titles/?kind=' + kind);
    setRows(current);
    const all = await api<MemberTitle[]>('landing/titles/?kind=' + kind + '&all=1');
    const counts: Record<string, number> = {};
    all.forEach(r => { counts[r.actor_code] = (counts[r.actor_code] || 0) + 1; });
    setHistory(counts);
  };
  useEffect(() => { load().catch(e => toast((e as Error).message)); }, []);
  const act = (fn: () => Promise<unknown>) => fn().then(load).catch(e => toast((e as Error).message));
  const label = CARD_LABEL[Object.keys(KIND_BY_CARD).find(k => KIND_BY_CARD[k] === kind) || ''] || 'لیست';
  if (!user) return <Modal title="لیست هفته" close={close}><p>برای مشاهدهٔ این لیست وارد حساب خود شوید.</p></Modal>;
  return <Modal title={'لیست ' + label + ' هفته'} close={close}>
    {!rows ? <Loading /> : rows.length ? <ul className="title-list">
      {rows.map(r => <li key={r.id}>
        <span>{r.actor_name}</span>
        <small>تعداد دفعات قبلی: {fa(history[r.actor_code] || 0)}</small>
        {r.wanted_poster && <button className="btn light" onClick={() => setView(r.wanted_poster!)}>پوستر</button>}
        {isManager && <button className="link" onClick={() => act(() => api('landing/titles/' + r.id + '/', 'DELETE'))}>حذف</button>}
      </li>)}
    </ul> : <p>این هفته کسی ثبت نشده است.</p>}
    {isManager && data && <details className="title-add"><summary>افزودن عضو به لیست این هفته</summary>
      <ul>{data.directory.map(u => <li key={u.code}><span>{u.name}</span>
        <small>تعداد دفعات قبلی: {fa(history[u.code] || 0)}</small>
        <button className="btn soft" onClick={() => act(() => api('landing/titles/add/', 'POST', { actor_code: u.code, kind }))}>ثبت</button></li>)}</ul>
    </details>}
    <p className="muted">کارگروه مسئول: {TEAM_BY_KIND[kind]} · لیست متعلق به {team}</p>
    {view && <ImageViewer src={view} close={() => setView(null)} />}
  </Modal>;
}

export function LandingManager({ close, onSaved }: { close: () => void; onSaved: () => void | Promise<void> }) {
  const { user, toast } = useApp();
  const team = user?.team || '';
  const options = TEAM_CARDS[team] || ['announcement'];
  const [type, setType] = useState(options[0]);
  const [title, setTitle] = useState('اطلاعیه');
  const [body, setBody] = useState('');
  const [meeting, setMeeting] = useState('');
  const [image, setImage] = useState<File | undefined>();
  const [html, setHtml] = useState<File | undefined>();
  const [busy, setBusy] = useState(false);
  const [titles, setTitles] = useState(false);
  const kind = KIND_BY_CARD[type];
  useEffect(() => {
    api<LandingCard[]>('landing/cards/').then(cards => {
      const mine = cards.find(c => c.team === team);
      if (!mine) return;
      setType(mine.card_type); setTitle(mine.title); setBody(mine.body);
      if (mine.meeting_at) setMeeting(toLocalInput(mine.meeting_at));
    }).catch(() => {});
  }, [team]);
  async function save() {
    if (busy) return;
    setBusy(true);
    try {
      const payload: Record<string, unknown> = { card_type: type, title: title.trim() || 'اطلاعیه', body };
      if (type === 'meeting') {
        if (!meeting) throw new Error('تاریخ و ساعت جلسه را وارد کنید.');
        payload.meeting_at = new Date(meeting).toISOString();
      }
      if (type === 'image') {
        const result = await upload(image, 'landing');
        if (!result) throw new Error('عکس کارت را انتخاب کنید.');
        payload.image = result.url;
      }
      if (type === 'html') {
        const result = await upload(html, 'landing');
        if (!result) throw new Error('فایل HTML را انتخاب کنید (حداکثر ۱ مگابایت).');
        payload.html_file = result.url;
      }
      await api('landing/card/', 'POST', payload);
      await onSaved(); toast('کارت کارگروه ذخیره شد'); close();
    } catch (e) { toast((e as Error).message); } finally { setBusy(false); }
  }
  async function remove() {
    if (busy) return;
    setBusy(true);
    try { await api('landing/card/', 'DELETE'); await onSaved(); toast('کارت کارگروه حذف شد'); close(); }
    catch (e) { toast((e as Error).message); } finally { setBusy(false); }
  }
  return <Modal title="مدیریت کارت کارگروه" close={close}>
    <label className="field">کارگروه<span>{team || 'تعیین نشده'}</span></label>
    <label className="field">نوع کارت
      <select value={type} onChange={e => setType(e.target.value)}>
        {options.map(o => <option key={o} value={o}>{CARD_LABEL[o]}</option>)}
      </select>
    </label>
    <label className="field">عنوان<input value={title} maxLength={200} onChange={e => setTitle(e.target.value)} /></label>
    <label className="field">متن<textarea value={body} maxLength={8000} onChange={e => setBody(e.target.value)} /></label>
    {type === 'meeting' && <label className="field">تاریخ و ساعت جلسه<input type="datetime-local" value={meeting} onChange={e => setMeeting(e.target.value)} /></label>}
    {type === 'image' && <label className="upload-zone"><Icon name="upload" /><strong>انتخاب عکس کارت</strong><small>حداکثر ۱ مگابایت</small>
      <input type="file" accept="image/*" onChange={e => setImage(e.target.files?.[0])} />{image && <span className="upload-filename">{image.name}</span>}</label>}
    {type === 'html' && <label className="upload-zone"><Icon name="upload" /><strong>انتخاب فایل HTML</strong><small>حداکثر ۱ مگابایت · در iframe سندباکس نمایش داده می‌شود</small>
      <input type="file" accept=".html,.htm,text/html" onChange={e => setHtml(e.target.files?.[0])} />{html && <span className="upload-filename">{html.name}</span>}</label>}
    {kind && <button className="btn light full" onClick={() => setTitles(true)}>مدیریت لیست {CARD_LABEL[type]} هفته</button>}
    <button className="btn full" disabled={busy} onClick={save}>{busy ? 'در حال ذخیره…' : 'ذخیرهٔ کارت'}</button>
    <button className="link" disabled={busy} onClick={remove}>حذف کارت فعال کارگروه</button>
    {titles && kind && <TitleList kind={kind} team={team} close={() => setTitles(false)} />}
  </Modal>;
}
