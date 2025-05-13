// UI组件类
class UI {
    constructor() {
        this.modal = document.getElementById('modal');
        this.modalContent = document.getElementById('modalContent');
        this.closeModalBtn = document.querySelector('.close');
        this.currentUser = null;
        this.setupEventListeners();
    }

    // 设置事件监听器
    setupEventListeners() {
        // 导航切换
        document.querySelectorAll('.nav-links li').forEach(item => {
            item.addEventListener('click', () => this.switchPage(item.dataset.page));
        });

        // 模态框关闭
        this.closeModalBtn.addEventListener('click', () => this.closeModal());
        window.addEventListener('click', (e) => {
            if (e.target === this.modal) this.closeModal();
        });

        // 按钮事件
        document.getElementById('createAuthorBtn').addEventListener('click', () => this.showCreateAuthorModal());
        document.getElementById('createPaperBtn').addEventListener('click', () => this.showCreatePaperModal());
        document.getElementById('createCitationBtn').addEventListener('click', () => this.showCreateCitationModal());
        document.getElementById('burnTokensBtn').addEventListener('click', () => this.showBurnTokensModal());
        document.getElementById('connectWallet').addEventListener('click', () => this.connectWallet());
    }

    // 页面切换
    switchPage(pageId) {
        document.querySelectorAll('.page').forEach(page => {
            page.classList.remove('active');
        });
        document.getElementById(pageId).classList.add('active');

        document.querySelectorAll('.nav-links li').forEach(item => {
            item.classList.remove('active');
        });
        document.querySelector(`[data-page="${pageId}"]`).classList.add('active');

        // 加载页面数据
        this.loadPageData(pageId);
    }

    // 加载页面数据
    async loadPageData(pageId) {
        try {
            switch (pageId) {
                case 'dashboard':
                    await this.loadDashboardData();
                    break;
                case 'authors':
                    await this.loadAuthorsData();
                    break;
                case 'papers':
                    await this.loadPapersData();
                    break;
                case 'citations':
                    await this.loadCitationsData();
                    break;
                case 'tokens':
                    await this.loadTokensData();
                    break;
            }
        } catch (error) {
            this.showError('Failed to load page data: ' + error.message);
        }
    }

    // 加载仪表盘数据
    async loadDashboardData() {
        const [networkStats, tokenStats] = await Promise.all([
            API.getNetworkStats(),
            API.getTokenStats()
        ]);

        // 更新统计卡片
        document.getElementById('totalPapers').textContent = networkStats.total_papers;
        document.getElementById('totalCitations').textContent = networkStats.total_citations;
        document.getElementById('totalAuthors').textContent = tokenStats.total_authors;
        document.getElementById('totalTokens').textContent = tokenStats.total_supply.toFixed(4);

        // 更新图表
        this.updateCitationNetworkChart(networkStats);
    }

    // 更新引用网络图表
    updateCitationNetworkChart(stats) {
        const ctx = document.getElementById('citationNetwork');
        // 使用vis.js创建网络图
        const nodes = new vis.DataSet([
            { id: 1, label: 'Papers', value: stats.total_papers },
            { id: 2, label: 'Citations', value: stats.total_citations }
        ]);

        const edges = new vis.DataSet([
            { from: 1, to: 2, value: stats.average_citations }
        ]);

        const data = { nodes, edges };
        const options = {
            nodes: {
                shape: 'dot',
                size: 20
            },
            edges: {
                width: 2
            }
        };

        new vis.Network(ctx, data, options);
    }

    // 显示创建作者模态框
    showCreateAuthorModal() {
        const content = `
            <h2>Create New Author</h2>
            <form id="createAuthorForm">
                <div class="form-group">
                    <label for="authorName">Name</label>
                    <input type="text" id="authorName" required>
                </div>
                <button type="submit" class="btn-primary">Create Author</button>
            </form>
        `;
        this.showModal(content);

        document.getElementById('createAuthorForm').addEventListener('submit', async (e) => {
            e.preventDefault();
            try {
                const name = document.getElementById('authorName').value;
                const keys = await API.generateKeys();
                const author = await API.createAuthor(name, keys.public_key);
                this.showSuccess('Author created successfully!');
                this.closeModal();
                await this.loadAuthorsData();
            } catch (error) {
                this.showError('Failed to create author: ' + error.message);
            }
        });
    }

