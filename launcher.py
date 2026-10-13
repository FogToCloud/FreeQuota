"""FreeQuota 启动器（PyInstaller 入口，冻结后即为 FreeQuota.exe）。

给不懂编程的普通人用的「双击即用」入口：
1. 重定向 stdout/stderr 到同目录 FreeQuota.log（无控制台打包版排错用）。
2. 兜底 importlib.metadata：冻结后 .dist-info 缺失会让 streamlit 导入即崩，
   这里给 distribution()/version() 加兜底，查不到就返回占位对象。
3. 解析打包后的资源路径（app.py / config.example.json 在 _MEIPASS 里）。
4. 首次运行时，若 exe 同目录没有 config.json，自动从 example 复制一份，并打开配置说明页。
5. 用 streamlit 的 bootstrap 在本进程内启动 app.py。

冻结版踩过的三个坑（都已在下面注释处处理，改动前请先读注释）：
- flag_options 不会自动生效：必须显式调 bootstrap.load_config_options()。
- 开发模式误判：必须显式 global.developmentMode=False，否则根路径 404。
- run() 第二个参数必须是布尔 False，不能是空字符串。
"""

import os
import sys


class _Tee:
    """同时写控制台和日志文件。"""

    def __init__(self, console, log_file):
        self._console = console
        self._log = log_file

    def write(self, data):
        try:
            self._log.write(data)
            self._log.flush()
        except Exception:
            pass
        try:
            self._console.write(data)
        except Exception:
            pass

    def flush(self):
        try:
            self._log.flush()
        except Exception:
            pass
        try:
            self._console.flush()
        except Exception:
            pass


# 1) 重定向到日志文件（仅冻结态、无控制台时更有意义，但开发态也不影响）
try:
    if getattr(sys, "frozen", False):
        _log_dir = os.path.dirname(os.path.abspath(sys.executable))
        _log_path = os.path.join(_log_dir, "FreeQuota.log")
        _lf = open(_log_path, "a", encoding="utf-8", buffering=1)
        sys.stdout = _Tee(sys.stdout, _lf)
        sys.stderr = _Tee(sys.stderr, _lf)
except Exception:
    pass


# 2) 兜底 importlib.metadata —— 必须在 import streamlit 之前打补丁。
#    注意：要打在 distribution 这一层（version() 内部通过模块全局名调用
#    distribution，只替换 version 拦不住 streamlit 的 `from ... import version` 别名）。
#   运行时钩子 rth_metadata.py 也会打同样的补丁，这里再兜底一次。
import importlib.metadata as _im


class _FallbackDistribution(_im.Distribution):
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


def resource_path(rel):
    """打包后资源在 _MEIPASS；开发态下在脚本同目录。"""
    base = getattr(sys, "_MEIPASS", os.path.dirname(os.path.abspath(__file__)))
    return os.path.join(base, rel)


def app_dir():
    """config.json 写在 exe 同目录（便携）；开发态下写 cwd。"""
    if getattr(sys, "frozen", False):
        return os.path.dirname(os.path.abspath(sys.executable))
    return os.getcwd()


def ensure_config():
    cfg = os.path.join(app_dir(), "config.json")
    if not os.path.exists(cfg):
        example = resource_path("config.example.json")
        if os.path.exists(example):
            import shutil
            shutil.copy(example, cfg)
            # 复制后给用户一个友好的配置说明页
            import webbrowser
            webbrowser.open(
                "https://github.com/FogToCloud/FreeQuota#%E5%AE%89%E8%A3%85%E6%9E%81%E7%AE%80%E6%A8%A1%E5%BC%8F%E4%B8%89%E6%AD%A5"
            )
    return cfg


def main():
    import webbrowser

    app_path = resource_path("app.py")
    cfg = ensure_config()
    os.environ["FREQUOTA_CONFIG"] = cfg

    # 把 app.py 所在目录加入 sys.path，保证 `from core.relay import` 能被 importlib 找到
    app_base = os.path.dirname(app_path)
    if app_base and app_base not in sys.path:
        sys.path.insert(0, app_base)

    import streamlit.web.bootstrap as bootstrap

    flag_options = {
        "server.headless": False,
        "browser.gatherUsageStats": False,
        "server.port": 8501,
        # 必须显式关闭开发模式：streamlit 靠自身 __file__ 里有没有 "site-packages"
        # 来猜在不在开发模式；冻结后 __file__ 落在 _internal 下，会被误判成 True，
        # 从而不挂载前端静态资源路由 —— 表现为网页根路径返回 404（/_stcore/* 却是 200）。
        "global.developmentMode": False,
    }

    # 关键：bootstrap.run() 内部只注册了「配置文件变更」回调，启动时并不会应用
    # flag_options（那是 streamlit CLI 才做的事）。直接以库方式调用 run() 时，
    # 必须自己先显式 load 一次，否则上面这些 flag 全部空转不生效。
    bootstrap.load_config_options(flag_options)

    # 第二个参数是 is_hello（是否运行 Hello 演示脚本），必须是布尔 False。
    # 传 "" 会被写进 protobuf 的 bool 字段，报 TypeError: 'str' object cannot be
    # interpreted as an integer，导致会话建不起来。
    bootstrap.run(app_path, False, [], flag_options)


if __name__ == "__main__":
    main()
