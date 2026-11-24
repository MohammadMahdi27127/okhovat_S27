import { useEffect, useState, useRef } from 'react';
import { Link, useNavigate, useSearchParams } from 'react-router-dom';
import { motion, useReducedMotion } from 'framer-motion';
import { api, dateLabel, fa, today, upload, Post, Growth, Form, User } from '../api';
import { useApp } from '../context';
import { Avatar, AvatarUpload, Field, FilePicker, Icon, Loading, Modal, PlanDialog, Reveal, SubmitForm, Title } from '../components';

export function NotificationsPage() {
  const { data, refresh, toast } = useApp();
  const labels: Record<string, string> = { post: 'پست جدید', like: 'پسند برای پست‌هایت', comment: 'دیدگاه جدید' };
  return <><Title title="اعلان‌ها" /><Reveal className="card">{data?.notifications.length ? <>
    {data.notifications.map(n => <p key={n.kind}>{fa(n.count)} {labels[n.kind] || n.kind}</p>)}
    <button className="btn soft" onClick={async () => { try { await api('notices/read/', 'POST'); await refresh(); } catch (e) { toast((e as Error).message); } }}>همه را خواندم</button>
  </> : <p>اعلان تازه‌ای نداری.</p>}</Reveal></>;
}