    // 显示创建论文模态框
    async showCreatePaperModal() {
        if (!this.currentUser) {
            this.showError('Please connect your wallet first');
            return;
        }

        const content = `
            <h2>Create New Paper</h2>
            <form id="createPaperForm">
                <div class="form-group">
                    <label for="paperTitle">Title</label>
                    <input type="text" id="paperTitle" required>
                </div>
                <button type="submit" class="btn-primary">Create Paper</button>
            </form>
        `;
        this.showModal(content);

        document.getElementById('createPaperForm').addEventListener('submit', async (e) => {
            e.preventDefault();
            try {
                const title = document.getElementById('paperTitle').value;
                // 使用特定的消息进行签名
                const message = `Create paper: ${title}`;
                const signResponse = await API.signMessage(this.currentUser.privateKey, message);
                const paper = await API.createPaper(
                    title,
                    [this.currentUser.id],
                    this.currentUser.publicKey,
                    signResponse.signature,
                    message
                );
                this.showSuccess('Paper created successfully!');
                this.closeModal();
                await this.loadPapersData();
            } catch (error) {
                this.showError('Failed to create paper: ' + error.message);
            }
        });
    }

    // 显示创建引用模态框
    async showCreateCitationModal() {
        if (!this.currentUser) {
            this.showError('Please connect your wallet first');
            return;
        }

        const content = `
            <h2>Create New Citation</h2>
            <form id="createCitationForm">
                <div class="form-group">
                    <label for="citingPaper">Citing Paper</label>
                    <select id="citingPaper" required></select>
                </div>
                <div class="form-group">
                    <label for="citedPaper">Cited Paper</label>
                    <select id="citedPaper" required></select>
                </div>
                <button type="submit" class="btn-primary">Create Citation</button>
            </form>
        `;
        this.showModal(content);

        // 加载论文列表
        await this.loadPapersForCitation();

        document.getElementById('createCitationForm').addEventListener('submit', async (e) => {
            e.preventDefault();
            try {
                const citingPaperId = document.getElementById('citingPaper').value;
                const citedPaperId = document.getElementById('citedPaper').value;
                
                // 获取论文标题用于消息
                const [citingPaper, citedPaper] = await Promise.all([
                    API.getPaper(citingPaperId),
                    API.getPaper(citedPaperId)
                ]);
                
                // 使用特定的消息进行签名
                const message = `Create citation from "${citingPaper.title}" to "${citedPaper.title}"`;
                const signResponse = await API.signMessage(this.currentUser.privateKey, message);
                
                const citation = await API.createCitation(
                    citingPaperId,
                    citedPaperId,
                    this.currentUser.publicKey,
                    signResponse.signature,
                    message
                );
                this.showSuccess('Citation created successfully!');
                this.closeModal();
                await this.loadCitationsData();
            } catch (error) {
                this.showError('Failed to create citation: ' + error.message);
            }
        });
    }

    // 显示销毁代币模态框
    showBurnTokensModal() {
        if (!this.currentUser) {
            this.showError('Please connect your wallet first');
            return;
        }

        const content = `
            <h2>Burn Tokens</h2>
            <form id="burnTokensForm">
                <div class="form-group">
                    <label for="burnAmount">Amount to Burn</label>
                    <input type="number" id="burnAmount" step="0.0001" min="0" required>
                </div>
                <button type="submit" class="btn-danger">Burn Tokens</button>
            </form>
        `;
        this.showModal(content);

        document.getElementById('burnTokensForm').addEventListener('submit', async (e) => {
            e.preventDefault();
            try {
                const amount = parseFloat(document.getElementById('burnAmount').value);
                const signResponse = await API.signMessage(this.currentUser.privateKey);
                await API.burnTokens(
                    this.currentUser.id,
                    amount,
                    this.currentUser.publicKey,
                    signResponse.signature
                );
                this.showSuccess('Tokens burned successfully!');
                this.closeModal();
                await this.loadTokensData();
            } catch (error) {
                this.showError('Failed to burn tokens: ' + error.message);
            }
        });
    }

