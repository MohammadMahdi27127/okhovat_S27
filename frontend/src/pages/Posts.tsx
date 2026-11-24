import { useEffect, useState, useRef } from 'react';
import { Link, useNavigate, useSearchParams } from 'react-router-dom';
import { motion, useReducedMotion } from 'framer-motion';
import { api, dateLabel, fa, today, upload, Post, Growth, Form, User } from '../api';
import { useApp } from '../context';
import { Avatar, AvatarUpload, Field, FilePicker, Icon, Loading, Modal, PlanDialog, Reveal, SubmitForm, Title } from '../components';

type Comment = { id: string; name: string; text: string; parent: string | null; likes: number; liked: boolean };
function CommentsDialog({ post, close, refreshPosts }: { post: Post; close: () => void; refreshPosts: () => Promise<void> }) {
  const [comments, setComments] = useState<Comment[] | null>(null);
  const [reply, setReply] = useState<string | null>(null);
  const { toast } = useApp();
  const load = async () => setComments(await api<Comment[]>('posts/' + post.id + '/comments/'));
  useEffect(() => { load().catch(e => toast(e.message)); }, [post.id]);
  return <Modal title="دیدگاه‌ها" close={close}>
    {comments ? comments.map(c => <article key={c.id} className={'comment-item ' + (c.parent ? 'reply-item' : '')}><b>{c.name}</b><p>{c.text}</p>
      <button className="link" onClick={async () => { try { await api('comments/' + c.id + '/like/', 'PUT', { active: !c.liked }); await load(); } catch (e) { toast((e as Error).message); } }}><Icon name="heart" /> {fa(c.likes)}</button>
      {!c.parent && <button className="link" onClick={() => setReply(c.id)}>پاسخ</button>}</article>) : <Loading />}
    {reply && <button className="link" onClick={() => setReply(null)}>لغو پاسخ</button>}
    <SubmitForm label="ارسال دیدگاه" onSubmit={async f => { await api('posts/' + post.id + '/comments/', 'POST', { text: f.get('text'), parent: reply }); setReply(null); await load(); await refreshPosts(); }}>
      <Field label="دیدگاهت را بنویس" name="text" type="textarea" required />
    </SubmitForm>
  </Modal>;
}
export function PostsPage() {
  const { data, user, refresh, toast } = useApp();
  const [params] = useSearchParams();
  const [tab, setTab] = useState('all');
  const [type, setType] = useState(params.get('type') || 'همه');
  const [items, setItems] = useState<Post[]>([]);
  const [page, setPage] = useState(1);
  const [more, setMore] = useState(false);
  const [busy, setBusy] = useState(true);
  const [error, setError] = useState('');
  const [comment, setComment] = useState<Post | null>(null);
  const [author, setAuthor] = useState<Post | null>(null);
  const [moderate, setModerate] = useState<Post | null>(null);
  const load = async () => {
    setBusy(true); setError('');
    try {
      const result = await api<{ results: Post[]; more: boolean }>('posts/?' + new URLSearchParams({ tab, type, page: String(page), ...(params.get('id') ? { id: params.get('id')! } : {}) }));
      setItems(result.results); setMore(result.more);
    } catch (e) { setError((e as Error).message); } finally { setBusy(false); }
  };
  useEffect(() => { load(); }, [tab, type, page, params]);
  const vote = async (p: Post, kind: string, active: boolean) => {
    try { await api('posts/' + p.id + '/votes/' + kind + '/', 'PUT', { active }); await load(); await refresh(); } catch (e) { toast((e as Error).message); }
  };
  return <section className="community-feed">
    <header className="feed-head"><h1>پست‌ها</h1><button onClick={() => toast('به‌زودی فعال می‌شود')}><Icon name="play" /> ریلز</button><Link className="btn" to="/posts/new/"><Icon name="new" /> پست جدید</Link></header>
    <div className="feed-toolbar">{[['all', 'برای شما'], ['following', 'دنبال‌شده‌ها'], ['trending', 'پست‌های ترند شده']].map(([key, label]) =>
      <button key={key} aria-pressed={tab === key} onClick={() => { setTab(key); setPage(1); }}>{label}</button>)}
      <select aria-label="نوع پست" value={type} onChange={e => { setType(e.target.value); setPage(1); }}>{['همه', 'حلقه', 'کارگروه', 'رشد فردی', 'شخصی'].map(t => <option key={t}>{t}</option>)}</select></div>
    {error && <p className="login-error" role="alert">{error}</p>}
    {busy ? <Loading /> : items.length ? items.map(post => <Reveal key={post.id}><article className={'feed-post' + (post.coachPost ? ' coach-post' : '')}>
      <button className="feed-avatar" aria-label={'پروفایل ' + post.name} onClick={() => setAuthor(post)}><Avatar name={post.name} src={post.avatar} /></button>
      <div className="feed-body"><header><button onClick={() => setAuthor(post)}><strong>{post.name}</strong>{post.coachPost && <span className="coach-label">پست مربی</span>}</button><small>{post.type} · {dateLabel(post.createdAt)}</small></header>
        <h2>{post.title}</h2><p className="preserve-lines">{post.text}</p>
        {post.image && <img className="feed-media" src={post.image} loading="lazy" alt={post.title} />}
        {post.video && <video className="feed-media" src={post.video} controls playsInline preload="metadata" />}
        {post.file && <a className="link" href={post.file} download>{post.fileName || 'دریافت فایل'}</a>}
        <div className="feed-actions">
          <button aria-label="دیدگاه" onClick={() => setComment(post)}><Icon name="comment" /><span>{fa(post.comments)}</span></button>
          <button aria-label="پسندیدن" aria-pressed={post.liked} onClick={() => vote(post, 'like', !post.liked)}><Icon name="heart" /><span>{fa(post.likes)}</span></button>
          <button aria-label="پیشنهاد به مربی" aria-pressed={post.recommended} onClick={() => vote(post, 'recommend', !post.recommended)}><Icon name="star" /></button>
          <button aria-label="ذخیره" aria-pressed={post.bookmarked} onClick={() => vote(post, 'bookmark', !post.bookmarked)}><Icon name="bookmark" /></button>
          <button aria-label="اشتراک‌گذاری" onClick={async () => { try { const url = location.origin + '/posts/?id=' + encodeURIComponent(post.id); if (navigator.share) await navigator.share({ title: post.title, url }); else { await navigator.clipboard.writeText(url); toast('نشانی کپی شد'); } } catch { /* Sharing was dismissed. */ } }}><Icon name="send" /></button>
        </div>
        {user?.is_admin && <button className="link" onClick={() => setModerate(post)}>مدیریت پست</button>}
      </div>
    </article></Reveal>) : <p className="empty">هنوز پستی در این بخش نیست.</p>}
    <div className="feed-pagination">{page > 1 && <button className="btn soft" onClick={() => setPage(page - 1)}>صفحهٔ قبل</button>}{more && <button className="btn soft" onClick={() => setPage(page + 1)}>صفحهٔ بعد</button>}</div>
    {comment && <CommentsDialog post={comment} close={() => setComment(null)} refreshPosts={load} />}
    {author && <Modal title={author.name} close={() => setAuthor(null)}><div className="author-profile"><Avatar name={author.name} src={author.avatar} /><h2>{author.name}</h2>
      {author.authorId !== user?.code && <button className="btn" onClick={async () => { try { await api('follows/' + author.authorId + '/', 'PUT', { active: !data?.following.includes(author.authorId) }); await refresh(); } catch (e) { toast((e as Error).message); } }}>{data?.following.includes(author.authorId) ? 'دنبال می‌کنی' : 'دنبال کردن'}</button>}</div></Modal>}
    {moderate && <Modal title="مدیریت پست" close={() => setModerate(null)}><p>پست «{moderate.title}»</p><SubmitForm label="تأیید حذف پست" onSubmit={async () => { await api('posts/' + moderate.id + '/', 'DELETE'); await load(); setModerate(null); }}><p>این پست از نمایش عمومی حذف می‌شود.</p></SubmitForm>
      <SubmitForm label="تعلیق نویسنده" onSubmit={async f => { await api('admin/members/' + moderate.authorId + '/suspend/', 'POST', { days: Number(f.get('days')) }); setModerate(null); toast('تعلیق ثبت شد'); }}>
        <label className="field">مدت تعلیق<select name="days"><option value="1">یک روز</option><option value="3">سه روز</option></select></label>
      </SubmitForm></Modal>}
  </section>;
}

