import asyncio
import aiohttp
from bs4 import BeautifulSoup
import json
from typing import List, Dict, Any
import urllib.parse
from Bio import Entrez
import xml.etree.ElementTree as ET
from datetime import datetime
import re
from config import Config

class SearchResult:
    def __init__(self, title: str, url: str, snippet: str, source: str = "web"):
        self.title = title
        self.url = url
        self.snippet = snippet
        self.source = source
        self.timestamp = datetime.now().isoformat()
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "title": self.title,
            "url": self.url,
            "snippet": self.snippet,
            "source": self.source,
            "timestamp": self.timestamp
        }

class WebSearchClient:
    def __init__(self):
        self.config = Config()
        self.session = None
    
    async def __aenter__(self):
        self.session = aiohttp.ClientSession()
        return self
    
    async def __aexit__(self, exc_type, exc_val, exc_tb):
        if self.session:
            await self.session.close()
    
    async def search_duckduckgo(self, query: str, max_results: int = 10) -> List[SearchResult]:
        """
        使用DuckDuckGo进行网络搜索
        """
        try:
            search_url = "https://html.duckduckgo.com/html/"
            params = {'q': query}
            
            headers = {
                'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
            }
            
            async with self.session.get(search_url, params=params, headers=headers) as response:
                if response.status == 200:
                    html = await response.text()
                    return self._parse_duckduckgo_results(html, max_results)
                else:
                    print(f"DuckDuckGo搜索失败: {response.status}")
                    return []
        except Exception as e:
            print(f"DuckDuckGo搜索错误: {e}")
            return []
    
    def _parse_duckduckgo_results(self, html: str, max_results: int) -> List[SearchResult]:
        """
        解析DuckDuckGo搜索结果
        """
        results = []
        soup = BeautifulSoup(html, 'html.parser')
        
        # 查找搜索结果
        result_divs = soup.find_all('div', class_='result__body')
        
        for div in result_divs[:max_results]:
            try:
                title_elem = div.find('h2', class_='result__title')
                if title_elem:
                    title_link = title_elem.find('a')
                    if title_link:
                        title = title_link.get_text().strip()
                        url = title_link.get('href', '')
                        
                        # 获取描述
                        snippet_elem = div.find('a', class_='result__snippet')
                        snippet = snippet_elem.get_text().strip() if snippet_elem else ""
                        
                        if title and url:
                            results.append(SearchResult(
                                title=title,
                                url=url,
                                snippet=snippet,
                                source="duckduckgo"
                            ))
            except Exception as e:
                print(f"解析搜索结果时出错: {e}")
                continue
        
        return results
    
    async def search_bing(self, query: str, max_results: int = 10) -> List[SearchResult]:
        """
        使用Bing进行网络搜索（备用）
        """
        try:
            search_url = "https://www.bing.com/search"
            params = {'q': query, 'count': max_results}
            
            headers = {
                'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
            }
            
            async with self.session.get(search_url, params=params, headers=headers) as response:
                if response.status == 200:
                    html = await response.text()
                    return self._parse_bing_results(html, max_results)
                else:
                    print(f"Bing搜索失败: {response.status}")
                    return []
        except Exception as e:
            print(f"Bing搜索错误: {e}")
            return []
    
    def _parse_bing_results(self, html: str, max_results: int) -> List[SearchResult]:
        """
        解析Bing搜索结果
        """
        results = []
        soup = BeautifulSoup(html, 'html.parser')
        
        # 查找搜索结果
        result_divs = soup.find_all('li', class_='b_algo')
        
        for div in result_divs[:max_results]:
            try:
                title_elem = div.find('h2')
                if title_elem:
                    title_link = title_elem.find('a')
                    if title_link:
                        title = title_link.get_text().strip()
                        url = title_link.get('href', '')
                        
                        # 获取描述
                        snippet_elem = div.find('p')
                        snippet = snippet_elem.get_text().strip() if snippet_elem else ""
                        
                        if title and url:
                            results.append(SearchResult(
                                title=title,
                                url=url,
                                snippet=snippet,
                                source="bing"
                            ))
            except Exception as e:
                print(f"解析Bing结果时出错: {e}")
                continue
        
        return results