    // 连接钱包
    async connectWallet() {
        try {
            // 显示选择作者模态框
            const content = `
                <h2>Connect Wallet</h2>
                <div class="wallet-connect-options">
                    <div class="option-section">
                        <h3>Select Existing Author</h3>
                        <select id="existingAuthors" class="form-control">
                            <option value="">Select an author...</option>
                        </select>
                        <button id="selectAuthorBtn" class="btn-primary" style="margin-top: 10px;">Connect Selected Author</button>
                    </div>
                    <div class="option-section" style="margin-top: 20px;">
                        <h3>Create New Author</h3>
                        <form id="createAuthorForm">
                            <div class="form-group">
                                <label for="authorName">Author Name</label>
                                <input type="text" id="authorName" required>
                            </div>
                            <button type="submit" class="btn-primary">Create & Connect</button>
                        </form>
                    </div>
                </div>
            `;
            this.showModal(content);

            // 加载现有作者列表
            const authors = await API.request('/authors');
            const select = document.getElementById('existingAuthors');
            select.innerHTML = '<option value="">Select an author...</option>' + 
                authors.map(author => 
                    `<option value="${author.id}">${author.name}</option>`
                ).join('');

            // 处理选择现有作者
            document.getElementById('selectAuthorBtn').addEventListener('click', async () => {
                const select = document.getElementById('existingAuthors');
                if (!select.value) {
                    this.showError('Please select an author');
                    return;
                }

                try {
                    // 为现有作者生成新的密钥对
                    const keys = await API.generateKeys();
                    const signResponse = await API.signMessage(keys.private_key);
                    
                    // 存储用户信息
                    this.currentUser = {
                        id: select.value,
                        privateKey: keys.private_key,
                        publicKey: keys.public_key,
                        signature: signResponse.signature
                    };

                    // 更新UI
                    document.querySelector('.user-name').textContent = select.options[select.selectedIndex].text;
                    document.getElementById('connectWallet').textContent = 'Wallet Connected';
                    document.getElementById('connectWallet').disabled = true;

                    this.closeModal();
                    await this.loadUserData();
                    // 加载代币数据
                    await this.loadTokensData();
                } catch (error) {
                    this.showError('Failed to connect author: ' + error.message);
                }
            });

            // 处理创建新作者
            document.getElementById('createAuthorForm').addEventListener('submit', async (e) => {
                e.preventDefault();
                try {
                    const name = document.getElementById('authorName').value;
                    const keys = await API.generateKeys();
                    const signResponse = await API.signMessage(keys.private_key);
                    const author = await API.createAuthor(name, keys.public_key);
                    
                    // 存储用户信息
                    this.currentUser = {
                        id: author.id,
                        privateKey: keys.private_key,
                        publicKey: keys.public_key,
                        signature: signResponse.signature
                    };

                    // 更新UI
                    document.querySelector('.user-name').textContent = author.name;
                    document.getElementById('connectWallet').textContent = 'Wallet Connected';
                    document.getElementById('connectWallet').disabled = true;

                    this.closeModal();
                    await this.loadUserData();
                    // 加载代币数据
                    await this.loadTokensData();
                } catch (error) {
                    this.showError('Failed to create author: ' + error.message);
                }
            });

        } catch (error) {
            this.showError('Failed to connect wallet: ' + error.message);
        }
    }

    // 加载用户数据
    async loadUserData() {
        if (!this.currentUser) return;

        try {
            const [balance, transactions] = await Promise.all([
                API.getAuthorBalance(this.currentUser.id),
                API.getAuthorTransactions(this.currentUser.id)
            ]);

            document.getElementById('userBalance').textContent = balance.balance.toFixed(4);
            this.updateTransactionsList(transactions);
        } catch (error) {
            this.showError('Failed to load user data: ' + error.message);
        }
    }

    // 更新交易列表
    updateTransactionsList(transactions) {
        const container = document.getElementById('transactionsList');
        container.innerHTML = transactions.map(tx => `
            <div class="transaction-item">
                <div class="transaction-info">
                    <span class="transaction-type ${tx.transaction_type.toLowerCase()}">${tx.transaction_type}</span>
                    <span class="transaction-amount">${tx.amount.toFixed(4)}</span>
                </div>
                <div class="transaction-details">
                    <span class="transaction-reason">${tx.reason}</span>
                    <span class="transaction-date">${new Date(tx.created_at).toLocaleString()}</span>
                </div>
            </div>
        `).join('');
    }

