from langchain_openai import ChatOpenAI
from langchain_core.messages import AIMessage
from src.config import settings

llm = ChatOpenAI(
    model=settings.MODEL_NAME,
    api_key=settings.OPENAI_API_KEY,
    base_url=settings.OPENAI_BASE_URL,
    temperature=0.2,  # 代码生成稍高温度，增加创造性
)

def coder(state):
    """代码生成节点"""
    prompt = f"""根据以下规划和任务，生成代码：

任务：{state['task']}

规划：
{state['plan']}

要求：
1. 代码要完整、可运行
2. 包含必要的注释
3. 遵循项目现有代码风格
4. 如果是修改现有文件，请标注修改位置

请直接输出代码，用 ``` 包裹。"""
    
    response = llm.invoke(prompt)
    
    return {
        "code": response.content,
        "messages": [AIMessage(content=f"代码生成完成，长度：{len(response.content)}")],
        "current_step": "coding_done"
    }