// API基础URL
const BASE_URL = 'http://127.0.0.1:8090';

// API请求工具类
class API {
    static baseUrl = BASE_URL;

    static async request(endpoint, options = {}) {
        try {
            const response = await fetch(`${BASE_URL}${endpoint}`, {
                ...options,
                headers: {
                    'Content-Type': 'application/json',
                    ...options.headers
                }
            });

            if (!response.ok) {
                const error = await response.json();
                throw new Error(error.detail || 'API request failed');
            }

            return await response.json();
        } catch (error) {
            console.error('API Error:', error);
            throw error;
        }
    }

    // 作者相关API`
    static async generateKeys() {
        return this.request('/auth/generate-keys', {
            method: 'POST'
        });
    }

    static async signMessage(privateKey, message = 'verify') {
        return this.request('/auth/sign', {
            method: 'POST',
            body: JSON.stringify({
                private_key: privateKey,
                message: message
            })
        });
    }

    static async createAuthor(name, publicKey) {
        return this.request('/authors', {
            method: 'POST',
            body: JSON.stringify({
                name: name,
                public_key: publicKey
            })
        });
    }

    static async getAuthor(authorId) {
        return this.request(`/authors/${authorId}`);
    }

    static async getAuthorBalance(authorId) {
        return this.request(`/authors/${authorId}/balance`);
    }

    static async getAuthorTransactions(authorId) {
        return this.request(`/authors/${authorId}/transactions`);
    }

    static async burnTokens(authorId, amount, publicKey, signature) {
        return this.request(`/authors/${authorId}/burn`, {
            method: 'POST',
            headers: {
                'public-key': publicKey,
                'signature': signature
            },
            body: JSON.stringify({
                amount: amount,
                reason: 'Token burn request',
                signature: signature
            })
        });
    }

    // 论文相关API
    static async createPaper(title, authors, publicKey, signature, message) {
        return await this.request('/papers', {
            method: 'POST',
            headers: {
                'public-key': publicKey,
                'signature': signature,
                'message': message
            },
            body: JSON.stringify({
                title,
                authors,
                citations: []
            })
        });
    }

    static async getPaper(paperId) {
        return this.request(`/papers/${paperId}`);
    }

    // 引用相关API
    static async createCitation(citingPaperId, citedPaperId, publicKey, signature, message) {
        return this.request('/citations', {
            method: 'POST',
            headers: {
                'public-key': publicKey,
                'signature': signature,
                'message': message
            },
            body: JSON.stringify({
                citing_paper_id: citingPaperId,
                cited_paper_id: citedPaperId,
                signature: signature
            })
        });
    }

    // 统计相关API
    static async getNetworkStats() {
        return this.request('/stats/network');
    }

    static async getTokenStats() {
        return this.request('/stats/tokens');
    }
}

// 导出API类
window.API = API; 