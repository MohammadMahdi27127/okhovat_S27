import React, { useEffect, useState } from 'react';
import { createRoot } from 'react-dom/client';
import { BrowserRouter, Link, Navigate, NavLink, Outlet, Route, Routes, useLocation } from 'react-router-dom';
import { AnimatePresence, motion } from 'framer-motion';
import { AppProvider, useApp } from './context';
import { Icon, Loading } from './components';
import { HomePage, LoginPage, ProfilePage, GrowthPage, NewPostPage, PostsPage, ChatPage, NotificationsPage, CoachPage, AdminPage, ForgotPage } from './pages';
import './legacy.css';
import './styles.css';

const navigation = [
  { path: '/', label: 'خانهٔ اخوت', icon: 'home' },
  { path: '/posts/', label: 'پست‌ها', icon: 'posts' },
  { path: '/growth/', label: 'رشد فردی', icon: 'growth' },
  { path: '/profile/', label: 'پروفایل من', icon: 'profile' },
];
function Preloader() {
  const { loading, error } = useApp();
  const [progress, setProgress] = useState(0);
  const [visible, setVisible] = useState(true);
  useEffect(() => {
    if (!loading) { setProgress(100); const timer = setTimeout(() => setVisible(false), 180); return () => clearTimeout(timer); }
    const timer = setInterval(() => setProgress(p => Math.min(92, p + (95 - p) / 9)), 100);
    return () => clearInterval(timer);
  }, [loading]);
  return <AnimatePresence>{visible && !error && <motion.div className="react-preloader" exit={{ opacity: 0 }} transition={{ duration: .35 }} role="status" aria-label="در حال بارگذاری اخوت">
    <motion.strong animate={{ color: progress === 100 ? '#E6F2EF' : '#777' }} initial={{ color: '#222' }} transition={{ duration: 1 }}>اخوت</motion.strong>
    <small dir="ltr">loading... {Math.round(progress)}%</small>
  </motion.div>}</AnimatePresence>;
}
function Guard({ role }: { role?: 'coach' | 'admin' }) {
  const { user, loading, data } = useApp();
  const location = useLocation();
  if (loading) return <Loading />;
  if (!user) return <Navigate to={'/login/?next=' + encodeURIComponent(location.pathname)} replace />;
  if (!data) return <Loading />;
  if ((role === 'coach' && !user.is_coach) || (role === 'admin' && !user.is_admin)) return <div className="card">دسترسی این صفحه برای حساب شما فعال نیست.</div>;
  return <Outlet />;
}
function Tour() {
  const { user } = useApp();
  const [step, setStep] = useState(() => localStorage.getItem('okhovat-tour-complete') ? -1 : 0);
  const steps = [
    ['به اخوت خوش آمدی', 'در خانه، برنامه‌های هفته و محتوای کارگروه‌ها را می‌بینی.'],
    ['پست‌ها', 'روایت اعضا را بخوان، نظر بده و پست‌های مورد علاقه‌ات را به مربی پیشنهاد کن.'],
    ['رشد فردی', 'ورزش، مطالعه و مهارتت را ثبت کن. انتشار خلاصه در پست‌ها با انتخاب خودت است.'],
    ['پروفایل من', 'درصد حضور، برنامهٔ ورزشی، کتاب و پیام‌های مربی اینجاست.'],
    ['همراه اخوت', 'برای راهنمایی صفحات و مرور آمار رشد، روی لوگوی همراه اخوت بزن.'],
  ];
  if (!user || step < 0) return null;
  return <div className="tour-backdrop"><section className="card tour-card" role="dialog" aria-modal="true" aria-labelledby="tour-title">
    <h2 id="tour-title">{steps[step][0]}</h2><p>{steps[step][1]}</p><small>{step + 1} / {steps.length}</small>
    <button className="btn full" onClick={() => {
      if (step === steps.length - 1) { localStorage.setItem('okhovat-tour-complete', '1'); setStep(-1); }
      else setStep(step + 1);
    }}>{step === steps.length - 1 ? 'شروع کنیم' : 'بعدی'}</button>
  </section></div>;
}
function Layout() {
  const { user, data, error, toast } = useApp();
  const [menu, setMenu] = useState(false);
  const [dark, setDark] = useState(() => localStorage.getItem('theme') === 'dark');
  const location = useLocation();
  useEffect(() => { document.body.dataset.theme = dark ? 'dark' : 'light'; localStorage.setItem('theme', dark ? 'dark' : 'light'); }, [dark]);
  useEffect(() => { setMenu(false); window.scrollTo(0, 0); }, [location.pathname]);
  const coachNav = [navigation[0], navigation[1], { path: '/coach/', label: 'پنل نظارتی', icon: 'users' }, navigation[3]];
  const entries = user?.is_coach ? coachNav : navigation;
  const title = [...entries, { path: '/chat/', label: 'همراه اخوت' }, { path: '/login/', label: 'ورود به اخوت' }].find(n => n.path === location.pathname)?.label || 'اخوت';
  const unread = data?.messages.some(m => !m.seen);
  const navLink = (entry: { path: string; label: string; icon: string }, mobile = false) =>
    <NavLink key={entry.path} end to={entry.path} className={({ isActive }) => (mobile ? 'mobileitem' : 'navitem') + (isActive ? ' active' : '')}>
      <Icon name={entry.icon} /><span>{entry.label}</span>
    </NavLink>;
  return <>
    <aside id="sidebar"><Link className="brand" to="/"><img src="/assets/logo-ui.webp" alt="اخوت" /><div><strong>اخوت</strong><small>کنار هم، رو به رشد</small></div></Link>
      <div className="navs">{entries.map(e => navLink(e))}{user?.is_admin && navLink({ path: '/admin/reports/', label: 'مدیریت سایت', icon: 'users' })}</div>
    </aside>
    <div className={'workspace ' + (location.pathname === '/chat/' ? 'chat-workspace' : '')}>
      <header id="header">
        {location.pathname !== '/chat/' && <div className="breadcrumb"><Link to="/">اخوت</Link> / {title}</div>}
        <div className="header-actions">
          {location.pathname !== '/chat/' && <><button className="iconbtn theme-button" aria-label="تغییر حالت روشن و تاریک" onClick={() => setDark(!dark)}><Icon name={dark ? 'sun' : 'moon'} /></button>
          <Link className="iconbtn bell-button" to="/notifications/" aria-label="اعلان‌ها"><Icon name="bell" />{data?.notifications.length ? <i className="unread-dot" /> : null}</Link></>}
          <Link className="iconbtn profile-header" to={user ? '/profile/' : '/login/'} aria-label={user ? 'پروفایل' : 'ورود'}>{data?.preferences.avatar ? <img src={data.preferences.avatar} alt="" /> : <Icon name="profile" />}{unread && <i className="unread-dot" />}</Link>
        </div>
      </header>
      <main id="app">{error ? <div className="card"><p role="alert">{error}</p><button className="btn" onClick={() => location && window.location.reload()}>تلاش دوباره</button></div> : <Outlet />}</main>
      {location.pathname !== '/chat/' && <footer>اخوت، جایی برای با هم بودن <span><Icon name="support" /><a href="tel:09052893115">۰۹۰۵۲۸۹۳۱۱۵</a></span></footer>}
    </div>
    <nav id="mobileNav" className={user?.is_coach ? 'coach-dock' : ''} aria-label="ناوبری اصلی">
      {user?.is_coach ? coachNav.map(e => navLink(e, true)) : <>
        {navLink(navigation[0], true)}
        <div className={'react-capsule ' + (menu ? 'open' : '')}>
          <button className="capsule-logo" aria-label="منوی اخوت" aria-expanded={menu} onClick={() => setMenu(!menu)}>{menu ? <Icon name="close" /> : <img src="/assets/logo-ui.webp" alt="اخوت" />}</button>
          <AnimatePresence>{menu && <><motion.button initial={{ opacity: 0 }} animate={{ opacity: 1 }} exit={{ opacity: 0 }} className="capsule-overlay" onClick={() => setMenu(false)} aria-label="بستن منو" />
            <motion.div className="react-shortcuts" initial={{ opacity: 0, y: 20, scale: .9 }} animate={{ opacity: 1, y: 0, scale: 1 }} exit={{ opacity: 0, y: 15 }} transition={{ duration: .3 }}>
              <Link to="/posts/new/"><Icon name="new" /><span>پست جدید</span></Link>
              <Link to="/growth/"><Icon name="growth" /><span>رشد فردی</span></Link>
              <button onClick={() => { toast('به‌زودی فعال می‌شود'); setMenu(false); }}><Icon name="play" /><span>ریلز</span></button>
            </motion.div></>}</AnimatePresence>
        </div>
        {navLink(navigation[1], true)}
      </>}
    </nav>
    {location.pathname !== '/chat/' && <Link className="assistant" to="/chat/" aria-label="همراه اخوت"><img src="/assets/logo-ui.webp" alt="" /></Link>}
    <Tour />
  </>;
}
function App() {
  return <AppProvider><BrowserRouter><Preloader /><Routes><Route element={<Layout />}>
    <Route index element={<HomePage />} /><Route path="login/" element={<LoginPage />} /><Route path="forgot-password/" element={<ForgotPage />} />
    <Route element={<Guard />}><Route path="posts/" element={<PostsPage />} /><Route path="posts/new/" element={<NewPostPage />} />
      <Route path="growth/" element={<GrowthPage />} /><Route path="profile/" element={<ProfilePage />} /><Route path="chat/" element={<ChatPage />} />
      <Route path="notifications/" element={<NotificationsPage />} /><Route path="reels/" element={<div className="card">به‌زودی فعال می‌شود</div>} />
    </Route>
    <Route element={<Guard role="coach" />}><Route path="coach/" element={<CoachPage />} /></Route>
    <Route element={<Guard role="admin" />}><Route path="admin/reports/" element={<AdminPage />} /></Route>
    <Route path="*" element={<div className="card"><h1>صفحه پیدا نشد</h1><Link to="/">بازگشت به خانه</Link></div>} />
  </Route></Routes></BrowserRouter></AppProvider>;
}
createRoot(document.getElementById('root')!).render(<React.StrictMode><App /></React.StrictMode>);
