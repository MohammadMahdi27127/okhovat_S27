import { useEffect, useState, useRef } from 'react';
import { Link, useNavigate, useSearchParams } from 'react-router-dom';
import { motion, useReducedMotion } from 'framer-motion';
import { api, dateLabel, fa, today, upload, Post, Growth, Form, User } from '../api';
import { useApp } from '../context';
import { Avatar, AvatarUpload, Field, FilePicker, Icon, Loading, Modal, PlanDialog, Reveal, SubmitForm, Title } from '../components';

type Weekly = { members: { code: string; name: string; nights: number }[]; rings: { actor__ring: string; count: number }[]; groups: { actor__team: string; count: number }[] };
export function AdminPage() {
  const { data, refresh, toast, restore } = useApp();
  const [editing, setEditing] = useState<User | null>(null);
  const [report, setReport] = useState<Weekly | null>(null);
  const [register, setRegister] = useState(false);
  const [error, setError] = useState('');
  useEffect(() => { api<Weekly>('admin/reports/').then(setReport).catch(e => setError(e.message)); }, []);
  function exportReport() {
    if (!report) return;
    const escape = (value: string | number) => '"' + String(value).replace(/^[=+@-]/, "'$&").replaceAll('"', '""') + '"';
    const text = '\uFEFF' + [['کد', 'نام', 'شب‌های ثبت رشد'], ...report.members.map(m => [m.code, m.name, m.nights])].map(row => row.map(escape).join(',')).join('\r\n');
    const url = URL.createObjectURL(new Blob([text], { type: 'text/csv;charset=utf-8' }));
    const a = document.createElement('a'); a.href = url; a.download = 'weekly-growth.csv'; a.click(); URL.revokeObjectURL(url);
  }
  return <><Title title="مدیریت سایت" subtitle="گزارش‌های هفته و مدیریت اعضا" /><div className="row"><button className="btn" onClick={() => setRegister(true)}>ثبت عضو جدید</button><button className="btn soft" onClick={exportReport} disabled={!report}>دریافت گزارش رشد</button></div>
    {error && <p className="login-error" role="alert">{error}</p>}
    {!report ? <Loading /> : <>
      <Reveal className="card"><h2>ثبت رشد این هفته</h2><div className="report-scroll"><table><thead><tr><th>نام</th><th>کد گروهی</th><th>تعداد شب</th></tr></thead><tbody>{report.members.map(m => <tr key={m.code}><td>{m.name}</td><td>{m.code}</td><td>{fa(m.nights)}</td></tr>)}</tbody></table></div></Reveal>
      <Reveal className="card"><h2>اعضای بدون گزارش</h2>{report.members.filter(m => !m.nights).map(m => <p key={m.code}>{m.name}</p>)}</Reveal>
      <Reveal className="card"><h2>جلسات کارگروه‌ها</h2>{report.groups.map(g => <p key={g.actor__team}>{g.actor__team} · {fa(g.count)} جلسه</p>)}</Reveal>
      <Reveal className="card"><h2>برنامه‌های حلقه‌ها</h2>{report.rings.map(r => <p key={r.actor__ring}>{r.actor__ring} · {fa(r.count)} برنامه</p>)}</Reveal>
    </>}
    <Reveal className="card"><h2>نقش‌ها و مسئولیت‌ها</h2>{data?.directory.map(member => <div className="rank" key={member.code}><span>{member.name} · {member.code}</span><button className="btn soft" onClick={() => setEditing(member)}>ویرایش دسترسی</button></div>)}</Reveal>
    {editing && <Modal title={'دسترسی ' + editing.name} close={() => setEditing(null)}><SubmitForm onSubmit={async f => {
      await api('admin/members/' + editing.code + '/roles/', 'PUT', {
        ring: f.get('ring'), team: f.get('team'), bale_id: f.get('bale_id'),
        is_admin: f.get('is_admin') === 'on', is_coach: f.get('is_coach') === 'on',
        is_ring_leader: f.get('is_ring_leader') === 'on', is_workgroup_manager: f.get('is_workgroup_manager') === 'on',
        is_concerned_member: f.get('is_concerned_member') === 'on',
      });
      setEditing(null); await restore(); toast('دسترسی ذخیره شد');
    }}>
      <Field label="حلقه" name="ring" value={editing.ring} /><Field label="کارگروه" name="team" value={editing.team} />
      <Field label="شناسهٔ بله" name="bale_id" value={editing.bale_id || ''} />
      {([['is_admin', 'ادمین'], ['is_coach', 'مربی'], ['is_ring_leader', 'مسئول حلقه'], ['is_workgroup_manager', 'مسئول کارگروه'], ['is_concerned_member', 'عضو دغدغه‌مند']] as const).map(([key, label]) =>
        <label className="check" key={key}><input type="checkbox" name={key} defaultChecked={editing[key]} />{label}</label>)}
    </SubmitForm></Modal>}
    {register && <Modal title="ثبت عضو جدید" close={() => setRegister(false)}><SubmitForm onSubmit={async f => {
      await api('admin/members/', 'POST', {
        code: f.get('code'), name: f.get('name'), password: f.get('password'), ring: f.get('ring'), team: f.get('team'),
        is_coach: f.get('is_coach') === 'on', is_admin: f.get('is_admin') === 'on',
        is_ring_leader: f.get('is_ring_leader') === 'on', is_workgroup_manager: f.get('is_workgroup_manager') === 'on',
      }); await refresh(); setRegister(false); toast('عضو ثبت شد');
    }}><Field label="کد گروهی" name="code" required /><Field label="نام" name="name" required /><Field label="رمز اولیه" name="password" type="password" required /><Field label="حلقه" name="ring" /><Field label="کارگروه" name="team" />
      {[['is_coach', 'مربی'], ['is_admin', 'ادمین'], ['is_ring_leader', 'مسئول حلقه'], ['is_workgroup_manager', 'مسئول کارگروه']].map(([name, label]) => <label className="check" key={name}><input name={name} type="checkbox" />{label}</label>)}
    </SubmitForm></Modal>}
  </>;
}
