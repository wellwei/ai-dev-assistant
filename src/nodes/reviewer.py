from langchain_openai import ChatOpenAI
from langchain_core.messages import AIMessage
from src.config import settings

llm = ChatOpenAI(
    model=settings.MODEL_NAME,
    api_key=settings.OPENAI_API_KEY,
    base_url=settings.OPENAI_BASE_URL,
    temperature=0.1,
)

def reviewer(state):
    """代码审查节点"""
    prompt = f"""审查以下代码和测试：

代码：
{state['code']}

测试：
{state['test_result']}

请检查：
1. 是否有明显 bug 或逻辑错误
2. 是否有安全隐患（如 SQL 注入、XSS）
3. 代码风格是否一致
4. 测试是否充分

如果有问题，请详细说明。如果通过，请回复"审查通过"。"""

    response = llm.invoke(prompt)
    
    approved = "审查通过" in response.content or "通过" in response.content
    
    return {
        "review_feedback": response.content,
        "approved": approved,
        "messages": [AIMessage(content=f"审查结果：{'通过' if approved else '需修改'}")],
        "current_step": "review_done"
    }