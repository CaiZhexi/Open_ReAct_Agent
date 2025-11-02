/**
 * ReAct Agent智能系统前端JavaScript
 */

// 全局变量
let selectedKnowledgeBases = new Set();
let currentKbId = null;
let isLoading = false;
let currentView = 'chat';  // 当前视图：chat 或 kb-management
let sidebarCollapsed = false;
let currentSelectedKbId = null;  // 当前在管理视图中选中的知识库ID
let currentAbortController = null;  // 当前请求的AbortController
let conversationHistory = [];  // 对话历史 [{role: 'user', content: '...'}, {role: 'assistant', content: '...'}]
const MAX_HISTORY_ROUNDS = 3;  // 保留最近3轮对话

// 思维链计时器相关
let thinkingTimers = {};  // 存储每个消息的计时器 {messageId: {startTime, intervalId}}

// 配置Markdown渲染
if (typeof marked !== 'undefined') {
    marked.setOptions({
        highlight: function(code, lang) {
            if (lang && typeof hljs !== 'undefined' && hljs.getLanguage(lang)) {
                return hljs.highlight(code, { language: lang }).value;
            }
            if (typeof hljs !== 'undefined') {
                return hljs.highlightAuto(code).value;
            }
            return code;
        },
        breaks: true,
        gfm: true,
        smartLists: true,
        smartypants: true,
        langPrefix: 'language-'
    });
}

// 页面加载完成后初始化
document.addEventListener('DOMContentLoaded', function() {
    initializeApp();
    setupMarkdownRenderer();

    // 对页面现有内容执行一次LaTeX渲染（例如模板预填内容）
    requestAnimationFrame(() => {
        document.querySelectorAll('.message-content').forEach(element => {
            renderMath(element);
        });
    });
});

/**
 * 初始化应用
 */
async function initializeApp() {
    try {
        // 初始化响应式布局
        initializeResponsiveLayout();
        
        // 检查系统状态
        await checkSystemHealth();
        // 加载知识库列表
        await loadKnowledgeBases();
        // 移除初始化成功弹窗，保持界面简洁
        // showToast('系统初始化完成', 'success');
    } catch (error) {
        console.error('系统初始化失败:', error);
        showToast('系统初始化失败，请刷新页面', 'error');
    }
}

/**
 * 设置Markdown渲染器
 */
function setupMarkdownRenderer() {
    if (typeof marked === 'undefined') {
        console.warn('Marked.js 未加载，Markdown渲染功能不可用');
    }
}

/**
 * 渲染LaTeX数学公式
 */
function renderMath(element) {
    if (!element) return;

    if (element.closest('.python-output-section') || element.closest('.python-code-section')) {
        return;
    }

    if (typeof katex === 'undefined') {
        setTimeout(() => renderMath(element), 120);
        return;
    }

    const IGNORED_SELECTORS = ['pre', 'code', 'kbd', 'samp', '.no-math', '.python-output', '.python-code'];
    // v1.0规范：仅支持 $...$ 和 $$...$$，不支持 \(...\) 和 \[...\]
    const MATH_TOKEN = /(\$\$[\s\S]+?\$\$|\$(?!\$)[^$]+?\$)/g;

    const walker = document.createTreeWalker(
        element,
        NodeFilter.SHOW_TEXT,
        {
            acceptNode(node) {
                if (!node || !node.textContent || !MATH_TOKEN.test(node.textContent)) {
                    return NodeFilter.FILTER_SKIP;
                }
                const parent = node.parentElement;
                if (!parent) return NodeFilter.FILTER_REJECT;
                for (const selector of IGNORED_SELECTORS) {
                    if (parent.matches(selector) || parent.closest(selector)) {
                        return NodeFilter.FILTER_SKIP;
                    }
                }
                return NodeFilter.FILTER_ACCEPT;
            }
        }
    );

    const targetNodes = [];
    while (walker.nextNode()) {
        targetNodes.push(walker.currentNode);
    }

    targetNodes.forEach(node => {
        const text = node.textContent;
        if (!text) return;

        const fragments = [];
        let lastIndex = 0;
        MATH_TOKEN.lastIndex = 0;
        let match;

        while ((match = MATH_TOKEN.exec(text)) !== null) {
            const matchIndex = match.index;
            if (matchIndex > lastIndex) {
                fragments.push({ type: 'text', value: text.slice(lastIndex, matchIndex) });
            }
            fragments.push({ type: 'math', value: match[0] });
            lastIndex = MATH_TOKEN.lastIndex;
        }

        if (lastIndex < text.length) {
            fragments.push({ type: 'text', value: text.slice(lastIndex) });
        }

        if (fragments.length <= 1) {
            return;
        }

        const frag = document.createDocumentFragment();

        fragments.forEach(fragment => {
            if (fragment.type === 'text') {
                frag.appendChild(document.createTextNode(fragment.value));
                return;
            }

            // v1.0规范：只处理 $...$ 和 $$...$$
            let isBlock = false;
            let rawExpr = '';

            if (fragment.value.startsWith('$$') && fragment.value.endsWith('$$')) {
                isBlock = true;
                rawExpr = fragment.value.slice(2, -2);
            } else {
                // 行内公式 $...$
                rawExpr = fragment.value.slice(1, -1);
            }

            const expr = rawExpr.trim();

            if (!expr) {
                frag.appendChild(document.createTextNode(fragment.value));
                return;
            }

            const wrapper = document.createElement(isBlock ? 'div' : 'span');
            wrapper.className = isBlock ? 'math-block' : 'math-inline';

            try {
                katex.render(expr, wrapper, {
                    throwOnError: false,
                    displayMode: isBlock,
                    strict: 'ignore'
                });
            } catch (error) {
                console.error('LaTeX 渲染失败:', error);
                wrapper.textContent = fragment.value;
            }

            frag.appendChild(wrapper);
        });

        node.parentNode.replaceChild(frag, node);
    });
}

/**
 * 切换视图
 */
function switchView(viewName) {
    currentView = viewName;
    
    // 更新导航活动状态
    document.querySelectorAll('.nav-item').forEach(item => {
        item.classList.remove('active');
    });
    event.target.closest('.nav-item').classList.add('active');
    
    // 显示/隐藏视图
    document.getElementById('chat-view').style.display = viewName === 'chat' ? 'flex' : 'none';
    document.getElementById('kb-management-view').style.display = viewName === 'kb-management' ? 'flex' : 'none';
    
    // 如果切换到资源管理，加载知识库网格
    if (viewName === 'kb-management') {
        loadKnowledgeBasesGrid();
    }
}

/**
 * 切换侧边栏
 */
function toggleSidebar() {
    sidebarCollapsed = !sidebarCollapsed;
    const sidebar = document.getElementById('sidebar');
    const mainContent = document.getElementById('main-content');
    
    // 检查是否为移动端
    const isMobile = window.innerWidth <= 768;
    
    if (isMobile) {
        // 移动端使用 show/hide 逻辑
        if (sidebarCollapsed) {
            sidebar.classList.remove('show');
        } else {
            sidebar.classList.add('show');
        }
    } else {
        // 桌面端使用 collapsed 逻辑
        if (sidebarCollapsed) {
            sidebar.classList.add('collapsed');
            mainContent.classList.add('sidebar-collapsed');
        } else {
            sidebar.classList.remove('collapsed');
            mainContent.classList.remove('sidebar-collapsed');
        }
    }
}

/**
 * 初始化响应式布局
 */
function initializeResponsiveLayout() {
    const handleResize = () => {
        const isMobile = window.innerWidth <= 768;
        const sidebar = document.getElementById('sidebar');
        const mainContent = document.getElementById('main-content');
        
        if (isMobile) {
            // 移动端：默认隐藏侧边栏
            sidebar.classList.remove('collapsed', 'show');
            mainContent.classList.remove('sidebar-collapsed');
            sidebarCollapsed = true;
        } else {
            // 桌面端：默认显示侧边栏
            sidebar.classList.remove('show');
            if (sidebarCollapsed) {
                sidebar.classList.add('collapsed');
                mainContent.classList.add('sidebar-collapsed');
            } else {
                sidebar.classList.remove('collapsed');
                mainContent.classList.remove('sidebar-collapsed');
            }
        }
    };
    
    // 初始化
    handleResize();
    
    // 监听窗口大小变化
    window.addEventListener('resize', handleResize);
    
    // 移动端点击主内容区域时隐藏侧边栏
    document.getElementById('main-content')?.addEventListener('click', (e) => {
        const isMobile = window.innerWidth <= 768;
        const sidebar = document.getElementById('sidebar');
        
        if (isMobile && sidebar.classList.contains('show')) {
            sidebar.classList.remove('show');
            sidebarCollapsed = true;
        }
    });
}

/**
 * 自动调整文本框高度
 */
function autoResize(textarea) {
    textarea.style.height = 'auto';
    textarea.style.height = Math.min(textarea.scrollHeight, 200) + 'px';
}

/**
 * 检查系统健康状态
 */
async function checkSystemHealth() {
    try {
        const response = await fetch('/api/health');
        const data = await response.json();
        
        if (data.status === 'ok') {
            document.getElementById('system-status').innerHTML = 
                '<i class="fas fa-circle text-success"></i> 系统正常';
        } else {
            throw new Error('系统状态异常');
        }
    } catch (error) {
        document.getElementById('system-status').innerHTML = 
            '<i class="fas fa-circle text-danger"></i> 系统异常';
        throw error;
    }
}

/**
 * 显示Toast消息
 */
function showToast(message, type = 'info') {
    const toast = document.getElementById('toast');
    const toastTitle = document.getElementById('toast-title');
    const toastBody = document.getElementById('toast-body');
    const toastIcon = document.getElementById('toast-icon');
    
    // 设置图标和标题
    switch (type) {
        case 'success':
            toastIcon.className = 'fas fa-check-circle text-success me-2';
            toastTitle.textContent = '成功';
            break;
        case 'error':
            toastIcon.className = 'fas fa-exclamation-circle text-danger me-2';
            toastTitle.textContent = '错误';
            break;
        case 'warning':
            toastIcon.className = 'fas fa-exclamation-triangle text-warning me-2';
            toastTitle.textContent = '警告';
            break;
        default:
            toastIcon.className = 'fas fa-info-circle text-info me-2';
            toastTitle.textContent = '信息';
    }
    
    toastBody.textContent = message;
    
    const bsToast = new bootstrap.Toast(toast);
    bsToast.show();
}

/**
 * 显示/隐藏加载状态
 */
function toggleLoading(show) {
    const overlay = document.getElementById('loading-overlay');
    overlay.style.display = show ? 'flex' : 'none';
    isLoading = show;
}

/**
 * 知识库相关函数
 */

/**
 * 加载知识库列表
 */
async function loadKnowledgeBases() {
    try {
        const response = await fetch('/api/kb/list');
        const data = await response.json();
        
        if (data.success) {
            renderKnowledgeBases(data.data);
            renderKnowledgeBasesSidebar(data.data);  // 同时渲染侧边栏
        } else {
            throw new Error(data.message);
        }
    } catch (error) {
        console.error('加载知识库失败:', error);
        showToast('加载知识库失败', 'error');
    }
}

/**
 * 渲染侧边栏知识库列表
 */
function renderKnowledgeBasesSidebar(knowledgeBases) {
    const container = document.getElementById('kb-list-sidebar');
    
    if (!container) return;
    
    if (knowledgeBases.length === 0) {
        container.innerHTML = `
            <div class="text-muted small text-center py-2">
                暂无知识库
            </div>
        `;
        return;
    }
    
    container.innerHTML = knowledgeBases.map(kb => {
        const status = kb.status || 'ready';
        const isReady = status === 'ready';
        const isSelected = selectedKnowledgeBases.has(kb.id);
        
        let statusIcon = '';
        if (isReady) {
            statusIcon = '<i class="fas fa-check-circle text-success"></i>';
        } else {
            statusIcon = '<i class="fas fa-spinner fa-spin text-warning"></i>';
        }
        
        return `
            <div class="kb-list-item ${isSelected ? 'selected' : ''}" 
                 onclick="toggleKnowledgeBaseSelection(${kb.id}, '${escapeHtml(kb.name)}', ${isReady})">
                <div class="kb-list-item-name">${escapeHtml(kb.name)}</div>
                <div class="kb-list-item-status">${statusIcon}</div>
            </div>
        `;
    }).join('');
}

/**
 * 切换知识库选择（用于问答）
 */
function toggleKnowledgeBaseSelection(kbId, kbName, isReady) {
    if (!isReady) {
        showToast('该知识库正在处理中，请等待完成后再使用', 'warning');
        return;
    }
    
    if (selectedKnowledgeBases.has(kbId)) {
        selectedKnowledgeBases.delete(kbId);
    } else {
        selectedKnowledgeBases.add(kbId);
    }
    
    // 更新侧边栏显示
    loadKnowledgeBases();  // 重新渲染以更新选中状态
}

/**
 * 渲染知识库列表（已废弃，保留兼容性）
 * 新版本使用 renderKnowledgeBasesSidebar 和 renderKnowledgeBasesGrid
 */
function renderKnowledgeBases(knowledgeBases) {
    const container = document.getElementById('knowledge-bases-list');
    
    // 容器不存在时直接返回（新设计中不需要这个容器）
    if (!container) {
        return;
    }
    
    if (knowledgeBases.length === 0) {
        container.innerHTML = `
            <div class="text-center text-muted py-3">
                <i class="fas fa-database fa-2x mb-2"></i>
                <div>暂无知识库</div>
            </div>
        `;
        return;
    }
    
    container.innerHTML = knowledgeBases.map(kb => {
        const status = kb.status || 'ready';
        const isReady = status === 'ready';
        const isProcessing = status === 'processing';
        
        let statusBadge = '';
        let progressBar = '';
        
        if (isProcessing) {
            const progress = Math.round((kb.processing_progress || 0) * 100);
            statusBadge = `<span class="badge bg-warning ms-2">处理中 ${progress}%</span>`;
            
            if (kb.queue_info) {
                const { processed, total_pending } = kb.queue_info;
                progressBar = `
                    <div class="progress mt-2" style="height: 4px;">
                        <div class="progress-bar bg-warning" style="width: ${progress}%"></div>
                    </div>
                    <div class="small text-muted mt-1">
                        已处理: ${processed}/${total_pending} 个文档
                    </div>
                `;
            }
        } else if (isReady) {
            statusBadge = `<span class="badge bg-success ms-2">就绪</span>`;
        }
        
        const kbClass = isReady ? '' : 'kb-processing';
        
        return `
            <div class="kb-item list-group-item ${kbClass}" data-kb-id="${kb.id}" data-status="${status}" onclick="selectKnowledgeBase(${kb.id})">
                <div class="kb-info">
                    <div class="kb-name">
                        ${escapeHtml(kb.name)}
                        ${statusBadge}
                    </div>
                    ${kb.description ? `<div class="kb-description">${escapeHtml(kb.description)}</div>` : ''}
                    <div class="kb-stats">
                        <span><i class="fas fa-file"></i> ${kb.document_count || 0}个文档</span>
                        <span class="ms-2"><i class="fas fa-vector-square"></i> ${kb.vector_stats?.total_vectors || 0}个向量</span>
                    </div>
                    ${progressBar}
                </div>
                <div class="kb-actions">
                    <button class="btn btn-sm btn-outline-primary" onclick="event.stopPropagation(); editKnowledgeBase(${kb.id})" title="编辑">
                        <i class="fas fa-edit"></i>
                    </button>
                    <button class="btn btn-sm btn-outline-danger" onclick="event.stopPropagation(); deleteKnowledgeBase(${kb.id}, '${escapeHtml(kb.name)}')" title="删除" ${isProcessing ? 'disabled' : ''}>
                        <i class="fas fa-trash"></i>
                    </button>
                </div>
            </div>
        `;
    }).join('');
}

