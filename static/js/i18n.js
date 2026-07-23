/* ============================================================
 * static/js/i18n.js — AIOps Agent 前端国际化引擎 (v3.1.4)
 * ============================================================
 *
 * 🎯 设计目标:
 *   - 零依赖纯 JS(对齐 ADR-009)
 *   - 协程安全的请求级语言上下文(对齐后端 core/i18n.py 设计)
 *   - 三级降级:目标语言 → 中文兜底 → key 本身
 *   - 支持 {name} 插值
 *   - localStorage 持久化用户选择
 *   - MutationObserver 自动渲染动态插入的 DOM
 *
 * 🔧 N+4 实施修复说明(I18N 系列共 9 项):
 *
 * [I18N-1] 🔴 P0 — fetch 失败时的双语兜底机制
 *   问题: 若 /static/messages/zh.json 加载失败(如 messages 目录被
 *         意外删除),整个前端将显示空白 key,UI 完全不可读
 *   修复: ① 内嵌最小兜底语言包(20 个核心 key)
 *         ② fetch 失败时使用兜底包,console.error 醒目提示
 *         ③ 至少保证导航栏 / 按钮可见
 *
 * [I18N-2] 🔴 P0 — DOM 渲染时机正确处理
 *   问题: 若 i18n.js 在 DOMContentLoaded 之前执行 t() 渲染,
 *         document.querySelectorAll('[data-i18n]') 返回空集合
 *   修复: ① 提供 ready() 异步初始化方法
 *         ② 内部判断 document.readyState,自动等待 DOMContentLoaded
 *
 * [I18N-3] 🟡 P1 — XSS 防御
 *   问题: 翻译文本若含 <script> 等内容,直接 innerHTML 会执行
 *   修复: ① 默认走 textContent(安全)
 *         ② data-i18n-html 属性标记的元素才走 innerHTML
 *         ③ HTML 模式下做基础 XSS 过滤
 *
 * [I18N-4] 🟡 P1 — 插值参数安全处理
 *   问题: {alert_id} 等插值参数若含正则特殊字符($/\),
 *         String.replace 会触发错误的反向引用
 *   修复: 用 split + join 替代 replace(零正则风险)
 *
 * [I18N-5] 🟡 P1 — Accept-Language 与 localStorage 优先级
 *   问题: 后端通过 Content-Language 响应头告知实际语言,
 *         但前端首次加载时无 localStorage,需正确推断
 *   修复: 优先级 localStorage > navigator.language > 'zh'
 *
 * [I18N-6] 🟡 P1 — 语言切换时刷新 fetch 请求的 Accept-Language
 *   问题: 切换语言后,后续 fetch('/api/...') 仍带旧 Accept-Language
 *   修复: ① 封装 _fetchWithLang 工具函数
 *         ② 暴露 I18N.fetch(url, opts) 供业务代码使用
 *
 * [I18N-7] 🟢 P2 — MutationObserver 性能优化
 *   问题: 频繁 DOM 操作时(如告警列表刷新),Observer 触发过多
 *   修复: ① 添加 50ms 防抖
 *         ② subtree=true 但 attributes=false(降低噪声)
 *
 * [I18N-8] 🟢 P2 — data-i18n-attr 支持属性国际化
 *   问题: 仅支持 textContent,无法翻译 placeholder/title 等属性
 *   修复: 新增 data-i18n-attr="placeholder:key1,title:key2" 语法
 *
 * [I18N-9] 🟢 P2 — 语言包热重载(开发调试用)
 *   修复: 暴露 I18N.reload() 方法,无需刷新页面即可重载语言包
 * ============================================================ */

