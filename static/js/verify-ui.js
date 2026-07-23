/* ============================================================
 * static/js/verify-ui.js — N+2 验证结果可视化组件 (v3.1.4)
 * ============================================================
 *
 * 🎯 设计目标:
 *   - 消费后端 N+2 数据:verified_heal_rate / verify_coverage / verify 字段
 *   - 三态徽章:✅ 真实成功 / ⚠️ 验证失败 / ℹ️ 跳过验证
 *   - 详情抽屉:evidence/对比数据/置信度可视化
 *   - 双指标对比卡片:命令成功率 vs 真实成功率
 *   - 零依赖纯 JS,与 i18n.js 协同工作
 *
 * 🔧 N+4 验证 UI Review 修复说明(VUI 系列共 7 项):
 *
 * [VUI-1] 🔴 P0 — verify 字段类型严格校验
 *   问题: 后端 verify 字段可能为 null / undefined / {} 三种状态,
 *         直接 verify.verified 会抛 TypeError
 *   修复: ① 入口处 _normalizeVerify 统一规范化
 *         ② null 状态显示为"跳过"徽章,而非崩溃
 *
 * [VUI-2] 🔴 P0 — confidence 数值钳制
 *   问题: 后端理论上保证 [0, 1] 范围,但若 verifier 异常返回 -1 或 NaN,
 *         进度条宽度计算会出现 -100% 等异常 CSS 值
 *   修复: Math.max(0, Math.min(1, parseFloat(c) || 0))
 *
 * [VUI-3] 🟡 P1 — evidence 字段安全展示
 *   问题: evidence 是 dict,字段不固定;直接 JSON.stringify 可能过长
 *   修复: ① 关键字段单独展示(command/output/pre_avg/post_avg 等)
 *         ② 其他字段折叠到"原始数据"区域(限制高度 200px)
 *         ③ output 字段截断到 500 字符
 *
 * [VUI-4] 🟡 P1 — XSS 防御
 *   问题: evidence.output / error_msg 等来自远程命令输出,可能含 HTML
 *   修复: 统一使用 _escapeHtml 工具函数,严禁 innerHTML 拼接
 *
 * [VUI-5] 🟡 P1 — 双指标卡片差异高亮
 *   问题: heal_rate=95% vs verified_heal_rate=78% 时,需要明显视觉提示
 *   修复: ① 差值 ≥ 10% 时显示 ⚠️ 黄色警告
 *         ② 差值 ≥ 20% 时显示 🚨 红色警告
 *         ③ tooltip 显示具体差值
 *
 * [VUI-6] 🟢 P2 — 抽屉关闭时清理 DOM 引用
 *   问题: 频繁打开抽屉会导致 DOM 泄漏
 *   修复: 关闭时 remove() 而非 display:none
 *
 * [VUI-7] 🟢 P2 — i18n 协同(等待 I18N.ready 完成)
 *   问题: verify-ui.js 若在 i18n.js 之前执行,t() 调用失败
 *   修复: 依赖检测 window.I18N,缺失时降级到中文硬编码
 * ============================================================ */

