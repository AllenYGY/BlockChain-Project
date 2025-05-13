import networkx as nx
import numpy as np
from typing import Dict, List, Tuple
from .models import Paper, Citation

class CitationNetwork:
    def __init__(self):
        self.graph = nx.DiGraph()
        self.papers: Dict[str, Paper] = {}
        self.citations: Dict[str, Citation] = {}
        
    def add_paper(self, paper: Paper) -> None:
        """添加论文到网络"""
        self.papers[paper.id] = paper
        self.graph.add_node(paper.id)
        
    def add_citation(self, citation: Citation) -> bool:
        """添加引用关系"""
        # 验证论文是否存在
        if citation.citing_paper_id not in self.papers or citation.cited_paper_id not in self.papers:
            return False
            
        # 验证不是自引用
        if citation.citing_paper_id == citation.cited_paper_id:
            return False
            
        # 添加引用关系
        self.citations[citation.id] = citation
        self.graph.add_edge(citation.citing_paper_id, citation.cited_paper_id)
        
        # 更新论文的引用列表
        citing_paper = self.papers[citation.citing_paper_id]
        if citation.cited_paper_id not in citing_paper.citations:
            citing_paper.citations.append(citation.cited_paper_id)
            
        return True
        
    def calculate_pagerank(self, damping: float = 0.85, max_iter: int = 100) -> Dict[str, float]:
        """计算论文的PageRank值"""
        return nx.pagerank(self.graph, alpha=damping, max_iter=max_iter)
        
    def get_citation_count(self, paper_id: str) -> int:
        """获取论文被引用次数"""
        return self.graph.in_degree(paper_id)
        
    def get_citing_papers(self, paper_id: str) -> List[str]:
        """获取引用该论文的所有论文ID"""
        return list(self.graph.predecessors(paper_id))
        
    def get_cited_papers(self, paper_id: str) -> List[str]:
        """获取该论文引用的所有论文ID"""
        return list(self.graph.successors(paper_id))
        
    def get_author_papers(self, author_id: str) -> List[str]:
        """获取作者的所有论文ID"""
        return [paper_id for paper_id, paper in self.papers.items() 
                if author_id in paper.authors]
        
    def get_author_citation_count(self, author_id: str) -> int:
        """获取作者所有论文的总被引用次数"""
        author_papers = self.get_author_papers(author_id)
        return sum(self.get_citation_count(paper_id) for paper_id in author_papers)
        
    def get_author_pagerank(self, author_id: str, damping: float = 0.85) -> float:
        """计算作者的PageRank值（基于其所有论文的PageRank）"""
        author_papers = self.get_author_papers(author_id)
        if not author_papers:
            return 0.0
            
        paper_ranks = self.calculate_pagerank(damping=damping)
        return sum(paper_ranks.get(paper_id, 0.0) for paper_id in author_papers)
        
    def get_citation_network_stats(self) -> Dict:
        """获取引用网络统计信息"""
        total_papers = len(self.papers)
        total_citations = len(self.citations)
        
        # 计算平均引用次数，处理空网络的情况
        citation_counts = [self.get_citation_count(paper_id) for paper_id in self.papers]
        average_citations = float(np.mean(citation_counts)) if citation_counts else 0.0
        max_citations = max(citation_counts) if citation_counts else 0
        
        # 计算网络密度，处理空网络的情况
        try:
            network_density = float(nx.density(self.graph))
        except (ZeroDivisionError, nx.NetworkXError):
            network_density = 0.0
            
        return {
            'total_papers': total_papers,
            'total_citations': total_citations,
            'average_citations': average_citations,
            'max_citations': max_citations,
            'network_density': network_density,
            'is_dag': nx.is_directed_acyclic_graph(self.graph) if total_papers > 0 else True
        } 