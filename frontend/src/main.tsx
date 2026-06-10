import React from "react";
import ReactDOM from "react-dom/client";
import {
  AlertTriangle,
  Check,
  CheckCircle2,
  ClipboardList,
  Code2,
  Download,
  FileText,
  Filter,
  History,
  Loader2,
  LogOut,
  Play,
  RefreshCw,
  Search,
  Settings,
  ShieldCheck,
  Sparkles,
  TestTube2,
  UserPlus,
  Users,
  X
} from "lucide-react";
import "./styles.css";

type Severity = "critical" | "high" | "medium" | "low" | "info";
type IssueStatus = "pending" | "accepted" | "ignored" | "fixed";
type TestStatus = "suggested" | "implemented" | "skipped";
type Role = "developer" | "reviewer" | "tester" | "admin";

type User = {
  id: number;
  username: string;
  role: Role;
  created_at: string;
};

type AuthOut = {
  access_token: string;
  token_type: "bearer";
  user: User;
};

type CodeInput = {
  file_name: string;
  code_hash: string;
  code_excerpt: string;
  diff_text: string;
  redaction_count: number;
};

type Issue = {
  id: number;
  type: string;
  severity: Severity;
  file: string;
  line_start: number;
  line_end: number;
  description: string;
  suggestion: string;
  confidence: number;
  status: IssueStatus;
  source: string;
  reviewer_note: string;
};

type TestCase = {
  id: number;
  name: string;
  category: string;
  input: string;
  expected: string;
  priority: "high" | "medium" | "low";
  status: TestStatus;
};

type TaskSummary = {
  id: number;
  user_id: number | null;
  project_name: string;
  language: string;
  status: string;
  summary: string;
  source_kind: string;
  created_at: string;
  completed_at: string | null;
};

type Task = TaskSummary & {
  input: CodeInput | null;
  issues: Issue[];
  test_cases: TestCase[];
};

type Health = {
  status: string;
  demo_mode: boolean;
  openai_configured: boolean;
  auth_required: boolean;
};

type PromptTemplate = {
  id: number;
  name: string;
  template: string;
  version: string;
  enabled: boolean;
};

type AuditLog = {
  id: number;
  user_id: number | null;
  task_id: number | null;
  action: string;
  target_id: string;
  detail: string;
  created_at: string;
};

const API_BASE = import.meta.env.VITE_API_BASE ?? "";
const TOKEN_KEY = "codemate_token";
const USER_KEY = "codemate_user";

const SAMPLE_CODE = `def create_order(amount, user_id):
    # TODO: connect real permission checks
    if amount < 0:
        return {"ok": False, "error": "invalid amount"}
    total = amount * 1.13
    query = "SELECT * FROM users WHERE id = " + str(user_id)
    return {"ok": True, "total": total, "query": query}
`;

const severityWeight: Record<Severity, number> = {
  critical: 5,
  high: 4,
  medium: 3,
  low: 2,
  info: 1
};

