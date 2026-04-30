import React, { useEffect, useMemo, useState } from "react";
import { createRoot } from "react-dom/client";
import { BookOpen, Briefcase, Newspaper, Settings, UserRound, X, Minus, Square, Volume2 } from "lucide-react";
import { api } from "@/api";
import { Button } from "@/components/ui/button";
import "./styles.css";

const sidebarItems = [
  { key: "workspace", label: "工作区", icon: Briefcase },
  { key: "profile", label: "个人主页", icon: UserRound },
  { key: "settings", label: "设置", icon: Settings },
];

const contentTabs = [
  { key: "dashboard", label: "工作台" },
  { key: "words", label: "词库概览" },
  { key: "news", label: "日报" },
];

function Field({ label, children }) {
  return (
    <label className="flex flex-col gap-1.5 text-xs text-muted-foreground">
      {label}
      {children}
    </label>
  );
}

function inputClass() {
  return "h-10 rounded-lg border-[1.5px] border-border bg-white px-3 text-sm text-foreground outline-none transition focus:border-primary focus:ring-4 focus:ring-[#E0E7FF]";
}

function Card({ title, subtitle, children, className = "" }) {
  return (
    <section className={`rounded-xl bg-white p-5 shadow-card ${className}`}>
      {title ? <h2 className="text-sm font-semibold text-foreground">{title}</h2> : null}
      {subtitle ? <p className="mt-1 mb-4 text-xs text-muted-foreground">{subtitle}</p> : null}
      {children}
    </section>
  );
}

function WindowControls() {
  const controls = window.floatVocab;
  return (
    <div className="electron-no-drag flex h-full items-center">
      <button className="flex h-9 w-11 items-center justify-center text-muted-foreground hover:bg-muted" onClick={() => controls?.minimize()}>
        <Minus size={14} />
      </button>
      <button className="flex h-9 w-11 items-center justify-center text-muted-foreground hover:bg-muted" onClick={() => controls?.toggleMaximize()}>
        <Square size={12} />
      </button>
      <button className="flex h-9 w-11 items-center justify-center text-muted-foreground hover:bg-red-500 hover:text-white" onClick={() => controls?.close()}>
        <X size={15} />
      </button>
    </div>
  );
}

function FloatingCardLauncher({ card, plan }) {
  const [message, setMessage] = useState("");

  async function openFloatingCard() {
    setMessage("");
    if (!window.floatVocab?.showFloatingCard) {
      setMessage("当前不是 Electron 运行环境，无法打开系统悬浮窗。");
      return;
    }
    try {
      await window.floatVocab.showFloatingCard();
    } catch (error) {
      setMessage(error.message || "悬浮窗打开失败。");
    }
  }

  return (
    <Card title="悬浮词卡" subtitle="背词仍然在独立置顶窗口里进行。">
      <div className="rounded-lg bg-background p-4">
        <div className="text-xs text-muted-foreground">下一张</div>
        <div className="mt-2 text-2xl font-bold">{card?.word || "暂无待复习"}</div>
        <div className="mt-1 text-sm text-muted-foreground">{card?.phonetic || "点击下方按钮打开悬浮窗"}</div>
      </div>
      <Button className="mt-4 w-full" variant="primary" onClick={openFloatingCard}>
        打开悬浮窗
      </Button>
      {message ? <p className="mt-3 rounded-lg bg-red-50 p-3 text-xs text-red-600">{message}</p> : null}
      <div className="mt-4 space-y-2 border-t border-border pt-4 text-xs text-muted-foreground">
        <div className="flex justify-between">
          <span>透明度</span>
          <span className="font-medium text-foreground">{Math.round((plan?.float_alpha || 0.88) * 100)}%</span>
        </div>
        <div className="flex justify-between">
          <span>字号</span>
          <span className="font-medium text-foreground">{plan?.font_size || 26}px</span>
        </div>
        <div className="flex justify-between">
          <span>默认尺寸</span>
          <span className="font-medium text-foreground">{plan?.widget_size || "medium"}</span>
        </div>
      </div>
    </Card>
  );
}

