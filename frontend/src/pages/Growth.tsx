import { useEffect, useState, useRef } from 'react';
import { Link, useNavigate, useSearchParams } from 'react-router-dom';
import { motion, useReducedMotion } from 'framer-motion';
import { api, dateLabel, fa, today, upload, Post, Growth, Form, User } from '../api';
import { useApp } from '../context';
import { Avatar, AvatarUpload, Field, FilePicker, Icon, Loading, Modal, PlanDialog, Reveal, SubmitForm, Title } from '../components';

export function GrowthPage() {
  const { data, user, refresh, toast } = useApp();
  const [plan, setPlan] = useState(false);
  const [leisureOpen, setLeisureOpen] = useState(false);
  const day = today();
  const current = data?.growth.find(g => g.day === day && g.userId === user?.code);
  const [leisure, setLeisure] = useState(current?.leisure || '');
  const [answering, setAnswering] = useState<Form | null>(null);
  const [builder, setBuilder] = useState(false);
  const choices = [['خواب', 'sleep'], ['ورزش', 'leisureSport'], ['بازی', 'game'], ['شبکه‌های اجتماعی', 'social']];
  return <>
    <Title title="رشد فردی" subtitle="ثبت ورزش، مطالعه، مهارت و فعالیت‌های روزانه" extra={<button className="iconbtn" aria-label="برنامه و کتاب من" onClick={() => setPlan(true)}><Icon name="plans" /></button>} />
    <div className="growth-date-row"><span className="growth-date">{dateLabel(day + 'T12:00:00')}</span>{current && <span className="badge">گزارش امروز ثبت شده</span>}</div>
    <Reveal className="growth-main"><SubmitForm className="card daily-growth-form" label={current ? 'به‌روزرسانی گزارش امروز' : 'ثبت رشد امروز'} onSubmit={async f => {
      const proof = await upload(f.get('proof') as File, 'proof');
      const record = {
        day, dateJalali: dateLabel(day + 'T12:00:00'), sport: Number(f.get('sport')), reading: Number(f.get('reading')),
        skillTitle: f.get('skillTitle'), learned: f.get('learned'), practice: f.get('practice'), responsibility: f.get('responsibility'),
        leisure, publish: f.get('publish') === 'on', proof: proof?.url || current?.proof || '',
        proofName: (f.get('proof') as File)?.name || current?.proofName || '',
      };
      await api('growth/', 'PUT', record); await refresh(); toast('گزارش رشد ذخیره شد');
    }}>
      <div className="top"><h2>امروزت چطور گذشت؟</h2><Icon name="growth" /></div>
      <div className="growth-grid"><div className="growth-tile"><Icon name="sport" /><label htmlFor="sport">ورزش</label><input id="sport" name="sport" type="number" min="0" max="24" step=".25" defaultValue={current?.sport || 0} required /><small>ساعت</small></div>
        <div className="growth-tile"><Icon name="book" /><label htmlFor="reading">مطالعه</label><input id="reading" name="reading" type="number" min="0" max="10000" step="1" defaultValue={current?.reading || 0} required /><small>صفحه</small></div></div>
      <div className="skill"><h3>مسیر مهارت من</h3><Field name="skillTitle" label="۱. عنوان مبحث تدریس‌شده" value={current?.skillTitle} maxLength={250} />
        <Field name="learned" label="۲. چه چیزی از این مبحث یاد گرفتی؟" type="textarea" value={current?.learned} maxLength={10000} />
        <Field name="practice" label="۳. امروز چه کار عملی انجام دادی؟" type="textarea" value={current?.practice} maxLength={10000} />
        <FilePicker name="proof" label="۴. مستندات فعالیت" existing={current?.proofName} /></div>
      <Field name="responsibility" label="مسئولیت گروهی" type="textarea" value={current?.responsibility} />
      <div className="field"><span>اوقات فراغت</span><button type="button" className="leisure-trigger" aria-expanded={leisureOpen} onClick={() => setLeisureOpen(!leisureOpen)}>{leisure || 'از حال خوب امروزت بگو'}</button>
        {leisureOpen && <div className="leisure-options">{choices.map(([label, icon]) => <button type="button" key={label} aria-pressed={leisure === label} onClick={() => { setLeisure(label); setLeisureOpen(false); }}><Icon name={icon} /><span>{label}</span></button>)}</div>}</div>
      <label className="growth-publish-option"><input type="checkbox" name="publish" defaultChecked={current?.publish === true} /><span><strong>گزارشم در پست‌ها منتشر شود</strong><small>خلاصهٔ ورزش، مطالعه و عنوان مهارت برای اعضا نمایش داده می‌شود.</small></span></label>
    </SubmitForm></Reveal>
    <div className="sectionhead"><h2>فرم‌های کارگروه‌ها</h2>{user?.is_workgroup_manager && <button className="btn soft" onClick={() => setBuilder(true)}>ایجاد فرم</button>}</div>
    {data?.forms.length ? data.forms.map(form => <Reveal className="card" key={form.id}><span className="badge">{form.team}</span><h3>{form.title}</h3><button className="btn soft" onClick={() => setAnswering(form)}>تکمیل فرم</button></Reveal>) : <div className="card">هنوز فرم فعالی نداریم.</div>}
    {plan && <PlanDialog close={() => setPlan(false)} />}
    {answering && <Modal title={answering.title} close={() => setAnswering(null)}><SubmitForm onSubmit={async f => {
      await api('forms/' + answering.id + '/answers/', 'PUT', { answers: answering.questions.map((_, i) => f.get('q' + i)) }); await refresh(); setAnswering(null);
    }}>{answering.questions.map((q, i) => <Field key={i} name={'q' + i} label={q} value={data?.answers.find(a => a.form_id === answering.id)?.answers[i]} type="textarea" required />)}</SubmitForm></Modal>}
    {builder && <Modal title="فرم تازه" close={() => setBuilder(false)}><SubmitForm onSubmit={async f => {
      await api('forms/', 'POST', { title: f.get('title'), questions: String(f.get('questions')).split('\n').filter(Boolean) }); await refresh(); setBuilder(false);
    }}><Field label="عنوان فرم" name="title" required /><Field label="پرسش‌ها، هر پرسش در یک خط" name="questions" type="textarea" required /></SubmitForm></Modal>}
  </>;
}
