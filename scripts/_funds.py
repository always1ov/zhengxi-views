# -*- coding: utf-8 -*-
"""全市场基金列表的共享加载器。

数据拆分为 references/all_funds/fund_list_meta.json（元数据）和
fund_list_chunk_0.json … fund_list_chunk_N.json（分片，每片 <1MB）存储，
避免触发技能打包的单文件 1MB 上限。
兼容旧格式：若存在 fund_list.json.gz 或 fund_list.json 也能读。
"""
import os, json, gzip

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
_DIR = os.path.join(ROOT, "references", "all_funds")
LIST_GZ = os.path.join(_DIR, "fund_list.json.gz")
LIST_JSON = os.path.join(_DIR, "fund_list.json")
LIST_META = os.path.join(_DIR, "fund_list_meta.json")


def list_path():
    """返回实际存在的数据文件路径（分片优先），都没有则返回 None。"""
    if os.path.exists(LIST_META):
        return LIST_META
    if os.path.exists(LIST_GZ):
        return LIST_GZ
    if os.path.exists(LIST_JSON):
        return LIST_JSON
    return None


def load_list():
    """读出整个 {updated, source, count, funds} 字典；文件不存在返回 None。"""
    # chunked format
    if os.path.exists(LIST_META):
        with open(LIST_META, encoding="utf-8") as f:
            meta = json.load(f)
        all_funds = []
        i = 0
        while True:
            chunk_path = os.path.join(_DIR, f"fund_list_chunk_{i}.json")
            if not os.path.exists(chunk_path):
                break
            with open(chunk_path, encoding="utf-8") as f:
                all_funds.extend(json.load(f))
            i += 1
        meta["funds"] = all_funds
        return meta
    # legacy gz
    if os.path.exists(LIST_GZ):
        with gzip.open(LIST_GZ, "rt", encoding="utf-8") as f:
            return json.load(f)
    # legacy plain json
    if os.path.exists(LIST_JSON):
        with open(LIST_JSON, encoding="utf-8") as f:
            return json.load(f)
    return None
