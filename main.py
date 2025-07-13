#!/usr/bin/env python3
"""
AI驱动的研究工作流本地化程序
复制n8n工作流的功能：LLM联想 -> 双重评审 -> 优化 -> 网络搜索 + PubMed搜索
"""

import asyncio
import json
import os
from datetime import datetime
from typing import Dict, List, Any
import click
from rich.console import Console
from rich.progress import Progress, SpinnerColumn, TextColumn
from rich.table import Table
from rich.panel import Panel
from rich.markdown import Markdown

from config import Config
from llm_client import ResearchWorkflow
from search_client import SearchManager

console = Console()

class ResearchApp:
    def __init__(self):
        self.config = Config()
        self.workflow = ResearchWorkflow()
        self.search_manager = SearchManager()
        self.results_dir = "results"
        
        # 创建结果目录
        os.makedirs(self.results_dir, exist_ok=True)
    
    def save_results(self, keyword: str, organized_content: str, search_results: Dict) -> str:
        """
        保存研究结果到文件
        """
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        filename = f"{self.results_dir}/research_{keyword}_{timestamp}.json"
        
        results_data = {
            "keyword": keyword,
            "timestamp": timestamp,
            "organized_content": organized_content,
            "search_results": {}
        }
        
        # 转换搜索结果为可序列化格式
        for query, sources in search_results.items():
            results_data["search_results"][query] = {}
            for source, results in sources.items():
                results_data["search_results"][query][source] = [
                    result.to_dict() for result in results
                ]
        
        with open(filename, 'w', encoding='utf-8') as f:
            json.dump(results_data, f, ensure_ascii=False, indent=2)
        
        return filename
    
    def display_organized_content(self, content: str):
        """
        显示组织化的内容
        """
        console.print(Panel(content, title="🎯 研究框架", border_style="green"))
    
    def display_search_summary(self, search_results: Dict):
        """
        显示搜索结果摘要
        """
        table = Table(title="🔍 搜索结果摘要")
        table.add_column("查询", style="cyan")
        table.add_column("网络结果", style="blue")
        table.add_column("PubMed结果", style="magenta")
        
        for query, sources in search_results.items():
            web_count = len(sources.get("web", []))
            pubmed_count = len(sources.get("pubmed", []))
            
            # 限制查询显示长度
            display_query = query[:50] + "..." if len(query) > 50 else query
            
            table.add_row(
                display_query,
                str(web_count),
                str(pubmed_count)
            )
        
        console.print(table)
    
    def display_top_results(self, search_results: Dict, top_n: int = 3):
        """
        显示每个查询的前N个结果
        """
        for query, sources in search_results.items():
            console.print(f"\n📋 查询: {query}")
            console.print("=" * 60)
            
            # 显示网络搜索结果
            web_results = sources.get("web", [])
            if web_results:
                console.print("🌐 网络搜索结果:")
                for i, result in enumerate(web_results[:top_n], 1):
                    console.print(f"  {i}. {result.title}")
                    console.print(f"     {result.url}")
                    if result.snippet:
                        console.print(f"     {result.snippet[:100]}...")
                    console.print()
            
            # 显示PubMed搜索结果
            pubmed_results = sources.get("pubmed", [])
            if pubmed_results:
                console.print("📚 PubMed搜索结果:")
                for i, result in enumerate(pubmed_results[:top_n], 1):
                    console.print(f"  {i}. {result.title}")
                    console.print(f"     {result.url}")
                    if result.snippet:
                        console.print(f"     {result.snippet[:100]}...")
                    console.print()
    
    async def run_research(self, keyword: str, save_results: bool = True, show_details: bool = False):
        """
        运行完整的研究工作流
        """
        try:
            # 验证配置
            self.config.validate()
            
            console.print(f"🚀 启动AI驱动的研究工作流")
            console.print(f"📌 关键词: {keyword}")
            console.print("=" * 60)
            
            # 阶段1-4: LLM处理
            with Progress(
                SpinnerColumn(),
                TextColumn("[progress.description]{task.description}"),
                console=console,
            ) as progress:
                
                # 运行LLM工作流
                task = progress.add_task("🤖 运行LLM工作流...", total=None)
                organized_content, search_queries = await self.workflow.run_workflow(keyword)
                progress.update(task, description="✅ LLM工作流完成")
            
            # 显示组织化内容
            self.display_organized_content(organized_content)
            
            console.print(f"\n📝 提取到 {len(search_queries)} 个搜索查询")
            if show_details:
                for i, query in enumerate(search_queries, 1):
                    console.print(f"  {i}. {query}")
            
            # 阶段5: 批量搜索
            with Progress(
                SpinnerColumn(),
                TextColumn("[progress.description]{task.description}"),
                console=console,
            ) as progress:
                
                task = progress.add_task("🔍 执行批量搜索...", total=None)
                search_results = await self.search_manager.batch_search(search_queries)
                progress.update(task, description="✅ 批量搜索完成")
            
            # 显示搜索结果摘要
            self.display_search_summary(search_results)
            
            # 显示详细结果
            if show_details:
                self.display_top_results(search_results)
            
            # 保存结果
            if save_results:
                filename = self.save_results(keyword, organized_content, search_results)
                console.print(f"\n💾 结果已保存到: {filename}")
            
            # 生成报告
            report = self.generate_report(keyword, organized_content, search_results)
            report_filename = f"{self.results_dir}/report_{keyword}_{datetime.now().strftime('%Y%m%d_%H%M%S')}.md"
            with open(report_filename, 'w', encoding='utf-8') as f:
                f.write(report)
            
            console.print(f"📊 研究报告已生成: {report_filename}")
            
            return organized_content, search_results
            
        except Exception as e:
            console.print(f"❌ 错误: {e}")
            raise
    
    def generate_report(self, keyword: str, organized_content: str, search_results: Dict) -> str:
        """
        生成研究报告
        """
        report = f"""# 研究报告: {keyword}

**生成时间**: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}

## 📋 研究框架

{organized_content}

## 🔍 搜索结果统计

| 查询 | 网络结果数 | PubMed结果数 |
|------|-----------|-------------|
"""
        
        for query, sources in search_results.items():
            web_count = len(sources.get("web", []))
            pubmed_count = len(sources.get("pubmed", []))
            report += f"| {query[:50]}{'...' if len(query) > 50 else ''} | {web_count} | {pubmed_count} |\n"
        
        report += "\n## 📚 详细搜索结果\n\n"
        
        for query, sources in search_results.items():
            report += f"### 查询: {query}\n\n"
            
            # 网络搜索结果
            web_results = sources.get("web", [])
            if web_results:
                report += "#### 🌐 网络搜索结果\n\n"
                for i, result in enumerate(web_results[:5], 1):
                    report += f"{i}. **{result.title}**\n"
                    report += f"   - URL: {result.url}\n"
                    report += f"   - 摘要: {result.snippet}\n\n"
            
            # PubMed搜索结果
            pubmed_results = sources.get("pubmed", [])
            if pubmed_results:
                report += "#### 📚 PubMed搜索结果\n\n"
                for i, result in enumerate(pubmed_results[:5], 1):
                    report += f"{i}. **{result.title}**\n"
                    report += f"   - URL: {result.url}\n"
                    report += f"   - 摘要: {result.snippet}\n\n"
            
            report += "---\n\n"
        
        return report

# CLI界面
@click.command()
@click.argument('keyword', type=str)
@click.option('--no-save', is_flag=True, help='不保存结果到文件')
@click.option('--details', is_flag=True, help='显示详细搜索结果')
@click.option('--config-check', is_flag=True, help='只检查配置')
def main(keyword: str, no_save: bool, details: bool, config_check: bool):
    """
    AI驱动的研究工作流
    
    KEYWORD: 要研究的关键词
    """
    
    if config_check:
        try:
            Config.validate()
            console.print("✅ 配置验证通过")
        except Exception as e:
            console.print(f"❌ 配置错误: {e}")
            console.print("\n请检查 .env 文件中的配置项")
        return
    
    app = ResearchApp()
    
    try:
        # 运行异步主程序
        asyncio.run(app.run_research(
            keyword=keyword,
            save_results=not no_save,
            show_details=details
        ))
    except KeyboardInterrupt:
        console.print("\n⏹️  用户中断")
    except Exception as e:
        console.print(f"❌ 程序错误: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    main()
