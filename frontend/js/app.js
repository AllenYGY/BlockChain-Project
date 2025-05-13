// 主应用类
class App {
    constructor() {
        this.ui = new UI();
        this.initializeApp();
    }

    // 初始化应用
    async initializeApp() {
        try {
            // 检查后端服务是否可用
            await this.checkBackendStatus();
            
            // 默认显示仪表盘
            this.ui.switchPage('dashboard');
            
            // 添加加载动画
            this.showLoading();
            
            // 初始化数据
            await this.initializeData();
            
            // 隐藏加载动画
            this.hideLoading();
            
        } catch (error) {
            console.error('Failed to initialize app:', error);
            this.ui.showError('Failed to connect to backend service. Please try again later.');
        }
    }

    // 检查后端状态
    async checkBackendStatus() {
        try {
            // 使用 /stats/network 端点来检查后端状态
            const response = await fetch(`${API.baseUrl}/stats/network`);
            if (!response.ok) {
                throw new Error('Backend service is not available');
            }
        } catch (error) {
            throw new Error('Cannot connect to backend service');
        }
    }

    // 初始化数据
    async initializeData() {
        try {
            // 加载仪表盘数据
            await this.ui.loadDashboardData();
            
            // 加载作者列表
            await this.ui.loadAuthorsData();
            
            // 加载论文列表
            await this.ui.loadPapersData();
            
            // 加载引用列表
            await this.ui.loadCitationsData();
            
            // 加载代币数据
            await this.ui.loadTokensData();
            
        } catch (error) {
            console.error('Failed to initialize data:', error);
            this.ui.showError('Failed to load initial data. Some features may not be available.');
        }
    }

    // 显示加载动画
    showLoading() {
        const loading = document.createElement('div');
        loading.id = 'loadingOverlay';
        loading.innerHTML = `
            <div class="loading-spinner"></div>
            <div class="loading-text">Loading...</div>
        `;
        document.body.appendChild(loading);
    }

    // 隐藏加载动画
    hideLoading() {
        const loading = document.getElementById('loadingOverlay');
        if (loading) {
            loading.remove();
        }
    }
}

// 当DOM加载完成后初始化应用
document.addEventListener('DOMContentLoaded', () => {
    window.app = new App();
}); 