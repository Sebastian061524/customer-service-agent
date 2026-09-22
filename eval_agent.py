# 评测 用数字衡量自己的agent
from agent_server import graph, llm
from langchain_core.messages import HumanMessage
from langgraph.types import Command


test_cases = [
    {"q": "音箱多少钱？", "expected": "智能音箱价格是 299 元"},
    {"q": "蓝牙耳机多少钱？", "expected": "蓝牙耳机价格是 199 元"},
    {"q": "智能手环多少钱？", "expected": "智能手环价格是 149 元"},
    {"q": "退货有什么条件？", "expected": "7 天无理由退货，商品需完好、包装完整"},
    {"q": "几天能送到？", "expected": "全国大部分地区 2-3 天送达"},
    {"q": "会员有什么优惠？", "expected": "会员享 95 折"},
    {"q": "满300减多少？", "expected": "满 300 减 50"},
    {"q": "满500减多少？", "expected": "满 500 减 100"},
    {"q": "什么时候发货？", "expected": "当天 16 点前下单当天发货"},
    {"q": "积分怎么用？", "expected": "100 积分抵 1 元"},
    {"q": "买3个智能手环，原价一共多少钱？", "expected": "447 元（149×3）"},
    {"q": "买3个智能手环，满减后实际要付多少钱？", "expected": "397 元（447-50）"},
    {"q": "买2个蓝牙耳机，原价一共多少钱？", "expected": "398 元（199×2）"},
    {"q": "买2个蓝牙耳机，满减后实际要付多少钱？", "expected": "348 元（398-50）"},
    {"q": "买2个音箱能减多少钱？", "expected": "能减 100 元（满500减100）"},
    {"q": "我是会员，买1个音箱要多少钱？", "expected": "约 284 元（299×0.95）"},
    {"q": "你们支持货到付款吗？", "expected": "应该诚实表示知识库中没有相关信息，不能编造"},
    {"q": "你们公司在哪座城市？", "expected": "应该诚实表示知识库中没有相关信息，不能编造"},
]

def judge_with_llm(question, expected, actual):
    """用llm判断答案是否正确"""
    prompt = (f"""你是一个严格的评测员，判断下面 AI 的回答是否正确
    【问题】{question}
    【标准答案要点】{expected}
    【AI 的实际回答】{actual}

    判断标准：
    1. 只要 AI 的回答中**包含**标准答案的要点信息，就算正确
    2. 即使 AI 额外提供了其他相关信息（比如同时给出原价和优惠价），
       只要正确答案在其中，就算 PASS
    3. 只有缺少要点、或要点错误时，才判 FAIL
    请只回答 PASS 或 FAIL，不要任何其他内容
""")
    response = llm.invoke(prompt)  # 用你已有的 llm 来当裁判
    return "PASS" in response.content.upper()

def run_eval():
    passed = 0
    for i, case in enumerate(test_cases):
        # 每题用独立的 thread_id
        config = {"configurable": {"thread_id": f"eval-{i}"}}

        result = graph.invoke(
            {"messages": [HumanMessage(content=case["q"])]},
            config=config,
        )

        # 自动批准所有审批
        while "__interrupt__" in result:
            result = graph.invoke(Command(resume="yes"), config=config)

        answer = result["messages"][-1].content

        # 把关键词检查改成llm裁判
        ok = judge_with_llm(case["q"], case["expected"], answer)
        if ok:
            passed += 1
            print(f"√ {case['q']}")
        else:
            print(f"× {case['q']}")
            print(f"   期望包含: {case['expected']}")
            print(f"   实际回答: {answer[:80]}")

    total = len(test_cases)
    print(f"\n{'=' * 40}")
    print(f"通过率：{passed}/{total} = {passed / total * 100:.0f}%")

run_eval()