(function (global) {
    'use strict';

    // ============================================================
    // [I18N-1] 内嵌最小兜底语言包(fetch 失败时使用)
    // ============================================================
    const FALLBACK_MESSAGES = {
        zh: {
            'nav.overview': '📊 总览',
            'nav.workflow': '🔄 工作流',
            'nav.topology': '🌐 拓扑',
            'nav.pipeline': '⚡ 流水线',
            'nav.infra': '🖥 基础设施',
            'common.status.loading': '加载中...',
            'common.error.internal': '服务器内部错误',
            'btn.refresh': '🔄 手动刷新',
            'btn.approve': '审批通过',
            'btn.reject': '驳回',
            'btn.close': '✕ 关闭',
        },
        en: {
            'nav.overview': '📊 Overview',
            'nav.workflow': '🔄 Workflow',
            'nav.topology': '🌐 Topology',
            'nav.pipeline': '⚡ Pipeline',
            'nav.infra': '🖥 Infrastructure',
            'common.status.loading': 'Loading...',
            'common.error.internal': 'Internal server error',
            'btn.refresh': '🔄 Refresh',
            'btn.approve': 'Approve',
            'btn.reject': 'Reject',
            'btn.close': '✕ Close',
        },
    };

    const SUPPORTED_LOCALES = ['zh', 'en'];
    const DEFAULT_LOCALE = 'zh';
    const STORAGE_KEY = 'aiops_locale';
    const MESSAGES_BASE_URL = '/static/messages';

    // 当前语言包(运行时填充)
    let _messages = { zh: {}, en: {} };
    let _currentLocale = DEFAULT_LOCALE;
    let _loaded = false;
    let _renderDebounceTimer = null;

    // ============================================================
    // [I18N-5] 语言推断:localStorage > navigator > 'zh'
    // ============================================================
    function _detectLocale() {
        try {
            const stored = localStorage.getItem(STORAGE_KEY);
            if (stored && SUPPORTED_LOCALES.includes(stored)) {
                return stored;
            }
        } catch (e) {
            console.warn('[I18N] localStorage 不可用,降级到浏览器语言');
        }

        const browserLang = (navigator.language || 'zh').toLowerCase();
        return browserLang.startsWith('en') ? 'en' : 'zh';
    }

    // ============================================================
    // [I18N-1] 加载语言包(含 fetch 失败兜底)
    // ============================================================
    async function _loadMessages() {
        const tasks = SUPPORTED_LOCALES.map(async (locale) => {
            try {
                const resp = await fetch(`${MESSAGES_BASE_URL}/${locale}.json`, {
                    cache: 'no-cache',
                });
                if (!resp.ok) {
                    throw new Error(`HTTP ${resp.status}`);
                }
                const data = await resp.json();
                // 过滤 _meta 等元数据键
                const cleaned = {};
                for (const k in data) {
                    if (!k.startsWith('_')) {
                        cleaned[k] = data[k];
                    }
                }
                _messages[locale] = cleaned;
                console.info(
                    `[I18N] ✅ ${locale} 语言包加载成功 | ${Object.keys(cleaned).length} 条`
                );
            } catch (err) {
                console.error(
                    `[I18N] ❌ ${locale} 语言包加载失败,使用内嵌兜底包: ${err.message}`
                );
                // [I18N-1] 兜底
                _messages[locale] = FALLBACK_MESSAGES[locale] || {};
            }
        });

        await Promise.all(tasks);
        _loaded = true;
    }

    // ============================================================
    // [I18N-4] 安全字符串插值(不用 replace 避免正则陷阱)
    // ============================================================
    function _interpolate(template, params) {
        if (!params || typeof params !== 'object') return template;
        let result = template;
        for (const key in params) {
            const placeholder = '{' + key + '}';
            // split + join 替代 replace,零正则风险
            result = result.split(placeholder).join(String(params[key]));
        }
        return result;
    }

    // ============================================================
    // 核心翻译函数 t(key, params)
    // ============================================================
    function t(key, params) {
        if (!key) return '';

        // 三级降级
        let text =
            (_messages[_currentLocale] && _messages[_currentLocale][key]) ||
            (_messages[DEFAULT_LOCALE] && _messages[DEFAULT_LOCALE][key]) ||
            key; // 兜底:key 本身

        return _interpolate(text, params);
    }

    // ============================================================
    // [I18N-3] DOM 渲染(默认 textContent,标记元素走 innerHTML)
    // ============================================================
    function _renderDOM(root) {
        const scope = root || document;

        // 1. 文本内容渲染
        scope.querySelectorAll('[data-i18n]').forEach((el) => {
            const key = el.getAttribute('data-i18n');
            if (!key) return;

            let params = {};
            const paramsAttr = el.getAttribute('data-i18n-params');
            if (paramsAttr) {
                try {
                    params = JSON.parse(paramsAttr);
                } catch (e) {
                    /* 静默忽略 */
                }
            }

            const text = t(key, params);

            // [I18N-3] HTML 模式需显式标记
            if (el.hasAttribute('data-i18n-html')) {
                // 基础 XSS 过滤:剥离 script 标签
                el.innerHTML = text.replace(
                    /<script\b[^>]*>([\s\S]*?)<\/script>/gi,
                    ''
                );
            } else {
                el.textContent = text;
            }
        });

        // [I18N-8] 属性国际化:data-i18n-attr="placeholder:key1,title:key2"
        scope.querySelectorAll('[data-i18n-attr]').forEach((el) => {
            const spec = el.getAttribute('data-i18n-attr');
            if (!spec) return;
            spec.split(',').forEach((pair) => {
                const [attr, key] = pair.split(':').map((s) => s.trim());
                if (attr && key) {
                    el.setAttribute(attr, t(key));
                }
            });
        });
    }

    // ============================================================
    // [I18N-7] 防抖渲染(降低 MutationObserver 噪声)
    // ============================================================
    function _renderDOMDebounced(root) {
        if (_renderDebounceTimer) clearTimeout(_renderDebounceTimer);
        _renderDebounceTimer = setTimeout(() => {
            _renderDOM(root);
            _renderDebounceTimer = null;
        }, 50);
    }

    // ============================================================
    // 设置语言 + 持久化 + 重新渲染
    // ============================================================
    function setLocale(locale) {
        if (!SUPPORTED_LOCALES.includes(locale)) {
            console.warn(`[I18N] 不支持的语言: ${locale},降级到 ${DEFAULT_LOCALE}`);
            locale = DEFAULT_LOCALE;
        }
        _currentLocale = locale;
        try {
            localStorage.setItem(STORAGE_KEY, locale);
        } catch (e) {
            /* 静默 */
        }
        document.documentElement.lang = locale === 'en' ? 'en' : 'zh-CN';
        _renderDOM();

        // 触发自定义事件,业务代码可监听
        window.dispatchEvent(new CustomEvent('i18n:changed', { detail: { locale } }));
    }

    function getLocale() {
        return _currentLocale;
    }

    // ============================================================
    // [I18N-6] 封装 fetch,自动带 Accept-Language
    // ============================================================
    function fetchWithLang(url, opts) {
        opts = opts || {};
        opts.headers = Object.assign({}, opts.headers, {
            'Accept-Language': _currentLocale === 'en' ? 'en-US,en;q=0.9' : 'zh-CN,zh;q=0.9',
        });
        // 同时通过 URL 参数告知后端
        try {
            const u = new URL(url, window.location.origin);
            if (!u.searchParams.has('lang')) {
                u.searchParams.set('lang', _currentLocale);
            }
            url = `${u.pathname}?${u.searchParams.toString()}`;
        } catch (e) {
            /* URL 解析失败时降级 */
        }
        return fetch(url, opts);
    }

    // ============================================================
    // [I18N-2] 异步初始化(自动等待 DOMContentLoaded)
    // ============================================================
    async function ready() {
        // 1. 推断初始语言
        _currentLocale = _detectLocale();
        document.documentElement.lang = _currentLocale === 'en' ? 'en' : 'zh-CN';

        // 2. 加载语言包
        await _loadMessages();

        // 3. 等待 DOM 就绪
        if (document.readyState === 'loading') {
            await new Promise((resolve) =>
                document.addEventListener('DOMContentLoaded', resolve, { once: true })
            );
        }

        // 4. 首次渲染
        _renderDOM();

        // 5. [I18N-7] 启动 MutationObserver 自动渲染动态 DOM
        try {
            const observer = new MutationObserver((mutations) => {
                let needRender = false;
                for (const m of mutations) {
                    if (m.addedNodes && m.addedNodes.length > 0) {
                        needRender = true;
                        break;
                    }
                }
                if (needRender) _renderDOMDebounced();
            });
            observer.observe(document.body, {
                childList: true,
                subtree: true,
                attributes: false,
                characterData: false,
            });
        } catch (e) {
            console.warn('[I18N] MutationObserver 启动失败,动态 DOM 需手动调用 render():', e);
        }

        console.info(`[I18N] ✅ 初始化完成 | 当前语言: ${_currentLocale}`);
        return _currentLocale;
    }

    // ============================================================
    // [I18N-9] 热重载语言包(开发调试)
    // ============================================================
    async function reload() {
        console.info('[I18N] 热重载语言包...');
        await _loadMessages();
        _renderDOM();
        console.info('[I18N] ✅ 热重载完成');
    }

    // ============================================================
    // 暴露公共 API
    // ============================================================
    global.I18N = {
        ready: ready,
        t: t,
        setLocale: setLocale,
        getLocale: getLocale,
        render: _renderDOM,
        fetch: fetchWithLang,
        reload: reload,
        SUPPORTED_LOCALES: SUPPORTED_LOCALES,
    };
})(window);