/**
 * 选择知识库
 */
async function selectKnowledgeBase(kbId) {
    try {
        // 获取知识库状态
        const kbElement = document.querySelector(`[data-kb-id="${kbId}"]`);
        const status = kbElement?.dataset.status || 'ready';
        
        // 更新UI状态
        document.querySelectorAll('.kb-item').forEach(item => {
            item.classList.remove('active');
        });
        kbElement?.classList.add('active');
        
        currentKbId = kbId;
        
        // 根据知识库状态启用/禁用操作按钮
        const isReady = status === 'ready';
        document.getElementById('upload-btn').disabled = false; // 上传总是可用
        document.getElementById('create-doc-btn').disabled = !isReady; // 创建文档需要就绪状态

        // 显示/隐藏状态卡片
        const statusCard = document.getElementById('kb-status-card');
        if (statusCard) {
            if (status === 'processing') {
                statusCard.style.display = 'block';
            } else {
                statusCard.style.display = 'none';
            }
        }
        
        // 加载文档列表
        await loadDocuments(kbId);
        
        // 加载知识库统计
        await loadKnowledgeBaseStats(kbId);
        
        // 启动处理状态监控
        if (status === 'processing') {
            startProcessingStatusMonitor(kbId);
        }
        
        // 如果知识库就绪且未被选中用于问答，添加到选中列表
        if (isReady && !selectedKnowledgeBases.has(kbId)) {
            selectedKnowledgeBases.add(kbId);
            updateSelectedKnowledgeBases();
        }
        
        // 如果知识库正在处理，从问答列表中移除
        if (!isReady && selectedKnowledgeBases.has(kbId)) {
            selectedKnowledgeBases.delete(kbId);
            updateSelectedKnowledgeBases();
            showToast(`知识库"${kbElement?.querySelector('.kb-name')?.textContent || ''}"正在处理中，已从问答列表中移除`, 'info');
        }
        
    } catch (error) {
        console.error('选择知识库失败:', error);
        showToast('选择知识库失败', 'error');
    }
}

/**
 * 更新处理进度显示
 */
function updateProcessingDisplay(kbId, status, progress, processedDocs, totalDocs) {
    // 更新知识库列表中的进度显示
    const kbElement = document.querySelector(`[data-kb-id="${kbId}"]`);
    if (kbElement) {
        const progressBar = kbElement.querySelector('.progress-bar');
        const progressText = kbElement.querySelector('.small.text-muted');

        if (progressBar && progressText) {
            const progressPercent = Math.round(progress * 100);
            progressBar.style.width = progressPercent + '%';
            progressText.textContent = `已处理: ${processedDocs}/${totalDocs} 个文档`;
        }
    }

    // 如果这是当前选中的知识库，更新顶部状态显示
    if (currentKbId === kbId) {
        updateCurrentKbStatus(status, progress, processedDocs, totalDocs);
    }
}

/**
 * 更新当前知识库状态显示
 */
function updateCurrentKbStatus(status, progress, processedDocs, totalDocs) {
    const statusElement = document.querySelector('.kb-processing-status');
    if (!statusElement) return;

    const progressPercent = Math.round(progress * 100);

    if (status === 'processing') {
        statusElement.innerHTML = `
            <div class="d-flex align-items-center">
                <div class="spinner-border spinner-border-sm me-2" role="status">
                    <span class="visually-hidden">处理中...</span>
                </div>
                <span>处理中: ${processedDocs}/${totalDocs} (${progressPercent}%)</span>
            </div>
            <div class="progress mt-1" style="height: 4px;">
                <div class="progress-bar bg-warning progress-bar-striped progress-bar-animated"
                     style="width: ${progressPercent}%"></div>
            </div>
        `;
    }
}

/**
 * 启动处理状态监控
 */
function startProcessingStatusMonitor(kbId) {
    // 避免重复监控
    if (window.processingMonitors && window.processingMonitors[kbId]) {
        return;
    }
    
    if (!window.processingMonitors) {
        window.processingMonitors = {};
    }
    
    window.processingMonitors[kbId] = setInterval(async () => {
        try {
            const response = await fetch(`/api/docs/processing-status/${kbId}`);
            const data = await response.json();

            if (data.success) {
                const status = data.data.status;
                const progress = data.data.progress || 0;
                const processedDocs = data.data.processed_docs || 0;
                const totalDocs = data.data.total_pending_docs || 0;

                // 更新界面显示的进度信息
                updateProcessingDisplay(kbId, status, progress, processedDocs, totalDocs);

                if (status === 'ready') {
                    // 处理完成，停止监控并刷新界面
                    clearInterval(window.processingMonitors[kbId]);
                    delete window.processingMonitors[kbId];

                    showToast(`知识库"${data.data.kb_name}"处理完成！`, 'success');

                    // 刷新知识库列表
                    await loadKnowledgeBases();

                    // 如果是当前选中的知识库，刷新相关信息
                    if (currentKbId === kbId) {
                        await loadDocuments(kbId);
                        await loadKnowledgeBaseStats(kbId);

                        // 自动添加到问答列表
                        if (!selectedKnowledgeBases.has(kbId)) {
                            selectedKnowledgeBases.add(kbId);
                            updateSelectedKnowledgeBases();
                        }
                    }
                }
            }
        } catch (error) {
            console.error('监控处理状态失败:', error);
        }
    }, 1000); // 每1秒检查一次
}

/**
 * 更新选中的知识库显示
 */
function updateSelectedKnowledgeBases() {
    const container = document.getElementById('selected-kbs');
    
    if (selectedKnowledgeBases.size === 0) {
        container.innerHTML = '<div class="text-muted text-center py-2">请选择知识库</div>';
        return;
    }
    
    // 获取知识库名称
    const kbElements = document.querySelectorAll('.kb-item');
    const kbNames = {};
    kbElements.forEach(el => {
        const id = parseInt(el.dataset.kbId);
        const name = el.querySelector('.kb-name').textContent;
        kbNames[id] = name;
    });
    
    container.innerHTML = Array.from(selectedKnowledgeBases).map(kbId => `
        <span class="selected-kb-badge">
            <i class="fas fa-database me-1"></i>
            ${escapeHtml(kbNames[kbId] || '未知')}
            <button class="remove-btn" onclick="removeSelectedKnowledgeBase(${kbId})">
                <i class="fas fa-times"></i>
            </button>
        </span>
    `).join('');
}

/**
 * 移除选中的知识库
 */
function removeSelectedKnowledgeBase(kbId) {
    selectedKnowledgeBases.delete(kbId);
    updateSelectedKnowledgeBases();
}

/**
 * 显示创建知识库模态框
 */
function showCreateKbModal() {
    const modal = new bootstrap.Modal(document.getElementById('createKbModal'));
    document.getElementById('create-kb-form').reset();
    modal.show();
}

/**
 * 创建知识库
 */
async function createKnowledgeBase() {
    const name = document.getElementById('kb-name').value.trim();
    const description = document.getElementById('kb-description').value.trim();
    
    if (!name) {
        showToast('请输入知识库名称', 'warning');
        return;
    }
    
    try {
        toggleLoading(true);
        
        const response = await fetch('/api/kb/create', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json'
            },
            body: JSON.stringify({ name, description })
        });
        
        const data = await response.json();
        
        if (data.success) {
            showToast('知识库创建成功', 'success');
            bootstrap.Modal.getInstance(document.getElementById('createKbModal')).hide();
            await loadKnowledgeBases();
        } else {
            throw new Error(data.message);
        }
    } catch (error) {
        console.error('创建知识库失败:', error);
        showToast(error.message || '创建知识库失败', 'error');
    } finally {
        toggleLoading(false);
    }
}

/**
 * 删除知识库
 */
async function deleteKnowledgeBase(kbId, name) {
    if (!confirm(`确定要删除知识库"${name}"吗？此操作不可撤销，将同时删除所有相关文档。`)) {
        return;
    }
    
    try {
        toggleLoading(true);
        
        const response = await fetch(`/api/kb/${kbId}/delete`, {
            method: 'DELETE'
        });
        
        const data = await response.json();
        
        if (data.success) {
            showToast('知识库删除成功', 'success');
            
            // 从选中列表中移除
            selectedKnowledgeBases.delete(kbId);
            updateSelectedKnowledgeBases();
            
            // 如果是当前选中的知识库，清空右侧内容
            if (currentKbId === kbId) {
                currentKbId = null;
                document.getElementById('documents-list').innerHTML = '<div class="text-muted text-center py-3">请选择知识库</div>';
                document.getElementById('kb-stats').innerHTML = '<div class="text-muted text-center">请选择知识库查看统计</div>';
                document.getElementById('upload-btn').disabled = true;
                document.getElementById('create-doc-btn').disabled = true;
            }
            
            await loadKnowledgeBases();
        } else {
            throw new Error(data.message);
        }
    } catch (error) {
        console.error('删除知识库失败:', error);
        showToast(error.message || '删除知识库失败', 'error');
    } finally {
        toggleLoading(false);
    }
}

/**
 * 文档相关函数
 */

/**
 * 加载文档列表
 */
async function loadDocuments(kbId) {
    try {
        const response = await fetch(`/api/docs/list/${kbId}`);
        const data = await response.json();
        
        if (data.success) {
            renderDocuments(data.data);
        } else {
            throw new Error(data.message);
        }
    } catch (error) {
        console.error('加载文档失败:', error);
        document.getElementById('documents-list').innerHTML = 
            '<div class="text-center text-danger py-3">加载文档失败</div>';
    }
}

/**
 * 渲染文档列表
 */
function renderDocuments(documents) {
    const container = document.getElementById('documents-list');
    
    if (documents.length === 0) {
        container.innerHTML = `
            <div class="text-center text-muted py-3">
                <i class="fas fa-file-text fa-2x mb-2"></i>
                <div>暂无文档</div>
            </div>
        `;
        return;
    }
    
    container.innerHTML = documents.map(doc => `
        <div class="doc-item">
            <div class="doc-name">${escapeHtml(doc.name)}</div>
            <div class="doc-meta">
                <span>
                    <i class="fas fa-file"></i> ${doc.file_type || 'txt'}
                    <span class="ms-2"><i class="fas fa-cubes"></i> ${doc.chunk_count || 0}块</span>
                    <span class="ms-2"><i class="fas fa-clock"></i> ${formatDate(doc.created_at)}</span>
                </span>
                <div class="doc-actions">
                    <button class="btn btn-sm btn-outline-info" onclick="viewDocument(${doc.id})" title="查看">
                        <i class="fas fa-eye"></i>
                    </button>
                    <button class="btn btn-sm btn-outline-danger" onclick="deleteDocument(${doc.id}, '${escapeHtml(doc.name)}')" title="删除">
                        <i class="fas fa-trash"></i>
                    </button>
                </div>
            </div>
        </div>
    `).join('');
}

/**
 * 显示上传模态框
 */
function showUploadModal() {
    if (!currentKbId) {
        showToast('请先选择知识库', 'warning');
        return;
    }
    
    const modal = new bootstrap.Modal(document.getElementById('uploadModal'));
    document.getElementById('upload-form').reset();
    
    // 重置文件预览和进度
    document.getElementById('selected-files-list').style.display = 'none';
    document.getElementById('upload-progress').style.display = 'none';
    document.getElementById('files-preview').innerHTML = '';
    
    // 添加文件选择监听器
    const fileInput = document.getElementById('file-input');
    fileInput.addEventListener('change', handleFileSelection);
    
    modal.show();
}

/**
 * 处理文件选择
 */
function handleFileSelection(event) {
    const files = Array.from(event.target.files);
    const previewContainer = document.getElementById('files-preview');
    const filesList = document.getElementById('selected-files-list');
    
    if (files.length === 0) {
        filesList.style.display = 'none';
        return;
    }
    
    // 显示选中的文件
    previewContainer.innerHTML = files.map((file, index) => {
        const sizeStr = (file.size / (1024 * 1024)).toFixed(2);
        const isValidSize = file.size <= 16 * 1024 * 1024; // 16MB限制
        const extension = file.name.split('.').pop()?.toLowerCase() || '';
        const isValidType = ['txt', 'pdf', 'docx', 'xlsx', 'md'].includes(extension);
        
        return `
            <div class="d-flex justify-content-between align-items-center py-1 ${!isValidSize || !isValidType ? 'text-danger' : ''}">
                <div class="flex-grow-1">
                    <i class="fas fa-file me-2"></i>
                    <span>${escapeHtml(file.name)}</span>
                    <small class="text-muted ms-2">(${sizeStr}MB)</small>
                </div>
                <div>
                    ${!isValidType ? '<span class="badge bg-danger">格式不支持</span>' : ''}
                    ${!isValidSize ? '<span class="badge bg-danger">文件过大</span>' : ''}
                    ${isValidType && isValidSize ? '<span class="badge bg-success">有效</span>' : ''}
                </div>
            </div>
        `;
    }).join('');
    
    filesList.style.display = 'block';
    
    // 更新上传按钮文本
    const validFiles = files.filter(file => {
        const extension = file.name.split('.').pop()?.toLowerCase() || '';
        const isValidType = ['txt', 'pdf', 'docx', 'xlsx', 'md'].includes(extension);
        const isValidSize = file.size <= 16 * 1024 * 1024;
        return isValidType && isValidSize;
    });
    
    const uploadBtn = document.getElementById('upload-submit');
    if (validFiles.length > 0) {
        uploadBtn.innerHTML = `<i class="fas fa-cloud-upload-alt"></i> 上传 ${validFiles.length} 个文件`;
        uploadBtn.disabled = false;
    } else {
        uploadBtn.innerHTML = '<i class="fas fa-cloud-upload-alt"></i> 没有有效文件';
        uploadBtn.disabled = true;
    }
}