function Dashboard({ plan, setPlan, languages, lexicons, setLexicons, stats, setStats, card, setCard }) {
  const [error, setError] = useState("");
  const [saving, setSaving] = useState(false);
  const summary = stats?.summary || {};
  const mastery = summary.total ? Math.round((summary.mastered / summary.total) * 100) : 0;
  const heatmap = useMemo(() => Array.from({ length: 30 }, (_, index) => stats?.days?.[index]?.reviewed || 0), [stats]);

  async function loadLexicons(languageCode, preferredLexiconId = null) {
    const rows = await api.lexicons(languageCode);
    setLexicons(rows);
    const selected = rows.find((row) => String(row.id) === String(preferredLexiconId)) || rows[0];
    setPlan((current) => ({
      ...current,
      current_language_code: languageCode,
      lexicon_id: selected?.id || "",
    }));
  }

  function updatePlanField(field, value) {
    setPlan((current) => ({ ...current, [field]: value }));
  }

  async function handleLanguageChange(event) {
    setError("");
    try {
      await loadLexicons(event.target.value);
    } catch (error) {
      setError(error.message);
    }
  }

  async function handleSavePlan() {
    if (!plan?.lexicon_id) {
      setError("请先选择一个词库。");
      return;
    }
    setSaving(true);
    setError("");
    try {
      const savedPlan = await api.savePlan({
        lexicon_id: Number(plan.lexicon_id),
        daily_new: Number(plan.daily_new || 20),
        target_date: plan.target_date,
        float_alpha: Number(plan.float_alpha || 0.88),
        font_size: Number(plan.font_size || 26),
        bg_color: plan.bg_color || "#F7FAF5",
        widget_size: plan.widget_size || "medium",
        current_language_code: plan.current_language_code,
      });
      setPlan(savedPlan);
      await loadLexicons(savedPlan.current_language_code, savedPlan.lexicon_id);
      const [nextStats, nextCard] = await Promise.all([api.stats(), api.nextCard()]);
      setStats(nextStats);
      setCard(nextCard);
    } catch (error) {
      setError(error.message);
    } finally {
      setSaving(false);
    }
  }

  return (
    <div className="grid gap-5 lg:grid-cols-[minmax(0,1fr)_300px]">
      <div className="flex min-w-0 flex-col gap-4">
        {error ? <div className="rounded-xl bg-red-50 p-4 text-sm text-red-600">{error}</div> : null}
        <Card title="学习计划" subtitle="选择词库、调整节奏，然后继续复习。">
          <div className="grid gap-3 md:grid-cols-2">
            <Field label="学习语言">
              <select className={inputClass()} value={plan?.current_language_code || ""} onChange={handleLanguageChange}>
                {languages.map((language) => (
                  <option key={language.code} value={language.code}>
                    {language.label} · {language.code}
                  </option>
                ))}
              </select>
            </Field>
            <Field label="当前词库">
              <select className={inputClass()} value={plan?.lexicon_id || ""} onChange={(event) => updatePlanField("lexicon_id", Number(event.target.value))}>
                {lexicons.map((lexicon) => (
                  <option key={lexicon.id} value={lexicon.id}>
                    {lexicon.id} · {lexicon.name} ({lexicon.mastered || 0}/{lexicon.total || 0})
                  </option>
                ))}
              </select>
            </Field>
            <Field label="目标日期">
              <input className={inputClass()} value={plan?.target_date || ""} onChange={(event) => updatePlanField("target_date", event.target.value)} />
            </Field>
            <Field label="每日新词">
              <input className={inputClass()} type="number" min="1" value={plan?.daily_new || ""} onChange={(event) => updatePlanField("daily_new", event.target.value)} />
            </Field>
          </div>
          <div className="mt-4 flex flex-wrap gap-2">
            <Button variant="primary" onClick={handleSavePlan} disabled={saving}>
              {saving ? "保存中" : "保存计划"}
            </Button>
            <Button>导入词库</Button>
            <Button>重命名</Button>
            <Button variant="danger">删除</Button>
          </div>
        </Card>

        <Card title="学习状态" subtitle="今天的复习完成度和最近 30 天的节奏。">
          <div className="grid grid-cols-3 gap-2.5">
            {[
              ["完成度", `${mastery}%`, "今日"],
              ["已掌握", summary.mastered || 0, `/ ${summary.total || 0}`],
              ["待复习", summary.due || 0, "今日"],
            ].map(([label, value, sub]) => (
              <div key={label} className="rounded-lg bg-background p-3">
                <div className="text-[11px] text-muted-foreground">{label}</div>
                <div className="mt-1 text-lg font-semibold">{value}</div>
                <div className="text-[11px] text-primary">{sub}</div>
              </div>
            ))}
          </div>
          <div className="mt-4 h-1 rounded-full bg-border">
            <div className="h-full rounded-full bg-primary" style={{ width: `${mastery}%` }} />
          </div>
          <div className="mt-3 flex flex-wrap gap-[3px]">
            {heatmap.map((count, index) => (
              <div
                key={index}
                className="h-3.5 w-3.5 rounded-[3px]"
                style={{ background: count > 14 ? "#6366F1" : count > 4 ? "#818CF8" : count > 0 ? "#C7D2FE" : "#E5E7EB" }}
              />
            ))}
          </div>
        </Card>
      </div>
      <aside className="flex flex-col gap-4">
        <FloatingCardLauncher card={card} plan={plan} />
      </aside>
    </div>
  );
}