function App() {
  const [token, setToken] = React.useState(() => localStorage.getItem(TOKEN_KEY));
  const [user, setUser] = React.useState<User | null>(() => {
    const stored = localStorage.getItem(USER_KEY);
    return stored ? (JSON.parse(stored) as User) : null;
  });
  const [health, setHealth] = React.useState<Health | null>(null);
  const [tasks, setTasks] = React.useState<TaskSummary[]>([]);
  const [selectedTask, setSelectedTask] = React.useState<Task | null>(null);
  const [activeTab, setActiveTab] = React.useState<
    "issues" | "tests" | "code" | "admin"
  >("issues");
  const [projectName, setProjectName] = React.useState("CodeMate Demo");
  const [fileName, setFileName] = React.useState("order_service.py");
  const [language, setLanguage] = React.useState("python");
  const [sourceKind, setSourceKind] =
    React.useState<"snippet" | "diff" | "file">("snippet");
  const [code, setCode] = React.useState(SAMPLE_CODE);
  const [severityFilter, setSeverityFilter] = React.useState<Severity | "all">(
    "all"
  );
  const [query, setQuery] = React.useState("");
  const [isSubmitting, setSubmitting] = React.useState(false);
  const [isLoading, setLoading] = React.useState(true);
  const [error, setError] = React.useState<string | null>(null);

  const authedApi = React.useCallback(
    <T,>(path: string, init?: RequestInit) => api<T>(path, token, init),
    [token]
  );

  const refresh = React.useCallback(async () => {
    setError(null);
    const healthResult = await api<Health>("/api/health", null);
    setHealth(healthResult);
    if (!token) {
      setTasks([]);
      setSelectedTask(null);
      return;
    }
    const tasksResult = await authedApi<TaskSummary[]>("/api/review-tasks");
    setTasks(tasksResult);
    if (!selectedTask && tasksResult[0]) {
      const task = await authedApi<Task>(`/api/review-tasks/${tasksResult[0].id}`);
      setSelectedTask(sortTask(task));
    }
  }, [authedApi, selectedTask, token]);

  React.useEffect(() => {
    refresh()
      .catch((err: Error) => setError(err.message))
      .finally(() => setLoading(false));
  }, [refresh]);

  const handleLogin = (auth: AuthOut) => {
    localStorage.setItem(TOKEN_KEY, auth.access_token);
    localStorage.setItem(USER_KEY, JSON.stringify(auth.user));
    setToken(auth.access_token);
    setUser(auth.user);
    setSelectedTask(null);
    setActiveTab("issues");
  };

  const logout = () => {
    localStorage.removeItem(TOKEN_KEY);
    localStorage.removeItem(USER_KEY);
    setToken(null);
    setUser(null);
    setTasks([]);
    setSelectedTask(null);
  };

  const submitReview = async () => {
    setSubmitting(true);
    setError(null);
    try {
      const task = await authedApi<Task>("/api/review-tasks", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          project_name: projectName,
          file_name: fileName,
          language: language || null,
          source_kind: sourceKind,
          code
        })
      });
      setSelectedTask(sortTask(task));
      setActiveTab("issues");
      setTasks(await authedApi<TaskSummary[]>("/api/review-tasks"));
    } catch (err) {
      setError(err instanceof Error ? err.message : "Review failed");
    } finally {
      setSubmitting(false);
    }
  };

  const openTask = async (taskId: number) => {
    setError(null);
    const task = await authedApi<Task>(`/api/review-tasks/${taskId}`);
    setSelectedTask(sortTask(task));
    if (activeTab === "admin") {
      setActiveTab("issues");
    }
  };

  const updateIssue = async (
    issue: Issue,
    status: IssueStatus,
    reviewerNote = issue.reviewer_note
  ) => {
    const updated = await authedApi<Issue>(`/api/issues/${issue.id}`, {
      method: "PATCH",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ status, reviewer_note: reviewerNote })
    });
    setSelectedTask((task) =>
      task
        ? {
            ...task,
            issues: task.issues.map((item) =>
              item.id === updated.id ? updated : item
            )
          }
        : task
    );
  };

  const updateTest = async (testCase: TestCase, status: TestStatus) => {
    const updated = await authedApi<TestCase>(`/api/test-cases/${testCase.id}`, {
      method: "PATCH",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ status })
    });
    setSelectedTask((task) =>
      task
        ? {
            ...task,
            test_cases: task.test_cases.map((item) =>
              item.id === updated.id ? updated : item
            )
          }
        : task
    );
  };

  const filteredIssues = React.useMemo(() => {
    if (!selectedTask) return [];
    return selectedTask.issues.filter((issue) => {
      const matchesSeverity =
        severityFilter === "all" || issue.severity === severityFilter;
      const text = `${issue.type} ${issue.description} ${issue.suggestion}`.toLowerCase();
      return matchesSeverity && text.includes(query.toLowerCase());
    });
  }, [selectedTask, severityFilter, query]);

  const stats = selectedTask ? summarize(selectedTask) : null;

  if (!token || !user) {
    return (
      <AuthScreen
        health={health}
        error={error}
        onLogin={handleLogin}
        setError={setError}
      />
    );
  }

  return (
    <main className="shell">
      <aside className="sidebar">
        <div className="brand">
          <div className="brandMark">
            <Code2 size={22} aria-hidden />
          </div>
          <div>
            <strong>CodeMate</strong>
            <span>AI Code Review</span>
          </div>
        </div>

        <section className="userBar">
          <div>
            <strong>{user.username}</strong>
            <span>{user.role}</span>
          </div>
          <button
            className="iconButton"
            onClick={logout}
            type="button"
            aria-label="退出登录"
            title="退出登录"
          >
            <LogOut size={16} aria-hidden />
          </button>
        </section>

        <section className="panel compose">
          <div className="panelTitle">
            <Sparkles size={18} aria-hidden />
            <h2>新建审查</h2>
          </div>
          <label>
            项目
            <input
              value={projectName}
              onChange={(event) => setProjectName(event.target.value)}
              placeholder="Project name"
            />
          </label>
          <div className="fieldGrid">
            <label>
              文件
              <input
                value={fileName}
                onChange={(event) => setFileName(event.target.value)}
                placeholder="src/app.py"
              />
            </label>
            <label>
              语言
              <select
                value={language}
                onChange={(event) => setLanguage(event.target.value)}
              >
                <option value="">自动识别</option>
                <option value="python">Python</option>
                <option value="javascript">JavaScript</option>
                <option value="typescript">TypeScript</option>
                <option value="java">Java</option>
                <option value="go">Go</option>
                <option value="unknown">Other</option>
              </select>
            </label>
          </div>
          <div className="segmented" aria-label="Source kind">
            {(["snippet", "diff", "file"] as const).map((kind) => (
              <button
                key={kind}
                className={sourceKind === kind ? "active" : ""}
                onClick={() => setSourceKind(kind)}
                type="button"
              >
                {kind}
              </button>
            ))}
          </div>
          <label>
            代码
            <textarea
              value={code}
              onChange={(event) => setCode(event.target.value)}
              spellCheck={false}
            />
          </label>
          <button
            className="primaryAction"
            onClick={submitReview}
            disabled={isSubmitting || code.trim().length === 0}
            type="button"
          >
            {isSubmitting ? (
              <Loader2 className="spin" size={18} aria-hidden />
            ) : (
              <Play size={18} aria-hidden />
            )}
            开始审查
          </button>
          {health && (
            <div className="runtime">
              <ShieldCheck size={16} aria-hidden />
              <span>{health.demo_mode ? "Demo mode" : "OpenAI mode"}</span>
            </div>
          )}
        </section>

        <section className="history">
          <div className="panelTitle historyTitle">
            <History size={18} aria-hidden />
            <h2>历史任务</h2>
            <button
              className="iconButton"
              onClick={() => refresh().catch((err: Error) => setError(err.message))}
              type="button"
              aria-label="刷新任务"
              title="刷新任务"
            >
              <RefreshCw size={16} aria-hidden />
            </button>
          </div>
          <div className="taskList">
            {tasks.map((task) => (
              <button
                key={task.id}
                className={`taskItem ${
                  selectedTask?.id === task.id ? "selected" : ""
                }`}
                onClick={() => openTask(task.id)}
                type="button"
              >
                <span>{task.project_name}</span>
                <small>
                  #{task.id} · {task.language} · {formatTime(task.created_at)}
                </small>
              </button>
            ))}
            {!tasks.length && !isLoading && (
              <div className="empty">暂无历史任务</div>
            )}
          </div>
        </section>
      </aside>

      <section className="workspace">
        {error && (
          <div className="errorBanner">
            <AlertTriangle size={18} aria-hidden />
            <span>{error}</span>
            <button
              className="iconButton ghost"
              onClick={() => setError(null)}
              type="button"
              aria-label="关闭错误"
              title="关闭错误"
            >
              <X size={16} aria-hidden />
            </button>
          </div>
        )}

        <nav className="tabs appTabs" aria-label="Task views">
          <button
            className={activeTab === "issues" ? "active" : ""}
            onClick={() => setActiveTab("issues")}
            type="button"
          >
            <ClipboardList size={16} aria-hidden />
            问题
          </button>
          <button
            className={activeTab === "tests" ? "active" : ""}
            onClick={() => setActiveTab("tests")}
            type="button"
          >
            <TestTube2 size={16} aria-hidden />
            测试
          </button>
          <button
            className={activeTab === "code" ? "active" : ""}
            onClick={() => setActiveTab("code")}
            type="button"
          >
            <FileText size={16} aria-hidden />
            输入
          </button>
          {user.role === "admin" && (
            <button
              className={activeTab === "admin" ? "active" : ""}
              onClick={() => setActiveTab("admin")}
              type="button"
            >
              <Settings size={16} aria-hidden />
              管理
            </button>
          )}
        </nav>

        {activeTab === "admin" && user.role === "admin" ? (
          <AdminPanel token={token} />
        ) : selectedTask ? (
          <>
            <header className="taskHeader">
              <div>
                <p className="eyebrow">Task #{selectedTask.id}</p>
                <h1>{selectedTask.project_name}</h1>
                <p>{selectedTask.summary}</p>
              </div>
              <div className="headerActions">
                <a
                  className="secondaryAction"
                  href={`${API_BASE}/api/review-tasks/${selectedTask.id}/report.md`}
                  onClick={(event) => {
                    event.preventDefault();
                    downloadReport(selectedTask.id, "md", token, setError);
                  }}
                >
                  <Download size={17} aria-hidden />
                  Markdown
                </a>
                <a
                  className="secondaryAction"
                  href={`${API_BASE}/api/review-tasks/${selectedTask.id}/report.pdf`}
                  onClick={(event) => {
                    event.preventDefault();
                    downloadReport(selectedTask.id, "pdf", token, setError);
                  }}
                >
                  <Download size={17} aria-hidden />
                  PDF
                </a>
                <a
                  className="secondaryAction"
                  href={`${API_BASE}/api/review-tasks/${selectedTask.id}/report.docx`}
                  onClick={(event) => {
                    event.preventDefault();
                    downloadReport(selectedTask.id, "docx", token, setError);
                  }}
                >
                  <Download size={17} aria-hidden />
                  Word
                </a>
              </div>
            </header>

            {stats && (
              <section className="metrics">
                <Metric
                  icon={<AlertTriangle size={18} aria-hidden />}
                  label="高危"
                  value={stats.risky}
                />
                <Metric
                  icon={<ClipboardList size={18} aria-hidden />}
                  label="问题"
                  value={selectedTask.issues.length}
                />
                <Metric
                  icon={<TestTube2 size={18} aria-hidden />}
                  label="测试"
                  value={selectedTask.test_cases.length}
                />
                <Metric
                  icon={<ShieldCheck size={18} aria-hidden />}
                  label="脱敏"
                  value={selectedTask.input?.redaction_count ?? 0}
                />
              </section>
            )}

            {activeTab === "issues" && (
              <section className="contentRegion">
                <div className="toolbar">
                  <div className="searchBox">
                    <Search size={16} aria-hidden />
                    <input
                      value={query}
                      onChange={(event) => setQuery(event.target.value)}
                      placeholder="搜索问题或建议"
                    />
                  </div>
                  <div className="selectBox">
                    <Filter size={16} aria-hidden />
                    <select
                      value={severityFilter}
                      onChange={(event) =>
                        setSeverityFilter(event.target.value as Severity | "all")
                      }
                    >
                      <option value="all">全部等级</option>
                      <option value="critical">Critical</option>
                      <option value="high">High</option>
                      <option value="medium">Medium</option>
                      <option value="low">Low</option>
                      <option value="info">Info</option>
                    </select>
                  </div>
                </div>
                <div className="issueList">
                  {filteredIssues.map((issue) => (
                    <IssueCard
                      key={issue.id}
                      issue={issue}
                      onStatus={(status) => updateIssue(issue, status)}
                    />
                  ))}
                  {!filteredIssues.length && <div className="empty">没有匹配的问题</div>}
                </div>
              </section>
            )}

            {activeTab === "tests" && (
              <section className="testGrid">
                {selectedTask.test_cases.map((testCase) => (
                  <article className="testCard" key={testCase.id}>
                    <div className="testTop">
                      <span className={`priority ${testCase.priority}`}>
                        {testCase.priority}
                      </span>
                      <select
                        value={testCase.status}
                        onChange={(event) =>
                          updateTest(testCase, event.target.value as TestStatus)
                        }
                      >
                        <option value="suggested">suggested</option>
                        <option value="implemented">implemented</option>
                        <option value="skipped">skipped</option>
                      </select>
                    </div>
                    <h3>{testCase.name}</h3>
                    <p className="category">{testCase.category}</p>
                    <dl>
                      <dt>输入</dt>
                      <dd>{testCase.input}</dd>
                      <dt>预期</dt>
                      <dd>{testCase.expected}</dd>
                    </dl>
                  </article>
                ))}
              </section>
            )}

            {activeTab === "code" && (
              <section className="codePanel">
                <div className="codeMeta">
                  <span>{selectedTask.input?.file_name}</span>
                  <span>{selectedTask.language}</span>
                  <span>{selectedTask.source_kind}</span>
                </div>
                <pre>{selectedTask.input?.code_excerpt}</pre>
              </section>
            )}
          </>
        ) : (
          <section className="blankSlate">
            <Code2 size={42} aria-hidden />
            <h1>CodeMate</h1>
            <p>提交左侧代码片段后，审查结果会显示在这里。</p>
          </section>
        )}
      </section>
    </main>
  );
}

