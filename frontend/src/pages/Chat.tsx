import { useEffect, useState, useRef } from 'react';
import { Link, useNavigate, useSearchParams } from 'react-router-dom';
import { motion, useReducedMotion } from 'framer-motion';
import { api, dateLabel, fa, today, upload, Post, Growth, Form, User } from '../api';
import { useApp } from '../context';
import { Avatar, AvatarUpload, Field, FilePicker, Icon, Loading, Modal, PlanDialog, Reveal, SubmitForm, Title } from '../components';

export function ChatPage() {
  const { user, data } = useApp();
  const [messages, setMessages] = useState<{ role: string; text: string; route?: string }[]>([]);
  const [text, setText] = useState('');
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState('');
  const list = useRef<HTMLDivElement>(null);
  useEffect(() => { list.current?.scrollTo({ top: list.current.scrollHeight, behavior: 'smooth' }); }, [messages, busy]);
  async function send(value: string) {
    if (!value.trim() || busy) return;
    setMessages(current => [...current, { role: 'user', text: value }]); setText(''); setBusy(true); setError('');
    try {
      const answer = await api<{ text: string; route?: string }>('assistant/chat/', 'POST', { message: value });
      setMessages(current => [...current, { role: 'assistant', ...answer }]);
    } catch (e) { setError((e as Error).message); } finally { setBusy(false); }
  }
  return <section className="react-chat">
    <header className="chat-header"><Link to="/" className="iconbtn" aria-label="بازگشت"><Icon name="arrow" /></Link><img src="/assets/logo-ui.webp" alt="" /><div><h1>همراه اخوت</h1><small>راهنمای داخلی سامانه</small></div>
      <button className="iconbtn" aria-label="پاک کردن گفتگو" onClick={() => { setMessages([]); setError(''); }}><Icon name="trash" /></button></header>
    <div className="chat-messages" ref={list} aria-live="polite">
      {!messages.length && <div className="chat-empty"><img src="/assets/logo-ui.webp" alt="اخوت" /><h2>سلام {user?.name}</h2><p>برای مرور رشدت یا پیدا کردن بخش‌های سامانه اینجا هستم.</p></div>}
      {messages.map((message, i) => <article key={i} className={'chat-bubble ' + message.role}><p className="preserve-lines">{message.text}</p>{message.route && <Link className="link" to={message.route}>مشاهدهٔ بخش</Link>}</article>)}
      {busy && <Loading label="در حال بررسی…" />}{error && <p className="login-error" role="alert">{error}</p>}
    </div>
    <div className="chat-bottom"><div className="chat-suggestions">{['این هفته چقدر مطالعه کردم؟', 'آمار رشد حلقه‌ام چطور است؟', 'گزارش روزانه را کجا ثبت کنم؟'].map(t => <button key={t} disabled={busy} onClick={() => send(t)}>{t}</button>)}</div>
      <form className="chat-composer" onSubmit={e => { e.preventDefault(); send(text); }}><button className="btn send-button" disabled={busy || !text.trim()} aria-label="ارسال"><Icon name="send" /></button>
        <input value={text} onChange={e => setText(e.target.value)} maxLength={2000} placeholder="پیامت را بنویس…" aria-label="پیام" /><Avatar name={user!.name} src={data?.preferences.avatar} />
      </form></div>
  </section>;
}