/**
 * 批量上传文档
 */
async function uploadDocuments() {
    const fileInput = document.getElementById('file-input');
    const files = Array.from(fileInput.files);
    
    if (files.length === 0) {
        showToast('请选择文件', 'warning');
        return;
    }
    
    if (!currentKbId) {
        showToast('请先选择知识库', 'warning');
        return;
    }
    
    try {
        // 显示进度条
        const progressContainer = document.getElementById('upload-progress');
        const progressBar = document.getElementById('progress-bar');
        const progressText = document.getElementById('progress-text');
        const uploadBtn = document.getElementById('upload-submit');
        const cancelBtn = document.getElementById('cancel-upload');
        
        progressContainer.style.display = 'block';
        uploadBtn.disabled = true;
        cancelBtn.textContent = '关闭';
        
        // 准备FormData
        const formData = new FormData();
        files.forEach(file => {
            formData.append('files', file);
        });
        
        // 发送请求
        const response = await fetch(`/api/docs/batch-upload/${currentKbId}`, {
            method: 'POST',
            body: formData
        });
        
        const data = await response.json();
        
        if (data.success) {
            progressBar.style.width = '100%';
            progressText.textContent = '100%';
            
            let message = `成功提交 ${data.queued_files} 个文档到处理队列`;
            if (data.skipped_files > 0) {
                message += `，跳过 ${data.skipped_files} 个文件`;
            }
            
            showToast(message, 'success');
            
            // 显示警告信息
            if (data.warnings && data.warnings.length > 0) {
                setTimeout(() => {
                    showToast(`跳过的文件：${data.warnings.join(', ')}`, 'warning');
                }, 2000);
            }
            
            // 延迟关闭模态框
            setTimeout(() => {
                bootstrap.Modal.getInstance(document.getElementById('uploadModal')).hide();
            }, 1500);
            
            // 刷新知识库列表（显示处理状态）
            await loadKnowledgeBases();
            
            // 如果是当前选中的知识库，开始监控处理状态
            if (currentKbId) {
                startProcessingStatusMonitor(currentKbId);
            }
            
        } else {
            throw new Error(data.message);
        }
    } catch (error) {
        console.error('批量上传失败:', error);
        showToast(error.message || '批量上传失败', 'error');
        
        // 重置界面
        document.getElementById('upload-progress').style.display = 'none';
        document.getElementById('upload-submit').disabled = false;
    }
}

// 保持原有单文件上传函数的兼容性
async function uploadDocument() {
    return uploadDocuments();
}

/**
 * 显示创建文档模态框
 */
function showCreateDocModal() {
    if (!currentKbId) {
        showToast('请先选择知识库', 'warning');
        return;
    }
    
    const modal = new bootstrap.Modal(document.getElementById('createDocModal'));
    document.getElementById('create-doc-form').reset();
    modal.show();
}

/**
 * 创建文档
 */
async function createDocument() {
    const name = document.getElementById('doc-name').value.trim();
    const content = document.getElementById('doc-content').value.trim();
    
    if (!name || !content) {
        showToast('请填写文档名称和内容', 'warning');
        return;
    }
    
    if (!currentKbId) {
        showToast('请先选择知识库', 'warning');
        return;
    }
    
    try {
        toggleLoading(true);
        
        const response = await fetch(`/api/docs/create/${currentKbId}`, {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json'
            },
            body: JSON.stringify({ name, content })
        });
        
        const data = await response.json();
        
        if (data.success) {
            showToast('文档创建成功', 'success');
            bootstrap.Modal.getInstance(document.getElementById('createDocModal')).hide();
            await loadDocuments(currentKbId);
            await loadKnowledgeBaseStats(currentKbId);
        } else {
            throw new Error(data.message);
        }
    } catch (error) {
        console.error('创建文档失败:', error);
        showToast(error.message || '创建文档失败', 'error');
    } finally {
        toggleLoading(false);
    }
}

/**
 * 删除文档
 */
async function deleteDocument(docId, name) {
    if (!confirm(`确定要删除文档"${name}"吗？`)) {
        return;
    }
    
    try {
        toggleLoading(true);
        
        const response = await fetch(`/api/docs/${docId}/delete`, {
            method: 'DELETE'
        });
        
        const data = await response.json();
        
        if (data.success) {
            showToast('文档删除成功', 'success');
            await loadDocuments(currentKbId);
            await loadKnowledgeBaseStats(currentKbId);
        } else {
            throw new Error(data.message);
        }
    } catch (error) {
        console.error('删除文档失败:', error);
        showToast(error.message || '删除文档失败', 'error');
    } finally {
        toggleLoading(false);
    }
}

/**
 * 加载知识库统计信息
 */
async function loadKnowledgeBaseStats(kbId) {
    try {
        const response = await fetch(`/api/kb/${kbId}/stats`);
        const data = await response.json();
        
        if (data.success) {
            renderKnowledgeBaseStats(data.data);
        } else {
            throw new Error(data.message);
        }
    } catch (error) {
        console.error('加载统计信息失败:', error);
        document.getElementById('kb-stats').innerHTML = 
            '<div class="text-center text-danger">加载统计失败</div>';
    }
}

/**
 * 渲染知识库统计信息
 */
function renderKnowledgeBaseStats(stats) {
    const container = document.getElementById('kb-stats');
    
    container.innerHTML = `
        <div class="stats-grid">
            <div class="stat-item">
                <div class="stat-value">${stats.document_count}</div>
                <div class="stat-label">文档数量</div>
            </div>
            <div class="stat-item">
                <div class="stat-value">${stats.total_chunks}</div>
                <div class="stat-label">文档块</div>
            </div>
            <div class="stat-item">
                <div class="stat-value">${stats.vector_stats.total_vectors}</div>
                <div class="stat-label">向量数量</div>
            </div>
            <div class="stat-item">
                <div class="stat-value">${stats.vector_stats.dimensions}</div>
                <div class="stat-label">向量维度</div>
            </div>
        </div>
        <div class="mt-3">
            <small class="text-muted">
                知识库: ${escapeHtml(stats.kb_info.name)}<br>
                创建时间: ${formatDate(stats.kb_info.created_at)}
            </small>
        </div>
    `;
}

/**
 * 问答相关函数
 */

/**
 * 发送问题
 */
async function sendQuestion() {
    const input = document.getElementById('question-input');
    const question = input.value.trim();
    
    if (!question) {
        showToast('请输入问题', 'warning');
        return;
    }
    
    // 检查是否使用 Lite 模式
    const useLite = document.getElementById('use-lite-mode');
    const useLiteMode = useLite ? useLite.checked : false;
    
    // Agent 模式允许不选择知识库（支持纯计算/问候等场景）
    // 无论是默认模式还是 Lite 模式都支持
    
    if (isLoading) {
        return;
    }
    
    // 清空输入框
    input.value = '';
    
    // 添加用户消息
    addChatMessage(question, 'user');
    
    // 滚动到底部
    scrollChatToBottom();
    
    // 新版本默认使用 Agentic 模式（带流式输出）
    const agenticMode = document.getElementById('agentic-mode');
    const useAgenticMode = agenticMode ? agenticMode.checked : true;
    
    // Lite 模式状态已在前面检查时获取
    
    // Agentic 模式使用流式输出
    await sendQuestionNonStream(question, useAgenticMode, useLiteMode);
}

/**
 * 非流式问答
 */
async function sendQuestionNonStream(question, useAgenticMode = false, useLiteMode = false) {
    try {
        toggleSendButton(false);
        
        // 对于Agentic模式且支持流式输出，使用流式处理
        if (useAgenticMode) {
            await sendAgenticQuestionStream(question, useLiteMode);
            return;
        }
        
        // 添加加载消息
        const loadingId = addChatMessage('正在思考中...', 'assistant', true);
        
        // 选择API端点
        const endpoint = '/api/rag/chat';
        const requestBody = {
            question: question,
            kb_ids: Array.from(selectedKnowledgeBases),
            stream: false,
            top_k: 5
        };
        
        const response = await fetch(endpoint, {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json'
            },
            body: JSON.stringify(requestBody)
        });
        
        const data = await response.json();
        
        // 移除加载消息
        removeLoadingMessage(loadingId);
        
        if (data.success) {
            const sources = data.data.sources || [];
            addChatMessage(data.data.answer, 'assistant', false, sources, null);
        } else {
            throw new Error(data.message);
        }
    } catch (error) {
        console.error('问答失败:', error);
        addChatMessage('抱歉，出现了错误：' + error.message, 'assistant');
        showToast('问答失败', 'error');
    } finally {
        toggleSendButton(true);
        scrollChatToBottom();
    }
}

/**
 * ReAct Agent 流式对话
 */
async function sendAgenticQuestionStream(question, useLiteMode = false) {
    let assistantMessageId = null;
    let toolCallsContainer = null;
    let sources = [];
    let processInfo = {
        confidence: 0,
        confidenceReason: '',
        usedRetrieval: false,
        processLog: {}
    };
    
    // 创建新的AbortController
    currentAbortController = new AbortController();
    
    try {
        toggleSendButton(false);
        
        // 添加助手消息容器
        assistantMessageId = addChatMessage('', 'assistant');
        
        // 添加工具调用展示区域
        toolCallsContainer = addToolCallsContainer(assistantMessageId);
        
        // 根据 Lite 标志选择API端点和参数
        // 默认使用 V2 API，如果勾选 Lite 则使用 V1 Lite API
        const apiEndpoint = useLiteMode ? '/api/rag/agentic-chat' : '/api/v2/chat';
        
        // 获取最近N轮对话历史（只保留用户问题和助手回答）
        const recentHistory = conversationHistory.slice(-MAX_HISTORY_ROUNDS * 2);
        
        // 获取选中的文件列表
        const selectedFileNames = getSelectedFileNames();
        
        // 构建请求体（默认模式使用 query 参数，Lite 模式使用 question 参数）
        const requestBody = useLiteMode ? {
            question: question,
            kb_ids: Array.from(selectedKnowledgeBases),
            use_lite: true,  // 启用 Lite 模式
            stream: true,
            selected_files: selectedFileNames  // 添加选中的文件
        } : {
            query: question,
            kb_ids: Array.from(selectedKnowledgeBases),
            stream: true,
            history: recentHistory,  // 添加对话历史
            selected_files: selectedFileNames  // 添加选中的文件
        };
        
        // 发送请求
        const response = await fetch(apiEndpoint, {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json'
            },
            body: JSON.stringify(requestBody),
            signal: currentAbortController.signal  // 添加取消信号
        });
        
        if (!response.ok) {
            throw new Error('网络请求失败');
        }
        
        const reader = response.body.getReader();
        const decoder = new TextDecoder();
        let buffer = '';
        
        while (true) {
            const { done, value } = await reader.read();
            
            if (done) break;
            
            buffer += decoder.decode(value, { stream: true });
            
            // 处理完整的事件
            const lines = buffer.split('\n');
            buffer = lines.pop() || '';
            
            for (const line of lines) {
                if (line.startsWith('data: ')) {
                    try {
                        const data = JSON.parse(line.slice(6));
                        
                        if (data.type === 'start') {
                            // 开始处理
                            updateToolCallsStatus(toolCallsContainer, '开始思考...');
                        } else if (data.type === 'thinking') {
                            // V2: 规划开始 - 显示思考状态
                            updateToolCallsStatus(toolCallsContainer, data.message || '正在规划...');
                        } else if (data.type === 'plan') {
                            // V2: 规划完成 - 显示决策信息
                            const planMessage = data.message || `决策: ${data.action}`;
                            updateToolCallsStatus(toolCallsContainer, planMessage);
                        } else if (data.type === 'evaluate') {
                            // V2: 评估阶段 - 显示评估结果
                            const evalMessage = data.message || '评估中...';
                            updateToolCallsStatus(toolCallsContainer, evalMessage);
                        } else if (data.type === 'tool_start') {
                            // 工具调用开始
                            addToolCallItem(toolCallsContainer, data);
                        } else if (data.type === 'tool_end') {
                            // 工具调用完成
                            updateToolCallItem(toolCallsContainer, data);
                        } else if (data.type === 'tool_error') {
                            // 工具调用出错
                            updateToolCallError(toolCallsContainer, data);
                        } else if (data.type === 'answer_start') {
                            // V2: 开始生成答案
                            updateToolCallsStatus(toolCallsContainer, '[生成答案] 正在生成最终答案...');
                            // 初始化流式答案缓冲区
                            if (!window.streamingAnswerBuffer) {
                                window.streamingAnswerBuffer = {};
                            }
                            window.streamingAnswerBuffer[assistantMessageId] = '';
                        } else if (data.type === 'answer_chunk') {
                            // V2: 流式答案片段
                            if (!window.streamingAnswerBuffer) {
                                window.streamingAnswerBuffer = {};
                            }
                            if (!window.streamingAnswerBuffer[assistantMessageId]) {
                                window.streamingAnswerBuffer[assistantMessageId] = '';
                            }
                            // 累积答案片段
                            window.streamingAnswerBuffer[assistantMessageId] += data.chunk;
                            // 实时渲染并更新答案（支持 Markdown 和 LaTeX）
                            updateMessageContentWithMarkdown(assistantMessageId, window.streamingAnswerBuffer[assistantMessageId]);
                            // 触发 LaTeX 渲染
                            if (typeof renderMathInElement !== 'undefined') {
                                const messageElement = document.getElementById(assistantMessageId);
                                if (messageElement) {
                                    const contentElement = messageElement.querySelector('.message-content');
                                    if (contentElement) {
                                        renderMathInElement(contentElement, {
                                            delimiters: [
                                                {left: '$$', right: '$$', display: true},
                                                {left: '$', right: '$', display: false},
                                                {left: '\\[', right: '\\]', display: true},
                                                {left: '\\(', right: '\\)', display: false}
                                            ],
                                            throwOnError: false
                                        });
                                    }
                                }
                            }
                        } else if (data.type === 'refuse_request' || data.type === 'security_blocked') {
                            // 【安全拦截】显示拒绝消息
                            updateToolCallsTitle(toolCallsContainer, '已停止');  // 更新标题为"已停止"
                            updateToolCallsStatus(toolCallsContainer, '');  // 清空右侧状态
                            
                            const reason = data.reason || data.message || '该请求不被支持';
                            const securityMessage = `
<div class="alert alert-warning" role="alert" style="border-left: 4px solid #f0ad4e; margin: 20px 0;">
    <h4 class="alert-heading">
        <i class="fas fa-shield-alt"></i> ${reason}
    </h4>
</div>`;
                            
                            updateMessageContent(assistantMessageId, securityMessage);
                            
                            // 设置标志，防止done事件覆盖安全拒绝UI
                            if (!window.securityBlockedMessages) {
                                window.securityBlockedMessages = new Set();
                            }
                            window.securityBlockedMessages.add(assistantMessageId);
                            
                            // 标记流结束
                            isStreaming = false;
                            // 流会自然结束，不需要手动abort
                            return;
                        } else if (data.type === 'done') {
                            // 处理完成，显示最终答案
                            sources = data.sources || [];
                            processInfo.confidence = data.confidence || 0;
                            processInfo.confidenceReason = data.confidence_reason || '';
                            processInfo.usedRetrieval = data.used_retrieval || false;
                            processInfo.processLog = data.process_log || {};
                            processInfo.requestId = data.request_id || null;  // 保存request_id
                            
                            // 将仍在执行中的工具标记为完成
                            if (toolCallsContainer) {
                                markRemainingToolCalls(toolCallsContainer);
                            }
                            
                            // 【检查是否已被安全拦截】如果已经显示了安全拒绝UI，不要覆盖
                            const isSecurityBlocked = window.securityBlockedMessages && window.securityBlockedMessages.has(assistantMessageId);
                            
                            // 定义finalAnswer变量（在所有分支都需要使用）
                            let finalAnswer = '';
                            
                            if (!isSecurityBlocked) {
                                // 获取最终答案
                                // 如果没有流式答案片段，使用完整答案更新
                                if (!window.streamingAnswerBuffer || !window.streamingAnswerBuffer[assistantMessageId]) {
                                    finalAnswer = data.answer || '';
                                    updateMessageContent(assistantMessageId, finalAnswer);
                                } else {
                                    // 有流式答案，进行最后一次完整渲染确保正确性
                                    finalAnswer = window.streamingAnswerBuffer[assistantMessageId];
                                    updateMessageContentWithMarkdown(assistantMessageId, finalAnswer);
                                    // 最终 LaTeX 渲染
                                    if (typeof renderMathInElement !== 'undefined') {
                                        const messageElement = document.getElementById(assistantMessageId);
                                        if (messageElement) {
                                            const contentElement = messageElement.querySelector('.message-content');
                                            if (contentElement) {
                                                renderMathInElement(contentElement, {
                                                    delimiters: [
                                                        {left: '$$', right: '$$', display: true},
                                                        {left: '$', right: '$', display: false},
                                                        {left: '\\[', right: '\\]', display: true},
                                                        {left: '\\(', right: '\\)', display: false}
                                                    ],
                                                    throwOnError: false
                                                });
                                            }
                                        }
                                    }
                                    // 清理缓冲区
                                    delete window.streamingAnswerBuffer[assistantMessageId];
                                }
                            } else {
                                // 安全拦截情况，从backend返回的答案中获取
                                finalAnswer = data.answer || '安全拒绝：任务已终止';
                            }
                            
                            // 添加来源和额外信息
                            finishAgenticMessage(assistantMessageId, sources, processInfo);
                            
                            // 自动收起工具调用容器
                            if (toolCallsContainer) {
                                collapseToolCalls(assistantMessageId);
                            }
                            
                            // 添加到对话历史（只保留问题和答案文本）
                            conversationHistory.push({
                                role: 'user',
                                content: question
                            });
                            conversationHistory.push({
                                role: 'assistant',
                                content: finalAnswer
                            });
                            
                            // 只保留最近N轮对话
                            if (conversationHistory.length > MAX_HISTORY_ROUNDS * 2) {
                                conversationHistory = conversationHistory.slice(-MAX_HISTORY_ROUNDS * 2);
                            }
                            
                            console.log('已添加到对话历史，当前历史长度:', conversationHistory.length / 2, '轮');
                        } else if (data.type === 'error') {
                            // 显示详细的错误信息
                            let errorMessage = '❌ ' + (data.message || '任务执行失败');
                            
                            // 如果有连续错误信息，添加详情
                            if (data.consecutive_errors) {
                                errorMessage += `\n\n连续错误次数：${data.consecutive_errors}`;
                                if (data.last_error) {
                                    errorMessage += `\n最后错误：${data.last_error}`;
                                }
                            }
                            
                            // 更新消息显示
                            if (assistantMessageId) {
                                replaceMessage(assistantMessageId, errorMessage);
                            }
                            
                            // 更新工具调用状态
                            if (toolCallsContainer) {
                                updateToolCallsStatus(toolCallsContainer, '任务失败');
                            }
                            
                            // 不再抛出错误，而是优雅地处理
                            console.error('Agent任务失败:', data);
                            showToast('任务执行失败', 'error');
                            break;  // 退出循环
                        }
                        
                        scrollChatToBottom();
                    } catch (parseError) {
                        console.error('解析流式数据失败:', parseError);
                    }
                }
            }
        }
    } catch (error) {
        console.error('Agent对话失败:', error);
        
        // 检查是否是用户主动取消
        if (error.name === 'AbortError') {
            if (assistantMessageId) {
                replaceMessage(assistantMessageId, '⚠️ 已停止生成');
            }
            showToast('已停止任务', 'info');
        } else {
            if (assistantMessageId) {
                replaceMessage(assistantMessageId, '抱歉，出现了错误：' + error.message);
            } else {
                addChatMessage('抱歉，出现了错误：' + error.message, 'assistant');
            }
            showToast('问答失败', 'error');
        }
    } finally {
        currentAbortController = null;  // 清理
        toggleSendButton(true);
        scrollChatToBottom();
    }
}

