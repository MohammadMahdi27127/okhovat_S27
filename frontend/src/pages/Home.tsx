import { useEffect, useState, useRef } from 'react';
import { Link, useNavigate, useSearchParams } from 'react-router-dom';
import { motion, useReducedMotion } from 'framer-motion';
import { api, dateLabel, fa, today, upload, Post, Growth, Form, User } from '../api';
import { useApp } from '../context';
import { Avatar, AvatarUpload, Field, FilePicker, Icon, Loading, Modal, PlanDialog, Reveal, SubmitForm, Title } from '../components';

export function HomePage() {
  const { data, user } = useApp();
  const greeting = 'سلام دوست عزیز، به سامانهٔ ما خوش آمدی. اگر کمکی خواستی بهم بگو.';
  const reduced = useReducedMotion();
  const [length, setLength] = useState(() => localStorage.getItem('welcome-seen') ? greeting.length : 0);
  useEffect(() => {
    if (reduced) { setLength(greeting.length); return; }
    if (length >= greeting.length) { localStorage.setItem('welcome-seen', '1'); return; }
    const timer = setTimeout(() => setLength(n => n + 1), 25);
    return () => clearTimeout(timer);
  }, [length, reduced]);
  const [editor, setEditor] = useState(false);
  const { refresh } = useApp();
  return <>
    <Title title="خانهٔ اخوت" subtitle="اطلاعیه‌ها و برنامه‌های این هفته" />
    <Reveal><section className="hero"><div className="hero-copy"><small>یک جمع صمیمی، برای یک مسیر بزرگ</small><h2 aria-label={greeting}>{greeting.slice(0, length)}</h2>
      <Link to="/chat/" className="btn gold"><Icon name="comment" /> گفت‌وگو با همراه اخوت</Link></div><div className="hero-art"><img src="/assets/logo-ui.webp" alt="اخوت" /></div></section></Reveal>
    <div className="columns home-columns"><section>
      <div className="sectionhead"><h2>برنامه‌های هفته</h2></div><Reveal className="card"><Link to="/posts/?type=حلقه">دیدن برنامه‌های حلقه‌ها و جلسات کارگروه‌ها</Link></Reveal>
      <div className="sectionhead"><h2>محتوای کارگروه‌ها</h2>{user?.is_workgroup_manager && <button className="btn soft" onClick={() => setEditor(true)}>ثبت محتوا</button>}</div>
      <motion.div className="cards workgroup-cards" initial="hidden" animate="visible" variants={{ visible: { transition: { staggerChildren: .08 } } }}>
        {data?.landing.length ? data.landing.map((card, i) => <motion.article key={card.id} className="card"
          variants={{ hidden: { opacity: 0, y: 30, rotate: card.team === 'تدارکات' ? -2 : 0 }, visible: { opacity: 1, y: 0, rotate: 0 } }}
          transition={{ duration: .6, type: card.team === 'تربیت بدنی' ? 'spring' : 'tween' }}>
          <span className="tile-icon"><Icon name={card.team === 'تربیت بدنی' ? 'sport' : card.team === 'علوم اسلامی' ? 'book' : i % 2 ? 'users' : 'growth'} /></span>
          <h3>{card.team}</h3><strong>{card.title}</strong><p>{card.body}</p>
        </motion.article>) : <div className="card">هنوز محتوایی منتشر نشده است.</div>}
      </motion.div>
    </section><aside className="rail"><Reveal className="card"><h3>گزارش روزانه</h3><p>امروزت چطور گذشت؟</p><Link className="btn soft full" to="/growth/">ثبت رشد فردی</Link></Reveal></aside></div>
    {editor && <Modal title="محتوای کارگروه" close={() => setEditor(false)}><SubmitForm onSubmit={async f => {
      await api('landing/', 'POST', { title: f.get('title'), body: f.get('body') }); await refresh(); setEditor(false);
    }}><Field name="title" label="عنوان" required /><Field name="body" label="توضیح" type="textarea" required maxLength={4000} /></SubmitForm></Modal>}
  </>;
}
