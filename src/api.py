from fastapi import FastAPI, HTTPException, Depends, Header
from fastapi.middleware.cors import CORSMiddleware
from typing import List, Optional
from pydantic import BaseModel
from .models import Author, Paper, Citation, TokenTransaction
from .auth import AuthSystem
from .citation_network import CitationNetwork
from .token_system import TokenSystem

app = FastAPI(title="Academic Citation System API")

# 添加CORS中间件
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:8097"],  # 允许的前端源
    allow_credentials=True,
    allow_methods=["*"],  # 允许所有HTTP方法
    allow_headers=["*"],  # 允许所有HTTP头
)

# 初始化系统组件
auth_system = AuthSystem()
citation_network = CitationNetwork()
token_system = TokenSystem(citation_network)

# 请求模型
class AuthorCreate(BaseModel):
    name: str
    public_key: str

class PaperCreate(BaseModel):
    title: str
    authors: List[str]
    citations: List[str] = []

class CitationCreate(BaseModel):
    citing_paper_id: str
    cited_paper_id: str
    signature: str

class TokenBurnRequest(BaseModel):
    amount: float
    reason: str
    signature: str

class SignMessageRequest(BaseModel):
    private_key: str
    message: str

# 依赖项
async def verify_author(public_key: str = Header(...), signature: str = Header(...), message: str = Header(...)):
    if not auth_system.verify_author(public_key, message, signature):
        raise HTTPException(status_code=401, detail="Invalid author signature")
    return auth_system.get_author_id(public_key)

# 作者相关接口
@app.get("/authors", response_model=List[Author])
async def get_authors():
    """获取所有作者列表"""
    return list(token_system.authors.values())

@app.post("/authors", response_model=Author)
async def create_author(author_data: AuthorCreate):
    author = Author(**author_data.dict())
    auth_system.register_author(author.id, author.public_key)
    token_system.register_author(author)
    return author

@app.get("/authors/{author_id}", response_model=Author)
async def get_author(author_id: str):
    author = token_system.authors.get(author_id)
    if not author:
        raise HTTPException(status_code=404, detail="Author not found")
    return author

# 论文相关接口
@app.get("/papers", response_model=List[Paper])
async def get_papers():
    """获取所有论文列表"""
    return list(citation_network.papers.values())

@app.post("/papers", response_model=Paper)
async def create_paper(paper_data: PaperCreate, author_id: str = Depends(verify_author)):
    if author_id not in paper_data.authors:
        raise HTTPException(status_code=403, detail="Author must be included in paper authors")
    paper = Paper(**paper_data.dict())
    citation_network.add_paper(paper)
    return paper

@app.get("/papers/{paper_id}", response_model=Paper)
async def get_paper(paper_id: str):
    paper = citation_network.papers.get(paper_id)
    if not paper:
        raise HTTPException(status_code=404, detail="Paper not found")
    return paper

# 引用相关接口
@app.get("/citations", response_model=List[Citation])
async def get_citations():
    """获取所有引用列表"""
    return list(citation_network.citations.values())

@app.post("/citations", response_model=Citation)
async def create_citation(citation_data: CitationCreate, author_id: str = Depends(verify_author)):
    # 验证引用论文的作者身份
    citing_paper = citation_network.papers.get(citation_data.citing_paper_id)
    if not citing_paper or author_id not in citing_paper.authors:
        raise HTTPException(status_code=403, detail="Author must be the citing paper's author")
    
    citation = Citation(**citation_data.dict())
    if not citation_network.add_citation(citation):
        raise HTTPException(status_code=400, detail="Invalid citation")
    
    # 为被引用者铸造代币
    cited_paper = citation_network.papers.get(citation.cited_paper_id)
    for author_id in cited_paper.authors:
        token_system.mint_tokens_for_citation(author_id)
    
    return citation

# 代币相关接口
@app.get("/authors/{author_id}/balance")
async def get_balance(author_id: str):
    return {"balance": token_system.get_author_balance(author_id)}

@app.post("/authors/{author_id}/burn")
async def burn_tokens(author_id: str, burn_request: TokenBurnRequest):
    if not token_system.burn_tokens(author_id, burn_request.amount, burn_request.reason):
        raise HTTPException(status_code=400, detail="Invalid burn request")
    return {"status": "success"}

@app.get("/authors/{author_id}/transactions", response_model=List[TokenTransaction])
async def get_transactions(author_id: str):
    return token_system.get_author_token_history(author_id)

# 统计信息接口
@app.get("/stats/network")
async def get_network_stats():
    return citation_network.get_citation_network_stats()

@app.get("/stats/tokens")
async def get_token_stats():
    return token_system.get_token_stats()

# 工具接口
@app.post("/auth/generate-keys")
async def generate_keys():
    return auth_system.generate_key_pair()

@app.post("/auth/sign")
async def sign_message(request: SignMessageRequest):
    """使用私钥签名消息"""
    try:
        print(f"Received sign request with data: {request.dict()}")  # 添加日志
        signature = auth_system.sign_message(request.private_key, request.message)
        return {"signature": signature}
    except Exception as e:
        print(f"Error in sign_message: {str(e)}")  # 添加错误日志
        raise HTTPException(status_code=400, detail=str(e))

# 添加请求日志中间件
@app.middleware("http")
async def log_requests(request, call_next):
    print(f"\nRequest: {request.method} {request.url}")
    print(f"Headers: {request.headers}")
    try:
        body = await request.body()
        if body:
            print(f"Body: {body.decode()}")
    except:
        pass
    response = await call_next(request)
    return response 