/**
 * 流式问答
 */
async function sendQuestionStream(question) {
    let assistantMessageId = null;
    let sources = [];
    
    try {
        toggleSendButton(false);
        
        const response = await fetch('/api/rag/chat', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json'
            },
            body: JSON.stringify({
                question: question,
                kb_ids: Array.from(selectedKnowledgeBases),
                stream: true,
                top_k: 5
            })
        });
        
        if (!response.ok) {
            throw new Error('网络请求失败');
        }
        
        const reader = response.body.getReader();
        const decoder = new TextDecoder();
        let buffer = '';
        
        while (true) {
            const { done, value } = await reader.read();
            
            if (done) break;
            
            buffer += decoder.decode(value, { stream: true });
            
            // 处理完整的事件
            const lines = buffer.split('\n');
            buffer = lines.pop() || '';
            
            for (const line of lines) {
                if (line.startsWith('data: ')) {
                    try {
                        const data = JSON.parse(line.slice(6));
                        
                        if (data.type === 'start') {
                            sources = data.sources;
                            assistantMessageId = addChatMessage('', 'assistant');
                        } else if (data.type === 'chunk' && assistantMessageId) {
                            appendToMessage(assistantMessageId, data.content);
                            scrollChatToBottom();
                        } else if (data.type === 'done' && assistantMessageId) {
                            finishMessage(assistantMessageId, sources);
                        } else if (data.type === 'error') {
                            throw new Error(data.message);
                        }
                    } catch (parseError) {
                        console.error('解析流式数据失败:', parseError);
                    }
                }
            }
        }
    } catch (error) {
        console.error('流式问答失败:', error);
        if (assistantMessageId) {
            replaceMessage(assistantMessageId, '抱歉，出现了错误：' + error.message);
        } else {
            addChatMessage('抱歉，出现了错误：' + error.message, 'assistant');
        }
        showToast('问答失败', 'error');
    } finally {
        toggleSendButton(true);
        scrollChatToBottom();
    }
}

/**
 * 添加聊天消息
 */
function addChatMessage(content, type, isLoading = false, sources = null, extraInfo = null) {
    const messagesContainer = document.getElementById('chat-messages');
    const messageId = 'msg-' + Date.now() + '-' + Math.random().toString(36).substr(2, 9);
    
    // 移除欢迎消息
    const welcomeMessage = messagesContainer.querySelector('.welcome-message');
    if (welcomeMessage) {
        welcomeMessage.remove();
    }
    
    const messageDiv = document.createElement('div');
    messageDiv.className = `chat-message ${type}-message`;
    messageDiv.id = messageId;
    
    let sourcesHtml = '';
    if (sources && sources.length > 0) {
        sourcesHtml = `
            <div class="message-sources">
                <div class="mb-2"><strong><i class="fas fa-book-open"></i> 参考资料:</strong></div>
                ${sources.map(source => `
                    <div class="source-item">
                        <div class="source-header">
                            <span><strong>${escapeHtml(source.doc_name)}</strong></span>
                            <span class="score-badge">相似度: ${((source.final_score || source.score) * 100).toFixed(1)}%</span>
                        </div>
                        <div class="source-meta">知识库: ${escapeHtml(source.kb_name)}</div>
                        <div class="source-content">${escapeHtml(source.content)}</div>
                    </div>
                `).join('')}
            </div>
        `;
    }
    
    // ReAct Agent 额外信息
    let extraInfoHtml = '';
    if (extraInfo && type === 'assistant') {
        const confidenceColor = extraInfo.confidence >= 0.8 ? 'success' : 
                               extraInfo.confidence >= 0.6 ? 'warning' : 'danger';
        
        extraInfoHtml = `
            <div class="agentic-info mt-3 p-2 bg-light rounded">
                <div class="d-flex justify-content-between align-items-center">
                    <div>
                        <small><strong><i class="fas fa-robot"></i> ReAct Agent 分析:</strong></small>
                    </div>
                    <div>
                        <span class="badge bg-${confidenceColor}">
                            置信度: ${(extraInfo.confidence * 100).toFixed(1)}%
                        </span>
                        ${extraInfo.usedRetrieval ? 
                            '<span class="badge bg-info ms-1">已检索</span>' : 
                            '<span class="badge bg-secondary ms-1">直接回答</span>'}
                    </div>
                </div>
                <div class="mt-1">
                    <small class="text-muted">${escapeHtml(extraInfo.confidenceReason)}</small>
                </div>
                ${extraInfo.processLog ? `
                    <div class="mt-2">
                        <a href="#" onclick="toggleProcessLog('${messageId}')" class="text-decoration-none">
                            <small><i class="fas fa-cog"></i> 查看处理详情</small>
                        </a>
                        <div id="${messageId}-process-log" class="process-log mt-2" style="display: none;">
                            <pre class="small bg-white p-2 rounded border">${JSON.stringify(extraInfo.processLog, null, 2)}</pre>
                        </div>
                    </div>
                ` : ''}
            </div>
        `;
    }
    
    messageDiv.innerHTML = `
        <div class="message-bubble">
            <div class="message-content">${escapeHtml(content)}${isLoading ? '<span class="typing-animation">...</span>' : ''}</div>
            ${sourcesHtml}
            ${extraInfoHtml}
            <div class="message-time">${new Date().toLocaleTimeString()}</div>
        </div>
    `;
    
    messagesContainer.appendChild(messageDiv);
    return messageId;
}

/**
 * 切换过程日志显示
 */
function toggleProcessLog(messageId) {
    const logElement = document.getElementById(`${messageId}-process-log`);
    if (logElement) {
        logElement.style.display = logElement.style.display === 'none' ? 'block' : 'none';
    }
}

/**
 * 向消息追加内容
 */
function appendToMessage(messageId, content) {
    const messageElement = document.getElementById(messageId);
    if (messageElement) {
        const contentElement = messageElement.querySelector('.message-content');
        if (contentElement) {
            const currentContent = contentElement.textContent.replace('...', '');
            contentElement.innerHTML = escapeHtml(currentContent + content) + '<span class="typing-animation">...</span>';
        }
    }
}

/**
 * 完成消息（添加来源并移除加载动画）
 */
function finishMessage(messageId, sources) {
    const messageElement = document.getElementById(messageId);
    if (messageElement) {
        const contentElement = messageElement.querySelector('.message-content');
        if (contentElement) {
            // 移除加载动画
            contentElement.innerHTML = contentElement.textContent.replace('...', '');
            
            // 添加来源信息
            if (sources && sources.length > 0) {
                const sourcesHtml = `
                    <div class="message-sources">
                        <div class="mb-2"><strong><i class="fas fa-book-open"></i> 参考资料:</strong></div>
                        ${sources.map(source => `
                            <div class="source-item">
                                <div class="source-header">
                                    <span><strong>${escapeHtml(source.doc_name)}</strong></span>
                                    <span class="score-badge">相似度: ${(source.score * 100).toFixed(1)}%</span>
                                </div>
                                <div class="source-meta">知识库: ${escapeHtml(source.kb_name)}</div>
                                <div class="source-content">${escapeHtml(source.content)}</div>
                            </div>
                        `).join('')}
                    </div>
                `;
                
                const messageBubble = messageElement.querySelector('.message-bubble');
                messageBubble.insertAdjacentHTML('beforeend', sourcesHtml);
            }
        }
    }
}

/**
 * 替换消息内容
 */
function replaceMessage(messageId, content) {
    const messageElement = document.getElementById(messageId);
    if (messageElement) {
        const contentElement = messageElement.querySelector('.message-content');
        if (contentElement) {
            contentElement.textContent = content;
        }
    }
}

/**
 * 移除加载消息
 */
function removeLoadingMessage(messageId) {
    const messageElement = document.getElementById(messageId);
    if (messageElement) {
        messageElement.remove();
    }
}

/**
 * 清空对话
 */
function clearChat() {
    const messagesContainer = document.getElementById('chat-messages');
    messagesContainer.innerHTML = `
        <div class="welcome-message">
            <div class="text-center text-muted py-5">
                <i class="fas fa-robot fa-3x mb-3"></i>
                <h5>欢迎使用 ReAct Agent</h5>
                <p>请选择知识库并输入您的问题</p>
            </div>
        </div>
    `;
    // 重置对话历史
    conversationHistory = [];
    // 清理安全拦截标志
    if (window.securityBlockedMessages) {
        window.securityBlockedMessages.clear();
    }
    console.log('已清空对话历史');
}

/**
 * 滚动聊天到底部
 */
function scrollChatToBottom() {
    const messagesContainer = document.getElementById('chat-messages');
    messagesContainer.scrollTop = messagesContainer.scrollHeight;
}

/**
 * 切换发送按钮状态
 */
function toggleSendButton(enabled) {
    const sendBtn = document.getElementById('send-btn');
    const stopBtn = document.getElementById('stop-btn');
    
    sendBtn.disabled = !enabled;
    
    if (enabled) {
        sendBtn.innerHTML = '<i class="fas fa-paper-plane"></i>';
        sendBtn.style.display = '';
        if (stopBtn) stopBtn.style.display = 'none';
    } else {
        sendBtn.innerHTML = '<i class="fas fa-spinner fa-spin"></i>';
        sendBtn.style.display = 'none';
        if (stopBtn) stopBtn.style.display = '';
    }
}

