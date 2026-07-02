from langchain_openai import ChatOpenAI
from langchain_core.messages import AIMessage
from src.config import settings

llm = ChatOpenAI(
    model=settings.MODEL_NAME,
    api_key=settings.OPENAI_API_KEY,
    base_url=settings.OPENAI_BASE_URL,
    temperature=0.1,
)

def planner(state):
    prompt = f"""你是一个资深开发组长。请将以下开发任务分解为可执行的步骤：

任务：{state['task']}

要求：
1. 列出需要修改/创建的文件
2. 说明每个文件的核心逻辑
3. 标注依赖关系

请用中文回答，格式清晰。"""

    response = llm.invoke(prompt)

    return {
        "plan": response.content,
        "messages": [AIMessage(content=f"📋 规划完成：\n{response.content[:200]}...")],
        "current_step": "planning_done"
    }