function AuthScreen({
  health,
  error,
  onLogin,
  setError
}: {
  health: Health | null;
  error: string | null;
  onLogin: (auth: AuthOut) => void;
  setError: (error: string | null) => void;
}) {
  const [mode, setMode] = React.useState<"login" | "register">("login");
  const [username, setUsername] = React.useState("admin");
  const [password, setPassword] = React.useState("admin123");
  const [busy, setBusy] = React.useState(false);

  const submit = async () => {
    setBusy(true);
    setError(null);
    try {
      const auth = await api<AuthOut>(
        mode === "login" ? "/api/auth/login" : "/api/auth/register",
        null,
        {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify({ username, password, role: "developer" })
        }
      );
      onLogin(auth);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Authentication failed");
    } finally {
      setBusy(false);
    }
  };

  return (
    <main className="authShell">
      <section className="authPanel">
        <div className="brand">
          <div className="brandMark">
            <Code2 size={22} aria-hidden />
          </div>
          <div>
            <strong>CodeMate</strong>
            <span>AI assisted review platform</span>
          </div>
        </div>
        <div className="authIntro">
          <h1>{mode === "login" ? "登录工作台" : "注册开发者账号"}</h1>
          <p>默认演示账号：admin / admin123。管理员可以维护提示词模板、用户与审计日志。</p>
        </div>
        {error && <div className="errorBanner">{error}</div>}
        <label>
          用户名
          <input value={username} onChange={(event) => setUsername(event.target.value)} />
        </label>
        <label>
          密码
          <input
            value={password}
            type="password"
            onChange={(event) => setPassword(event.target.value)}
          />
        </label>
        <button
          className="primaryAction"
          onClick={submit}
          disabled={busy || !username || !password}
          type="button"
        >
          {busy ? <Loader2 className="spin" size={18} aria-hidden /> : <ShieldCheck size={18} aria-hidden />}
          {mode === "login" ? "登录" : "注册"}
        </button>
        <button
          className="secondaryAction fullWidth"
          onClick={() => setMode(mode === "login" ? "register" : "login")}
          type="button"
        >
          <UserPlus size={17} aria-hidden />
          {mode === "login" ? "创建开发者账号" : "返回登录"}
        </button>
        {health && (
          <div className="runtime">
            <ShieldCheck size={16} aria-hidden />
            <span>{health.demo_mode ? "Demo mode" : "OpenAI mode"}</span>
          </div>
        )}
      </section>
    </main>
  );
}