class PubMedSearchClient:
    def __init__(self):
        self.config = Config()
        Entrez.email = self.config.PUBMED_EMAIL
        Entrez.tool = "ResearchWorkflow"
    
    async def search_pubmed(self, query: str, max_results: int = 10) -> List[SearchResult]:
        """
        在PubMed中搜索学术文献
        """
        try:
            # 搜索PubMed
            search_handle = Entrez.esearch(
                db="pubmed",
                term=query,
                retmax=max_results,
                sort="relevance"
            )
            search_results = Entrez.read(search_handle)
            search_handle.close()
            
            id_list = search_results["IdList"]
            if not id_list:
                return []
            
            # 获取详细信息
            fetch_handle = Entrez.efetch(
                db="pubmed",
                id=id_list,
                rettype="medline",
                retmode="xml"
            )
            
            records = Entrez.read(fetch_handle)
            fetch_handle.close()
            
            return self._parse_pubmed_results(records)
            
        except Exception as e:
            print(f"PubMed搜索错误: {e}")
            return []
    
    def _parse_pubmed_results(self, records) -> List[SearchResult]:
        """
        解析PubMed搜索结果
        """
        results = []
        
        for record in records['PubmedArticle']:
            try:
                article = record['MedlineCitation']['Article']
                
                # 获取标题
                title = article.get('ArticleTitle', '')
                if isinstance(title, list):
                    title = ' '.join(title)
                
                # 获取摘要
                abstract = ""
                if 'Abstract' in article:
                    abstract_texts = article['Abstract'].get('AbstractText', [])
                    if isinstance(abstract_texts, list):
                        abstract = ' '.join([str(text) for text in abstract_texts])
                    else:
                        abstract = str(abstract_texts)
                
                # 获取PMID
                pmid = record['MedlineCitation']['PMID']
                url = f"https://pubmed.ncbi.nlm.nih.gov/{pmid}/"
                
                # 获取作者
                authors = []
                if 'AuthorList' in article:
                    for author in article['AuthorList']:
                        if 'LastName' in author and 'ForeName' in author:
                            authors.append(f"{author['LastName']} {author['ForeName']}")
                
                # 获取发表年份
                pub_year = ""
                if 'Journal' in article and 'JournalIssue' in article['Journal']:
                    pub_date = article['Journal']['JournalIssue'].get('PubDate', {})
                    pub_year = pub_date.get('Year', '')
                
                # 构建片段
                snippet = f"{abstract[:200]}..."
                if authors:
                    snippet = f"作者: {', '.join(authors[:3])}. {snippet}"
                if pub_year:
                    snippet = f"({pub_year}) {snippet}"
                
                results.append(SearchResult(
                    title=title,
                    url=url,
                    snippet=snippet,
                    source="pubmed"
                ))
                
            except Exception as e:
                print(f"解析PubMed结果时出错: {e}")
                continue
        
        return results

class SearchManager:
    def __init__(self):
        self.config = Config()
    
    async def search_all_sources(self, query: str) -> Dict[str, List[SearchResult]]:
        """
        在所有搜索源中搜索
        """
        results = {
            "web": [],
            "pubmed": []
        }
        
        print(f"🔍 搜索查询: {query}")
        
        # 创建搜索任务
        async with WebSearchClient() as web_client:
            tasks = [
                self._search_web(web_client, query),
                self._search_pubmed(query)
            ]
            
            web_results, pubmed_results = await asyncio.gather(*tasks, return_exceptions=True)
            
            # 处理结果
            if not isinstance(web_results, Exception):
                results["web"] = web_results
            else:
                print(f"网络搜索失败: {web_results}")
            
            if not isinstance(pubmed_results, Exception):
                results["pubmed"] = pubmed_results
            else:
                print(f"PubMed搜索失败: {pubmed_results}")
        
        return results
    
    async def _search_web(self, client: WebSearchClient, query: str) -> List[SearchResult]:
        """
        网络搜索
        """
        # 首先尝试DuckDuckGo
        results = await client.search_duckduckgo(query, self.config.MAX_SEARCH_RESULTS)
        
        # 如果DuckDuckGo失败，尝试Bing
        if not results:
            results = await client.search_bing(query, self.config.MAX_SEARCH_RESULTS)
        
        return results
    
    async def _search_pubmed(self, query: str) -> List[SearchResult]:
        """
        PubMed搜索
        """
        client = PubMedSearchClient()
        return await client.search_pubmed(query, self.config.MAX_SEARCH_RESULTS)
    
    async def batch_search(self, queries: List[str]) -> Dict[str, Dict[str, List[SearchResult]]]:
        """
        批量搜索多个查询
        """
        print(f"🔍 开始批量搜索 {len(queries)} 个查询...")
        
        all_results = {}
        
        for i, query in enumerate(queries, 1):
            print(f"[{i}/{len(queries)}] 搜索: {query}")
            
            # 搜索
            results = await self.search_all_sources(query)
            all_results[query] = results
            
            # 添加延迟以避免被封禁
            if i < len(queries):
                await asyncio.sleep(self.config.SEARCH_DELAY)
        
        print("✅ 批量搜索完成")
        return all_results
    
    def format_search_results(self, all_results: Dict[str, Dict[str, List[SearchResult]]]) -> str:
        """
        格式化搜索结果用于显示
        """
        formatted = []
        
        for query, results in all_results.items():
            formatted.append(f"\n## 搜索查询: {query}")
            formatted.append("=" * 50)
            
            # 网络搜索结果
            web_results = results.get("web", [])
            if web_results:
                formatted.append("\n### 网络搜索结果")
                for i, result in enumerate(web_results[:5], 1):
                    formatted.append(f"{i}. **{result.title}**")
                    formatted.append(f"   URL: {result.url}")
                    formatted.append(f"   摘要: {result.snippet}")
                    formatted.append("")
            
            # PubMed搜索结果
            pubmed_results = results.get("pubmed", [])
            if pubmed_results:
                formatted.append("\n### PubMed搜索结果")
                for i, result in enumerate(pubmed_results[:5], 1):
                    formatted.append(f"{i}. **{result.title}**")
                    formatted.append(f"   URL: {result.url}")
                    formatted.append(f"   摘要: {result.snippet}")
                    formatted.append("")
            
            formatted.append("\n" + "-" * 50)
        
        return "\n".join(formatted)