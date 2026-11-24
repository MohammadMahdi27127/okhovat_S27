import { useEffect, useRef, useState, ReactNode, FormEvent } from 'react';
import { motion, useReducedMotion } from 'framer-motion';
import { Home, Newspaper, Plus, Bell, Moon, Sun, LogOut, Heart, MessageCircle, Bookmark, Send, Star, Users, Trash2, X, Check, Upload, Play, ArrowRight, Search, Camera, BookOpen, Dumbbell, Sprout, CircleHelp } from 'lucide-react';
import { useApp } from './context';
import { api, upload } from './api';

const glyphs = { home: Home, posts: Newspaper, new: Plus, bell: Bell, moon: Moon, sun: Sun, logout: LogOut,
  heart: Heart, comment: MessageCircle, bookmark: Bookmark, send: Send, star: Star, users: Users,
  trash: Trash2, close: X, check: Check, upload: Upload, play: Play, arrow: ArrowRight, search: Search,
  camera: Camera, book: BookOpen, sport: Dumbbell, growth: Sprout, help: CircleHelp };
const assets: Record<string, string> = { growth: 'growth', sport: 'dumbbell', book: 'reading', profile: 'profile',
  support: 'support', plans: 'plans', sleep: 'sleep', game: 'game', social: 'social', leisureSport: 'leisure-sport' };
export function Icon({ name }: { name: string }) {
  if (assets[name]) return <img className="asset-icon" src={'/assets/icon-' + assets[name] + '.png'} alt="" aria-hidden="true" />;
  const Glyph = glyphs[name as keyof typeof glyphs] || CircleHelp;
  return <Glyph aria-hidden="true" size={21} />;
}
export function Reveal({ children, className = '' }: { children: ReactNode; className?: string }) {
  const reduced = useReducedMotion();
  return <motion.div className={className} initial={reduced ? false : { opacity: 0, y: 30 }}
    whileInView={{ opacity: 1, y: 0 }} viewport={{ once: true, amount: 0.05 }}
    transition={{ duration: reduced ? 0 : .58, ease: [.22, 1, .36, 1] }}>{children}</motion.div>;
}
export function Avatar({ name, src }: { name: string; src?: string }) {
  return <span className="avatar">{src ? <img src={src} alt={name} /> : name.split(' ').slice(0, 2).map(n => n[0]).join('')}</span>;
}
export function Title({ title, subtitle, extra }: { title: string; subtitle?: string; extra?: ReactNode }) {
  return <div className="page-title"><div><h1>{title}</h1>{subtitle && <p>{subtitle}</p>}</div>{extra}</div>;
}
export function Loading({ label = 'در حال بارگذاری…' }: { label?: string }) {
  return <div className="section-loading" role="status"><span className="loading-ring" />{label}</div>;
}
export function Modal({ title, close, children }: { title: string; close: () => void; children: ReactNode }) {
  const ref = useRef<HTMLDialogElement>(null);
  useEffect(() => { ref.current?.showModal(); }, []);
  return <dialog ref={ref} onCancel={close} onClick={e => { if (e.target === ref.current) close(); }} aria-label={title}>
    <button type="button" className="close" aria-label="بستن" onClick={close}><Icon name="close" /></button>
    <h2>{title}</h2>{children}
  </dialog>;
}
export function SubmitForm({ children, onSubmit, label = 'ذخیره', className = '' }: {
  children: ReactNode; onSubmit: (data: FormData) => Promise<void>; label?: string; className?: string;
}) {
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState('');
  async function submit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    if (busy) return;
    const data = new FormData(event.currentTarget);
    setBusy(true); setError('');
    try { await onSubmit(data); } catch (e) { setError((e as Error).message); } finally { setBusy(false); }
  }
  return <form className={className} onSubmit={submit}>
    {children}
    {error && <p className="login-error" role="alert">{error}</p>}
    <button disabled={busy} className="btn full" type="submit">{busy ? 'در حال ثبت…' : label}</button>
  </form>;
}
export function Field({ label, name, value, type = 'text', required = false, maxLength = 2000 }: {
  label: string; name: string; value?: string | number; type?: string; required?: boolean; maxLength?: number;
}) {
  return <label className="field"><span>{label}</span>{type === 'textarea'
    ? <textarea name={name} defaultValue={value} required={required} maxLength={maxLength} />
    : <input name={name} type={type} defaultValue={value} required={required} maxLength={maxLength} />}</label>;
}
export function FilePicker({ name, accept, label = 'عکس یا فایل را انتخاب کن', existing }: { name: string; accept?: string; label?: string; existing?: string }) {
  const [filename, setFilename] = useState(existing || '');
  return <label className="upload-zone">
    <Icon name="upload" /><strong>{label}</strong><small>حداکثر ۱۰ مگابایت</small>
    <input type="file" name={name} accept={accept} onChange={e => setFilename(e.target.files?.[0]?.name || existing || '')} />
    {filename && <span className="upload-filename">{filename}</span>}
  </label>;
}
export function PlanDialog({ close }: { close: () => void }) {
  const { data, refresh, toast } = useApp();
  const [tab, setTab] = useState('sport');
  const current = data?.preferences.personalStatus;
  return <Modal title="برنامه و مطالعهٔ من" close={close}>
    <div className="tabs">
      <button onClick={() => setTab('sport')} className={'tab ' + (tab === 'sport' ? 'active' : '')}><Icon name="sport" /> برنامهٔ ورزشی</button>
      <button onClick={() => setTab('book')} className={'tab ' + (tab === 'book' ? 'active' : '')}><Icon name="book" /> کتاب در حال مطالعه</button>
    </div>
    <SubmitForm onSubmit={async form => {
      await api('profile/status/', 'PUT', {
        sportPlan: form.get('sportPlan'), currentBook: form.get('currentBook'),
      });
      await refresh(); toast('وضعیت من ذخیره شد'); close();
    }} label="ذخیرهٔ وضعیت من">
      <div hidden={tab !== 'sport'}><Field name="sportPlan" label="برنامهٔ ورزشی" type="textarea" value={current?.sportPlan} /></div>
      <div hidden={tab !== 'book'}><Field name="currentBook" label="نام کتاب در حال مطالعه" value={current?.currentBook} maxLength={300} /></div>
    </SubmitForm>
  </Modal>;
}
export function AvatarUpload() {
  const { user, data, refresh, toast } = useApp();
  return <label className="profile-avatar-control">
    <Avatar name={user!.name} src={data?.preferences.avatar} />
    <span className="avatar-camera"><Icon name="camera" /></span>
    <input className="sr-only" aria-label="بارگذاری آواتار" type="file" accept="image/*" onChange={async e => {
      try {
        const result = await upload(e.target.files?.[0], 'avatar');
        if (result) { await api('profile/avatar/', 'PUT', { url: result.url }); await refresh(); }
      } catch (error) { toast((error as Error).message); }
    }} />
  </label>;
}
