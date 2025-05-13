# 学术引用系统 (Python版)

这是一个基于Python实现的学术引用系统，使用NetworkX构建引用网络，实现作者身份认证和身份币系统。

## 功能特点

1. **作者身份认证**
   - 基于RSA公私钥对实现作者身份认证
   - 支持数字签名验证
   - 安全的身份管理系统

2. **引用网络**
   - 使用NetworkX构建有向图表示引用关系
   - 实现PageRank算法计算论文影响力
   - 支持引用关系追踪和验证

3. **身份币系统**
   - 基于引用数量和质量动态铸造代币
   - 实现引用曲线控制代币供应
   - 支持代币销毁和交易历史记录

## 安装

1. 克隆仓库：
```bash
git clone <repository-url>
cd academic-citation-system
```

2. 安装依赖：
```bash
pip install -r requirements.txt
```

## 运行

启动服务器：
```bash
python main.py
```

服务器将在 http://localhost:8000 运行，API文档可在 http://localhost:8000/docs 查看。

## API使用示例

1. 生成作者密钥对：
```bash
curl -X POST http://localhost:8000/auth/generate-keys
```

2. 注册新作者：
```bash
curl -X POST http://localhost:8000/authors \
  -H "Content-Type: application/json" \
  -d '{"name": "John Doe", "public_key": "your_public_key"}'
```

3. 创建论文：
```bash
curl -X POST http://localhost:8000/papers \
  -H "Content-Type: application/json" \
  -H "public-key: your_public_key" \
  -H "signature: your_signature" \
  -d '{"title": "My Paper", "authors": ["author_id"], "citations": []}'
```

4. 添加引用：
```bash
curl -X POST http://localhost:8000/citations \
  -H "Content-Type: application/json" \
  -H "public-key: your_public_key" \
  -H "signature: your_signature" \
  -d '{"citing_paper_id": "paper1", "cited_paper_id": "paper2"}'
```

5. 查询作者代币余额：
```bash
curl http://localhost:8000/authors/{author_id}/balance
```

## 系统架构

- `src/models.py`: 数据模型定义
- `src/auth.py`: 身份认证系统
- `src/citation_network.py`: 引用网络管理
- `src/token_system.py`: 身份币系统
- `src/api.py`: REST API接口
- `main.py`: 应用入口

## 开发说明

1. 引用曲线参数可在 `token_system.py` 中调整：
   - `base_mint_rate`: 基础铸币率
   - `citation_decay`: 引用衰减率
   - `max_citations_for_mint`: 最大有效引用次数

2. PageRank参数可在 `citation_network.py` 中调整：
   - `damping`: 阻尼系数
   - `max_iter`: 最大迭代次数

## 许可证

MIT License
