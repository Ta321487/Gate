    const projects = [
      { id: "gf-20260717-001", name: "基于 Spring Boot 的图书借阅管理系统", arch: "ARCH-FLOW · DOM-LIBRARY", status: "needs_confirm", statusLabel: "待确认匹配", pill: "pill-amber", runtime: "—", running: false, updated: "刚刚" },
      { id: "gf-20260716-014", name: "宿舍报修管理系统", arch: "ARCH-FLOW · DOM-DORM", status: "generated", statusLabel: "已生成 · 可交付", pill: "pill-green", runtime: "—", running: false, updated: "昨天 21:10" },
      { id: "gf-20260716-011", name: "校园二手交易平台", arch: "ARCH-TRADE · DOM-SHOP", status: "failed", statusLabel: "质量检查未过 · 暂不可交付", pill: "pill-red", runtime: "—", running: false, updated: "昨天 18:40" },
      { id: "gf-20260715-008", name: "停车场预约系统", arch: "ARCH-RESERVE · DOM-PARKING", status: "running", statusLabel: "已生成 · 可交付", pill: "pill-green", runtime: "9101 / 9201", running: true, updated: "2 小时前" },
      { id: "gf-20260714-006", name: "医院挂号管理系统", arch: "ARCH-RESERVE · DOM-HOSPITAL", status: "generating", statusLabel: "生成中", pill: "pill-teal", runtime: "—", running: false, updated: "12 分钟前" },
      { id: "gf-20260712-003", name: "影视点播管理系统", arch: "ARCH-CONTENT · DOM-MEDIA", status: "generated", statusLabel: "已生成 · 可交付", pill: "pill-green", runtime: "—", running: false, updated: "3 天前" },
      { id: "gf-20260710-002", name: "进销存管理系统", arch: "ARCH-STOCK · DOM-GENERIC", status: "generated", statusLabel: "已生成 · 可交付", pill: "pill-green", runtime: "—", running: false, updated: "5 天前" },
      { id: "gf-20260708-001", name: "社团活动报名系统", arch: "ARCH-FLOW · DOM-ACTIVITY", status: "archived", statusLabel: "已归档", pill: "pill-neutral", runtime: "—", running: false, updated: "上周" },
    ];

    const logSamples = {
      job: `[11:02:01] INFO  job#1042 parse_report done (1.2s)
[11:02:03] INFO  match ARCH-FLOW / DOM-LIBRARY confidence=0.86
[11:02:04] INFO  confirm gate passed by operator
[11:02:10] INFO  copy_skeleton ARCH-FLOW → workspace/gf-20260717-001
[11:02:18] INFO  bake_backend emit entities: Book, Borrow, Category, Notice
[11:03:40] INFO  llm_fill slots=4 tokens=12480
[11:04:12] INFO  bake_frontend pages=12
[11:04:55] INFO  build backend SUCCESS
[11:05:40] WARN  build frontend retry 1/5 — missing view import
[11:06:12] INFO  auto_fix applied patch to router/index.js
[11:06:48] INFO  build frontend SUCCESS
[11:07:01] INFO  seed_db ok · pack zip ok`,
      backend: `[boot] Starting ThesisApplication v1.0.0
[boot] Tomcat started on port 9103
[boot] HikariPool-1 - Start completed
[http] GET /api/auth/captcha 200 18ms
[http] POST /api/auth/login 200 42ms
[http] GET /api/admin/books?page=1&size=10 200 25ms`,
      frontend: `VITE v5.4.2  ready in 420 ms
➜  Local:   http://127.0.0.1:9203/
➜  Network: use --host to expose
[proxy] /api -> http://127.0.0.1:9103`,
      deepseek: `[ds] stage=parse_spec model=deepseek-v4-flash thinking=on
[ds] prompt_tokens=2100 completion=1110
[ds] stage=island_fill files=4 ok
[ds] stage=auto_fix round=1 error=MODULE_NOT_FOUND → patched router`,
    };

    const liveSteps = [
      { t: "done", title: "解析开题 · 合并 Spec", meta: "匹配与 Spec" },
      { t: "done", title: "复制骨架 · 领域 SQL", meta: "确定性生成" },
      { t: "done", title: "业务配置填充", meta: "大模型补全" },
      { t: "run", title: "构建验证", meta: "编译检查" },
      { t: "wait", title: "门禁：登录 + 主流程", meta: "关键路径" },
      { t: "wait", title: "开题对照 · 打包 ZIP", meta: "检查通过后打包" },
    ];

    const JOB_STEP_LABELS = {
      queued: "排队",
      parse_merge: "解析开题 · 合并 Spec",
      copy_bake: "复制骨架 · 领域 SQL",
      island_fill: "业务配置填充",
      build_verify: "构建验证",
      gate_e2e: "门禁：登录 + 主流程",
      pack: "开题对照 · 打包 ZIP",
    };

    let uploadJobSeq = 1;
    const uploadJobs = [];
    let planDraft = null;

    let beOn = false;
    let feOn = false;
    let currentLogSide = "job";
    let genTimer = null;
    let matchConfirmed = false;
    let matchUnlocked = false;
    /** 交付质量检查：未过则 zip 锁定 */
    let gatesPass = true;

    const RECOMMENDED = {
      arch: "ARCH-FLOW · 审核流",
      dom: "DOM-LIBRARY · 图书",
      conf: 0.86,
    };

    function setDisabled(id, off) {
      const el = document.getElementById(id);
      if (!el) return;
      el.classList.toggle("is-disabled", !!off);
      el.setAttribute("aria-disabled", off ? "true" : "false");
    }

    function isDisabled(el) {
      return !!(el && (el.classList.contains("is-disabled") || el.getAttribute("aria-disabled") === "true"));
    }

    function toast(msg) {
      const el = document.getElementById("toast");
      el.textContent = msg;
      el.classList.add("show");
      clearTimeout(toast._t);
      toast._t = setTimeout(() => el.classList.remove("show"), 2200);
    }

    function openModal(title, body) {
      document.getElementById("modal-title").textContent = title;
      document.getElementById("modal-body").textContent = body;
      document.getElementById("modal-mask").classList.add("show");
    }

    function closeModal() {
      document.getElementById("modal-mask").classList.remove("show");
    }

    function setCrumb(parts) {
      document.getElementById("crumb").innerHTML = parts.map((p, i) =>
        i === parts.length - 1 ? `<strong>${p}</strong>` : p
      ).join(" / ");
    }

    function showView(name) {
      document.querySelectorAll(".view").forEach((v) => v.classList.remove("active"));
      document.querySelectorAll(".nav-item").forEach((n) => n.classList.remove("active"));
      const view = document.getElementById("view-" + name);
      if (view) view.classList.add("active");
      const navKey = name === "project" ? "home" : name;
      const nav = document.querySelector(`.nav-item[data-nav="${navKey}"]`);
      if (nav) nav.classList.add("active");
      const crumbs = {
        home: ["毕设港", "项目"],
        jobs: ["毕设港", "任务队列"],
        help: ["毕设港", "帮助文档"],
        llm: ["毕设港", "大模型"],
        unsplash: ["毕设港", "Unsplash"],
        system: ["毕设港", "运行环境"],
        project: ["毕设港", "项目", "详情"],
      };
      setCrumb(crumbs[name] || ["毕设港"]);
      closeNav();
    }

    function setNavOpen(open) {
      const shell = document.getElementById("app-shell");
      const toggle = document.getElementById("nav-toggle");
      const backdrop = document.getElementById("nav-backdrop");
      if (!shell) return;
      shell.classList.toggle("nav-open", open);
      document.body.classList.toggle("nav-lock", open);
      if (toggle) {
        toggle.setAttribute("aria-expanded", open ? "true" : "false");
        toggle.setAttribute("aria-label", open ? "关闭菜单" : "打开菜单");
      }
      if (backdrop) backdrop.hidden = !open;
    }

    function closeNav() {
      setNavOpen(false);
    }

    function toggleNav() {
      const shell = document.getElementById("app-shell");
      setNavOpen(!(shell && shell.classList.contains("nav-open")));
    }

    function renderList(filter = "all", q = "") {
      const tb = document.getElementById("project-tbody");
      const map = {
        all: () => true,
        active: (p) => p.running || p.status === "running",
        generating: (p) => p.status === "generating",
        done: (p) => ["generated", "running"].includes(p.status),
        fail: (p) => p.status === "failed",
      };
      const rows = projects
        .filter(map[filter] || map.all)
        .filter((p) => !q || p.name.includes(q) || p.id.includes(q));
      if (!rows.length) {
        tb.innerHTML = `<tr><td colspan="5"><div class="empty-hint"><div class="empty-title">暂无项目</div><div class="empty-desc">上传材料后确认分堆即可创建；同课题会合并，不同课题会拆开</div></div></td></tr>`;
      } else {
        tb.innerHTML = rows.map((p) => `
          <tr class="clickable" data-action="open-project" data-id="${p.id}">
            <td>
              <div style="font-weight:600">${p.name}</div>
              <div class="small muted mono">${p.id}</div>
            </td>
            <td class="small">${p.arch}</td>
            <td><span class="pill ${p.pill}">${p.statusLabel}</span></td>
            <td class="small">${p.running
              ? `<span class="pill pill-green">运行中</span><div class="mono muted" style="margin-top:4px">${p.runtime}</div>`
              : `<span class="muted">—</span>`}</td>
            <td class="small muted">${p.updated}</td>
          </tr>
        `).join("");
      }
      document.getElementById("list-footer").textContent = `共 ${rows.length} 条 · 点击行进入详情`;
    }

    function setProjectTab(tab) {
      document.querySelectorAll("#proj-tabs .tab").forEach((t) => {
        t.classList.toggle("active", t.dataset.tab === tab);
      });
      document.querySelectorAll("#view-project .tab-panel").forEach((p) => p.classList.remove("active"));
      const panel = document.getElementById("tab-" + tab);
      if (panel) panel.classList.add("active");
    }

    function setArtifactView(view) {
      const v = view || "db";
      document.querySelectorAll("#artifact-subtabs button").forEach((b) => {
        b.classList.toggle("active", b.dataset.aview === v);
      });
      ["db", "thesis", "api", "gates"].forEach((id) => {
        const el = document.getElementById("aview-" + id);
        if (el) el.style.display = id === v ? "flex" : "none";
      });
    }

    function setUsageTab(tab) {
      const t = tab === "support" ? "support" : "project";
      document.querySelectorAll("#usage-detail-tabs button").forEach((b) => {
        b.classList.toggle("active", b.dataset.usageTab === t);
      });
      const project = document.getElementById("usage-pane-project");
      const support = document.getElementById("usage-pane-support");
      if (project) project.hidden = t !== "project";
      if (support) support.hidden = t !== "support";
    }

    function applyUsagePresence(mode) {
      const m = mode || "alive";
      const rows = document.querySelectorAll("#usage-tbody tr[data-presence]");
      let visible = 0;
      rows.forEach((tr) => {
        const p = tr.dataset.presence || "alive";
        const show = m === "all" || p === m;
        tr.hidden = !show;
        if (show) visible += 1;
      });
      const hint = document.getElementById("usage-count-hint");
      if (hint) hint.textContent = `共 ${visible} 个项目`;
      const labels = { alive: "在库", deleted: "已删除", all: "全部" };
      toast("用量筛选 · " + (labels[m] || m));
    }

    function renderGates(pass) {
      gatesPass = !!pass;
      const results = {
        p0a: true,
        p0b: true,
        p1: true,
        p2: pass,
        p3a: pass,
        p3b: true,
        p3t: true,
        p3d: true,
        p3c: true,
        accept: pass,
      };
      document.querySelectorAll("#gate-tbody tr[data-gate]").forEach((tr) => {
        const ok = results[tr.dataset.gate];
        const cell = tr.querySelector(".gate-res");
        cell.innerHTML = ok
          ? '<span class="pill pill-green">通过</span>'
          : '<span class="pill pill-red">未通过</span>';
      });
      const overall = document.getElementById("gate-overall-pill");
      const zipHint = document.getElementById("zip-hint");
      const zipBtn = document.getElementById("btn-zip-dl");
      if (pass) {
        overall.className = "pill pill-green";
        overall.textContent = "可交付";
        setDisabled("btn-download", false);
        if (zipHint) zipHint.textContent = "质量检查已过";
        if (zipBtn) {
          zipBtn.textContent = "下载";
          zipBtn.classList.remove("is-disabled");
        }
        document.getElementById("cl-flow").className = "pill pill-green";
        document.getElementById("cl-flow").textContent = "已实现";
        document.getElementById("cl-return").className = "pill pill-green";
        document.getElementById("cl-return").textContent = "已实现";
      } else {
        overall.className = "pill pill-red";
        overall.textContent = "暂不可交付";
        setDisabled("btn-download", true);
        if (zipHint) zipHint.textContent = "质量检查未过 · 锁定";
        if (zipBtn) {
          zipBtn.textContent = "锁定";
          zipBtn.classList.add("is-disabled");
        }
        document.getElementById("cl-flow").className = "pill pill-red";
        document.getElementById("cl-flow").textContent = "未覆盖";
        document.getElementById("cl-return").className = "pill pill-red";
        document.getElementById("cl-return").textContent = "未覆盖";
      }
    }

    function applyGenState(state) {
      const idle = document.getElementById("gen-idle");
      const run = document.getElementById("gen-running");
      const ok = document.getElementById("gen-success");
      const fail = document.getElementById("gen-failed");
      const reg = document.getElementById("gen-regression");
      [idle, run, ok, fail, reg].forEach((el) => { if (el) el.style.display = "none"; });
      if (state === "generating") {
        run.style.display = "block";
        document.getElementById("live-steps").innerHTML = liveSteps.map((s) => `
          <li class="${s.t === "done" ? "done" : s.t === "run" ? "run" : ""}">
            <span class="step-ico">${s.t === "done" ? "✓" : s.t === "run" ? "…" : "·"}</span>
            <div><div>${s.title}</div><div class="meta">${s.meta}</div></div>
          </li>
        `).join("");
      } else if (state === "running") {
        ok.style.display = "block";
        document.getElementById("gen-success-title").textContent = "已生成 · 预览运行中";
        document.getElementById("gen-success-desc").textContent = "前后端已启动，可打开预览或下载交付包。";
        renderGates(true);
      } else if (state === "generated") {
        ok.style.display = "block";
        document.getElementById("gen-success-title").textContent = "生成完成 · 质量检查已通过 · 可交付";
        document.getElementById("gen-success-desc").textContent = "交付包已解锁。建议到「运行」预览后再交付。";
        renderGates(true);
      } else if (state === "regression") {
        reg.style.display = "block";
        renderGates(false);
      } else if (state === "failed") {
        fail.style.display = "block";
        document.getElementById("fail-title").textContent = "质量检查未通过 · 暂不可交付";
        document.getElementById("fail-desc").textContent =
          "主流程或功能清单未通过时，暂不可下载交付包。";
        renderGates(false);
      } else {
        idle.style.display = "block";
        renderGates(false);
        setDisabled("btn-download", true);
      }
    }

    function setStatus(label, pill) {
      const el = document.getElementById("proj-status-pill");
      el.className = "pill " + pill;
      el.textContent = label;
    }

    function syncRuntimeUI() {
      const bePill = document.getElementById("be-pill");
      const fePill = document.getElementById("fe-pill");
      bePill.className = "pill " + (beOn ? "pill-green" : "pill-neutral");
      bePill.textContent = beOn ? "健康" : "已停止";
      fePill.className = "pill " + (feOn ? "pill-green" : "pill-neutral");
      fePill.textContent = feOn ? "健康" : "已停止";
      document.getElementById("toggle-be").textContent = beOn ? "停止" : "启动";
      document.getElementById("toggle-fe").textContent = feOn ? "停止" : "启动";
      setDisabled("open-preview", !(beOn && feOn));
      setDisabled("copy-preview", !(beOn && feOn));
      document.getElementById("be-log").innerHTML = beOn
        ? `<span class="ok">Tomcat started on 9103</span>\nHikariPool ready\nGET /api/auth/captcha 200`
        : "—";
      document.getElementById("fe-log").innerHTML = feOn
        ? `<span class="ok">VITE ready</span>\nLocal: http://127.0.0.1:9203/\nproxy /api -> 9103`
        : "—";
    }

    function setRuntime(on) {
      beOn = on;
      feOn = on;
      syncRuntimeUI();
    }

    function showLog(side) {
      currentLogSide = side || currentLogSide;
      let text = logSamples[currentLogSide] || logSamples.job;
      const q = (document.getElementById("log-filter").value || "").trim().toLowerCase();
      let lines = text.split("\n");
      if (q) lines = lines.filter((l) => l.toLowerCase().includes(q));
      document.getElementById("log-viewer").textContent = lines.join("\n") || (q ? "（无匹配）" : "（无日志）");
      document.querySelectorAll("#log-side button").forEach((b) => {
        b.classList.toggle("active", b.dataset.side === currentLogSide);
      });
      const viewer = document.getElementById("log-viewer");
      viewer.scrollTop = viewer.scrollHeight;
    }

    function isDeviated() {
      const arch = document.getElementById("sel-arch").value;
      const dom = document.getElementById("sel-dom").value;
      return arch !== RECOMMENDED.arch || dom !== RECOMMENDED.dom;
    }

    function updateMatchRiskUI(clearAck) {
      document.getElementById("field-arch").classList.toggle("locked", !matchUnlocked);
      document.getElementById("field-dom").classList.toggle("locked", !matchUnlocked);
      document.getElementById("btn-unlock-match").textContent = matchUnlocked ? "重新锁定" : "解锁调整";
      document.getElementById("btn-reset-match").style.display = matchUnlocked || isDeviated() ? "inline-flex" : "none";

      const pill = document.getElementById("match-mode-pill");
      const banner = document.getElementById("override-banner");
      const ackText = document.getElementById("match-ack-text");
      const btnConfirm = document.getElementById("btn-confirm");
      const conf = isDeviated() ? 0.41 : RECOMMENDED.conf;
      document.getElementById("conf-val").textContent = conf.toFixed(2);
      document.getElementById("conf-fill").style.width = Math.round(conf * 100) + "%";
      document.getElementById("conf-fill").style.background = conf >= 0.75 ? "var(--green)" : "#d97706";

      if (!matchUnlocked && !isDeviated()) {
        pill.className = "pill pill-green";
        pill.textContent = "已锁定推荐";
        banner.classList.remove("show", "danger");
        ackText.textContent = "已核对骨架、领域与本期范围，确认后开始生成。";
        btnConfirm.textContent = "确认并继续";
      } else if (matchUnlocked && !isDeviated()) {
        pill.className = "pill pill-amber";
        pill.textContent = "已解锁";
        banner.classList.add("show");
        banner.classList.remove("danger");
        banner.textContent = "骨架 / 领域可调整。如无把握，建议恢复推荐。";
        ackText.textContent = "已核对骨架、领域与本期范围，确认后开始生成。";
        btnConfirm.textContent = "确认并继续";
      } else {
        pill.className = "pill pill-red";
        pill.textContent = "已偏离推荐";
        banner.classList.add("show", "danger");
        banner.textContent = "当前与系统推荐不一致，请确认后再生成。";
        ackText.textContent = "确认按当前骨架 / 领域生成。";
        btnConfirm.textContent = "确认按当前选择继续";
      }

      if (clearAck) {
        document.getElementById("match-ack").checked = false;
        document.getElementById("match-gate").classList.remove("ok");
        setDisabled("btn-confirm", true);
      }
    }

    function syncMatchFields(clearAck) {
      const arch = document.getElementById("sel-arch").value;
      const dom = document.getElementById("sel-dom").value;
      document.getElementById("proj-arch").textContent =
        arch.split(" · ")[0] + " · " + dom.split(" · ")[0];
      document.getElementById("rec-label").textContent =
        "ARCH-FLOW · 审核流  ×  DOM-LIBRARY · 图书";
      document.getElementById("spec-preview").textContent = `{
  "title": "图书借阅管理系统",
  "archetype": "${arch.split(" · ")[0]}",
  "domain": "${dom.split(" · ")[0]}",
  "match_mode": "${isDeviated() ? "manual_override" : "recommended"}",
  "roles": ["reader", "admin"],
  "entities": ["Book", "Category", "Borrow", "Notice"],
  "flows": ["申请借阅 → 审核 → 归还"],
  "baseline": ["captcha", "upload", "page", "errorcode"],
  "out_of_mvp": ["人脸识别", "协同过滤推荐"]
}`;
      updateMatchRiskUI(!!clearAck);
    }

    function openProject(id, demoOverride) {
      clearTimeout(genTimer);
      const p = projects.find((x) => x.id === id) || projects[0];
      document.getElementById("proj-title").textContent = p.name;
      document.getElementById("proj-id").textContent = p.id;
      document.getElementById("proj-arch").textContent = p.arch;
      const statusEl = document.getElementById("proj-status-pill");
      statusEl.className = "pill " + p.pill;
      statusEl.textContent = p.statusLabel;

      const state = demoOverride || p.status;
      matchConfirmed = state !== "needs_confirm";
      matchUnlocked = false;
      document.getElementById("sel-arch").value = RECOMMENDED.arch;
      document.getElementById("sel-dom").value = RECOMMENDED.dom;
      document.getElementById("match-ack").checked = matchConfirmed;
      document.getElementById("match-ack").disabled = false;
      document.getElementById("match-gate").classList.toggle("ok", matchConfirmed);
      setDisabled("btn-confirm", !matchConfirmed);
      // download 由质量检查决定，先锁上
      setDisabled("btn-download", true);

      if (state === "needs_confirm") setProjectTab("match");
      else if (state === "generating") setProjectTab("generate");
      else if (state === "failed") { setProjectTab("artifacts"); setArtifactView("gates"); }
      else if (state === "running") setProjectTab("runtime");
      else if (state === "generated") setProjectTab("runtime");
      else setProjectTab("generate");

      applyGenState(state === "needs_confirm" ? "idle" : state);
      setRuntime(state === "running");
      showView("project");
      syncMatchFields(false);
      if (matchConfirmed) {
        document.getElementById("match-ack").checked = true;
        setDisabled("btn-confirm", true);
      }
    }

    function startGenerate() {
      clearTimeout(genTimer);
      applyGenState("generating");
      setStatus("生成中", "pill-teal");
      setDisabled("btn-download", true);
      toast("Job #1042 已启动（将跑质量检查）");
      let w = 42;
      const bar = document.getElementById("job-bar");
      bar.style.width = w + "%";
      const tick = setInterval(() => {
        w = Math.min(w + 18, 100);
        bar.style.width = w + "%";
      }, 400);
      genTimer = setTimeout(() => {
        clearInterval(tick);
        applyGenState("generated");
        setStatus("已生成 · 可交付", "pill-green");
        toast("质量检查已过 · 交付包已解锁");
        setProjectTab("artifacts");
      }, 2000);
    }

    function handleAction(action, el, e) {
      if (!action) return;

      if (action === "open-project") {
        openProject(el.dataset.id || el.closest("[data-id]")?.dataset.id);
        return;
      }
      if (action === "open-job") {
        const state = el.dataset.jobState || el.closest("[data-job-state]")?.dataset.jobState || "generating";
        const pid = el.dataset.project || el.closest("[data-project]")?.dataset.project || "gf-20260717-001";
        openProject(pid, state);
        toast("已打开对应项目 · " + state);
        return;
      }
      if (action === "retry-from-jobs") {
        openProject("gf-20260716-011", "failed");
        toast("已进入失败项目 · 可点「从失败步骤重试」");
        return;
      }
      if (action === "refresh-list") {
        renderList(
          document.querySelector("#list-filter button.active")?.dataset.f || "all",
          document.getElementById("list-search").value.trim()
        );
        toast("列表已刷新");
        return;
      }
      if (action === "reupload") {
        toast("另建项目 · 回到列表上传新开题报告");
        showView("home");
        return;
      }
      if (action === "toggle-override") {
        if (!matchUnlocked) {
          if (!confirm("解锁后可改骨架/领域。改错会生成另一套系统。确认解锁？")) return;
          matchUnlocked = true;
          toast("已解锁 · 请谨慎修改");
        } else {
          if (isDeviated()) {
            toast("当前已偏离推荐，请先「恢复推荐」再锁定，或保持解锁状态");
            return;
          }
          matchUnlocked = false;
          toast("已重新锁定推荐");
        }
        syncMatchFields(true);
        return;
      }
      if (action === "reset-match") {
        document.getElementById("sel-arch").value = RECOMMENDED.arch;
        document.getElementById("sel-dom").value = RECOMMENDED.dom;
        matchUnlocked = false;
        syncMatchFields(true);
        toast("已恢复系统推荐 · 骨架/领域已锁定");
        return;
      }
      if (action === "confirm-match") {
        if (isDisabled(el)) {
          toast("请先勾选确认");
          return;
        }
        if (isDeviated() && !confirm("当前已偏离系统推荐。确认仍要用这套骨架/领域生成？")) {
          return;
        }
        const deviant = isDeviated();
        matchConfirmed = true;
        if (!deviant) matchUnlocked = false;
        else matchUnlocked = false; // lock whatever was chosen
        setStatus("待生成", "pill-teal");
        document.getElementById("match-gate").classList.add("ok");
        setDisabled("btn-confirm", true);
        updateMatchRiskUI(false);
        setProjectTab("generate");
        applyGenState("idle");
        toast(deviant ? "已按手动覆盖确认（有偏离风险）" : "已确认推荐匹配 · 可一键生成");
        return;
      }
      if (action === "generate") {
        if (!matchConfirmed && !document.getElementById("match-ack").checked) {
          toast("请先在「匹配确认」完成确认");
          setProjectTab("match");
          return;
        }
        matchConfirmed = true;
        startGenerate();
        return;
      }
      if (action === "cancel-job") {
        clearTimeout(genTimer);
        applyGenState("idle");
        setStatus("待生成", "pill-teal");
        toast("任务已取消");
        return;
      }
      if (action === "finish-job-demo") {
        clearTimeout(genTimer);
        applyGenState("generated");
        setStatus("已生成 · 可交付", "pill-green");
        toast("质量检查已过 · 交付包已解锁");
        setProjectTab("artifacts");
        return;
      }
      if (action === "demo-gate-fail") {
        applyGenState("failed");
        setStatus("质量检查未过 · 暂不可交付", "pill-red");
        setProjectTab("artifacts");
        setArtifactView("gates");
        toast("演示：P2 失败 → ZIP 锁定");
        return;
      }
      if (action === "demo-gate-pass") {
        applyGenState("generated");
        setStatus("已生成 · 可交付", "pill-green");
        setProjectTab("artifacts");
        setArtifactView("gates");
        toast("演示：质量检查全过 → 交付包解锁");
        return;
      }
      if (action === "regenerate") {
        if (!confirm("重新生成将覆盖当前工作区业务配置，确认？")) return;
        startGenerate();
        return;
      }
      if (action === "retry-job") {
        toast("从失败步骤续跑（演示）");
        startGenerate();
        return;
      }
      if (action === "rollback-island") {
        toast("现网已无「回滚业务岛」；请重新生成");
        applyGenState("idle");
        setStatus("待生成", "pill-teal");
        return;
      }
      if (action === "goto-tab") {
        setProjectTab(el.dataset.tab);
        return;
      }
      if (action === "goto-artifacts-gates") {
        setProjectTab("artifacts");
        setArtifactView("gates");
        return;
      }
      if (action === "goto-logs") {
        setProjectTab("logs");
        showLog(el.dataset.logSide || "job");
        return;
      }
      if (action === "download-zip") {
        if (!gatesPass || isDisabled(document.getElementById("btn-download"))) {
          toast("质量检查未过（尤其是主流程）· 禁止下载交付包");
          setProjectTab("artifacts");
          return;
        }
        toast("开始下载 thesis-app.zip（质量检查已通过）");
        return;
      }
      if (action === "delete-project") {
        if (!confirm("删除项目\n\n将清理工作区与 ZIP。\n确认删除？\n（演示：默认不保留数据库）")) return;
        toast("项目已删除（演示）");
        showView("home");
        return;
      }
      if (action === "toggle-be") {
        beOn = !beOn;
        syncRuntimeUI();
        toast(beOn ? "后端已启动 · 9103" : "后端已停止");
        return;
      }
      if (action === "toggle-fe") {
        feOn = !feOn;
        syncRuntimeUI();
        toast(feOn ? "前端已启动 · 9203" : "前端已停止");
        return;
      }
      if (action === "restart-be") {
        beOn = false;
        syncRuntimeUI();
        setTimeout(() => {
          beOn = true;
          syncRuntimeUI();
          toast("后端已重启");
        }, 250);
        return;
      }
      if (action === "restart-fe") {
        feOn = false;
        syncRuntimeUI();
        setTimeout(() => {
          feOn = true;
          syncRuntimeUI();
          toast("前端已重启");
        }, 250);
        return;
      }
      if (action === "start-all") {
        setRuntime(true);
        toast("已全部启动");
        return;
      }
      if (action === "stop-all") {
        setRuntime(false);
        toast("已全部关闭");
        return;
      }
      if (action === "restart-all") {
        setRuntime(false);
        setTimeout(() => {
          setRuntime(true);
          toast("已全部重启");
        }, 250);
        return;
      }
      if (action === "open-preview") {
        if (!(beOn && feOn)) {
          toast("请先启动后端与前端");
          return;
        }
        toast("原型：将打开 http://127.0.0.1:9203");
        return;
      }
      if (action === "copy-preview") {
        if (!(beOn && feOn)) {
          toast("请先启动前端预览");
          return;
        }
        toast("已复制预览地址 http://127.0.0.1:9203");
        return;
      }
      if (action === "refresh-log") {
        showLog(currentLogSide);
        toast("日志已刷新");
        return;
      }
      if (action === "view-spec") {
        openModal("生成配置", document.getElementById("spec-preview").textContent);
        return;
      }
      if (action === "view-er") {
        openModal("E-R 图（线框）", "演示：实际页面为可缩放平移的 SVG（拖拽平移 · 滚轮缩放）。\n实体：book / category / borrow / notice / sys_user …\n联系：belong / of / issued_by");
        return;
      }
      if (action === "view-modules") {
        setProjectTab("artifacts");
        setArtifactView("thesis");
        openModal("功能模块图", "演示：按交付菜单推导；可切换「按业务 / 按端」。\n节点：门户浏览 · 借阅申请 · 管理审核 · 公告 …");
        return;
      }
      if (action === "view-testcases") {
        setProjectTab("artifacts");
        setArtifactView("thesis");
        openModal("软件测试用例", "演示：默认 6 列；可选 5～9 列。\n大模型仅润色步骤/预期，不增删用例、不发明功能。");
        return;
      }
      if (action === "download-er") {
        toast("下载 E-R SVG（演示）");
        return;
      }
      if (action === "test-ds") {
        document.getElementById("ds-latency").textContent = "测试中…";
        setTimeout(() => {
          document.getElementById("ds-latency").textContent = "延迟 287 ms · 模型可用";
          toast("大模型连接正常");
        }, 500);
        return;
      }
      if (action === "test-gm") {
        toast("请先配置 GEMINI_API_KEY");
        return;
      }
      if (action === "test-unsplash" || action === "refresh-unsplash") {
        toast(action === "test-unsplash" ? "请先配置 UNSPLASH_ACCESS_KEY" : "已刷新（演示）");
        return;
      }
      if (action === "save-ds") {
        toast("已保存（Key 仍只读环境变量）");
        return;
      }
      if (action === "refresh-balance") {
        toast("余额已刷新");
        return;
      }
      if (action === "refresh-usage" || action === "refresh-calls") {
        toast("已刷新");
        return;
      }
      if (action === "filter-calls-stage") {
        const stage = el.dataset.stage || "";
        const sel = document.getElementById("call-filter-stage");
        if (sel) sel.value = stage;
        showView("llm");
        toast("已按阶段筛选调用 · " + (sel?.selectedOptions?.[0]?.textContent || stage));
        return;
      }
      if (action === "open-sample-proposal") {
        openSampleModal();
        return;
      }
      if (action === "close-sample-modal") {
        closeSampleModal();
        return;
      }
      if (action === "generate-sample") {
        const box = document.getElementById("sample-result");
        const dl = document.getElementById("sample-dl-btn");
        if (box) box.hidden = false;
        if (dl) dl.disabled = false;
        const btn = document.querySelector('[data-action="generate-sample"]');
        if (btn) btn.textContent = "再抽一份";
        toast("已生成测试开题（演示）");
        return;
      }
      if (action === "download-sample") {
        toast("已下载测试开题 txt（演示）");
        return;
      }
      if (action === "close-plan-modal") {
        closePlanModal();
        return;
      }
      if (action === "plan-split-all") {
        if (!planDraft) return;
        const files = planDraft.clusters.flatMap((c) => c.files);
        planDraft = {
          notes: "已全部拆开为单文件项目。",
          clusters: files.map((f, i) => ({
            id: i + 1,
            label: f.name.replace(/\.[^.]+$/, ""),
            reason: "全部拆开",
            files: [f],
          })),
          discard: planDraft.discard || [],
        };
        renderPlanModal(planDraft);
        toast("已全部拆开");
        return;
      }
      if (action === "plan-merge-all") {
        if (!planDraft) return;
        const files = planDraft.clusters.flatMap((c) => c.files);
        planDraft = {
          notes: "已合并为一个项目。",
          clusters: [{
            id: 1,
            label: files[0]?.name.replace(/\.[^.]+$/, "") || "合并项目",
            reason: "手动合并",
            files,
          }],
          discard: planDraft.discard || [],
        };
        renderPlanModal(planDraft);
        toast("已合并为一个");
        return;
      }
      if (action === "confirm-plan") {
        const n = planDraft?.clusters?.length || 0;
        closePlanModal();
        const job = uploadJobs.find((j) => j.status === "planned");
        if (job) {
          job.status = "done";
          job.phase = `已创建 ${n} 个项目`;
          job.projectId = "gf-20260717-001";
          job.bar = "var(--green, #2f9e44)";
          renderUploadJobs();
        }
        toast(n ? `已创建 ${n} 个项目 · 进入匹配确认` : "没有可创建的项目");
        if (n) setTimeout(() => openProject("gf-20260717-001", "needs_confirm"), 350);
        return;
      }
      if (action === "reopen-plan") {
        const id = Number(el.dataset.jobId);
        const job = uploadJobs.find((j) => j.id === id);
        if (job?.plan) openPlanModal(job.plan);
        return;
      }
      if (action === "dismiss-upload-job") {
        const id = Number(el.dataset.jobId);
        const idx = uploadJobs.findIndex((j) => j.id === id);
        if (idx >= 0) uploadJobs.splice(idx, 1);
        renderUploadJobs();
        return;
      }
      if (action === "dt-shortcut") {
        toast("时间范围 · " + (el.textContent || "").trim() + "（演示 · 中文快捷项）");
        return;
      }
      if (action === "filter-calls-project") {
        const pid = el.dataset.pid || "";
        const input = document.getElementById("call-filter-pid");
        if (input) input.value = pid;
        toast("已按项目筛选调用 · " + pid);
        return;
      }
      if (action === "sort-usage") {
        const key = el.dataset.sort || "tokens";
        const tbody = document.getElementById("usage-tbody");
        if (!tbody) return;
        const prev = el.dataset.order || "";
        const next = prev === "desc" ? "asc" : "desc";
        document.querySelectorAll("#usage-table .th-sort").forEach((th) => {
          th.dataset.order = "";
          const ico = th.querySelector(".sort-ico");
          if (ico) ico.textContent = "";
        });
        el.dataset.order = next;
        const ico = el.querySelector(".sort-ico");
        if (ico) ico.textContent = next === "desc" ? "↓" : "↑";
        const rows = [...tbody.querySelectorAll("tr")];
        const num = (r) => Number(r.dataset[key === "last_at" ? "last" : key] || 0);
        const ts = (r) => Date.parse(r.dataset.last || 0) || 0;
        rows.sort((a, b) => {
          const av = key === "last_at" ? ts(a) : num(a);
          const bv = key === "last_at" ? ts(b) : num(b);
          return next === "asc" ? av - bv : bv - av;
        });
        rows.forEach((r) => tbody.appendChild(r));
        toast("按「" + el.textContent.replace(/\s*[↑↓]\s*$/, "").trim() + "」" + (next === "asc" ? "升序" : "降序"));
        return;
      }
      if (action === "refresh-jobs") {
        toast("任务列表已刷新");
        return;
      }
      if (action === "toggle-job-group") {
        const row = el.closest("tr.job-group");
        const gid = row?.getAttribute("data-group");
        if (!row || !gid) return;
        const open = row.getAttribute("aria-expanded") === "true";
        row.setAttribute("aria-expanded", open ? "false" : "true");
        document.querySelectorAll(`tr.job-child[data-group="${gid}"]`).forEach((r) => {
          r.classList.toggle("hidden", open);
        });
        return;
      }
      if (action === "purge-finished") {
        if (!confirm("将删除成功、失败与已取消的任务，进行中的不受影响。")) return;
        toast("已清空历史（演示）");
        return;
      }
      if (action === "purge-orphans") {
        if (!confirm("将清空项目已不存在的任务，此操作不可恢复。")) return;
        toast("已清空项目不存在的任务（演示）");
        return;
      }
      if (action === "cancel-from-jobs") {
        toast("已取消任务（演示）");
        return;
      }
      if (action === "refresh-system") {
        toast("运行环境已刷新");
        return;
      }
      if (action === "free-ports") {
        toast("已释放异常占用（演示）");
        return;
      }
      if (action === "close-modal") {
        closeModal();
        return;
      }

      toast("已响应：" + action);
    }

    // —— Global click delegation ——
    document.addEventListener("click", (e) => {
      const switchBtn = e.target.closest("[data-switch]");
      if (switchBtn) {
        switchBtn.classList.toggle("on");
        toast(switchBtn.classList.contains("on") ? "阶段已开启" : "阶段已关闭 · 仍可 bake");
        return;
      }

      const nav = e.target.closest(".nav-item[data-nav]");
      if (nav) {
        showView(nav.dataset.nav);
        return;
      }

      if (e.target.closest("#nav-toggle")) {
        toggleNav();
        return;
      }

      if (e.target.id === "nav-backdrop" || e.target.closest("#nav-backdrop")) {
        closeNav();
        return;
      }

      const tab = e.target.closest("#proj-tabs .tab");
      if (tab) {
        setProjectTab(tab.dataset.tab);
        return;
      }

      const logSide = e.target.closest("#log-side button");
      if (logSide) {
        showLog(logSide.dataset.side);
        return;
      }

      const aviewBtn = e.target.closest("#artifact-subtabs button");
      if (aviewBtn) {
        setArtifactView(aviewBtn.dataset.aview);
        return;
      }

      const usageTabBtn = e.target.closest("#usage-detail-tabs button");
      if (usageTabBtn) {
        setUsageTab(usageTabBtn.dataset.usageTab);
        return;
      }

      const filterBtn = e.target.closest("#list-filter button");
      if (filterBtn) {
        document.querySelectorAll("#list-filter button").forEach((b) => b.classList.remove("active"));
        filterBtn.classList.add("active");
        renderList(filterBtn.dataset.f, document.getElementById("list-search").value.trim());
        return;
      }

      if (e.target.id === "back-home" || e.target.closest("#back-home")) {
        showView("home");
        return;
      }

      if (e.target.closest("#modal-mask") === e.target) {
        closeModal();
        return;
      }

      const actionable = e.target.closest("[data-action]");
      if (actionable) {
        e.preventDefault();
        handleAction(actionable.dataset.action, actionable, e);
      }
    });

    document.getElementById("match-ack").addEventListener("change", (e) => {
      setDisabled("btn-confirm", !e.target.checked);
      document.getElementById("match-gate").classList.toggle("ok", e.target.checked);
      if (e.target.checked) toast("已勾选 · 可确认匹配");
    });

    document.getElementById("list-search").addEventListener("input", (e) => {
      const active = document.querySelector("#list-filter button.active");
      renderList(active?.dataset.f || "all", e.target.value.trim());
    });

    document.getElementById("sel-arch").addEventListener("change", () => {
      if (!matchUnlocked) {
        document.getElementById("sel-arch").value = RECOMMENDED.arch;
        toast("骨架已锁定 · 请先点「解锁调整」");
        return;
      }
      syncMatchFields(true);
      toast(isDeviated() ? "已偏离推荐 · 请确认你知道后果" : "骨架已改回推荐值");
    });
    document.getElementById("sel-dom").addEventListener("change", () => {
      if (!matchUnlocked) {
        document.getElementById("sel-dom").value = RECOMMENDED.dom;
        toast("领域已锁定 · 请先点「解锁调整」");
        return;
      }
      syncMatchFields(true);
      toast(isDeviated() ? "已偏离推荐 · 请确认你知道后果" : "领域已改回推荐值");
    });
    document.getElementById("sel-theme")?.addEventListener("change", () => toast("行业配色已自动保存"));
    document.getElementById("sel-llm")?.addEventListener("change", () => toast("LLM 开关已自动保存"));
    document.getElementById("sel-password")?.addEventListener("change", () => toast("密码策略已自动保存"));
    document.getElementById("usage-presence")?.addEventListener("change", (e) => {
      applyUsagePresence(e.target.value || "alive");
    });

    document.getElementById("log-filter").addEventListener("input", () => showLog());

    document.getElementById("demo-state").addEventListener("change", (e) => {
      const v = e.target.value;
      if (v === "list") showView("home");
      else openProject("gf-20260717-001", v);
    });

    document.getElementById("theme-toggle").addEventListener("click", () => {
      const dark = document.documentElement.getAttribute("data-theme") === "dark";
      if (dark) {
        document.documentElement.removeAttribute("data-theme");
        document.getElementById("theme-toggle").textContent = "夜间";
        document.getElementById("theme-toggle").title = "切换夜间模式";
      } else {
        document.documentElement.setAttribute("data-theme", "dark");
        document.getElementById("theme-toggle").textContent = "日间";
        document.getElementById("theme-toggle").title = "切换日间模式";
      }
    });

    document.addEventListener("keydown", (e) => {
      if (e.key === "Escape") closeNav();
    });
    window.addEventListener("resize", () => {
      if (window.matchMedia("(min-width: 901px)").matches) closeNav();
    });

    document.getElementById("type-paren-mode")?.addEventListener("change", (e) => {
      document.getElementById("type-mode-label").textContent =
        e.target.checked ? "类型 varchar(60)" : "类型分列 varchar | 60";
    });

    // Upload → plan confirm（与现网一致：确认前不建项）
    const dz = document.getElementById("dropzone");
    const fileInput = document.getElementById("file-input");

    function roleLabel(role) {
      return ({ proposal: "开题", task: "任务书", features: "功能清单", material: "材料" })[role] || "材料";
    }

    function renderUploadJobs() {
      const panel = document.getElementById("upload-jobs-panel");
      const list = document.getElementById("upload-jobs-list");
      if (!panel || !list) return;
      if (!uploadJobs.length) {
        panel.hidden = true;
        list.innerHTML = "";
        return;
      }
      panel.hidden = false;
      const planned = uploadJobs.filter((j) => j.status === "planned").length;
      const hint = document.getElementById("upload-queue-hint");
      if (hint) hint.textContent = planned ? `并发 2 · ${planned} 份待确认分堆` : "并发 2";
      list.innerHTML = uploadJobs.map((job) => `
        <div class="upload-job" data-job-id="${job.id}">
          <div class="row" style="justify-content:space-between;margin-bottom:6px;gap:8px">
            <div style="min-width:0">
              <div style="font-weight:600;line-height:1.35">${job.name}</div>
              <div class="small muted">${job.fileCount} 份材料 · ${job.phase}</div>
            </div>
            <div class="row gap-sm" style="flex-shrink:0">
              ${job.status === "planned" ? `<button type="button" class="btn btn-secondary btn-sm" data-action="reopen-plan" data-job-id="${job.id}">查看分堆</button>` : ""}
              ${job.status === "done" ? `<button type="button" class="btn btn-secondary btn-sm" data-action="open-project" data-id="${job.projectId || "gf-20260717-001"}">查看</button>` : ""}
              ${["done", "error", "planned"].includes(job.status) ? `<button type="button" class="btn btn-ghost btn-sm" data-action="dismiss-upload-job" data-job-id="${job.id}">移除</button>` : ""}
            </div>
          </div>
          <div class="progress"><i style="width:${job.pct}%;background:${job.bar || "var(--teal)"}"></i></div>
          ${job.error ? `<div class="small warn" style="margin-top:6px">${job.error}</div>` : ""}
        </div>
      `).join("");
    }

    function demoPlan(files) {
      const names = files.length ? files : ["宿舍报修开题.txt", "食堂点餐开题.txt"];
      if (names.length === 1) {
        return {
          notes: "检测到单一课题材料。",
          clusters: [
            {
              id: 1,
              label: names[0].replace(/\.[^.]+$/, ""),
              reason: "单份材料自成一堆",
              files: [{ name: names[0], role: "proposal" }],
            },
          ],
          discard: [],
        };
      }
      return {
        notes: "检测到多份不同开题，建议拆成多个项目。",
        clusters: names.slice(0, 2).map((name, i) => ({
          id: i + 1,
          label: name.replace(/\.[^.]+$/, ""),
          reason: i === 0 ? "宿舍报修语义" : "食堂点餐语义",
          files: [{ name, role: "proposal" }],
        })),
        discard: names.length > 2
          ? [{ name: names[2], reason: "信号过弱 / 疑似无关材料" }]
          : [],
      };
    }

    function renderPlanModal(plan) {
      planDraft = plan;
      const box = document.getElementById("plan-clusters");
      const notes = document.getElementById("plan-notes");
      const btn = document.getElementById("plan-confirm-btn");
      if (notes) {
        notes.textContent = `${plan.notes || "请核对下方分堆后确认创建。"} · LLM 结构分堆 · 来源 demo`;
      }
      if (btn) btn.textContent = `确认创建 ${plan.clusters.length} 个项目`;
      if (!box) return;
      box.innerHTML = plan.clusters.map((cl) => `
        <div class="plan-cluster">
          <div class="row" style="justify-content:space-between;gap:8px;align-items:flex-start">
            <div style="min-width:0;flex:1">
              <div class="row" style="gap:8px;align-items:baseline;flex-wrap:wrap">
                <span class="plan-cluster-idx">项目 ${cl.id}</span>
                <span class="plan-cluster-title">${cl.label}</span>
              </div>
              <div class="small muted" style="margin-top:4px">${cl.reason || ""}</div>
            </div>
            <span class="small muted" style="flex-shrink:0">${cl.files.length} 份</span>
          </div>
          <div class="plan-cluster-files">
            ${cl.files.map((f) => `<span class="plan-file-chip">${f.name} <span class="muted">${roleLabel(f.role)}</span></span>`).join("")}
          </div>
        </div>
      `).join("") + (plan.discard?.length ? `
        <div class="small warn">
          <div style="font-weight:600;margin-bottom:4px">将剔除（不参与匹配）</div>
          <div class="plan-cluster-files">
            ${plan.discard.map((d) => `<span class="plan-file-chip plan-file-chip--discard" title="${d.reason || ""}">${d.name}</span>`).join("")}
          </div>
        </div>
      ` : "");
    }

    function openPlanModal(plan) {
      renderPlanModal(plan);
      document.getElementById("plan-modal-mask")?.classList.add("show");
    }

    function closePlanModal() {
      document.getElementById("plan-modal-mask")?.classList.remove("show");
    }

    function openSampleModal() {
      document.getElementById("sample-modal-mask")?.classList.add("show");
    }

    function closeSampleModal() {
      document.getElementById("sample-modal-mask")?.classList.remove("show");
    }

    function simulateUpload(fileNames) {
      const names = (fileNames || []).filter(Boolean);
      const label = names.length > 1 ? `${names[0]} 等 ${names.length} 份` : (names[0] || "开题材料.txt");
      const job = {
        id: uploadJobSeq++,
        name: label,
        fileCount: Math.max(1, names.length),
        files: names.length ? names : ["开题材料.txt"],
        status: "uploading",
        phase: "上传中 0%",
        pct: 0,
        bar: "var(--teal)",
        projectId: "",
        error: "",
        plan: null,
      };
      uploadJobs.unshift(job);
      renderUploadJobs();
      let pct = 0;
      const timer = setInterval(() => {
        pct += 14;
        const show = Math.min(pct, 100);
        job.pct = show;
        if (show < 55) job.phase = `上传中 ${show}%`;
        else if (show < 100) {
          job.status = "parsing";
          job.phase = "解析并分堆…";
        } else {
          clearInterval(timer);
          job.status = "planned";
          job.phase = "待确认分堆";
          job.pct = 100;
          job.plan = demoPlan(job.files);
          renderUploadJobs();
          openPlanModal(job.plan);
          toast("分堆完成 · 请确认后再创建");
          return;
        }
        renderUploadJobs();
      }, 80);
    }

    dz.addEventListener("dragover", (e) => { e.preventDefault(); dz.classList.add("dragover"); });
    dz.addEventListener("dragleave", () => dz.classList.remove("dragover"));
    dz.addEventListener("drop", (e) => {
      e.preventDefault();
      dz.classList.remove("dragover");
      const names = [...(e.dataTransfer.files || [])].map((f) => f.name);
      simulateUpload(names.length ? names : ["宿舍报修开题.txt", "食堂点餐开题.txt"]);
    });
    fileInput.addEventListener("change", () => {
      const names = [...(fileInput.files || [])].map((f) => f.name);
      if (names.length) simulateUpload(names);
      fileInput.value = "";
    });

    // Click dropzone label area (file input covers it already)

    renderList();
    showLog("job");
    syncRuntimeUI();
    syncMatchFields(false);
    renderGates(false);
    setArtifactView("db");
    renderUploadJobs();
