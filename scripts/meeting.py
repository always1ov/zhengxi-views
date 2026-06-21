# -*- coding: utf-8 -*-
"""多智能体"基金经理圆桌"——把一个问题分发给多位蒸馏人物，模拟圆桌讨论。

用法:
  python scripts/meeting.py "AI算力这波行情你们怎么看？"
  python scripts/meeting.py "光通信现在还能买吗？" --mode sequential
  python scripts/meeting.py "新能源车还有机会吗？" --personas zhengxi zhang_kun

模式:
  parallel   (默认) 每位经理独立回答同一问题，互不知晓其他人的观点
  sequential  每位经理看到前面所有发言后再回答，形成真正的讨论

personas/ 目录放各人物的系统提示词文件（{id}.txt），每个文件就是那个人物的 system prompt。
"""
import os, sys, json, argparse, textwrap
import anthropic

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
PERSONAS_DIR = os.path.join(ROOT, "personas")

MODEL = "claude-opus-4-8"

# 内置郑希 system prompt（也可以放到 personas/zhengxi.txt 里覆盖）
BUILTIN_PERSONAS = {
    "zhengxi": {
        "name": "郑希（易方达）",
        "system": textwrap.dedent("""\
            你是郑希，易方达权益投资管理部副总经理、基金经理。

            【投资方法】
            你的投资以景气度为核心，底层是"找通胀"：
            - 先在全球坐标系里找正在发生技术/需求变化、因此"涨价"的产业环节
            - 偏爱供给端创造需求的科技型通胀（新技术落地），而非纯供需错配的传统周期
            - 全球视野落到中国比较优势的那一环（例：AI Capex → 算力网络 → 光通信 → 中国光学传输）
            - 选股三件事：①流动性第一②偏好低ROE有弹性的标的③多维跟踪逐步拟合、周期拼接
            - 科技公司本质是周期股，不对个股形成信仰；底层逻辑变坏就卖

            【说话风格】
            客观、克制、产业逻辑清晰，不轻易给结论。习惯用产业链拆解+全球比较的框架分析行业。
            对不确定的事情会直接说"我没有研究清楚"或"需要跟踪验证"。
            不做涨跌预测、不给具体买卖指令。

            【角色边界】
            只代表郑希本人的公开观点与方法论，不构成投资建议。
            对没有直接研究过的话题，先声明，再用自己的框架推演，且把推演和已知事实清楚区分。
        """),
    }
}


def load_personas(ids: list[str]) -> list[dict]:
    """加载人物列表，优先读 personas/{id}.txt，没有就用内置。"""
    result = []
    for pid in ids:
        txt_path = os.path.join(PERSONAS_DIR, f"{pid}.txt")
        if os.path.exists(txt_path):
            with open(txt_path, encoding="utf-8") as f:
                content = f.read().strip()
            # 文件第一行如果是 # Name: xxx 则取那个名字
            name = pid
            lines = content.splitlines()
            if lines and lines[0].startswith("# Name:"):
                name = lines[0].replace("# Name:", "").strip()
                content = "\n".join(lines[1:]).strip()
            result.append({"id": pid, "name": name, "system": content})
        elif pid in BUILTIN_PERSONAS:
            result.append({"id": pid, **BUILTIN_PERSONAS[pid]})
        else:
            print(f"[警告] 找不到人物 '{pid}'（既没有 personas/{pid}.txt 也没有内置定义），已跳过。")
    return result


def call_persona(client: anthropic.Anthropic, persona: dict, messages: list) -> str:
    """调用单个人物，返回回复文本。"""
    resp = client.messages.create(
        model=MODEL,
        max_tokens=1024,
        system=persona["system"],
        messages=messages,
        thinking={"type": "adaptive"},
    )
    # 提取文本块
    return "\n".join(b.text for b in resp.content if b.type == "text")


def run_parallel(client, personas, question):
    """并行模式：每人独立回答同一问题。"""
    print(f"\n{'='*60}")
    print(f"问题：{question}")
    print(f"{'='*60}\n")

    results = {}
    for persona in personas:
        print(f"[{persona['name']}] 思考中…")
        reply = call_persona(client, persona, [{"role": "user", "content": question}])
        results[persona["id"]] = reply

    for persona in personas:
        print(f"\n{'─'*60}")
        print(f"【{persona['name']}】")
        print(f"{'─'*60}")
        print(results[persona["id"]])

    return results


def run_sequential(client, personas, question):
    """顺序讨论模式：每人看到前面所有发言后回答。"""
    print(f"\n{'='*60}")
    print(f"问题：{question}")
    print(f"{'='*60}\n")

    transcript = []  # 所有已发言的内容
    results = {}

    for i, persona in enumerate(personas):
        if i == 0:
            user_msg = question
        else:
            # 把前面的发言拼进来
            prior = "\n\n".join(
                f"【{p['name']}】说：\n{results[p['id']]}"
                for p in personas[:i]
            )
            user_msg = (
                f"{question}\n\n"
                f"以下是其他经理的看法，请你在此基础上发表自己的观点（可以同意、补充或不同意）：\n\n{prior}"
            )

        print(f"[{persona['name']}] 思考中…")
        reply = call_persona(client, persona, [{"role": "user", "content": user_msg}])
        results[persona["id"]] = reply

        print(f"\n{'─'*60}")
        print(f"【{persona['name']}】")
        print(f"{'─'*60}")
        print(reply)

    return results


def main():
    ap = argparse.ArgumentParser(description="基金经理圆桌讨论")
    ap.add_argument("question", help="你要提的问题")
    ap.add_argument(
        "--mode",
        choices=["parallel", "sequential"],
        default="parallel",
        help="parallel=各自独立回答；sequential=顺序发言互相回应（默认 parallel）",
    )
    ap.add_argument(
        "--personas",
        nargs="+",
        default=["zhengxi"],
        help="参与的人物 ID 列表（空格分隔），默认只有 zhengxi",
    )
    ap.add_argument("--save", help="把讨论结果保存到这个文件（JSON）")
    args = ap.parse_args()

    api_key = os.environ.get("ANTHROPIC_API_KEY")
    if not api_key:
        print("请设置环境变量 ANTHROPIC_API_KEY")
        sys.exit(1)

    client = anthropic.Anthropic(api_key=api_key)
    personas = load_personas(args.personas)
    if not personas:
        print("没有可用的人物，退出。")
        sys.exit(1)

    if args.mode == "sequential":
        results = run_sequential(client, personas, args.question)
    else:
        results = run_parallel(client, personas, args.question)

    if args.save:
        out = {
            "question": args.question,
            "mode": args.mode,
            "discussion": [
                {"persona": p["name"], "reply": results[p["id"]]}
                for p in personas
                if p["id"] in results
            ],
        }
        with open(args.save, "w", encoding="utf-8") as f:
            json.dump(out, f, ensure_ascii=False, indent=2)
        print(f"\n[已保存到 {args.save}]")


if __name__ == "__main__":
    main()
