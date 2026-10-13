"""FreeQuota 核心：双模式统一接入。

两种模式：
- 极简（simple）：FreeQuota 内置轻量接力，轮流试你填的国内免费 Key，一家挂了自动换下一家。
- 进阶（gateway）：FreeQuota 把自己指向你已装好的开源网关（FreeLLMAPI / OmniRoute），
  由网关内部路由几百家模型，FreeQuota 只负责中文界面。

设计要点（为什么这套只対「白嫖党」成立）：
- 各家大模型的注意力缓存是各自专属的，中途换模型会让缓存清零，
  整段对话历史要按全价重算一遍 —— 付费用户中途切换反而更贵。
- 但本项目用各家「免费额度」，重算成本由厂商承担，用户只多等几秒 —— 接力对免费用户净赚。
- 上下文通过标准 OpenAI messages 数组完整转发，用户无感。
- 所有调用只走各家官方接口或你自己的本地网关，密钥只存在本机 config.json。
"""

import json

import httpx

TIMEOUT = 60.0


def _post(base_url: str, api_key: str, model: str, messages: list) -> str:
    """对标准 OpenAI 兼容接口发一次非流式请求，返回回复文本。"""
    url = f"{base_url.rstrip('/')}/v1/chat/completions"
    payload = {"model": model, "messages": messages, "stream": False}
    headers = {
        "Authorization": f"Bearer {api_key}",
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


class Provider:
    """极简模式里一个被聚合的国内免费模型来源。"""

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
        """没启用、或 Key 还是模板占位符时，视为未配置，跳过。"""
        if not self.enabled:
            return False
        placeholder = ("在此填入" in self.api_key) or (not self.api_key)
        return not placeholder

    def chat(self, messages: list) -> str:
        return _post(self.base_url, self.api_key, self.model, messages)


class Gateway:
    """进阶模式：指向你已装好的开源网关（FreeLLMAPI / OmniRoute）。

    网关内部负责路由、接力、冷却、限流；FreeQuota 只把它当成一个「超大 provider」来调。
    网关通常跑在本地（localhost），很多免 key，所以 api_key 允许为空。
    """

    def __init__(self, cfg: dict):
        self.base_url = str(cfg.get("base_url", "")).rstrip("/")
        self.api_key = cfg.get("api_key", "")
        self.model = cfg.get("model", "auto")
        self.enabled = bool(cfg.get("enabled", False))
        self.last_status = "未测试"

    def is_configured(self) -> bool:
        if not self.enabled:
            return False
        return bool(self.base_url)

    def chat(self, messages: list) -> str:
        return _post(self.base_url, self.api_key, self.model, messages)


def load_config(path: str = "config.json") -> dict:
    """读取整个配置对象，返回 {mode, gateway, providers}。"""
    try:
        with open(path, "r", encoding="utf-8") as f:
            cfg = json.load(f)
    except FileNotFoundError:
        return {"mode": "auto", "gateway": None, "providers": []}

    gateway = Gateway(cfg["gateway"]) if cfg.get("gateway") else None
    raw = [Provider(c) for c in cfg.get("providers", [])]
    providers = [p for p in raw if p.is_configured()]
    providers.sort(key=lambda p: p.priority)
    return {"mode": cfg.get("mode", "auto"), "gateway": gateway, "providers": providers}


def relay_chat(messages: list, cfg: dict):
    """统一入口：根据 mode 决定走网关还是内置接力。

    返回 (回复文本, 实际来源名, 接力日志列表)。
    """
    mode = cfg.get("mode", "auto")
    gateway = cfg.get("gateway")
    providers = cfg.get("providers", [])
    log = []

    # 优先走网关（gateway / auto 且网关已配置）
    use_gateway = (mode in ("auto", "gateway")) and gateway and gateway.is_configured()
    if use_gateway:
        try:
            content = gateway.chat(messages)
            gateway.last_status = "正常"
            log.append(f"[成功] 由网关路由回复（{gateway.base_url}）")
            return content, f"网关 · {gateway.base_url}", log
        except Exception as e:
            gateway.last_status = f"失败: {str(e)[:40]}"
            log.append(f"[网关失败] {str(e)[:60]}")
            if mode == "gateway":
                raise RuntimeError(
                    "网关调用失败，请检查：网关是否已启动、config.json 的 gateway 配置是否正确"
                )
            # auto 模式：网关失败，自动回退到内置接力
            log.append("自动回退到内置接力模式……")

    if not providers:
        raise RuntimeError(
            "没有可用的 provider，也没有可用的网关。请检查 config.json："
            "填好 providers 的免费 Key，或在 gateway 中填好你的网关地址。"
        )

    # 极简模式：内置轻量接力，一家失败自动换下一家
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
