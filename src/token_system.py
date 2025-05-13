from typing import Dict, List
import math
from .models import Author, TokenTransaction
from .citation_network import CitationNetwork

class TokenSystem:
    def __init__(self, citation_network: CitationNetwork):
        self.citation_network = citation_network
        self.authors: Dict[str, Author] = {}
        self.transactions: List[TokenTransaction] = []
        self.total_supply: float = 0.0
        
        # 引用曲线参数
        self.base_mint_rate = 1.0  # 基础铸币率
        self.citation_decay = 0.1  # 引用衰减率
        self.max_citations_for_mint = 100  # 最大有效引用次数
        
    def register_author(self, author: Author) -> None:
        """注册新作者"""
        self.authors[author.id] = author
        
    def calculate_citation_curve(self, citation_count: int) -> float:
        """计算引用曲线值，用于确定铸币数量"""
        if citation_count <= 0:
            return 0.0
        # 使用对数函数实现边际收益递减
        return self.base_mint_rate * math.log(1 + citation_count * self.citation_decay)
        
    def mint_tokens_for_citation(self, cited_author_id: str) -> float:
        """为被引用者铸造代币"""
        if cited_author_id not in self.authors:
            return 0.0
            
        citation_count = self.citation_network.get_author_citation_count(cited_author_id)
        if citation_count > self.max_citations_for_mint:
            citation_count = self.max_citations_for_mint
            
        mint_amount = self.calculate_citation_curve(citation_count)
        
        # 记录交易
        transaction = TokenTransaction(
            author_id=cited_author_id,
            amount=mint_amount,
            transaction_type="MINT",
            reason=f"Citation reward for {citation_count} citations"
        )
        self.transactions.append(transaction)
        
        # 更新作者余额和总供应量
        self.authors[cited_author_id].token_balance += mint_amount
        self.total_supply += mint_amount
        
        return mint_amount
        
    def burn_tokens(self, author_id: str, amount: float, reason: str) -> bool:
        """销毁作者代币"""
        if author_id not in self.authors:
            return False
            
        author = self.authors[author_id]
        if author.token_balance < amount:
            return False
            
        # 记录交易
        transaction = TokenTransaction(
            author_id=author_id,
            amount=amount,
            transaction_type="BURN",
            reason=reason
        )
        self.transactions.append(transaction)
        
        # 更新作者余额和总供应量
        author.token_balance -= amount
        self.total_supply -= amount
        
        return True
        
    def get_author_balance(self, author_id: str) -> float:
        """获取作者代币余额"""
        return self.authors.get(author_id, Author(name="", public_key="")).token_balance
        
    def get_token_stats(self) -> Dict:
        """获取代币系统统计信息"""
        return {
            'total_supply': self.total_supply,
            'total_authors': len(self.authors),
            'total_transactions': len(self.transactions),
            'average_balance': sum(author.token_balance for author in self.authors.values()) / len(self.authors) if self.authors else 0,
            'max_balance': max((author.token_balance for author in self.authors.values()), default=0)
        }
        
    def get_author_token_history(self, author_id: str) -> List[TokenTransaction]:
        """获取作者的代币交易历史"""
        return [tx for tx in self.transactions if tx.author_id == author_id] 