# -*- coding: utf-8 -*-
"""PyInstaller 运行时钩子：在 App 导入前兜底 importlib.metadata。

问题根因：PyInstaller 冻结后默认不带 *.dist-info 元数据目录，而 streamlit
在导入时执行 `from importlib.metadata import version` → `version("streamlit")`
→ `distribution("streamlit").version`，查不到元数据就抛 PackageNotFoundError 直接崩。

修复策略（双重保险）：
1) FreeQuota.spec 已把全部 *.dist-info 作为 datas 打进包，原生查找本就能命中；
2) 这里再给 importlib.metadata.distribution / version 加兜底：查不到的包返回
   一个最小可用的占位 Distribution（版本号 "0.0.0"），既不崩溃，也保留真实包
   的元数据（优先用真值）。

注意：必须打在 distribution 这一层，而不是只打 version —— 因为 version() 内部
是通过模块全局名调用 distribution() 的，只替换 version 无法拦截 Streamlit
`from importlib.metadata import version` 这种别名绑定。

该文件由 PyInstaller 的 runtime_hooks 在入口脚本之前执行，因此时序上一定早于
任何 app 代码对 streamlit 的导入。
"""

import importlib.metadata as _im
import os
import sys


class _FallbackDistribution(_im.Distribution):
    """给缺失元数据的包一个最小可用的占位 Distribution。"""

    def __init__(self, name):
        super().__init__()
        self._name = name

    @property
    def name(self):
        return self._name

    @property
    def version(self):
        return "0.0.0"

    def locate_file(self, path):
        from pathlib import Path
        return Path(path)

    def metadata(self):
        from email.message import EmailMessage
        msg = EmailMessage()
        msg["Name"] = self._name
        msg["Version"] = "0.0.0"
        return msg

    def _get_metadata(self, name):
        return []

    @property
    def files(self):
        return None

    @property
    def requires(self):
        return None


_orig_distribution = _im.distribution


def _safe_distribution(name):
    try:
        return _orig_distribution(name)
    except Exception:
        return _FallbackDistribution(name)


try:
    _im.distribution = _safe_distribution
except Exception:
    pass


_orig_version = _im.version


def _safe_version(name):
    try:
        return _orig_version(name)
    except Exception:
        return "0.0.0"


try:
    _im.version = _safe_version
except Exception:
    pass


# 仅用于诊断：确认本钩子确实在冻结态被执行（不影响功能）。
try:
    if getattr(sys, "frozen", False):
        _marker = os.path.join(
            os.path.dirname(os.path.abspath(sys.executable)),
            "rth_metadata_ran.txt",
        )
        with open(_marker, "a", encoding="utf-8") as _f:
            _f.write("rth_metadata ran\n")
except Exception:
    pass