function AdminPanel({ token }: { token: string }) {
  const [templates, setTemplates] = React.useState<PromptTemplate[]>([]);
  const [users, setUsers] = React.useState<User[]>([]);
  const [logs, setLogs] = React.useState<AuditLog[]>([]);
  const [templateName, setTemplateName] = React.useState("team-review-standard");
  const [templateBody, setTemplateBody] = React.useState(
    "重点检查权限、输入校验、边界条件、异常处理、安全风险和测试覆盖。"
  );
  const [newUser, setNewUser] = React.useState("developer2");
  const [newPassword, setNewPassword] = React.useState("developer123");
  const [newRole, setNewRole] = React.useState<Role>("developer");
  const [error, setError] = React.useState<string | null>(null);

  const adminApi = React.useCallback(
    <T,>(path: string, init?: RequestInit) => api<T>(path, token, init),
    [token]
  );

  const refresh = React.useCallback(async () => {
    const [templateData, userData, logData] = await Promise.all([
      adminApi<PromptTemplate[]>("/api/admin/prompt-templates"),
      adminApi<User[]>("/api/admin/users"),
      adminApi<AuditLog[]>("/api/admin/audit-logs")
    ]);
    setTemplates(templateData);
    setUsers(userData);
    setLogs(logData);
  }, [adminApi]);

  React.useEffect(() => {
    refresh().catch((err: Error) => setError(err.message));
  }, [refresh]);

  const createTemplate = async () => {
    setError(null);
    try {
      await adminApi<PromptTemplate>("/api/admin/prompt-templates", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          name: templateName,
          template: templateBody,
          version: "1.0.0",
          enabled: true
        })
      });
      await refresh();
    } catch (err) {
      setError(err instanceof Error ? err.message : "Create template failed");
    }
  };

  const toggleTemplate = async (template: PromptTemplate) => {
    await adminApi<PromptTemplate>(`/api/admin/prompt-templates/${template.id}`, {
      method: "PATCH",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ enabled: !template.enabled })
    });
    await refresh();
  };

  const createUser = async () => {
    setError(null);
    try {
      await adminApi<User>("/api/admin/users", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          username: newUser,
          password: newPassword,
          role: newRole
        })
      });
      await refresh();
    } catch (err) {
      setError(err instanceof Error ? err.message : "Create user failed");
    }
  };

  return (
    <section className="adminGrid">
      {error && <div className="errorBanner">{error}</div>}
      <article className="adminPanel">
        <div className="panelTitle">
          <Settings size={18} aria-hidden />
          <h2>提示词模板</h2>
        </div>
        <label>
          模板名称
          <input value={templateName} onChange={(event) => setTemplateName(event.target.value)} />
        </label>
        <label>
          审查标准
          <textarea
            value={templateBody}
            onChange={(event) => setTemplateBody(event.target.value)}
          />
        </label>
        <button className="primaryAction" onClick={createTemplate} type="button">
          新增模板
        </button>
        <div className="tableList">
          {templates.map((template) => (
            <div className="tableRow" key={template.id}>
              <div>
                <strong>{template.name}</strong>
                <span>v{template.version}</span>
              </div>
              <button
                className={template.enabled ? "status active" : "status"}
                onClick={() => toggleTemplate(template)}
                type="button"
                title={template.enabled ? "已启用" : "已停用"}
                aria-label={template.enabled ? "已启用" : "已停用"}
              >
                <Check size={16} aria-hidden />
              </button>
            </div>
          ))}
        </div>
      </article>

      <article className="adminPanel">
        <div className="panelTitle">
          <Users size={18} aria-hidden />
          <h2>用户与角色</h2>
        </div>
        <div className="fieldGrid">
          <label>
            用户名
            <input value={newUser} onChange={(event) => setNewUser(event.target.value)} />
          </label>
          <label>
            角色
            <select value={newRole} onChange={(event) => setNewRole(event.target.value as Role)}>
              <option value="developer">developer</option>
              <option value="reviewer">reviewer</option>
              <option value="tester">tester</option>
              <option value="admin">admin</option>
            </select>
          </label>
        </div>
        <label>
          密码
          <input
            value={newPassword}
            type="password"
            onChange={(event) => setNewPassword(event.target.value)}
          />
        </label>
        <button className="primaryAction" onClick={createUser} type="button">
          新增用户
        </button>
        <div className="tableList">
          {users.map((item) => (
            <div className="tableRow" key={item.id}>
              <div>
                <strong>{item.username}</strong>
                <span>{item.role}</span>
              </div>
              <small>{formatTime(item.created_at)}</small>
            </div>
          ))}
        </div>
      </article>

      <article className="adminPanel wide">
        <div className="panelTitle">
          <ClipboardList size={18} aria-hidden />
          <h2>审计日志</h2>
        </div>
        <div className="tableList">
          {logs.map((log) => (
            <div className="tableRow logRow" key={log.id}>
              <div>
                <strong>{log.action}</strong>
                <span>{log.detail}</span>
              </div>
              <small>{formatTime(log.created_at)}</small>
            </div>
          ))}
        </div>
      </article>
    </section>
  );
}

