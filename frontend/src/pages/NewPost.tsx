import { useEffect, useState, useRef } from 'react';
import { Link, useNavigate, useSearchParams } from 'react-router-dom';
import { motion, useReducedMotion } from 'framer-motion';
import { api, dateLabel, fa, today, upload, Post, Growth, Form, User } from '../api';
import { useApp } from '../context';
import { Avatar, AvatarUpload, Field, FilePicker, Icon, Loading, Modal, PlanDialog, Reveal, SubmitForm, Title } from '../components';

export function NewPostPage() {
  const { user, data, refresh, toast } = useApp();
  const navigate = useNavigate();
  const [kind, setKind] = useState('شخصی');
  return <><Title title="یک روایت تازه" subtitle="اتفاق‌های خوب، با به اشتراک گذاشتن بیشتر می‌شوند." /><div className="form-shell">
    <SubmitForm className="card" label="انتشار روایت" onSubmit={async f => {
      const file = f.get('attachment') as File;
      const media = await upload(file, 'post');
      await api('posts/', 'POST', { title: f.get('title'), text: f.get('text'), type: kind, attachment: media?.url || '', fileName: file?.name || '',
        location: f.get('location') || '', when: f.get('when') ? new Date(String(f.get('when'))).toISOString() : null, people: f.getAll('people') });
      await refresh(); toast('پست منتشر شد'); navigate('/posts/');
    }}>
      <div className="posthead"><Avatar name={user!.name} /><div><b>{user!.name}</b><small>انتشار برای همهٔ اعضای اخوت</small></div></div>
      {(user?.is_ring_leader || user?.is_workgroup_manager) && <label className="field">نوع روایت<select value={kind} onChange={e => setKind(e.target.value)}>
        <option>شخصی</option>{user.is_ring_leader && <option value="حلقه">برنامهٔ حلقه</option>}{user.is_workgroup_manager && <option value="کارگروه">جلسهٔ کارگروه</option>}
      </select></label>}
      <Field label="عنوان روایت" name="title" required maxLength={300} /><Field label="متن روایت" name="text" type="textarea" required maxLength={20000} />
      {kind !== 'شخصی' && <div className="row"><Field label="محل برگزاری" name="location" /><Field label="زمان برگزاری" name="when" type="datetime-local" /></div>}
      {kind !== 'شخصی' && <fieldset className="attendees"><legend>چه کسانی همراه بودند؟</legend>
        {[...new Map((data?.programPeople || []).map(p => [p.code, p])).values()].filter(p => kind === 'حلقه' ? p.ring === user?.ring : p.team === user?.team).map(p =>
          <label className="check" key={p.code}><input name="people" type="checkbox" value={p.code} /><Avatar name={p.name} />{p.name}</label>)}
      </fieldset>}
      <FilePicker name="attachment" label="عکس، ویدیو یا فایل روایت" />
    </SubmitForm></div></>;
}