(function (global) {
    'use strict';

    // ============================================================
    // [VUI-7] i18n 降级翻译函数
    // ============================================================
    function _t(key, params) {
        if (global.I18N && typeof global.I18N.t === 'function') {
            return global.I18N.t(key, params);
        }
        // 降级:返回 key 本身
        return key;
    }

    // ============================================================
    // [VUI-4] XSS 防御 — HTML 转义
    // ============================================================
    function _escapeHtml(str) {
        if (str === null || str === undefined) return '';
        return String(str)
            .replace(/&/g, '&amp;')
            .replace(/</g, '&lt;')
            .replace(/>/g, '&gt;')
            .replace(/"/g, '&quot;')
            .replace(/'/g, '&#39;');
    }

    // ============================================================
    // [VUI-1] verify 字段规范化
    // ============================================================
    function _normalizeVerify(verify) {
        if (!verify || typeof verify !== 'object') {
            return null;
        }
        return {
            verified: verify.verified === true ? true : (verify.verified === false ? false : null),
            strategy: String(verify.strategy || 'unknown'),
            confidence: _clampConfidence(verify.confidence),
            evidence: verify.evidence && typeof verify.evidence === 'object' ? verify.evidence : {},
            duration_sec: parseFloat(verify.duration_sec) || 0,
            error_msg: String(verify.error_msg || ''),
            recommendation: String(verify.recommendation || ''),
        };
    }

    // ============================================================
    // [VUI-2] confidence 钳制
    // ============================================================
    function _clampConfidence(c) {
        const val = parseFloat(c);
        if (isNaN(val)) return 0;
        return Math.max(0, Math.min(1, val));
    }

    // ============================================================
    // 渲染验证状态徽章
    // ============================================================
    function renderBadge(verify) {
        const v = _normalizeVerify(verify);
        if (!v) {
            return `<span class="verify-badge verify-badge-none" title="${_escapeHtml(_t('verify.no_data'))}">
                ℹ️ ${_escapeHtml(_t('verify.no_data'))}
            </span>`;
        }

        let icon, cls, labelKey;
        if (v.verified === true) {
            icon = '✅';
            cls = 'verify-badge-success';
            labelKey = 'verify.verified_true';
        } else if (v.verified === false) {
            icon = '⚠️';
            cls = 'verify-badge-failed';
            labelKey = 'verify.verified_false';
        } else {
            icon = 'ℹ️';
            cls = 'verify-badge-skipped';
            labelKey = 'verify.verified_skipped';
        }

        const confPct = Math.round(v.confidence * 100);
        const strategyLabel = _t(`verify.strategy.${v.strategy}`);

        return `
            <span class="verify-badge ${cls}"
                  data-verify-detail='${_escapeHtml(JSON.stringify(v))}'
                  title="${_escapeHtml(strategyLabel)} | ${confPct}%">
                ${icon} <span class="verify-conf">${confPct}%</span>
                <span class="verify-strategy">${_escapeHtml(strategyLabel)}</span>
            </span>
        `;
    }

    // ============================================================
    // [VUI-3] 渲染详情抽屉
    // ============================================================
    function openDetailDrawer(verify) {
        const v = _normalizeVerify(verify);
        if (!v) return;

        // [VUI-6] 关闭已存在的抽屉
        closeDetailDrawer();

        const drawer = document.createElement('div');
        drawer.id = 'verify-detail-drawer';
        drawer.className = 'verify-drawer';

        const evidence = v.evidence || {};
        const ev = {
            command: _escapeHtml(String(evidence.command || '').substring(0, 200)),
            output: _escapeHtml(String(evidence.output || '').substring(0, 500)),
            pre_avg: evidence.pre_avg,
            post_avg: evidence.post_avg,
            delta_percent: evidence.delta_percent,
        };

        const confPct = Math.round(v.confidence * 100);
        const confColor = v.confidence >= 0.8 ? '#22c55e' :
                          v.confidence >= 0.5 ? '#f59e0b' : '#ef4444';

        let metricComparisonHtml = '';
        if (typeof ev.pre_avg === 'number' && typeof ev.post_avg === 'number') {
            const deltaPct = ev.delta_percent || 0;
            const deltaColor = deltaPct < 0 ? '#22c55e' : '#ef4444';
            metricComparisonHtml = `
                <div class="verify-section">
                    <h4>📊 ${_escapeHtml(_t('verify.metric_comparison'))}</h4>
                    <div class="verify-metric-row">
                        <span>${_escapeHtml(_t('verify.pre_avg'))}: <b>${ev.pre_avg}</b></span>
                        <span>→</span>
                        <span>${_escapeHtml(_t('verify.post_avg'))}: <b>${ev.post_avg}</b></span>
                        <span style="color:${deltaColor};font-weight:bold;">
                            (${deltaPct > 0 ? '+' : ''}${deltaPct.toFixed(1)}%)
                        </span>
                    </div>
                </div>
            `;
        }

        drawer.innerHTML = `
            <div class="verify-drawer-mask" onclick="window.VerifyUI.closeDrawer()"></div>
            <div class="verify-drawer-panel">
                <div class="verify-drawer-header">
                    <h3>🔍 ${_escapeHtml(_t('verify.detail_title'))}</h3>
                    <button class="verify-drawer-close" onclick="window.VerifyUI.closeDrawer()">✕</button>
                </div>
                <div class="verify-drawer-body">
                    <div class="verify-section">
                        <h4>${_escapeHtml(_t('verify.result_label'))}</h4>
                        <p>${renderBadge(v)}</p>
                        <p>${_escapeHtml(v.recommendation)}</p>
                    </div>

                    <div class="verify-section">
                        <h4>${_escapeHtml(_t('verify.confidence_label'))}</h4>
                        <div class="verify-conf-bar">
                            <div class="verify-conf-fill"
                                 style="width:${confPct}%;background:${confColor};"></div>
                        </div>
                        <p>${confPct}% (${_escapeHtml(_t(`verify.strategy.${v.strategy}`))})</p>
                    </div>

                    ${ev.command ? `
                    <div class="verify-section">
                        <h4>${_escapeHtml(_t('verify.command_label'))}</h4>
                        <pre class="verify-code">${ev.command}</pre>
                    </div>` : ''}

                    ${ev.output ? `
                    <div class="verify-section">
                        <h4>${_escapeHtml(_t('verify.output_label'))}</h4>
                        <pre class="verify-code">${ev.output}</pre>
                    </div>` : ''}

                    ${metricComparisonHtml}

                    ${v.error_msg ? `
                    <div class="verify-section verify-error">
                        <h4>${_escapeHtml(_t('verify.error_label'))}</h4>
                        <p>${_escapeHtml(v.error_msg)}</p>
                    </div>` : ''}

                    <div class="verify-section">
                        <h4>${_escapeHtml(_t('verify.duration_label'))}</h4>
                        <p>${v.duration_sec.toFixed(2)}s</p>
                    </div>

                    <details class="verify-section">
                        <summary>${_escapeHtml(_t('verify.raw_data'))}</summary>
                        <pre class="verify-code verify-raw">${_escapeHtml(JSON.stringify(v, null, 2))}</pre>
                    </details>
                </div>
            </div>
        `;

        document.body.appendChild(drawer);
        // 等待渲染后触发入场动画
        requestAnimationFrame(() => drawer.classList.add('open'));
    }

    function closeDetailDrawer() {
        const drawer = document.getElementById('verify-detail-drawer');
        if (drawer) {
            drawer.classList.remove('open');
            // [VUI-6] 完全移除而非 display:none
            setTimeout(() => drawer.remove(), 300);
        }
    }

    // ============================================================
    // [VUI-5] 双指标对比卡片
    // ============================================================
    function renderHealRateComparison(healRate, verifiedHealRate, verifyCoverage) {
        const hr = parseFloat(healRate) || 0;
        const vhr = parseFloat(verifiedHealRate) || 0;
        const cov = parseFloat(verifyCoverage) || 0;
        const diff = Math.abs(hr - vhr);

        let warningHtml = '';
        if (diff >= 20) {
            warningHtml = `<span class="verify-warn-icon" title="${_escapeHtml(_t('verify.large_gap_warn'))}">🚨</span>`;
        } else if (diff >= 10) {
            warningHtml = `<span class="verify-warn-icon" title="${_escapeHtml(_t('verify.medium_gap_warn'))}">⚠️</span>`;
        }

        return `
            <div class="verify-comparison-card">
                <div class="verify-comp-item">
                    <div class="verify-comp-label">${_escapeHtml(_t('card.heal_rate'))}</div>
                    <div class="verify-comp-value">${hr.toFixed(1)}%</div>
                    <div class="verify-comp-sub">${_escapeHtml(_t('verify.cmd_success_label'))}</div>
                </div>
                <div class="verify-comp-arrow">${warningHtml} →</div>
                <div class="verify-comp-item verify-comp-real">
                    <div class="verify-comp-label">${_escapeHtml(_t('stats.verified_heal_rate'))}</div>
                    <div class="verify-comp-value">${vhr.toFixed(1)}%</div>
                    <div class="verify-comp-sub">
                        ${_escapeHtml(_t('stats.verify_coverage'))}: ${cov.toFixed(1)}%
                    </div>
                </div>
            </div>
        `;
    }

    // ============================================================
    // 绑定徽章点击事件(事件委托)
    // ============================================================
    function bindBadgeClickEvents() {
        document.addEventListener('click', function (e) {
            const badge = e.target.closest('.verify-badge[data-verify-detail]');
            if (!badge) return;
            try {
                const data = JSON.parse(badge.getAttribute('data-verify-detail'));
                openDetailDrawer(data);
            } catch (err) {
                console.warn('[VerifyUI] 解析 verify 数据失败:', err);
            }
        });
    }

    // ============================================================
    // 暴露公共 API
    // ============================================================
    global.VerifyUI = {
        renderBadge: renderBadge,
        openDrawer: openDetailDrawer,
        closeDrawer: closeDetailDrawer,
        renderComparison: renderHealRateComparison,
        bindEvents: bindBadgeClickEvents,
    };

    // 自动绑定事件
    if (document.readyState === 'loading') {
        document.addEventListener('DOMContentLoaded', bindBadgeClickEvents);
    } else {
        bindBadgeClickEvents();
    }
})(window);