function Metric({
  icon,
  label,
  value
}: {
  icon: React.ReactNode;
  label: string;
  value: number;
}) {
  return (
    <div className="metric">
      {icon}
      <span>{label}</span>
      <strong>{value}</strong>
    </div>
  );
}

function IssueCard({
  issue,
  onStatus
}: {
  issue: Issue;
  onStatus: (status: IssueStatus) => void;
}) {
  return (
    <article className="issueCard">
      <div className="issueMain">
        <div className="issueTitle">
          <span className={`severity ${issue.severity}`}>{issue.severity}</span>
          <h3>{issue.type}</h3>
        </div>
        <p>{issue.description}</p>
        <p className="suggestion">{issue.suggestion}</p>
        <div className="issueMeta">
          <span>
            {issue.file}:{issue.line_start}-{issue.line_end}
          </span>
          <span>{Math.round(issue.confidence * 100)}%</span>
          <span>{issue.source}</span>
        </div>
      </div>
      <div className="statusRail">
        <button
          className={issue.status === "accepted" ? "status active" : "status"}
          onClick={() => onStatus("accepted")}
          type="button"
          title="采纳"
          aria-label="采纳"
        >
          <Check size={16} aria-hidden />
        </button>
        <button
          className={issue.status === "fixed" ? "status active" : "status"}
          onClick={() => onStatus("fixed")}
          type="button"
          title="已修复"
          aria-label="已修复"
        >
          <CheckCircle2 size={16} aria-hidden />
        </button>
        <button
          className={issue.status === "ignored" ? "status active" : "status"}
          onClick={() => onStatus("ignored")}
          type="button"
          title="忽略"
          aria-label="忽略"
        >
          <X size={16} aria-hidden />
        </button>
      </div>
    </article>
  );
}