/**
 * 停止生成
 */
function stopGeneration() {
    if (currentAbortController) {
        currentAbortController.abort();
        console.log('用户主动停止生成');
    }
}

/**
 * 处理回车键
 */
function handleEnterKey(event) {
    if (event.key === 'Enter' && !event.shiftKey) {
        event.preventDefault();
        sendQuestion();
    }
}

/**
 * 添加工具调用容器
 */
function addToolCallsContainer(messageId) {
    const messageElement = document.getElementById(messageId);
    if (!messageElement) return null;
    
    const messageBubble = messageElement.querySelector('.message-bubble');
    if (!messageBubble) return null;
    
    const toolCallsDiv = document.createElement('div');
    toolCallsDiv.className = 'tool-calls-container';
    toolCallsDiv.id = `${messageId}-tools`;
    toolCallsDiv.dataset.expanded = 'true';
    toolCallsDiv.innerHTML = `
        <div class="tool-calls-header" onclick="toggleToolCalls('${messageId}')">
            <div class="tool-calls-header-left">
                <i class="fas fa-robot me-2"></i>
                <span class="tool-calls-title">正在思考...</span>
            </div>
            <div class="tool-calls-header-right">
                <span class="tool-calls-time" id="${messageId}-thinking-time">0s</span>
                <i class="fas fa-chevron-down tool-calls-toggle-icon" id="${messageId}-toggle-icon"></i>
            </div>
        </div>
        <div class="tool-calls-list" id="${messageId}-tools-list"></div>
    `;
    
    messageBubble.insertBefore(toolCallsDiv, messageBubble.firstChild);
    
    // 启动计时器
    startThinkingTimer(messageId);
    
    return toolCallsDiv;
}

/**
 * 切换工具调用的展开/收起状态
 */
function toggleToolCalls(messageId) {
    const container = document.getElementById(`${messageId}-tools`);
    
    if (!container) return;
    
    // 使用 CSS 类来控制展开/折叠状态，实现平滑动画
    const isCollapsed = container.classList.contains('collapsed');
    
    if (isCollapsed) {
        // 展开
        container.classList.remove('collapsed');
        container.dataset.expanded = 'true';
    } else {
        // 收起
        container.classList.add('collapsed');
        container.dataset.expanded = 'false';
    }
}

/**
 * 完成工具调用,自动收起
 */
function collapseToolCalls(messageId) {
    const container = document.getElementById(`${messageId}-tools`);
    const list = document.getElementById(`${messageId}-tools-list`);
    const icon = document.getElementById(`${messageId}-toggle-icon`);
    const titleElement = container?.querySelector('.tool-calls-title');
    const statusElement = container?.querySelector('.tool-calls-status');
    
    if (!container || !list || !icon) return;
    
    // 停止计时器
    stopThinkingTimer(messageId);
    
    // 确保所有工具标记为完成
    markRemainingToolCalls(container);
    
    // 更新标题为"已完成工具调用"
    if (titleElement) {
        titleElement.textContent = '已思考';
    }
    if (statusElement) {
        statusElement.textContent = '';
    }
    
    // 收起工具调用列表 - 使用 CSS 类来控制，而不是直接操作 style
    container.classList.add('collapsed');
    container.dataset.expanded = 'false';
    
    // 添加完成状态样式
    container.classList.add('tool-calls-completed');
}

/**
 * 将仍在执行中的工具标记为完成
 */
function markRemainingToolCalls(container) {
    if (!container) return;
    const items = container.querySelectorAll('.tool-call-item');
    items.forEach(item => {
        const statusElement = item.querySelector('.tool-call-status');
        if (!statusElement) return;
        if (item.classList.contains('tool-call-running')) {
            item.classList.remove('tool-call-running');
            item.classList.add('tool-call-success');
            statusElement.innerHTML = `
                <i class="fas fa-check-circle text-success me-1"></i>
                完成
            `;
        }
    });
}

/**
 * 更新工具调用状态
 */
function updateToolCallsStatus(container, status) {
    if (!container) return;
    const statusElement = container.querySelector('.tool-calls-status');
    if (statusElement) {
        statusElement.textContent = status;
    }
}

/**
 * 更新工具调用标题
 */
function updateToolCallsTitle(container, title) {
    if (!container) return;
    const titleElement = container.querySelector('.tool-calls-title');
    if (titleElement) {
        titleElement.textContent = title;
    }
}

/**
 * 添加工具调用项
 */
function addToolCallItem(container, data) {
    if (!container) return;
    
    const listElement = container.querySelector('.tool-calls-list');
    if (!listElement) return;
    
    const toolItem = document.createElement('div');
    toolItem.className = 'tool-call-item tool-call-running';
    toolItem.id = `tool-${data.step}`;
    
    const toolIcon = getToolIcon(data.tool);
    
    toolItem.innerHTML = `
        <div class="tool-call-header">
            <div class="tool-call-icon">${toolIcon}</div>
            <div class="tool-call-info">
                <div class="tool-call-name">${escapeHtml(data.tool_name || data.tool)}</div>
                <div class="tool-call-status">
                    <span class="spinner-border spinner-border-sm me-1" role="status"></span>
                    执行中...
                </div>
            </div>
        </div>
        ${data.reasoning ? `<div class="tool-call-reasoning"><strong>推理:</strong> ${escapeHtml(data.reasoning)}</div>` : ''}
    `;
    
    listElement.appendChild(toolItem);
    scrollChatToBottom();
}

/**
 * 更新工具调用项（完成）
 */
function updateToolCallItem(container, data) {
    if (!container) return;
    
    const toolItem = document.getElementById(`tool-${data.step}`);
    if (!toolItem) return;
    
    toolItem.className = 'tool-call-item tool-call-success';
    updateToolCallStatus(toolItem, 'success', data.execution_time);
    
    // 特殊处理Python代码执行：折叠显示"代码分析"按钮
    if (data.tool === 'python_code' && data.python_details) {
        // 保存详情数据到全局变量，供模态框使用
        if (!window.toolDetailsData) window.toolDetailsData = {};
        window.toolDetailsData[`tool-${data.step}`] = {
            type: 'python',
            data: data.python_details
        };
        
        // 添加折叠按钮
        const detailsBtn = document.createElement('button');
        detailsBtn.className = 'tool-details-btn';
        detailsBtn.innerHTML = `<i class="fas fa-code me-1"></i>代码分析`;
        detailsBtn.onclick = () => showToolDetails(`tool-${data.step}`, 'Python 代码分析');
        toolItem.appendChild(detailsBtn);
    }
    // 处理检索结果（知识库检索、网络搜索）：折叠显示"源"按钮
    else if ((data.tool === 'search' || data.tool === 'web_search') && data.result_summary) {
        // 保存详情数据
        if (!window.toolDetailsData) window.toolDetailsData = {};
        window.toolDetailsData[`tool-${data.step}`] = {
            type: data.tool === 'web_search' ? 'web_search' : 'search',
            data: data,
            summary: data.result_summary
        };
        
        // 添加结果摘要和"源"按钮
        const resultDiv = document.createElement('div');
        resultDiv.className = 'tool-call-result-compact';
        resultDiv.innerHTML = `
            <span class="result-summary">
                <i class="fas fa-info-circle me-1"></i>${escapeHtml(data.result_summary)}
            </span>
            <button class="tool-details-btn" onclick="showToolDetails('tool-${data.step}', '${data.tool === 'web_search' ? '网络搜索结果' : '检索结果'}')">
                <i class="fas fa-link me-1"></i>源
            </button>
        `;
        toolItem.appendChild(resultDiv);
    }
    // 其他工具：显示简单摘要
    else if (data.result_summary) {
        const resultDiv = document.createElement('div');
        resultDiv.className = 'tool-call-result';
        resultDiv.innerHTML = `<i class="fas fa-info-circle me-1"></i>${escapeHtml(data.result_summary)}`;
        toolItem.appendChild(resultDiv);
    }
    
    scrollChatToBottom();
}

/**
 * 更新工具调用项（错误）
 */
function updateToolCallError(container, data) {
    if (!container) return;
    
    const toolItem = document.getElementById(`tool-${data.step}`);
    if (!toolItem) return;
    
    toolItem.className = 'tool-call-item tool-call-error';
    updateToolCallStatus(toolItem, 'error');
    
    // 添加错误信息
    if (data.error) {
        const errorDiv = document.createElement('div');
        errorDiv.className = 'tool-call-error-msg';
        errorDiv.innerHTML = `<i class="fas fa-times-circle me-1"></i>${escapeHtml(data.error)}`;
        toolItem.appendChild(errorDiv);
    }
    
    scrollChatToBottom();
}

/**
 * 获取工具图标
 */
function getToolIcon(toolName) {
    const icons = {
        'search': '<i class="fas fa-search"></i>',
        'rerank': '<i class="fas fa-sort-amount-down"></i>',
        'evaluate': '<i class="fas fa-chart-line"></i>',
        'answer': '<i class="fas fa-comment-dots"></i>',
        'decide': '<i class="fas fa-brain"></i>',
        'web_search': '<i class="fas fa-globe"></i>',
        'python_code': '<i class="fab fa-python"></i>',
        'finish': '<i class="fas fa-flag-checkered"></i>'
    };
    return icons[toolName] || '<i class="fas fa-cog"></i>';
}

/**
 * 更新消息内容
 */
function updateMessageContent(messageId, content) {
    const messageElement = document.getElementById(messageId);
    if (!messageElement) return;
    
    let contentElement = messageElement.querySelector('.message-content');
    if (!contentElement) {
        contentElement = document.createElement('div');
        contentElement.className = 'message-content';
        const messageBubble = messageElement.querySelector('.message-bubble');
        messageBubble.appendChild(contentElement);
    }
    
    // 渲染Markdown
    contentElement.innerHTML = renderMarkdown(content);
    
    // 高亮代码块
    const applyCodeHighlight = () => {
        if (typeof hljs === 'undefined') {
            return;
        }
        contentElement.querySelectorAll('pre code').forEach((block) => {
            hljs.highlightElement(block);
        });
    };
    requestAnimationFrame(applyCodeHighlight);
    
    // 渲染LaTeX数学公式
    requestAnimationFrame(() => renderMath(contentElement));
}

/**
 * 完成Agentic消息（添加来源和额外信息）
 */
function finishAgenticMessage(messageId, sources, processInfo) {
    const messageElement = document.getElementById(messageId);
    if (!messageElement) return;
    
    const messageBubble = messageElement.querySelector('.message-bubble');
    if (!messageBubble) return;
    
    // 添加来源信息（折叠按钮）
    if (sources && sources.length > 0) {
        if (!window.toolDetailsData) window.toolDetailsData = {};
        const sourceKey = `sources-${messageId}`;
        window.toolDetailsData[sourceKey] = {
            type: 'final_sources',
            data: sources
        };
        
        const sourcesHtml = `
            <div class="message-sources-compact">
                <div class="d-flex align-items-center gap-2">
                    <i class="fas fa-book-open text-muted"></i>
                    <span class="text-muted">参考资料 (${sources.length})</span>
                </div>
                <button class="tool-details-btn" onclick="showToolDetails('${sourceKey}', '参考资料')">
                    <i class="fas fa-link me-1"></i>源
                </button>
            </div>
        `;
        messageBubble.insertAdjacentHTML('beforeend', sourcesHtml);
    }
    
    // 添加 ReAct Agent 额外信息
    const confidenceColor = processInfo.confidence >= 0.8 ? 'success' : 
                           processInfo.confidence >= 0.6 ? 'warning' : 'danger';
    
    const extraInfoHtml = `
        <div class="agentic-info mt-3 p-2 bg-light rounded">
            <div class="d-flex justify-content-between align-items-center">
                <div>
                    <small><strong><i class="fas fa-robot"></i> ReAct Agent 分析:</strong></small>
                </div>
                <div>
                    <span class="badge bg-${confidenceColor}">
                        置信度: ${(processInfo.confidence * 100).toFixed(1)}%
                    </span>
                    ${processInfo.usedRetrieval ? 
                        '<span class="badge bg-info ms-1">已检索</span>' : 
                        '<span class="badge bg-secondary ms-1">直接回答</span>'}
                </div>
            </div>
            <div class="mt-1">
                <small class="text-muted">${escapeHtml(processInfo.confidenceReason)}</small>
            </div>
            ${processInfo.processLog ? `
                <div class="mt-2">
                    <button class="tool-details-btn" onclick="showToolDetails('process-${messageId}', '处理详情')">
                        <i class="fas fa-info-circle me-1"></i>查看处理详情
                    </button>
                    <button class="tool-details-btn ms-2" onclick="downloadLLMIO('${messageId}')" title="下载本次请求的完整LLM调用载荷">
                        <i class="fas fa-download me-1"></i>下载LLM IO
                    </button>
                </div>
            ` : ''}
        </div>
    `;
    messageBubble.insertAdjacentHTML('beforeend', extraInfoHtml);
    
    if (processInfo.processLog) {
        if (!window.toolDetailsData) window.toolDetailsData = {};
        window.toolDetailsData[`process-${messageId}`] = {
            type: 'process_log',
            data: processInfo.processLog,
            request_id: processInfo.requestId  // 保存request_id
        };
    }
}

/**
 * 工具函数
 */

/**
 * 显示工具详情模态框
 */
