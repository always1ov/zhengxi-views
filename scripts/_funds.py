# -*- coding: utf-8 -*-
"""全市场基金列表的共享加载器。

数据以 references/all_funds/fund_list.json.gz（gzip 压缩，约 0.7MB）入库：
未压缩约 4MB，超过技能打包的单文件 1MB 上限，故压缩存储。
为兼容旧数据，未压缩的 fund_list.json 若存在也能读。
"""
import os, json, gzip

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
_DIR = os.path.join(ROOT, "references", "all_funds")
LIST_GZ = os.path.join(_DIR, "fund_list.json.gz")
LIST_JSON = os.path.join(_DIR, "fund_list.json")


def list_path():
    """返回实际存在的数据文件路径（优先 .gz），都没有则返回 None。"""
    if os.path.exists(LIST_GZ):
        return LIST_GZ
    if os.path.exists(LIST_JSON):
        return LIST_JSON
    return None


def load_list():
    """读出整个 {updated, source, count, funds} 字典；文件不存在返回 None。"""
    p = list_path()
    if not p:
        return None
    if p.endswith(".gz"):
        with gzip.open(p, "rt", encoding="utf-8") as f:
            return json.load(f)
    with open(p, encoding="utf-8") as f:
        return json.load(f)