    // 显示模态框
    showModal(content) {
        this.modalContent.innerHTML = content;
        this.modal.style.display = 'block';
    }

    // 关闭模态框
    closeModal() {
        this.modal.style.display = 'none';
        this.modalContent.innerHTML = '';
    }

    // 显示成功消息
    showSuccess(message) {
        // 实现一个简单的提示框
        const toast = document.createElement('div');
        toast.className = 'toast success';
        toast.textContent = message;
        document.body.appendChild(toast);
        setTimeout(() => toast.remove(), 3000);
    }

    // 显示错误消息
    showError(message) {
        const toast = document.createElement('div');
        toast.className = 'toast error';
        toast.textContent = message;
        document.body.appendChild(toast);
        setTimeout(() => toast.remove(), 3000);
    }

    // 加载作者数据
    async loadAuthorsData() {
        try {
            const authors = await API.request('/authors');
            const container = document.getElementById('authorsGrid');
            
            container.innerHTML = authors.map(author => `
                <div class="author-card">
                    <h3>${author.name}</h3>
                    <div class="author-info">
                        <p><strong>ID:</strong> ${author.id}</p>
                        <p><strong>Public Key:</strong> ${author.public_key.substring(0, 20)}...</p>
                        <p><strong>Created:</strong> ${new Date(author.created_at).toLocaleString()}</p>
                    </div>
                    <div class="author-actions">
                        <button class="btn-primary" onclick="window.ui.viewAuthorDetails('${author.id}')">
                            View Details
                        </button>
                    </div>
                </div>
            `).join('');
        } catch (error) {
            this.showError('Failed to load authors: ' + error.message);
        }
    }

    // 加载论文数据
    async loadPapersData() {
        try {
            const papers = await API.request('/papers');
            const container = document.getElementById('papersList');
            
            container.innerHTML = papers.map(paper => `
                <div class="paper-card">
                    <h3>${paper.title}</h3>
                    <div class="paper-info">
                        <p><strong>ID:</strong> ${paper.id}</p>
                        <p><strong>Authors:</strong> ${paper.authors.join(', ')}</p>
                        <p><strong>Citations:</strong> ${paper.citations.length}</p>
                        <p><strong>Created:</strong> ${new Date(paper.created_at).toLocaleString()}</p>
                    </div>
                    <div class="paper-actions">
                        <button class="btn-primary" onclick="window.ui.viewPaperDetails('${paper.id}')">
                            View Details
                        </button>
                    </div>
                </div>
            `).join('');
        } catch (error) {
            this.showError('Failed to load papers: ' + error.message);
        }
    }

    // 加载引用数据
    async loadCitationsData() {
        try {
            const citations = await API.request('/citations');
            const container = document.getElementById('citationsList');
            
            container.innerHTML = citations.map(citation => `
                <div class="citation-card">
                    <div class="citation-info">
                        <p><strong>ID:</strong> ${citation.id}</p>
                        <p><strong>Citing Paper:</strong> ${citation.citing_paper_id}</p>
                        <p><strong>Cited Paper:</strong> ${citation.cited_paper_id}</p>
                        <p><strong>Created:</strong> ${new Date(citation.created_at).toLocaleString()}</p>
                    </div>
                    <div class="citation-actions">
                        <button class="btn-primary" onclick="window.ui.viewCitationDetails('${citation.id}')">
                            View Details
                        </button>
                    </div>
                </div>
            `).join('');
        } catch (error) {
            this.showError('Failed to load citations: ' + error.message);
        }
    }

    // 加载代币数据
    async loadTokensData() {
        if (!this.currentUser) {
            // 如果用户未登录，清空代币数据
            document.getElementById('userBalance').textContent = '0.0';
            document.getElementById('transactionsList').innerHTML = '';
            return;
        }

        try {
            const [balance, transactions] = await Promise.all([
                API.getAuthorBalance(this.currentUser.id),
                API.getAuthorTransactions(this.currentUser.id)
            ]);

            document.getElementById('userBalance').textContent = balance.balance.toFixed(4);
            this.updateTransactionsList(transactions);
        } catch (error) {
            this.showError('Failed to load token data: ' + error.message);
        }
    }

