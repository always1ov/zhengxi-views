# -*- coding: utf-8 -*-
"""下载全市场公募基金代码列表，生成 references/all_funds/ 下的分片 JSON 文件。
全市场约 2.7 万只基金。刷新重跑：  python scripts/build_fund_list.py
来源：天天基金 fundcode_search.js（公开数据）。
注：原始 JSON 约 4MB，拆分为多个 <1MB 的分片以符合技能打包单文件限制。
"""
import os, re, json, datetime
import requests

requests.packages.urllib3.disable_warnings()
HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
OUT = os.path.join(ROOT, "references", "all_funds")
CHUNK_SIZE = 5000


def main():
    os.makedirs(OUT, exist_ok=True)
    url = "http://fund.eastmoney.com/js/fundcode_search.js"
    r = requests.get(url, headers={"User-Agent": "Mozilla/5.0"}, timeout=60, verify=False)
    r.encoding = "utf-8"
    m = re.search(r"=\s*(\[.*\]);?\s*$", r.text, re.S)
    arr = json.loads(m.group(1))
    funds = [{"code": x[0], "abbr": x[1], "name": x[2], "type": x[3], "pinyin": x[4]}
             for x in arr if len(x) >= 5]

    meta = {
        "updated": datetime.datetime.now().strftime("%Y-%m-%d %H:%M"),
        "source": "天天基金 fundcode_search.js（公开数据）",
        "count": len(funds),
    }
    with open(os.path.join(OUT, "fund_list_meta.json"), "w", encoding="utf-8") as f:
        json.dump(meta, f, ensure_ascii=False)

    chunk_count = 0
    for i, start in enumerate(range(0, len(funds), CHUNK_SIZE)):
        chunk = funds[start:start + CHUNK_SIZE]
        path = os.path.join(OUT, f"fund_list_chunk_{i}.json")
        with open(path, "w", encoding="utf-8") as f:
            json.dump(chunk, f, ensure_ascii=False, separators=(",", ":"))
        chunk_count += 1

    # 删除旧的 gz 文件（如果存在）
    old_gz = os.path.join(OUT, "fund_list.json.gz")
    if os.path.exists(old_gz):
        os.remove(old_gz)
        print("已删除旧版 fund_list.json.gz")

    # 类型清单
    types = sorted({f["type"] for f in funds})
    with open(os.path.join(OUT, "_types.txt"), "w", encoding="utf-8") as f:
        f.write("\n".join(types))

    print(f"已写入 {len(funds)} 只基金 → {chunk_count} 个分片 (fund_list_chunk_0 … chunk_{chunk_count-1})")
    print(f"类型共 {len(types)} 种，见 references/all_funds/_types.txt")


if __name__ == "__main__":
    main()