function showToolDetails(toolId, title) {
    const detailsData = window.toolDetailsData?.[toolId];
    if (!detailsData) {
        console.error('未找到工具详情数据:', toolId);
        return;
    }
    
    const modal = new bootstrap.Modal(document.getElementById('toolDetailsModal'));
    const titleElement = document.getElementById('toolDetailsTitle');
    const bodyElement = document.getElementById('toolDetailsBody');
    
    titleElement.innerHTML = `<i class="fas fa-info-circle me-2"></i>${escapeHtml(title)}`;
    
    let htmlContent = '';
    
    // Python代码执行详情
    if (detailsData.type === 'python') {
        const pythonData = detailsData.data;
        
        // 显示生成的代码
        if (pythonData.code) {
            htmlContent += `
                <div class="detail-section">
                    <div class="detail-section-title">
                        <i class="fas fa-code me-2"></i>执行代码
                    </div>
                    <pre><code class="language-python">${escapeHtml(pythonData.code)}</code></pre>
                </div>
            `;
        }
        
        // 显示执行输出
        if (pythonData.output) {
            htmlContent += `
                <div class="detail-section">
                    <div class="detail-section-title">
                        <i class="fas fa-terminal me-2"></i>执行结果
                    </div>
                    <pre class="detail-output">${escapeHtml(pythonData.output)}</pre>
                </div>
            `;
        }
        
        // 显示执行时间
        if (pythonData.execution_time) {
            htmlContent += `
                <div class="detail-section">
                    <div class="detail-section-title">
                        <i class="fas fa-clock me-2"></i>执行时间
                    </div>
                    <p class="mb-0">${(pythonData.execution_time * 1000).toFixed(2)} ms</p>
                </div>
            `;
        }
        
        // 显示错误信息
        if (pythonData.error) {
            htmlContent += `
                <div class="detail-section">
                    <div class="detail-section-title text-danger">
                        <i class="fas fa-exclamation-triangle me-2"></i>错误信息
                    </div>
                    <pre class="detail-error">${escapeHtml(pythonData.error)}</pre>
                </div>
            `;
        }
    }
    // 网络搜索详情
    else if (detailsData.type === 'web_search') {
        htmlContent += `
            <div class="detail-section">
                <div class="detail-section-title">
                    <i class="fas fa-globe me-2"></i>搜索摘要
                </div>
                <p>${escapeHtml(detailsData.summary)}</p>
            </div>
        `;
        
        // 显示搜索结果（如果有）
        if (detailsData.data.web_search_results) {
            htmlContent += `
                <div class="detail-section">
                    <div class="detail-section-title">
                        <i class="fas fa-list me-2"></i>搜索结果
                    </div>
                    <div class="search-results-list">
            `;
            
            detailsData.data.web_search_results.forEach((result, index) => {
                htmlContent += `
                    <div class="search-result-item">
                        <div class="search-result-title">
                            <span class="badge bg-primary me-2">${index + 1}</span>
                            ${escapeHtml(result.title || result.doc_name || '搜索结果')}
                        </div>
                        ${result.url ? `
                            <div class="search-result-url">
                                <i class="fas fa-link me-1"></i>
                                <a href="${escapeHtml(result.url)}" target="_blank">${escapeHtml(result.url)}</a>
                            </div>
                        ` : ''}
                        <div class="search-result-content">
                            ${escapeHtml(result.content)}
                        </div>
                    </div>
                `;
            });
            
            htmlContent += `
                    </div>
                </div>
            `;
        }
    }
    // 知识库检索详情
    else if (detailsData.type === 'search') {
        htmlContent += `
            <div class="detail-section">
                <div class="detail-section-title">
                    <i class="fas fa-database me-2"></i>检索摘要
                </div>
                <p>${escapeHtml(detailsData.summary || '')}</p>
            </div>
        `;
        
        if (detailsData.data.search_results) {
            htmlContent += `
                <div class="detail-section">
                    <div class="detail-section-title">
                        <i class="fas fa-list me-2"></i>检索结果
                    </div>
                    <div class="search-results-list">
            `;
            
            detailsData.data.search_results.forEach((result, index) => {
                htmlContent += `
                    <div class="search-result-item">
                        <div class="search-result-title">
                            <span class="badge bg-success me-2">${index + 1}</span>
                            ${escapeHtml(result.doc_name || '文档')}
                            ${result.final_score ? `<span class="badge bg-secondary ms-2">相关度: ${(result.final_score * 100).toFixed(1)}%</span>` : ''}
                        </div>
                        <div class="search-result-content">
                            ${escapeHtml(result.content)}
                        </div>
                        ${result.kb_name ? `
                            <div class="search-result-meta">
                                <i class="fas fa-database me-1"></i>知识库: ${escapeHtml(result.kb_name)}
                            </div>
                        ` : ''}
                    </div>
                `;
            });
            
            htmlContent += `
                    </div>
                </div>
            `;
        }
    }
    // 最终参考资料详情
    else if (detailsData.type === 'final_sources') {
        const sources = detailsData.data || [];
        if (sources.length > 0) {
            htmlContent += `
                <div class="detail-section">
                    <div class="detail-section-title">
                        <i class="fas fa-book me-2"></i>参考资料
                    </div>
                    <div class="search-results-list">
            `;
            
            sources.forEach((source, index) => {
                htmlContent += `
                    <div class="search-result-item">
                        <div class="search-result-title">
                            <span class="badge bg-primary me-2">${index + 1}</span>
                            ${escapeHtml(source.doc_name || '资料')}
                            ${source.final_score || source.score ? `<span class="badge bg-secondary ms-2">相似度: ${(((source.final_score || source.score) || 0) * 100).toFixed(1)}%</span>` : ''}
                        </div>
                        <div class="search-result-content">
                            ${escapeHtml(source.content || '')}
                        </div>
                        ${source.kb_name ? `
                            <div class="search-result-meta">
                                <i class="fas fa-database me-1"></i>知识库: ${escapeHtml(source.kb_name)}
                            </div>
                        ` : ''}
                    </div>
                `;
            });
            
            htmlContent += `
                    </div>
                </div>
            `;
        }
    }
    // 处理日志详情
    else if (detailsData.type === 'process_log') {
        htmlContent += `
            <div class="detail-section">
                <div class="detail-section-title">
                    <i class="fas fa-list me-2"></i>执行流程
                </div>
                <pre class="detail-output bg-white border">${escapeHtml(JSON.stringify(detailsData.data, null, 2))}</pre>
            </div>
        `;
    }
    
    bodyElement.innerHTML = htmlContent;
    
    // 高亮代码
    bodyElement.querySelectorAll('pre code').forEach((block) => {
        hljs.highlightElement(block);
    });
    
    modal.show();
}

/**
 * HTML转义
 */
function escapeHtml(text) {
    const div = document.createElement('div');
    div.textContent = text;
    return div.innerHTML;
}

/**
 * 格式化日期
 */
function formatDate(dateString) {
    const date = new Date(dateString);
    return date.toLocaleDateString('zh-CN', {
        year: 'numeric',
        month: 'short',
        day: 'numeric',
        hour: '2-digit',
        minute: '2-digit'
    });
}

/**
 * ================ 新增功能 ================
 */

/**
 * 加载知识库网格（用于管理视图）
 */
async function loadKnowledgeBasesGrid() {
    try {
        const response = await fetch('/api/kb/list');
        const data = await response.json();
        
        if (data.success) {
            renderKnowledgeBasesGrid(data.data);
        }
    } catch (error) {
        console.error('加载知识库失败:', error);
    }
}

/**
 * 渲染知识库网格
 */
function renderKnowledgeBasesGrid(knowledgeBases) {
    const container = document.getElementById('knowledge-bases-grid');
    
    if (!container) return;
    
    if (knowledgeBases.length === 0) {
        container.innerHTML = `
            <div class="text-center text-muted py-5">
                <i class="fas fa-database fa-3x mb-3"></i>
                <p>暂无知识库，点击右上角创建</p>
            </div>
        `;
        return;
    }
    
    container.innerHTML = knowledgeBases.map(kb => {
        const status = kb.status || 'ready';
        const isReady = status === 'ready';
        const isProcessing = status === 'processing';
        
        let statusBadge = '';
        let actionButtons = '';
        
        if (isProcessing) {
            const progress = Math.round((kb.processing_progress || 0) * 100);
            statusBadge = `<span class="badge bg-warning">${progress}%</span>`;
            
            // 添加强制停止按钮
            actionButtons = `
                <button class="btn btn-sm btn-force-stop" onclick="forceStopKbProcessing(${kb.id})" title="强制停止">
                    <i class="fas fa-stop"></i> 停止处理
                </button>
                <button class="btn btn-sm btn-outline-secondary" disabled title="处理中无法删除">
                    <i class="fas fa-trash"></i>
                </button>
            `;
        } else if (isReady) {
            statusBadge = `<span class="badge bg-success">就绪</span>`;
            actionButtons = `
                <button class="btn btn-sm btn-outline-primary" onclick="showUploadModalForKb(${kb.id})">
                    <i class="fas fa-upload"></i> 上传
                </button>
                <button class="btn btn-sm btn-outline-danger" onclick="deleteKnowledgeBase(${kb.id}, '${escapeHtml(kb.name)}')">
                    <i class="fas fa-trash"></i> 删除
                </button>
            `;
        }
        
        return `
            <div class="kb-card ${isProcessing ? 'kb-processing' : ''}" onclick="selectKbCard(${kb.id})">
                <div class="kb-card-header">
                    <div class="kb-card-title">${escapeHtml(kb.name)}</div>
                    <div class="kb-card-status">${statusBadge}</div>
                </div>
                <div class="kb-card-body">
                    ${kb.description ? escapeHtml(kb.description) : '<span class="text-muted">无描述</span>'}
                </div>
                <div class="kb-card-stats">
                    <span><i class="fas fa-file"></i> ${kb.document_count || 0} 文档</span>
                    <span><i class="fas fa-cubes"></i> ${kb.vector_stats?.total_vectors || 0} 向量</span>
                </div>
                <div class="kb-card-actions" onclick="event.stopPropagation();">
                    ${actionButtons}
                </div>
            </div>
        `;
    }).join('');
}

/**
 * 选择知识库卡片
 */
function selectKbCard(kbId) {
    document.querySelectorAll('.kb-card').forEach(card => {
        card.classList.remove('active');
    });
    event.target.closest('.kb-card').classList.add('active');
    
    // 保存当前选中的知识库ID
    currentSelectedKbId = kbId;
    
    // 加载详细信息和文档列表
    loadKbDetails(kbId);
    loadKbDocuments(kbId);
    
    // 显示文档面板
    const documentsPanel = document.getElementById('kb-documents-panel');
    if (documentsPanel) {
        documentsPanel.style.display = 'block';
    }
}

/**
 * 加载知识库详情
 */
async function loadKbDetails(kbId) {
    try {
        const response = await fetch(`/api/kb/${kbId}/stats`);
        const data = await response.json();
        
        if (data.success) {
            renderKbDetails(data.data);
        }
    } catch (error) {
        console.error('加载知识库详情失败:', error);
    }
}

/**
 * 渲染知识库详情
 */
function renderKbDetails(stats) {
    const container = document.getElementById('kb-details-content');
    
    if (!container) return;
    
    container.innerHTML = `
        <h6 class="mb-3">${escapeHtml(stats.kb_info.name)}</h6>
        <div class="mb-3">
            <div class="small text-muted mb-1">文档数量</div>
            <div class="h4 text-primary">${stats.document_count}</div>
        </div>
        <div class="mb-3">
            <div class="small text-muted mb-1">文档块数</div>
            <div class="h4 text-primary">${stats.total_chunks}</div>
        </div>
        <div class="mb-3">
            <div class="small text-muted mb-1">向量数量</div>
            <div class="h4 text-primary">${stats.vector_stats.total_vectors}</div>
        </div>
        <div class="mb-3">
            <div class="small text-muted mb-1">创建时间</div>
            <div class="small">${formatDate(stats.kb_info.created_at)}</div>
        </div>
    `;
}

/**
 * 强制停止知识库处理
 */
async function forceStopKbProcessing(kbId) {
    if (!confirm('确定要强制停止处理吗？这可能导致部分文档未完成处理。')) {
        return;
    }
    
    try {
        toggleLoading(true);
        
        const response = await fetch(`/api/kb/${kbId}/force-stop`, {
            method: 'POST'
        });
        
        const data = await response.json();
        
        if (data.success) {
            showToast('已停止处理，知识库状态已重置', 'success');
            // 刷新知识库列表
            await loadKnowledgeBasesGrid();
        } else {
            throw new Error(data.message);
        }
    } catch (error) {
        console.error('停止处理失败:', error);
        showToast(error.message || '停止处理失败', 'error');
    } finally {
        toggleLoading(false);
    }
}

/**
 * 更新选中知识库显示（已移除UI，保留函数以防其他代码调用）
 */
function updateSelectedKnowledgeBasesSidebar() {
    // 该功能已移除，选中状态现在直接在知识库列表中显示（绿色勾选）
    return;
}

/**
 * 渲染Markdown内容
 */
function renderMarkdown(content) {
    if (typeof marked === 'undefined') {
        return escapeHtml(content);
    }

    try {
        if (window.__markdownCache && window.__markdownCache.has(content)) {
            return window.__markdownCache.get(content);
        }

        // ========== v1.0规范：保护数学公式 ==========
        // 在 Marked 处理之前，先保护数学公式，避免被 Markdown 解析器破坏
        const mathPlaceholders = [];
        let protectedContent = content;
        
        // 1. 保护块级公式 $$...$$（必须在行内公式之前处理）
        protectedContent = protectedContent.replace(/\$\$[\s\S]+?\$\$/g, (match) => {
            const index = mathPlaceholders.length;
            mathPlaceholders.push(match);
            // 使用HTML注释作为占位符，Marked不会处理它
            return `<!--MATH_BLOCK_${index}-->`;
        });
        
        // 2. 保护行内公式 $...$
        protectedContent = protectedContent.replace(/\$(?!\$)[^$\n]+?\$/g, (match) => {
            const index = mathPlaceholders.length;
            mathPlaceholders.push(match);
            // 使用HTML注释作为占位符
            return `<!--MATH_INLINE_${index}-->`;
        });
        
        // 3. 使用 Marked 渲染 Markdown
        let rendered = marked.parse(protectedContent);
        
        // 4. 恢复数学公式占位符
        mathPlaceholders.forEach((math, index) => {
            // HTML注释会被保留在HTML中，直接替换即可
            rendered = rendered.replace(new RegExp(`<!--MATH_BLOCK_${index}-->`, 'g'), math);
            rendered = rendered.replace(new RegExp(`<!--MATH_INLINE_${index}-->`, 'g'), math);
        });
        // ========== 保护数学公式结束 ==========

        if (!window.__markdownCache) {
            window.__markdownCache = new Map();
        }
        if (window.__markdownCache.size > 50) {
            const firstKey = window.__markdownCache.keys().next().value;
            window.__markdownCache.delete(firstKey);
        }
        window.__markdownCache.set(content, rendered);

        return rendered;
    } catch (e) {
        console.error('Markdown渲染失败:', e);
        return escapeHtml(content);
    }
}

/**
 * 更新消息内容（支持Markdown）
 */
function updateMessageContentWithMarkdown(messageId, content) {
    const messageElement = document.getElementById(messageId);
    if (!messageElement) return;
    
    let contentElement = messageElement.querySelector('.message-content');
    if (!contentElement) {
        contentElement = document.createElement('div');
        contentElement.className = 'message-content';
        const messageBubble = messageElement.querySelector('.message-bubble');
        messageBubble.appendChild(contentElement);
    }
    
    // 渲染Markdown
    contentElement.innerHTML = renderMarkdown(content);
    
    // 高亮代码块
    if (typeof hljs !== 'undefined') {
        contentElement.querySelectorAll('pre code').forEach((block) => {
            hljs.highlightElement(block);
        });
    }
    
    // 渲染LaTeX数学公式
    renderMath(contentElement);
}