function WordsView({ plan, words }) {
  return (
    <Card title="词库概览" subtitle="当前词库的最近词条。">
      {!plan?.lexicon_id ? (
        <div className="rounded-lg bg-background p-6 text-sm text-muted-foreground">请先在工作台选择词库。</div>
      ) : (
        <div className="overflow-hidden rounded-xl bg-white">
          <table className="w-full text-left text-sm">
            <thead className="bg-background text-xs text-muted-foreground">
              <tr>
                <th className="px-4 py-3 font-medium">单词</th>
                <th className="px-4 py-3 font-medium">释义</th>
                <th className="px-4 py-3 font-medium">状态</th>
              </tr>
            </thead>
            <tbody>
              {words.map((word) => (
                <tr key={word.id} className="border-t border-border">
                  <td className="px-4 py-3 font-medium">{word.word}</td>
                  <td className="px-4 py-3 text-muted-foreground">{word.meaning}</td>
                  <td className="px-4 py-3 text-muted-foreground">{word.status}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}
    </Card>
  );
}

function NewsView({ briefs, onRefresh }) {
  return (
    <Card title="日报" subtitle="当前学习语言下的最新内容。">
      <Button className="mb-4" onClick={onRefresh}>
        刷新最新 10 篇
      </Button>
      <div className="space-y-3">
        {briefs.length ? (
          briefs.map((brief) => (
            <article key={brief.id} className="rounded-xl bg-background p-4">
              <div className="text-sm font-semibold">{brief.title}</div>
              <div className="mt-1 text-xs text-muted-foreground">
                {brief.source_name} · {brief.published_at}
              </div>
              <p className="mt-2 text-sm text-muted-foreground">{brief.summary || "暂无摘要"}</p>
            </article>
          ))
        ) : (
          <div className="rounded-lg bg-background p-6 text-sm text-muted-foreground">还没有日报内容，可以点击刷新。</div>
        )}
      </div>
    </Card>
  );
}

function SettingsView({ plan, setPlan }) {
  return (
    <div className="grid gap-4 lg:grid-cols-2">
      <Card title="界面设置" subtitle="这些设置后续会写入本地配置。">
        <div className="space-y-3">
          <Field label="默认窗口大小">
            <select className={inputClass()} value="default" readOnly>
              <option value="default">1180 × 760</option>
            </select>
          </Field>
          <Field label="界面颜色">
            <select className={inputClass()} value="light" readOnly>
              <option value="light">浅色</option>
            </select>
          </Field>
          <label className="flex items-center justify-between rounded-lg bg-background p-3 text-sm">
            开机启动
            <input type="checkbox" className="h-4 w-4 accent-primary" readOnly />
          </label>
        </div>
      </Card>
      <Card title="悬浮窗默认值">
        <div className="space-y-3">
          <Field label="透明度">
            <input className={inputClass()} value={plan?.float_alpha || ""} onChange={(event) => setPlan((current) => ({ ...current, float_alpha: event.target.value }))} />
          </Field>
          <Field label="字号">
            <input className={inputClass()} value={plan?.font_size || ""} onChange={(event) => setPlan((current) => ({ ...current, font_size: event.target.value }))} />
          </Field>
        </div>
      </Card>
    </div>
  );
}

function formatSyncTime(value) {
  if (!value) {
    return "暂无";
  }
  try {
    return new Date(value).toLocaleString();
  } catch {
    return value;
  }
}

function ProfileView({ onCloudRestored }) {
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [session, setSession] = useState(null);
  const [syncStatus, setSyncStatus] = useState(null);
  const [message, setMessage] = useState("");
  const [busy, setBusy] = useState(false);

  async function refreshCloudState() {
    const sessionData = await api.cloudSession();
    setSession(sessionData);
    if (sessionData.user) {
      try {
        const status = await api.cloudSyncStatus();
        setSyncStatus(status);
        return status;
      } catch (error) {
        setMessage(error.message);
      }
    }
    return null;
  }

  useEffect(() => {
    refreshCloudState().catch((error) => setMessage(error.message));
  }, []);

  async function login(mode) {
    setBusy(true);
    setMessage("");
    try {
      const payload = { email, password };
      const result = mode === "signup" ? await api.cloudSignup(payload) : await api.cloudLogin(payload);
      if (result.needs_confirmation) {
        setMessage("注册成功，请先到邮箱完成确认后再登录。");
        return;
      }
      const status = await refreshCloudState();
      if (status?.remote && Number(status.local?.reviews_count || 0) === 0) {
        await api.cloudSyncDownload();
        setMessage("已登录，并自动从云端恢复学习数据。");
        await onCloudRestored?.();
        await refreshCloudState();
      } else {
        setMessage("已登录 FloatVocab 云同步。");
      }
    } catch (error) {
      setMessage(error.message);
    } finally {
      setBusy(false);
    }
  }

  async function logout() {
    setBusy(true);
    setMessage("");
    try {
      await api.cloudLogout();
      setSyncStatus(null);
      await refreshCloudState();
      setMessage("已退出云同步账号。");
    } catch (error) {
      setMessage(error.message);
    } finally {
      setBusy(false);
    }
  }

  async function upload() {
    setBusy(true);
    setMessage("");
    try {
      await api.cloudSyncUpload();
      await refreshCloudState();
      setMessage("已上传当前学习数据到云端。");
    } catch (error) {
      setMessage(error.message);
    } finally {
      setBusy(false);
    }
  }

  async function download() {
    setBusy(true);
    setMessage("");
    try {
      await api.cloudSyncDownload();
      await onCloudRestored?.();
      await refreshCloudState();
      setMessage("已从云端恢复学习数据。");
    } catch (error) {
      setMessage(error.message);
    } finally {
      setBusy(false);
    }
  }

  const user = session?.user;

  return (
    <div className="grid gap-4 lg:grid-cols-[1fr_1fr]">
      <Card title="FloatVocab 账号" subtitle="登录后会把学习进度同步到 Supabase。">
        {user ? (
          <div className="space-y-4">
            <div className="rounded-xl bg-background p-4">
              <div className="text-xs text-muted-foreground">当前账号</div>
              <div className="mt-1 text-base font-semibold">{user.email}</div>
            </div>
            <Button disabled={busy} onClick={logout}>
              退出登录
            </Button>
          </div>
        ) : (
          <div className="space-y-3">
            <Field label="邮箱">
              <input className={inputClass()} value={email} onChange={(event) => setEmail(event.target.value)} />
            </Field>
            <Field label="密码">
              <input className={inputClass()} type="password" value={password} onChange={(event) => setPassword(event.target.value)} />
            </Field>
            <div className="flex gap-2">
              <Button disabled={busy || !email || !password} variant="primary" onClick={() => login("login")}>
                登录
              </Button>
              <Button disabled={busy || !email || !password} onClick={() => login("signup")}>
                注册
              </Button>
            </div>
          </div>
        )}
        {message ? <p className="mt-4 rounded-lg bg-background p-3 text-xs text-muted-foreground">{message}</p> : null}
      </Card>

      <Card title="云端学习数据" subtitle="同步词库、复习进度、学习计划、统计和个人设置。">
        <div className="space-y-3 text-sm">
          <div className="grid grid-cols-2 gap-2">
            <div className="rounded-lg bg-background p-3">
              <div className="text-xs text-muted-foreground">本地复习记录</div>
              <div className="mt-1 text-lg font-semibold">{syncStatus?.local?.reviews_count ?? session?.local?.reviews_count ?? 0}</div>
            </div>
            <div className="rounded-lg bg-background p-3">
              <div className="text-xs text-muted-foreground">本地单词</div>
              <div className="mt-1 text-lg font-semibold">{syncStatus?.local?.words_count ?? session?.local?.words_count ?? 0}</div>
            </div>
          </div>
          <div className="rounded-lg bg-background p-3 text-xs text-muted-foreground">
            <div>云端更新时间：{formatSyncTime(syncStatus?.remote?.updated_at)}</div>
            <div className="mt-1">本地最近变化：{formatSyncTime(syncStatus?.local?.latest_local_change || session?.local?.latest_local_change)}</div>
          </div>
          <div className="flex flex-wrap gap-2">
            <Button disabled={busy || !user} variant="primary" onClick={upload}>
              上传到云端
            </Button>
            <Button disabled={busy || !user || !syncStatus?.remote} onClick={download}>
              从云端恢复
            </Button>
            <Button disabled={busy || !user} onClick={refreshCloudState}>
              刷新状态
            </Button>
          </div>
        </div>
      </Card>
    </div>
  );
}

function splitMeaning(meaning = "") {
  const trimmed = meaning.trim();
  const match = trimmed.match(/^(adj\.|adv\.|n\.|v\.|vt\.|vi\.|prep\.|conj\.|pron\.)\s*/i);
  if (!match) {
    return { pos: "", text: trimmed || "暂无释义" };
  }
  return { pos: match[1], text: trimmed.slice(match[0].length).trim() || trimmed };
}

function FloatingCardRoute() {
  const [card, setCard] = useState(null);
  const [flipped, setFlipped] = useState(false);
  const [feedback, setFeedback] = useState("");
  const [speaking, setSpeaking] = useState(false);
  const [stats, setStats] = useState(null);
  const [streak, setStreak] = useState(0);
  const [history, setHistory] = useState([]);
  const [toast, setToast] = useState("");

  useEffect(() => {
    Promise.all([api.nextCard(), api.stats()])
      .then(([nextCard, nextStats]) => {
        setCard(nextCard);
        setStats(nextStats);
      })
      .catch(() => setCard(null));
  }, []);

  useEffect(() => {
    function handleKeyDown(event) {
      if (event.key === "Escape") {
        window.floatVocab?.hideFloatingCard();
        return;
      }
      if (event.code === "Space") {
        event.preventDefault();
        setFlipped((value) => !value);
        return;
      }
      if (event.code === "ArrowLeft") {
        event.preventDefault();
        review(2);
        return;
      }
      if (event.code === "ArrowRight") {
        event.preventDefault();
        review(4);
      }
    }
    window.addEventListener("keydown", handleKeyDown);
    return () => window.removeEventListener("keydown", handleKeyDown);
  }, [card?.id]);

  async function review(rating) {
    if (!card?.id || feedback) {
      return;
    }
    const known = rating >= 4;
    const nextStreak = known ? streak + 1 : 0;
    setFeedback(known ? "known" : "forgot");
    setStreak(nextStreak);
    setHistory((items) => [...items.slice(-6), known ? "yes" : "no"]);
    setToast(known ? (nextStreak >= 3 ? `${nextStreak} 连击` : "认识") : "加入复习");
    const result = await api.review(card.id, rating);
    setStats(result.stats);
    window.setTimeout(() => {
      setCard(result.next_card);
      setFlipped(false);
      setFeedback("");
      window.setTimeout(() => setToast(""), 700);
    }, 260);
  }

  function speakWord() {
    if (!card?.word || !window.speechSynthesis) {
      return;
    }
    window.speechSynthesis.cancel();
    const utterance = new SpeechSynthesisUtterance(card.word);
    utterance.lang = "en-US";
    utterance.rate = 0.85;
    utterance.onend = () => setSpeaking(false);
    utterance.onerror = () => setSpeaking(false);
    setSpeaking(true);
    window.speechSynthesis.speak(utterance);
  }

  const meaning = splitMeaning(card?.meaning);
  const total = Number(stats?.summary?.total || 0);
  const mastered = Number(stats?.summary?.mastered || 0);
  const progress = total > 0 ? Math.round((mastered / total) * 100) : 0;
  const recentHistory = history.slice(-7);
  const streakDots = Array.from({ length: 7 }, (_, index) => recentHistory[index - (7 - recentHistory.length)] || null);

  return (
    <main className="floating-card-window">
      <section className={`floating-study-card ${feedback ? `floating-feedback-${feedback}` : ""}`}>
        <div className="floating-card-titlebar electron-drag">
          <span>FloatVocab · 当前学习卡</span>
          <button className="floating-close-button electron-no-drag" onClick={() => window.floatVocab?.hideFloatingCard()}>
            ×
          </button>
        </div>
        <div className="floating-word-area">
          <div className={`floating-word ${speaking ? "is-speaking" : ""}`}>
            <span>{card?.word || "Ready"}</span>
            <button className={`floating-sound-button electron-no-drag ${speaking ? "is-playing" : ""}`} onClick={speakWord} aria-label="朗读单词">
              <Volume2 size={14} />
            </button>
          </div>
          <div className="floating-phonetic">{card?.phonetic || "No due card"}</div>
        </div>

        <div className="floating-flip-shell">
          <div className={`floating-card-inner ${flipped ? "is-flipped" : ""}`}>
            <div className="floating-flip-face">
              <div className="floating-front-placeholder" />
            </div>
            <div className="floating-flip-face floating-flip-back">
              <div className="floating-meaning-area">
              {meaning.pos ? <div className="floating-pos">{meaning.pos}</div> : null}
              <div className="floating-meaning-text">{meaning.text}</div>
              {card?.example ? <div className="floating-example">{card.example}</div> : null}
              </div>
            </div>
          </div>
        </div>

        <div className="floating-progress-area">
          <div className="floating-progress-bar">
            <div className="floating-progress-fill" style={{ width: `${progress}%` }} />
          </div>
          <span className="floating-progress-text">{total > 0 ? `${mastered} / ${total}` : "0 / 0"}</span>
        </div>
        <div className="floating-card-actions electron-no-drag">
          <button className="floating-action-button floating-action-forgot" onClick={() => review(2)}>
            不认识
          </button>
          <button className="floating-action-button floating-action-flip" onClick={() => setFlipped((value) => !value)}>
            {flipped ? "收起" : "翻面"}
          </button>
          <button className="floating-action-button floating-action-known" onClick={() => review(4)}>
            认识
          </button>
        </div>
        <div className="floating-card-hint">Space 翻面 · ← 不认识 · → 认识</div>
        <div className="floating-streak-bar">
          <span className="floating-streak-label">连续</span>
          <div className="floating-streak-dots">
            {streakDots.map((item, index) => (
              <span key={`${index}-${item || "empty"}`} className={`floating-streak-dot ${item ? `is-${item}` : ""} ${index === 6 && item ? "is-new" : ""}`} />
            ))}
          </div>
          <span className="floating-streak-count">{streak} 连击</span>
        </div>
        <div className={`floating-toast ${toast ? "is-visible" : ""}`}>{toast}</div>
      </section>
    </main>
  );
}

function AppShell() {
  const [activeSidebar, setActiveSidebar] = useState("workspace");
  const [activeTab, setActiveTab] = useState("dashboard");
  const [plan, setPlan] = useState(null);
  const [languages, setLanguages] = useState([]);
  const [lexicons, setLexicons] = useState([]);
  const [stats, setStats] = useState(null);
  const [card, setCard] = useState(null);
  const [words, setWords] = useState([]);
  const [briefs, setBriefs] = useState([]);
  const [error, setError] = useState("");

  useEffect(() => {
    loadWorkspaceData().catch((reason) => setError(reason.message));
  }, []);

  async function loadWorkspaceData() {
    const [planData, languagesData, statsData, cardData] = await Promise.all([api.plan(), api.languages(), api.stats(), api.nextCard()]);
    setPlan(planData);
    setLanguages(languagesData);
    setStats(statsData);
    setCard(cardData);
    const [lexiconRows, briefRows] = await Promise.all([api.lexicons(planData.current_language_code), api.latestNews(planData.current_language_code)]);
    setLexicons(lexiconRows);
    setBriefs(briefRows);
    if (planData.lexicon_id) {
      setWords(await api.recentWords(planData.lexicon_id, 120));
    } else {
      setWords([]);
    }
  }

  useEffect(() => {
    if (!plan?.lexicon_id) {
      return;
    }
    api.recentWords(plan.lexicon_id, 120).then(setWords).catch(() => undefined);
  }, [plan?.lexicon_id]);

  async function refreshNews() {
    const rows = await api.refreshNews(plan?.current_language_code);
    setBriefs(rows);
  }

  function renderContent() {
    if (activeSidebar === "profile") {
      return <ProfileView onCloudRestored={loadWorkspaceData} />;
    }
    if (activeSidebar === "settings") {
      return <SettingsView plan={plan} setPlan={setPlan} />;
    }
    if (activeTab === "words") {
      return <WordsView plan={plan} words={words} />;
    }
    if (activeTab === "news") {
      return <NewsView briefs={briefs} onRefresh={refreshNews} />;
    }
    return (
      <Dashboard
        plan={plan}
        setPlan={setPlan}
        languages={languages}
        lexicons={lexicons}
        setLexicons={setLexicons}
        stats={stats}
        setStats={setStats}
        card={card}
        setCard={setCard}
      />
    );
  }

  return (
    <div className="flex h-full overflow-hidden bg-background">
      <aside className="w-[200px] shrink-0 bg-[#1C1C2E] px-3 py-5 text-white">
        <div className="mb-6 flex items-center gap-2 border-b border-white/10 px-2 pb-6">
          <div className="flex h-8 w-8 items-center justify-center rounded-lg bg-primary text-sm font-semibold">F</div>
          <div className="text-sm font-semibold">FloatVocab</div>
        </div>
        <nav className="space-y-0.5">
          {sidebarItems.map((item) => {
            const Icon = item.icon;
            const active = activeSidebar === item.key;
            return (
              <button
                key={item.key}
                onClick={() => setActiveSidebar(item.key)}
                className={`flex w-full items-center gap-2 rounded-lg px-3 py-2 text-left text-sm transition ${
                  active ? "bg-primary/20 text-[#A5B4FC]" : "text-white/45 hover:bg-white/5 hover:text-white/75"
                }`}
              >
                <Icon size={15} />
                {item.label}
              </button>
            );
          })}
        </nav>
      </aside>

      <div className="flex min-w-0 flex-1 flex-col">
        <header className="electron-drag flex h-14 shrink-0 items-center justify-between bg-white pl-6 shadow-[0_1px_0_rgba(229,231,235,0.85)]">
          <div className="text-sm font-semibold">{activeSidebar === "workspace" ? "工作区" : sidebarItems.find((item) => item.key === activeSidebar)?.label}</div>
          <div className="electron-no-drag flex h-full items-center gap-2">
            <Button onClick={refreshNews}>刷新日报</Button>
            <Button variant="primary" onClick={() => window.floatVocab?.showFloatingCard()}>
              继续复习
            </Button>
            <WindowControls />
          </div>
        </header>

        {activeSidebar === "workspace" ? (
          <div className="flex h-[45px] shrink-0 items-end gap-0 bg-white px-6 shadow-[0_1px_0_rgba(229,231,235,0.85)]">
            {contentTabs.map((tab) => (
              <button
                key={tab.key}
                onClick={() => setActiveTab(tab.key)}
                className={`h-full border-b-2 px-4 text-sm ${
                  activeTab === tab.key ? "border-primary font-medium text-primary" : "border-transparent text-muted-foreground"
                }`}
              >
                {tab.label}
              </button>
            ))}
          </div>
        ) : null}

        <main className="min-h-0 flex-1 overflow-auto p-6">
          {error ? <div className="mb-4 rounded-xl bg-red-50 p-4 text-sm text-red-600">{error}</div> : null}
          {renderContent()}
        </main>
      </div>
    </div>
  );
}

const root = createRoot(document.getElementById("root"));
root.render(window.location.hash === "#/floating-card" ? <FloatingCardRoute /> : <AppShell />);