    // 加载论文列表（用于创建引用）
    async loadPapersForCitation() {
        try {
            const papers = await API.request('/papers');
            const citingSelect = document.getElementById('citingPaper');
            const citedSelect = document.getElementById('citedPaper');
            
            const options = papers.map(paper => 
                `<option value="${paper.id}">${paper.title}</option>`
            ).join('');
            
            citingSelect.innerHTML = options;
            citedSelect.innerHTML = options;
        } catch (error) {
            this.showError('Failed to load papers for citation: ' + error.message);
        }
    }

    // 查看作者详情
    async viewAuthorDetails(authorId) {
        try {
            const [author, balance, transactions] = await Promise.all([
                API.getAuthor(authorId),
                API.getAuthorBalance(authorId),
                API.getAuthorTransactions(authorId)
            ]);

            const content = `
                <h2>Author Details</h2>
                <div class="author-details">
                    <p><strong>Name:</strong> ${author.name}</p>
                    <p><strong>ID:</strong> ${author.id}</p>
                    <p><strong>Public Key:</strong> ${author.public_key}</p>
                    <p><strong>Created:</strong> ${new Date(author.created_at).toLocaleString()}</p>
                    <p><strong>Token Balance:</strong> ${balance.balance.toFixed(4)}</p>
                </div>
                <h3>Transaction History</h3>
                <div class="transactions-list">
                    ${transactions.map(tx => `
                        <div class="transaction-item">
                            <div class="transaction-info">
                                <span class="transaction-type ${tx.transaction_type.toLowerCase()}">${tx.transaction_type}</span>
                                <span class="transaction-amount">${tx.amount.toFixed(4)}</span>
                            </div>
                            <div class="transaction-details">
                                <span class="transaction-reason">${tx.reason}</span>
                                <span class="transaction-date">${new Date(tx.created_at).toLocaleString()}</span>
                            </div>
                        </div>
                    `).join('')}
                </div>
            `;
            this.showModal(content);
        } catch (error) {
            this.showError('Failed to load author details: ' + error.message);
        }
    }

    // 查看论文详情
    async viewPaperDetails(paperId) {
        try {
            const paper = await API.getPaper(paperId);
            const content = `
                <h2>Paper Details</h2>
                <div class="paper-details">
                    <p><strong>Title:</strong> ${paper.title}</p>
                    <p><strong>ID:</strong> ${paper.id}</p>
                    <p><strong>Authors:</strong> ${paper.authors.join(', ')}</p>
                    <p><strong>Created:</strong> ${new Date(paper.created_at).toLocaleString()}</p>
                    <h3>Citations</h3>
                    <div class="citations-list">
                        ${paper.citations.map(citation => `
                            <div class="citation-item">
                                <p><strong>Cited Paper:</strong> ${citation.cited_paper_id}</p>
                                <p><strong>Created:</strong> ${new Date(citation.created_at).toLocaleString()}</p>
                            </div>
                        `).join('')}
                    </div>
                </div>
            `;
            this.showModal(content);
        } catch (error) {
            this.showError('Failed to load paper details: ' + error.message);
        }
    }

    // 查看引用详情
    async viewCitationDetails(citationId) {
        try {
            const citation = await API.request(`/citations/${citationId}`);
            const [citingPaper, citedPaper] = await Promise.all([
                API.getPaper(citation.citing_paper_id),
                API.getPaper(citation.cited_paper_id)
            ]);

            const content = `
                <h2>Citation Details</h2>
                <div class="citation-details">
                    <p><strong>ID:</strong> ${citation.id}</p>
                    <p><strong>Citing Paper:</strong> ${citingPaper.title}</p>
                    <p><strong>Cited Paper:</strong> ${citedPaper.title}</p>
                    <p><strong>Created:</strong> ${new Date(citation.created_at).toLocaleString()}</p>
                </div>
            `;
            this.showModal(content);
        } catch (error) {
            this.showError('Failed to load citation details: ' + error.message);
        }
    }
}

// 导出UI类
window.UI = UI; 