"""FreeQuota 核心：多模型统一接入 + 额度接力。

设计要点（决定这个项目为什么只对「白嫖党」成立）：
- 各家大模型的「注意力缓存」是各自专属的，中途换模型会让缓存清零，
  整段对话历史要按全价重新算一遍。付费用户中途切换反而更贵。
- 但本项目用的是各家「免费额度」，重算的成本由厂商承担，
  用户只多等几秒 —— 所以接力对免费用户是净赚。
- 上下文通过标准的 OpenAI messages 数组完整转发给下一家，用户无感。
"""

import json

import httpx

TIMEOUT = 60.0


class Provider:
    """一个被聚合的免费模型来源。"""

    def __init__(self, cfg: dict):
        self.name = cfg.get("name", "未命名")
        self.base_url = str(cfg["base_url"]).rstrip("/")
        self.api_key = cfg.get("api_key", "")
        self.model = cfg["model"]
        self.priority = int(cfg.get("priority", 100))
        self.enabled = bool(cfg.get("enabled", True))
        # 状态灯：未测试 / 正常 / 失败原因
        self.last_status = "未测试"

    def is_configured(self) -> bool:
        """Key 还是模板占位符时，视为未配置，跳过。"""
        placeholder = ("在此填入" in self.api_key) or (not self.api_key)
        return not placeholder

    def chat(self, messages: list) -> str:
        """调用一次对话接口，返回回复文本。失败抛异常由接力层捕获。"""
        url = f"{self.base_url}/v1/chat/completions"
        payload = {"model": self.model, "messages": messages, "stream": False}
        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json",
        }
        with httpx.Client(timeout=TIMEOUT) as client:
            resp = client.post(url, json=payload, headers=headers)
            if resp.status_code == 200:
                data = resp.json()
                return data["choices"][0]["message"]["content"]
            try:
                err = resp.json().get("error", {}).get("message", resp.text)
            except Exception:
                err = resp.text
            raise RuntimeError(f"HTTP {resp.status_code}: {err}")


def load_providers(path: str = "config.json") -> list:
    """读取配置，过滤掉未启用 / 未配置的，按优先级排序。"""
    try:
        with open(path, "r", encoding="utf-8") as f:
            cfgs = json.load(f)
    except FileNotFoundError:
        return []
    providers = [
        Provider(c)
        for c in cfgs
        if c.get("enabled", True) and Provider(c).is_configured()
    ]
    providers.sort(key=lambda p: p.priority)
    return providers


def relay_chat(messages: list, providers: list):
    """按优先级接力：一家失败自动换下一家，messages 完整转发。

    返回 (回复文本, 实际使用的 provider 名, 接力日志列表)。
    """
    log = []
    for p in providers:
        try:
            content = p.chat(messages)
            p.last_status = "正常"
            log.append(f"[成功] 本轮由「{p.name}」回复")
            return content, p.name, log
        except Exception as e:
            p.last_status = f"失败: {str(e)[:40]}"
            log.append(f"[接力] {p.name} 失败：{str(e)[:60]}，已自动切换下一家")
            continue
    raise RuntimeError("所有可用的 provider 都失败了，请检查 config.json 与网络")
