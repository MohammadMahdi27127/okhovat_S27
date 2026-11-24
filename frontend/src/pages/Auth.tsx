import { useEffect, useState, useRef } from 'react';
import { Link, useNavigate, useSearchParams } from 'react-router-dom';
import { motion, useReducedMotion } from 'framer-motion';
import { api, dateLabel, fa, today, upload, Post, Growth, Form, User } from '../api';
import { useApp } from '../context';
import { Avatar, AvatarUpload, Field, FilePicker, Icon, Loading, Modal, PlanDialog, Reveal, SubmitForm, Title } from '../components';

export function LoginPage() {
  const { restore, user } = useApp();
  const navigate = useNavigate();
  const [params] = useSearchParams();
  return <div className="form-shell login-shell"><section className="card login-card"><img className="login-logo" src="/assets/logo-ui.webp" alt="اخوت" /><h1>ورود به اخوت</h1>
    {user ? <Link className="btn full" to="/">ورود به خانه</Link> : <SubmitForm label="ورود" onSubmit={async form => {
      await api('login/', 'POST', { code: form.get('code'), password: form.get('password') });
      await restore();
      const next = params.get('next');
      navigate(next?.startsWith('/') && !next.startsWith('//') ? next : '/');
    }}>
      <Field label="کد گروهی" name="code" required maxLength={40} /><Field label="رمز عبور" name="password" type="password" required maxLength={256} />
    </SubmitForm>}
    <Link className="link" to="/forgot-password/">رمز عبور را فراموش کرده‌ام</Link>
  </section></div>;
}
export function ForgotPage() {
  return <section className="card form-shell"><Title title="بازیابی دسترسی" subtitle="برای بررسی هویت و بازیابی دسترسی، با پشتیبانی اخوت تماس بگیر." /><a className="btn" href="tel:09052893115">تماس با پشتیبانی</a><Link className="link" to="/login/">بازگشت به ورود</Link></section>;
}
