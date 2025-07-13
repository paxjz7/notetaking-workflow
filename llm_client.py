import asyncio
import aiohttp
from openai import OpenAI
import google.generativeai as genai
from typing import Optional, Dict, Any
import json
from config import Config

class LLMClient:
    def __init__(self):
        self.config = Config()
        self.client = None
        self.gemini_model = None
        self.use_local = bool(self.config.LOCAL_LLM_URL)
        self.use_gemini = bool(self.config.GEMINI_API_KEY)
        self.use_openai = bool(self.config.OPENAI_API_KEY)
        
        # 优先级: Gemini > OpenAI > 本地LLM
        if self.use_gemini:
            genai.configure(api_key=self.config.GEMINI_API_KEY)
            self.gemini_model = genai.GenerativeModel(self.config.GEMINI_MODEL)
            print(f"✅ 使用Gemini模型: {self.config.GEMINI_MODEL}")
        elif self.use_openai:
            self.client = OpenAI(
                api_key=self.config.OPENAI_API_KEY,
                base_url=self.config.OPENAI_BASE_URL
            )
            print(f"✅ 使用OpenAI模型: {self.config.OPENAI_MODEL}")
        elif self.use_local:
            print(f"✅ 使用本地LLM: {self.config.LOCAL_LLM_URL}")
        else:
            raise ValueError("未配置任何可用的LLM服务")
    
    async def chat_completion(self, prompt: str, temperature: float = 0.7, max_tokens: int = 4000) -> str:
        """
        发送聊天完成请求
        """
        if self.use_gemini:
            return await self._gemini_chat_completion(prompt, temperature, max_tokens)
        elif self.use_openai:
            return await self._openai_chat_completion(prompt, temperature, max_tokens)
        elif self.use_local:
            return await self._local_chat_completion(prompt, temperature, max_tokens)
        else:
            raise ValueError("未配置任何可用的LLM服务")
    
    async def _openai_chat_completion(self, prompt: str, temperature: float, max_tokens: int) -> str:
        """
        使用OpenAI API进行聊天完成
        """
        try:
            response = self.client.chat.completions.create(
                model=self.config.OPENAI_MODEL,
                messages=[
                    {"role": "user", "content": prompt}
                ],
                temperature=temperature,
                max_tokens=max_tokens
            )
            return response.choices[0].message.content.strip()
        except Exception as e:
            print(f"OpenAI API错误: {e}")
            return f"API调用失败: {str(e)}"
    
    async def _gemini_chat_completion(self, prompt: str, temperature: float, max_tokens: int) -> str:
        """
        使用Google Gemini API进行聊天完成
        """
        try:
            # 配置生成参数
            generation_config = genai.types.GenerationConfig(
                temperature=temperature,
                max_output_tokens=max_tokens,
            )
            
            # 生成响应
            response = self.gemini_model.generate_content(
                prompt,
                generation_config=generation_config
            )
            
            return response.text.strip()
        except Exception as e:
            print(f"Gemini API错误: {e}")
            return f"API调用失败: {str(e)}"
    
    async def _local_chat_completion(self, prompt: str, temperature: float, max_tokens: int) -> str:
        """
        使用本地LLM进行聊天完成
        """
        try:
            async with aiohttp.ClientSession() as session:
                payload = {
                    "model": self.config.LOCAL_LLM_MODEL,
                    "messages": [
                        {"role": "user", "content": prompt}
                    ],
                    "temperature": temperature,
                    "max_tokens": max_tokens
                }
                
                async with session.post(
                    f"{self.config.LOCAL_LLM_URL}/chat/completions",
                    json=payload,
                    headers={"Content-Type": "application/json"}
                ) as response:
                    if response.status == 200:
                        result = await response.json()
                        return result['choices'][0]['message']['content'].strip()
                    else:
                        error_text = await response.text()
                        return f"本地LLM错误: {error_text}"
        except Exception as e:
            print(f"本地LLM错误: {e}")
            return f"本地LLM调用失败: {str(e)}"

class ResearchWorkflow:
    def __init__(self):
        self.llm_client = LLMClient()
    
    async def association_stage(self, keyword: str) -> str:
        """
        阶段1: 联想生成
        """
        from config import PROMPTS
        prompt = PROMPTS["association"].format(keyword=keyword)
        print(f"🤔 联想阶段: 正在分析关键词 '{keyword}'...")
        
        result = await self.llm_client.chat_completion(
            prompt=prompt,
            temperature=1.0,
            max_tokens=2000
        )
        
        print("✅ 联想阶段完成")
        return result
    
    async def review_stage(self, keyword: str, framework: str) -> tuple[str, str]:
        """
        阶段2: 双重评审
        """
        from config import PROMPTS
        prompt = PROMPTS["reviewer"].format(keyword=keyword, framework=framework)
        
        print("🔍 评审阶段: 启动双重评审...")
        
        # 并行执行两个评审员
        tasks = [
            self.llm_client.chat_completion(prompt, temperature=1.0, max_tokens=3000),
            self.llm_client.chat_completion(prompt, temperature=1.0, max_tokens=3000)
        ]
        
        review1, review2 = await asyncio.gather(*tasks)
        
        print("✅ 双重评审完成")
        return review1, review2
    
    async def optimization_stage(self, framework: str, review1: str, review2: str) -> str:
        """
        阶段3: 最终优化
        """
        from config import PROMPTS
        prompt = PROMPTS["optimizer"].format(
            framework=framework,
            review1=review1,
            review2=review2
        )
        
        print("🔧 优化阶段: 整合评审意见...")
        
        result = await self.llm_client.chat_completion(
            prompt=prompt,
            temperature=0.7,
            max_tokens=3000
        )
        
        print("✅ 优化阶段完成")
        return result
    
    async def organization_stage(self, content: str) -> str:
        """
        阶段4: 内容整理
        """
        from config import PROMPTS
        prompt = PROMPTS["organizer"].format(content=content)
        
        print("📝 整理阶段: 格式化输出...")
        
        result = await self.llm_client.chat_completion(
            prompt=prompt,
            temperature=0.3,
            max_tokens=2000
        )
        
        print("✅ 整理阶段完成")
        return result
    
    def extract_search_queries(self, organized_content: str) -> list[str]:
        """
        从整理后的内容中提取搜索查询
        """
        lines = organized_content.split('\n')
        queries = []
        
        for line in lines:
            line = line.strip()
            if line and not line.startswith('#') and not line.startswith('**'):
                # 移除序号和格式化符号
                cleaned_line = line
                # 移除数字开头的序号
                if line[0].isdigit():
                    cleaned_line = line.split('.', 1)[-1].strip()
                # 移除markdown格式
                cleaned_line = cleaned_line.replace('**', '').replace('*', '')
                
                if cleaned_line:
                    queries.append(cleaned_line)
        
        return queries
    
    async def run_workflow(self, keyword: str) -> tuple[str, list[str]]:
        """
        运行完整工作流
        """
        print(f"🚀 启动研究工作流，关键词: '{keyword}'")
        print("=" * 50)
        
        # 阶段1: 联想
        framework = await self.association_stage(keyword)
        
        # 阶段2: 评审
        review1, review2 = await self.review_stage(keyword, framework)
        
        # 阶段3: 优化
        optimized = await self.optimization_stage(framework, review1, review2)
        
        # 阶段4: 整理
        organized = await self.organization_stage(optimized)
        
        # 提取搜索查询
        search_queries = self.extract_search_queries(organized)
        
        print("=" * 50)
        print("✅ 工作流完成！")
        
        return organized, search_queries