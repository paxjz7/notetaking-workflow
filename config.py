import os
from dotenv import load_dotenv

# 加载环境变量
load_dotenv()

class Config:
    # OpenAI配置
    OPENAI_API_KEY = os.getenv('OPENAI_API_KEY')
    OPENAI_MODEL = os.getenv('OPENAI_MODEL', 'gpt-4o-mini')
    OPENAI_BASE_URL = os.getenv('OPENAI_BASE_URL', 'https://api.openai.com/v1')
    
    # 本地LLM配置（可选）
    LOCAL_LLM_URL = os.getenv('LOCAL_LLM_URL')
    LOCAL_LLM_MODEL = os.getenv('LOCAL_LLM_MODEL', 'llama3:latest')
    
    # 搜索配置
    SEARCH_DELAY = int(os.getenv('SEARCH_DELAY', '1'))
    MAX_SEARCH_RESULTS = int(os.getenv('MAX_SEARCH_RESULTS', '10'))
    PUBMED_EMAIL = os.getenv('PUBMED_EMAIL', 'user@example.com')
    
    # 检查必要配置
    @classmethod
    def validate(cls):
        if not cls.OPENAI_API_KEY and not cls.LOCAL_LLM_URL:
            raise ValueError("必须配置OPENAI_API_KEY或LOCAL_LLM_URL")
        return True

# 联想维度模板
ASSOCIATION_DIMENSIONS = [
    "核心概念",
    "历史",
    "现状", 
    "技术基础",
    "应用",
    "争议",
    "未来",
    "人物",
    "交叉领域和影响"
]

# 提示词模板
PROMPTS = {
    "association": """# 角色
你是一位富有逻辑思维的联想大师。

# 任务
请针对我提供的核心关键词，从以下几个维度进行发散联想。

# 核心关键词
{keyword}

# 联想维度与输出格式
请严格按照以下结构输出（包含序号），每个维度仅输出1条短语
1.核心概念
2.历史
3.现状
4.技术基础
5.应用
6.争议
7.未来
8.人物
9.交叉领域和影响""",

    "reviewer": """**原始主题：** "{keyword}"
**初步分解框架：**
{framework}

**请从以下角度进行严格评审：**
1.  **知识盲点：** 是否遗漏了任何关键维度或子主题？
2.  **冗余与重叠：** 哪些部分可以合并以提高效率？
3.  **深度与粒度：** 划分是过宽还是过细？
4.  **可操作性：** 搜索指令是否有效？

**输出要求：** 以"评审报告"形式输出，清晰列出问题并提出具体的"优化建议"。""",

    "optimizer": """作为一名首席研究策略师，你的任务是综合以下不同的评审报告，并对最初的研究框架提出一个最终的、统一的优化。

**初始框架：**
{framework}

**评审汇总：**
---
**评审员1：**
{review1}
---
**评审员2：**
{review2}
---

**请完成以下任务：**
1.  **寻找共识：** 识别所有顾问都提到的关键问题和建议。
2.  **提炼独特洞见：** 找出某个顾问提出的、但其他顾问忽略的独特且有价值的观点。
3.  **解决冲突：** 如果存在矛盾的建议，请进行权衡并给出你的最终判断。
4.  **生成最终优化框架：** 基于以上所有信息，对初始框架进行修改，输出一个经过深思熟虑、结构清晰、可执行性强的"最终建议框架"，他应该与初始框架的结构类似。保持简洁。""",

    "organizer": """你是一位精通信息整理和文本编辑的专家，擅长将杂乱无章的文本内容进行逻辑化、条理化的整理，能够快速识别关键信息并进行精准的格式化处理。
你具备强大的文本分析能力、信息提取能力以及格式化编辑能力，能够高效地将文本内容按照用户需求进行整理和优化。输出应为整理后的文本，每一行一个序号加上对应的内容，格式应整齐划一。
任务目标为{content}
注意输出格式与初始框架保持一致。"""
}