/**
 * 显示上传模态框（指定知识库）
 */
function showUploadModalForKb(kbId) {
    currentKbId = kbId;
    showUploadModal();
}

// 重写原来的updateSelectedKnowledgeBases函数，同时更新两个地方
// 选中知识库的更新逻辑已整合到知识库列表渲染中

console.log('✨ 新功能已加载：视图切换、Markdown渲染、强制停止处理');

/**
 * 加载知识库文档列表
 */
async function loadKbDocuments(kbId) {
    try {
        const response = await fetch(`/api/docs/list/${kbId}`);
        const data = await response.json();
        
        if (data.success) {
            renderKbDocuments(data.data);
        } else {
            throw new Error(data.message);
        }
    } catch (error) {
        console.error('加载文档列表失败:', error);
        const container = document.getElementById('kb-documents-list');
        if (container) {
            container.innerHTML = '<div class="text-danger text-center p-3">加载文档失败</div>';
        }
    }
}

/**
 * 渲染知识库文档列表
 */
function renderKbDocuments(documents) {
    const container = document.getElementById('kb-documents-list');
    
    if (!container) return;
    
    if (documents.length === 0) {
        container.innerHTML = `
            <div class="text-center text-muted p-4">
                <i class="fas fa-file-text fa-2x mb-2"></i>
                <p class="small mb-0">暂无文档</p>
            </div>
        `;
        return;
    }
    
    container.innerHTML = documents.map(doc => `
        <div class="doc-item-simple">
            <div class="doc-item-icon">
                <i class="fas fa-file-text"></i>
            </div>
            <div class="doc-item-info">
                <div class="doc-item-name">${escapeHtml(doc.name)}</div>
                <div class="doc-item-meta">
                    <span><i class="fas fa-cubes"></i> ${doc.chunk_count || 0}块</span>
                    <span class="ms-2">${formatDate(doc.created_at)}</span>
                </div>
            </div>
            <div class="doc-item-actions">
                <button class="btn btn-sm btn-outline-danger" 
                        onclick="deleteDocumentFromKb(${doc.id}, '${escapeHtml(doc.name)}')" 
                        title="删除">
                    <i class="fas fa-trash"></i>
                </button>
            </div>
        </div>
    `).join('');
}

/**
 * 从知识库删除文档
 */
async function deleteDocumentFromKb(docId, docName) {
    if (!confirm(`确定要删除文档"${docName}"吗？`)) {
        return;
    }
    
    try {
        toggleLoading(true);
        
        const response = await fetch(`/api/docs/${docId}/delete`, {
            method: 'DELETE'
        });
        
        const data = await response.json();
        
        if (data.success) {
            showToast('文档删除成功', 'success');
            // 刷新文档列表和统计信息
            if (currentSelectedKbId) {
                loadKbDocuments(currentSelectedKbId);
                loadKbDetails(currentSelectedKbId);
            }
            // 同时刷新知识库列表（更新文档数量）
            loadKnowledgeBasesGrid();
        } else {
            throw new Error(data.message);
        }
    } catch (error) {
        console.error('删除文档失败:', error);
        showToast(error.message || '删除文档失败', 'error');
    } finally {
        toggleLoading(false);
    }
}

console.log('✨ 文档管理功能已加载');

/**
 * 更新工具项状态
 */
function updateToolCallStatus(toolItem, status, executionTime = null) {
    const statusElement = toolItem.querySelector('.tool-call-status');
    if (!statusElement) return;
    
    if (status === 'success') {
        const timeStr = executionTime ? ` (${(executionTime * 1000).toFixed(0)}ms)` : '';
        statusElement.innerHTML = `
            <i class="fas fa-check-circle text-success me-1"></i>
            完成${timeStr}
        `;
    } else if (status === 'error') {
        statusElement.innerHTML = `
            <i class="fas fa-exclamation-circle text-danger me-1"></i>
            失败
        `;
    }
}

/**
 * 检查是否所有工具调用都已经完成
 */
function checkToolCallsAllDone(container) {
    if (!container) return;
    const statusElement = container.querySelector('.tool-calls-status');
    const runningItems = container.querySelectorAll('.tool-call-item.tool-call-running');
    if (statusElement && runningItems.length === 0) {
        statusElement.textContent = '全部工具执行完成';
    }
}

/**
 * 下载LLM IO载荷
 */
function downloadLLMIO(messageId) {
    // 获取processLog数据
    const processData = window.toolDetailsData?.[`process-${messageId}`];
    if (!processData || !processData.data) {
        showToast('无法获取处理日志数据', 'warning');
        return;
    }
    
    // 如果有request_id，使用后端API下载完整的LLM调用载荷
    if (processData.request_id) {
        downloadFromBackend(processData.request_id);
        return;
    }
    
    // 否则使用本地processLog生成（fallback）
    const processLog = processData.data;
    
    // 格式化为易读的Markdown文本
    let content = '';
    content += '# LLM调用载荷详情\n\n';
    content += `**生成时间**: ${new Date().toLocaleString('zh-CN')}\n\n`;
    content += '---\n\n';
    
    // 用户问题
    content += '## 用户问题\n\n';
    content += `${processLog.user_query || '（无记录）'}\n\n`;
    content += '---\n\n';
    
    // 统计信息
    content += '## 统计摘要\n\n';
    content += `- 迭代次数: ${processLog.iteration_count || 0}\n`;
    content += `- 工具调用总数: ${processLog.tools_log?.length || 0}\n`;
    
    // 工具调用统计
    if (processLog.tool_call_counts) {
        content += '\n**工具调用次数**:\n';
        for (const [tool, count] of Object.entries(processLog.tool_call_counts)) {
            const limit = processLog.tool_call_limits?.[tool] || 0;
            content += `- ${tool}: ${count}/${limit}次\n`;
        }
    }
    
    content += '\n---\n\n';
    
    // 工具调用详情
    if (processLog.tools_log && processLog.tools_log.length > 0) {
        content += '## 工具调用详情\n\n';
        
        processLog.tools_log.forEach((log, index) => {
            content += `### 调用 #${index + 1}: ${log.tool}\n\n`;
            content += `- **查询**: ${log.query}\n`;
            content += `- **耗时**: ${log.execution_time?.toFixed(3)}秒\n`;
            content += `- **时间戳**: ${new Date(log.timestamp * 1000).toLocaleString('zh-CN')}\n\n`;
            
            // 参数
            if (log.args && Object.keys(log.args).length > 0) {
                content += '**参数**:\n```json\n';
                content += JSON.stringify(log.args, null, 2);
                content += '\n```\n\n';
            }
            
            // 结果摘要
            content += `**结果摘要**: ${log.result_summary}\n\n`;
            
            // 完整结果 - 格式化显示
            if (log.full_result) {
                content += '**完整结果**:\n\n';
                
                // 如果是代码执行结果
                if (log.full_result.code) {
                    content += '```python\n' + log.full_result.code + '\n```\n\n';
                    if (log.full_result.output) {
                        content += '**输出**:\n```\n' + log.full_result.output + '\n```\n\n';
                    }
                    if (log.full_result.error) {
                        content += '**错误**: ' + log.full_result.error + '\n\n';
                    }
                }
                // 如果是检索结果
                else if (log.full_result.chunks) {
                    content += `检索到 ${log.full_result.chunks.length} 条文档\n\n`;
                    log.full_result.chunks.slice(0, 3).forEach((chunk, i) => {
                        content += `**文档 ${i+1}** (相关度: ${chunk.score?.toFixed(3) || 'N/A'}):\n`;
                        const preview = chunk.text?.substring(0, 200) || chunk.content?.substring(0, 200) || '';
                        content += `${preview}...\n\n`;
                    });
                }
                // 如果是网络搜索结果
                else if (log.full_result.results || log.full_result.web_search_results) {
                    const results = log.full_result.results || log.full_result.web_search_results;
                    content += `找到 ${results.length} 条网络搜索结果\n\n`;
                    results.slice(0, 3).forEach((result, i) => {
                        content += `**结果 ${i+1}**: ${result.title || '无标题'}\n`;
                        content += `- URL: ${result.url || 'N/A'}\n`;
                        const preview = result.content?.substring(0, 150) || '';
                        if (preview) content += `- 摘要: ${preview}...\n`;
                        content += '\n';
                    });
                }
                // 其他类型：显示JSON
                else {
                    content += '```json\n';
                    content += JSON.stringify(log.full_result, null, 2);
                    content += '\n```\n\n';
                }
            }
            
            content += '---\n\n';
        });
    }
    
    // 评估历史
    if (processLog.evaluations && processLog.evaluations.length > 0) {
        content += '## 评估历史\n\n';
        processLog.evaluations.forEach((eval, index) => {
            content += `### 评估 #${index + 1}\n\n`;
            content += `- **应该回答**: ${eval.should_answer ? '是' : '否'}\n`;
            content += `- **理由**: ${eval.reason}\n`;
            if (eval.confidence !== undefined) {
                content += `- **置信度**: ${(eval.confidence * 100).toFixed(1)}%\n`;
            }
            content += '\n';
        });
        content += '\n---\n\n';
    }
    
    // 最终答案
    if (processLog.final_answer) {
        content += '## 最终答案\n\n';
        content += processLog.final_answer;
        content += '\n\n---\n\n';
    }
    
    // 最终评估
    if (processLog.final_evaluation) {
        content += '## 最终评估\n\n';
        content += `- **置信度**: ${(processLog.final_evaluation.confidence * 100).toFixed(1)}%\n`;
        content += `- **评估**: ${processLog.final_evaluation.reason}\n`;
    }
    
    // 创建Blob并下载
    const blob = new Blob([content], { type: 'text/markdown;charset=utf-8' });
    const url = URL.createObjectURL(blob);
    const a = document.createElement('a');
    a.href = url;
    const timestamp = new Date().toISOString().replace(/[:.]/g, '-').slice(0, -5);
    a.download = `llm-io-${messageId}-${timestamp}.md`;
    document.body.appendChild(a);
    a.click();
    document.body.removeChild(a);
    URL.revokeObjectURL(url);
    
    showToast('LLM IO已下载', 'success');
}

/**
 * 从后端下载完整的LLM IO载荷
 */
function downloadFromBackend(requestId) {
    if (!requestId) {
        showToast('无效的请求ID', 'error');
        return;
    }
    
    showToast('正在生成LLM IO文件...', 'info');
    
    // 创建一个隐藏的iframe来下载文件
    const iframe = document.createElement('iframe');
    iframe.style.display = 'none';
    iframe.src = `/api/v2/download_llm_io/${requestId}`;
    
    // 添加iframe到页面
    document.body.appendChild(iframe);
    
    // 5秒后移除iframe
    setTimeout(() => {
        document.body.removeChild(iframe);
        showToast('LLM IO已下载', 'success');
    }, 5000);
    
    // 错误处理：如果5秒后还没下载成功，提示用户
    setTimeout(() => {
        // 这里可以添加额外的错误检查
    }, 6000);
}

// ================ 思维链计时器功能 ================

/**
 * 启动思考计时器
 */
function startThinkingTimer(messageId) {
    // 如果已经存在计时器，先停止它
    if (thinkingTimers[messageId]) {
        stopThinkingTimer(messageId);
    }
    
    // 初始化计时器数据
    thinkingTimers[messageId] = {
        startTime: Date.now(),
        intervalId: null
    };
    
    // 立即更新一次
    updateThinkingTime(messageId);
    
    // 每秒更新一次
    thinkingTimers[messageId].intervalId = setInterval(() => {
        updateThinkingTime(messageId);
    }, 1000);
}

/**
 * 更新思考时间显示
 */
function updateThinkingTime(messageId) {
    const timer = thinkingTimers[messageId];
    if (!timer) return;
    
    const timeElement = document.getElementById(`${messageId}-thinking-time`);
    if (!timeElement) return;
    
    const elapsed = Math.floor((Date.now() - timer.startTime) / 1000);
    timeElement.textContent = `${elapsed}s`;
}

/**
 * 停止思考计时器
 */
function stopThinkingTimer(messageId) {
    const timer = thinkingTimers[messageId];
    if (!timer) return;
    
    // 清除定时器
    if (timer.intervalId) {
        clearInterval(timer.intervalId);
        timer.intervalId = null;
    }
    
    // 最后更新一次时间
    updateThinkingTime(messageId);
    
    // 更新标题
    const container = document.getElementById(`${messageId}-tools`);
    if (container) {
        const titleElement = container.querySelector('.tool-calls-title');
        if (titleElement) {
            titleElement.textContent = '已思考';
        }
        // 添加完成状态类
        container.classList.add('tool-calls-completed');
    }
}

/**
 * 清理计时器数据
 */
function cleanupThinkingTimer(messageId) {
    if (thinkingTimers[messageId]) {
        if (thinkingTimers[messageId].intervalId) {
            clearInterval(thinkingTimers[messageId].intervalId);
        }
        delete thinkingTimers[messageId];
    }
}

// ==================== 文件上传功能 ====================

let uploadedFiles = [];  // 已上传的文件列表

/**
 * 切换文件上传区域显示/隐藏
 */
function toggleFileUpload() {
    const uploadArea = document.getElementById('file-upload-area');
    const toggleBtn = document.getElementById('file-upload-toggle-btn');
    
    if (uploadArea.style.display === 'none') {
        uploadArea.style.display = 'block';
        toggleBtn.classList.add('active');
        loadUploadedFiles();  // 加载已上传的文件列表
    } else {
        uploadArea.style.display = 'none';
        toggleBtn.classList.remove('active');
    }
}

/**
 * 处理文件选择
 */
function handleFileSelect(event) {
    const files = event.target.files;
    if (files.length === 0) return;
    
    uploadFiles(files);
}

/**
 * 上传文件
 */
async function uploadFiles(files) {
    const formData = new FormData();
    
    // 验证文件类型
    for (let file of files) {
        const fileName = file.name.toLowerCase();
        if (!fileName.endsWith('.csv') && !fileName.endsWith('.xlsx')) {
            showToast('错误', `文件 ${file.name} 格式不支持，仅支持 .csv 和 .xlsx 文件`, 'error');
            return;
        }
        formData.append('files', file);
    }
    
    try {
        const response = await fetch('/api/upload_files', {
            method: 'POST',
            body: formData
        });
        
        const data = await response.json();
        
        if (data.success) {
            showToast('成功', data.message, 'success');
            loadUploadedFiles();  // 重新加载文件列表
            
            // 清空文件输入
            document.getElementById('data-file-input').value = '';
        } else {
            showToast('错误', data.error || '上传失败', 'error');
        }
    } catch (error) {
        console.error('上传文件失败:', error);
        showToast('错误', '上传文件失败: ' + error.message, 'error');
    }
}