async function api<T>(
  path: string,
  token: string | null,
  init?: RequestInit
): Promise<T> {
  const headers = new Headers(init?.headers);
  if (token) {
    headers.set("Authorization", `Bearer ${token}`);
  }
  const response = await fetch(`${API_BASE}${path}`, { ...init, headers });
  if (!response.ok) {
    const detail = await response.text();
    throw new Error(detail || `Request failed with ${response.status}`);
  }
  return response.json() as Promise<T>;
}

async function downloadReport(
  taskId: number,
  format: "md" | "pdf" | "docx",
  token: string,
  setError: (error: string) => void
) {
  try {
    const response = await fetch(`${API_BASE}/api/review-tasks/${taskId}/report.${format}`, {
      headers: { Authorization: `Bearer ${token}` }
    });
    if (!response.ok) {
      throw new Error(await response.text());
    }
    const blob = await response.blob();
    const href = URL.createObjectURL(blob);
    const link = document.createElement("a");
    link.href = href;
    link.download = `codemate-task-${taskId}.${format}`;
    link.click();
    URL.revokeObjectURL(href);
  } catch (err) {
    setError(err instanceof Error ? err.message : "Download failed");
  }
}

function summarize(task: Task) {
  return {
    risky: task.issues.filter((issue) =>
      ["critical", "high"].includes(issue.severity)
    ).length
  };
}

function sortTask(task: Task): Task {
  return {
    ...task,
    issues: [...task.issues].sort(
      (a, b) => severityWeight[b.severity] - severityWeight[a.severity]
    )
  };
}

function formatTime(value: string) {
  return new Intl.DateTimeFormat("zh-CN", {
    month: "2-digit",
    day: "2-digit",
    hour: "2-digit",
    minute: "2-digit"
  }).format(new Date(value));
}

ReactDOM.createRoot(document.getElementById("root")!).render(
  <React.StrictMode>
    <App />
  </React.StrictMode>
);
