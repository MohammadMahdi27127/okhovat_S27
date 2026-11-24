import { useEffect, useState } from 'react';
import { Link } from 'react-router-dom';
import { useReducedMotion } from 'framer-motion';
import { Icon, Reveal, Title } from '../components';
import { LandingCards } from '../landing';

export function HomePage() {
  const greeting = 'سلام دوست عزیز، به سامانهٔ ما خوش آمدی. اگر کمکی خواستی بهم بگو.';
  const reduced = useReducedMotion();
  const [length, setLength] = useState(() => localStorage.getItem('welcome-seen') ? greeting.length : 0);
  useEffect(() => {
    if (reduced) { setLength(greeting.length); return; }
    if (length >= greeting.length) { localStorage.setItem('welcome-seen', '1'); return; }
    const timer = setTimeout(() => setLength(n => n + 1), 25);
    return () => clearTimeout(timer);
  }, [length, reduced]);
  return <>
    <Title title="خانهٔ اخوت" subtitle="اطلاعیه‌ها و برنامه‌های این هفته" />
    <Reveal><section className="hero"><div className="hero-copy"><small>یک جمع صمیمی، برای یک مسیر بزرگ</small><h2 aria-label={greeting}>{greeting.slice(0, length)}</h2>
      <Link to="/chat/" className="btn gold"><Icon name="comment" /> گفت‌وگو با همراه اخوت</Link></div><div className="hero-art"><img src="/assets/logo-ui.webp" alt="اخوت" /></div></section></Reveal>
    <div className="columns home-columns"><section>
      <div className="sectionhead"><h2>برنامه‌های هفته</h2></div><Reveal className="card"><Link to="/posts/?type=حلقه">دیدن برنامه‌های حلقه‌ها و جلسات کارگروه‌ها</Link></Reveal>
      <LandingCards />
    </section><aside className="rail"><Reveal className="card"><h3>گزارش روزانه</h3><p>امروزت چطور گذشت؟</p><Link className="btn soft full" to="/growth/">ثبت رشد فردی</Link></Reveal></aside></div>
  </>;
}
