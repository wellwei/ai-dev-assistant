from langchain_openai import ChatOpenAI
from langchain_core.messages import AIMessage
from src.config import settings

llm = ChatOpenAI(
    model=settings.MODEL_NAME,
    api_key=settings.OPENAI_API_KEY,
    base_url=settings.OPENAI_BASE_URL,
    temperature=0.1,
)

def tester(state):
    """测试节点"""
    prompt = f"""为以下代码生成测试用例：

代码：
{state['code']}

要求：
1. 覆盖主要分支和边界条件
2. 使用 pytest 风格
3. 包含至少 3 个测试用例
4. 标注每个用例的测试目的

请直接输出测试代码。"""
    
    response = llm.invoke(prompt)
    
    return {
        "test_result": response.content,
        "messages": [AIMessage(content=f"测试生成完成")],
        "current_step": "testing_done"
    }