/**
 * 加载已上传的文件列表
 */
async function loadUploadedFiles() {
    try {
        const response = await fetch('/api/list_files');
        const data = await response.json();
        
        if (data.success) {
            uploadedFiles = data.files;
            displayUploadedFiles();
        } else {
            console.error('加载文件列表失败:', data.error);
        }
    } catch (error) {
        console.error('加载文件列表失败:', error);
    }
}

/**
 * 显示已上传的文件列表
 */
function displayUploadedFiles() {
    const listContainer = document.getElementById('uploaded-files-list');
    
    if (uploadedFiles.length === 0) {
        listContainer.innerHTML = '<p class="text-muted text-center py-2">暂无上传文件</p>';
        return;
    }
    
    listContainer.innerHTML = uploadedFiles.map(file => `
        <div class="uploaded-file-item">
            <div class="file-item-info">
                <i class="fas fa-file-${file.type === 'csv' ? 'csv' : 'excel'}"></i>
                <span class="file-item-name" title="${file.filename}">${file.filename}</span>
                <span class="file-item-size">(${file.size_str})</span>
            </div>
            <div class="file-item-actions">
                <button class="delete-btn" onclick="deleteFile('${file.filename}')" title="删除">
                    <i class="fas fa-trash"></i>
                </button>
            </div>
        </div>
    `).join('');
}

/**
 * 删除文件
 */
async function deleteFile(filename) {
    if (!confirm(`确定要删除文件 ${filename} 吗？`)) {
        return;
    }
    
    try {
        const response = await fetch(`/api/delete_file/${encodeURIComponent(filename)}`, {
            method: 'DELETE'
        });
        
        const data = await response.json();
        
        if (data.success) {
            showToast('成功', data.message, 'success');
            loadUploadedFiles();  // 重新加载文件列表
        } else {
            showToast('错误', data.error || '删除失败', 'error');
        }
    } catch (error) {
        console.error('删除文件失败:', error);
        showToast('错误', '删除文件失败: ' + error.message, 'error');
    }
}

/**
 * 清空所有已上传的文件
 */
async function clearUploadedFiles() {
    if (!confirm('确定要清空所有已上传的文件吗？')) {
        return;
    }
    
    try {
        const response = await fetch('/api/clear_files', {
            method: 'POST'
        });
        
        const data = await response.json();
        
        if (data.success) {
            showToast('成功', data.message, 'success');
            loadUploadedFiles();  // 重新加载文件列表
        } else {
            showToast('错误', data.error || '清空失败', 'error');
        }
    } catch (error) {
        console.error('清空文件失败:', error);
        showToast('错误', '清空文件失败: ' + error.message, 'error');
    }
}

/**
 * 设置拖拽上传
 */
function setupDragAndDrop() {
    const dropzone = document.getElementById('file-dropzone');
    
    if (!dropzone) return;
    
    // 防止默认拖拽行为
    ['dragenter', 'dragover', 'dragleave', 'drop'].forEach(eventName => {
        dropzone.addEventListener(eventName, preventDefaults, false);
        document.body.addEventListener(eventName, preventDefaults, false);
    });
    
    function preventDefaults(e) {
        e.preventDefault();
        e.stopPropagation();
    }
    
    // 高亮效果
    ['dragenter', 'dragover'].forEach(eventName => {
        dropzone.addEventListener(eventName, () => {
            dropzone.classList.add('drag-over');
        }, false);
    });
    
    ['dragleave', 'drop'].forEach(eventName => {
        dropzone.addEventListener(eventName, () => {
            dropzone.classList.remove('drag-over');
        }, false);
    });
    
    // 处理文件拖放
    dropzone.addEventListener('drop', function(e) {
        const dt = e.dataTransfer;
        const files = dt.files;
        
        if (files.length > 0) {
            uploadFiles(files);
        }
    }, false);
}

// 初始化拖拽上传（在页面加载后调用）
if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', setupDragAndDrop);
} else {
    setupDragAndDrop();
}

// ============================================================================
// 文件管理功能（新增）
// ============================================================================

/**
 * 显示文件上传模态框
 */
function showFileUploadModal() {
    const modal = new bootstrap.Modal(document.getElementById('fileUploadModal'));
    modal.show();
    
    // 监听文件选择
    const fileInput = document.getElementById('data-files-input');
    fileInput.addEventListener('change', function() {
        const files = Array.from(this.files);
        if (files.length > 0) {
            displaySelectedDataFiles(files);
        }
    });
}

/**
 * 显示选中的数据文件
 */
function displaySelectedDataFiles(files) {
    const preview = document.getElementById('data-files-preview');
    const list = document.getElementById('data-files-list');
    
    list.innerHTML = '';
    files.forEach(file => {
        const fileItem = document.createElement('div');
        fileItem.className = 'mb-2';
        fileItem.innerHTML = `
            <i class="fas fa-file-${file.name.endsWith('.csv') ? 'csv' : 'excel'} me-2"></i>
            ${file.name} (${formatFileSize(file.size)})
        `;
        list.appendChild(fileItem);
    });
    
    preview.style.display = 'block';
}

/**
 * 上传数据文件
 */
async function uploadDataFiles() {
    const fileInput = document.getElementById('data-files-input');
    const files = fileInput.files;
    
    if (files.length === 0) {
        showToast('提示', '请选择要上传的文件', 'warning');
        return;
    }
    
    const formData = new FormData();
    for (let i = 0; i < files.length; i++) {
        formData.append('files', files[i]);
    }
    
    try {
        const response = await fetch('/api/upload_files', {
            method: 'POST',
            body: formData
        });
        
        const data = await response.json();
        
        if (data.success) {
            showToast('成功', `成功上传 ${data.uploaded_count} 个文件`, 'success');
            
            // 关闭模态框
            const modal = bootstrap.Modal.getInstance(document.getElementById('fileUploadModal'));
            modal.hide();
            
            // 清空表单
            fileInput.value = '';
            document.getElementById('data-files-preview').style.display = 'none';
            
            // 刷新文件列表
            loadFileManagementList();
        } else {
            showToast('错误', data.error || '上传失败', 'error');
        }
    } catch (error) {
        console.error('上传文件失败:', error);
        showToast('错误', '上传文件失败: ' + error.message, 'error');
    }
}

/**
 * 加载文件管理列表
 */
async function loadFileManagementList() {
    try {
        const response = await fetch('/api/list_files');
        const data = await response.json();
        
        const container = document.getElementById('file-management-list');
        
        if (!data.success || data.files.length === 0) {
            container.innerHTML = `
                <div class="text-center text-muted py-5">
                    <i class="fas fa-folder-open fa-3x mb-3"></i>
                    <p>暂无上传的文件</p>
                    <button class="btn btn-outline-primary" onclick="showFileUploadModal()">
                        <i class="fas fa-upload me-1"></i> 上传第一个文件
                    </button>
                </div>
            `;
            return;
        }
        
        // 渲染文件列表
        let html = '<div class="table-responsive"><table class="table table-hover">';
        html += '<thead><tr><th>文件名</th><th>大小</th><th>上传时间</th><th>操作</th></tr></thead><tbody>';
        
        data.files.forEach(file => {
            const icon = file.filename.endsWith('.csv') ? 'file-csv' : 'file-excel';
            html += `
                <tr>
                    <td><i class="fas fa-${icon} me-2"></i>${file.filename}</td>
                    <td>${formatFileSize(file.size)}</td>
                    <td>${formatDate(file.modified_time)}</td>
                    <td>
                        <button class="btn btn-sm btn-danger" onclick="deleteDataFile('${file.filename}')">
                            <i class="fas fa-trash"></i>
                        </button>
                    </td>
                </tr>
            `;
        });
        
        html += '</tbody></table></div>';
        container.innerHTML = html;
        
    } catch (error) {
        console.error('加载文件列表失败:', error);
        showToast('错误', '加载文件列表失败', 'error');
    }
}

/**
 * 删除数据文件
 */
async function deleteDataFile(filename) {
    if (!confirm(`确定要删除文件 "${filename}" 吗？`)) {
        return;
    }
    
    try {
        const response = await fetch(`/api/delete_file/${encodeURIComponent(filename)}`, {
            method: 'DELETE'
        });
        
        const data = await response.json();
        
        if (data.success) {
            showToast('成功', '文件已删除', 'success');
            loadFileManagementList();
        } else {
            showToast('错误', data.error || '删除失败', 'error');
        }
    } catch (error) {
        console.error('删除文件失败:', error);
        showToast('错误', '删除文件失败', 'error');
    }
}

/**
 * 格式化文件大小
 */
function formatFileSize(bytes) {
    if (bytes === 0) return '0 B';
    const k = 1024;
    const sizes = ['B', 'KB', 'MB', 'GB'];
    const i = Math.floor(Math.log(bytes) / Math.log(k));
    return parseFloat((bytes / Math.pow(k, i)).toFixed(2)) + ' ' + sizes[i];
}

// 监听标签页切换，加载文件列表
document.addEventListener('DOMContentLoaded', function() {
    const fileManagementTab = document.getElementById('file-management-tab');
    if (fileManagementTab) {
        fileManagementTab.addEventListener('shown.bs.tab', function() {
            loadFileManagementList();
        });
    }
    
    // 监听Lite模式切换，禁用/启用文件选择按钮
    const liteCheckbox = document.getElementById('use-lite-mode');
    if (liteCheckbox) {
        liteCheckbox.addEventListener('change', function() {
            updateFileSelectButtonState();
        });
    }
});

// ==================== 文件选择器功能 ====================

// 已选择的文件列表
let selectedFiles = [];

/**
 * 切换文件选择器面板显示
 */
function toggleFileSelector() {
    const panel = document.getElementById('file-selector-panel');
    const isVisible = panel.style.display !== 'none';
    
    if (isVisible) {
        panel.style.display = 'none';
    } else {
        panel.style.display = 'block';
        loadAvailableFiles();
    }
}

/**
 * 加载可用文件列表
 */
async function loadAvailableFiles() {
    try {
        const response = await fetch('/api/list_files');
        const data = await response.json();
        
        const container = document.getElementById('available-files-list');
        
        if (data.success && data.files && data.files.length > 0) {
            let html = '';
            data.files.forEach(file => {
                const isSelected = selectedFiles.some(f => f.filename === file.filename);
                const icon = getFileIcon(file.filename);
                html += `
                    <div class="file-item ${isSelected ? 'selected' : ''}" onclick="toggleFileSelection('${file.filename}', ${file.size})">
                        <div class="file-item-info">
                            <div class="file-item-icon">
                                <i class="fas fa-${icon}"></i>
                            </div>
                            <div>
                                <div class="file-item-name">${file.filename}</div>
                                <div class="file-item-meta">${formatFileSize(file.size)}</div>
                            </div>
                        </div>
                        ${isSelected ? '<i class="fas fa-check text-success"></i>' : ''}
                    </div>
                `;
            });
            container.innerHTML = html;
        } else {
            container.innerHTML = '<div class="text-muted text-center py-3">暂无可用文件</div>';
        }
        
        updateSelectedFilesList();
    } catch (error) {
        console.error('加载文件列表失败:', error);
        showToast('加载文件列表失败', 'error');
    }
}

/**
 * 获取文件图标
 */
function getFileIcon(filename) {
    const ext = filename.split('.').pop().toLowerCase();
    switch(ext) {
        case 'csv': return 'file-csv';
        case 'xlsx':
        case 'xls': return 'file-excel';
        default: return 'file';
    }
}

/**
 * 切换文件选择状态
 */
function toggleFileSelection(filename, size) {
    const index = selectedFiles.findIndex(f => f.filename === filename);
    
    if (index > -1) {
        selectedFiles.splice(index, 1);
    } else {
        selectedFiles.push({ filename, size });
    }
    
    loadAvailableFiles();
    updateFileSelectButtonState();
}

/**
 * 更新已选择文件列表显示
 */
function updateSelectedFilesList() {
    const container = document.getElementById('selected-files-list');
    const section = document.getElementById('selected-files-section');
    
    if (selectedFiles.length === 0) {
        section.style.display = 'none';
        return;
    }
    
    section.style.display = 'block';
    let html = '';
    selectedFiles.forEach(file => {
        html += `
            <div class="selected-file-tag">
                <i class="fas fa-${getFileIcon(file.filename)}"></i>
                <span>${file.filename}</span>
                <span class="remove-file" onclick="removeSelectedFile('${file.filename}')">
                    <i class="fas fa-times"></i>
                </span>
            </div>
        `;
    });
    container.innerHTML = html;
}

/**
 * 移除已选择的文件
 */
function removeSelectedFile(filename) {
    selectedFiles = selectedFiles.filter(f => f.filename !== filename);
    loadAvailableFiles();
    updateFileSelectButtonState();
}

/**
 * 更新文件选择按钮状态
 */
function updateFileSelectButtonState() {
    const btn = document.getElementById('file-select-btn');
    const isLiteMode = document.getElementById('use-lite-mode').checked;
    
    // Lite模式下禁用按钮
    if (isLiteMode) {
        btn.disabled = true;
        btn.title = 'Lite模式不支持文件分析';
        selectedFiles = [];
        updateSelectedFilesList();
    } else {
        btn.disabled = false;
        btn.title = '选择文件';
    }
    
    // 根据是否有选中文件更新按钮样式
    if (selectedFiles.length > 0) {
        btn.classList.add('has-files');
    } else {
        btn.classList.remove('has-files');
    }
}

/**
 * 触发文件上传
 */
function triggerFileUpload() {
    document.getElementById('file-upload-input').click();
}

/**
 * 处理文件上传
 */
async function handleFileUpload(event) {
    const file = event.target.files[0];
    if (!file) return;
    
    const formData = new FormData();
    formData.append('file', file);
    
    try {
        showToast('正在上传文件...', 'info');
        
        const response = await fetch('/api/upload_file', {
            method: 'POST',
            body: formData
        });
        
        const data = await response.json();
        
        if (data.success) {
            showToast('文件上传成功', 'success');
            // 自动选中新上传的文件
            selectedFiles.push({
                filename: data.filename,
                size: file.size
            });
            loadAvailableFiles();
            updateFileSelectButtonState();
        } else {
            showToast(data.error || '文件上传失败', 'error');
        }
    } catch (error) {
        console.error('文件上传失败:', error);
        showToast('文件上传失败', 'error');
    }
    
    // 重置文件输入
    event.target.value = '';
}

/**
 * 获取选中的文件名列表
 */
function getSelectedFileNames() {
    return selectedFiles.map(f => f.filename);
}
