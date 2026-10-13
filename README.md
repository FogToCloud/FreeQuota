# FreeQuota

> 一个中文界面的免费大模型额度聚合客户端：把智谱、硅基流动、豆包等厂商送的免费 API 额度聚在一起，一家用完了自动换下一家，开箱即用。
> 路由和接力直接借用成熟的开源网关（FreeLLMAPI / OmniRoute），我们只补最缺的一层：给中文用户一个看得懂、装得上的客户端。

---

## 为什么有这个项目（取其精华，不重复造轮子）

GitHub 上已有 FreeLLMAPI（27K+ Star）、OmniRoute（74K+ Star）把"免费额度自动接力"做得非常完整。
但它们主要面向程序员，要 npm / Docker / 登录 / 绑定一大串手动操作，普通用户很难用起来。

我们不做第 N 个网关，我们做**它之上的那一层**：

- FreeLLMAPI / OmniRoute = 引擎（路由、接力、冷却、限流）—— 成熟方案，直接借用
- FreeQuota = 客户端（中文界面、开箱启动、国内免费额度引导、聊天体验）—— 最缺的那一层

> 设计原则：AI 时代，手动操作能省就省，尽量自动化、开箱即用。

---

## 两种用法（越往下越省事）

### 模式一：极简（推荐小白，无需装任何外部网关）
直接在 FreeQuota 里填你的**国内免费 Key**（智谱 / 硅基流动 / 豆包），客户端自带轻量路由自动接力。
双击即用，不用碰 Docker、不用登录绑定。

### 模式二：进阶（想要 800+ 模型）
如果你已装 FreeLLMAPI / OmniRoute，把 FreeQuota 指向它们的本地端点即可，
一个 Key 路由几百家模型，FreeQuota 负责把它变成中文聊天界面。

> 两种模式都遵循「Key 只存本机、不经第三方中转」的红线。

---

## 开箱即用设计清单

- 一键 / 双击启动，不出现命令行
- 填一次 Key 就能聊天，绝不出现"部署 → 登录 → 绑定 → 组合 → 密钥"流程
- 自动接力：一家额度用完，后台自动换下一家，你无感
- 自动更新：目录 / 模型列表自动同步（进阶模式由网关负责）
- 透明：每条回复标注「本次由 XX 回复」

---

## 功能

- 中文聊天界面（像用 ChatGPT 一样聊天）
- 额度油表（侧边栏实时看每家状态：正常 / 失败 / 未测试）
- 自动接力（极简模式内置轻量路由；进阶模式交给网关）
- 透明可见（每条回复显示当前模型）
- 纯本地、零月费、密钥只存本机

---

## 安装（极简模式，三步）

> 前提：电脑已装 Python 3.10+。没装去 python.org 下载，安装时勾选「Add to PATH」。

**第 1 步：装依赖**

```bash
pip install -r requirements.txt
```

**第 2 步：填你的免费 Key**

1. 把 `config.example.json` 复制一份，改名为 `config.json`
2. 打开 `config.json`，把占位符换成你自己的免费 API Key
3. 去哪申请（都免费，几分钟搞定）：
   - 智谱 GLM-Flash：**永久免费不限量**，注册即送，官方 bigmodel.cn
   - 硅基流动：新用户送 2000 万+ token，siliconflow.cn
   - 豆包方舟：每日 0 点刷新额度，volcengine.com（可选）

**第 3 步：启动**

```bash
streamlit run app.py
```

浏览器自动打开；没有就访问终端提示的地址（一般 http://localhost:8501）。

---

## 进阶模式配置

把 `config.example.json` 复制为 `config.json` 后，改成下面这样——核心是打开 `gateway.enabled` 并把 `mode` 设成 `gateway`（FreeLLMAPI 默认端口 3001，OmniRoute 默认 8402）：

```json
{
  "mode": "gateway",
  "gateway": {
    "base_url": "http://localhost:3001",
    "api_key": "你的网关密钥（部分网关免填）",
    "model": "auto",
    "enabled": true
  },
  "providers": []
}
```

FreeQuota 会把所有对话发给网关，由它内部路由几百家模型。

> 偷懒办法：把 `mode` 设成 `"auto"` 也行——FreeQuota 会优先用网关，网关万一挂了，自动回退到内置接力（用你填的 providers）。两种模式都遵守「密钥只存本机、不经第三方中转」红线。

---

## Windows 双击版（exe）—— 彻底告别命令行

面向不懂编程的普通人：不用装 Python、不用敲命令，双击一个 exe 就能用。

- 在本机构建好后，`dist/FreeQuota/FreeQuota.exe` 就是成品，双击即启动，浏览器自动打开。
- **自己重新打包**：双击仓库里的 `打包.bat`（前提电脑已装 Python 3.10+ 并勾选 Add to PATH），等它跑完即可在 `dist/FreeQuota/` 拿到 exe。
- 首次运行会在 exe 同目录自动生成 `config.json` 并弹出配置说明页，填好免费 Key 刷新即可。
- 打包配置 `FreeQuota.spec` 已处理几个关键坑，改之前建议先看 `launcher.py` 里的注释：
  1. **Streamlit 前端静态资源**必须随包收集，否则页面白屏；并且要用 `collect_submodules("streamlit")`
     递归收集全部子模块（像 `streamlit.runtime.scriptrunner.magic_funcs` 这种是运行时动态导入的，
     静态分析扫不到，漏了会报 `ModuleNotFoundError`）。
  2. **`.dist-info` 元数据**打进包（`app.py` / `config.example.json` 同理），否则 Streamlit 导入即崩。
  3. **`global.developmentMode` 必须显式设为 False**：Streamlit 靠自己 `__file__` 里有没有
     `site-packages` 来猜是否在开发模式，冻结后被误判为 True，就不会挂载前端资源路由 ——
     表现为 `http://localhost:8501/` 返回 404（但 `/_stcore/health` 却是 200）。
     另外注意：`bootstrap.run()` 传的 `flag_options` 不会自动生效，必须自己先调一次
     `bootstrap.load_config_options(flag_options)` 才行。
- 密钥只存在 exe 同目录的 `config.json`，不联网、不上传。

---

## 工作原理（给想了解的人）

```
极简模式：  你的提问 → [FreeQuota 的轻量接力器] → 智谱/硅基流动/豆包 轮流试，一家挂了自动换下一家
进阶模式：  你的提问 → [FreeQuota 的中文界面] → FreeLLMAPI/OmniRoute → 它们内部路由 800+ 模型
```

两种模式都走标准 OpenAI 兼容接口，密钥只在本机。

---

## 安全红线（本项目铁律）

1. **密钥只存在你本机的 `config.json`**，不收集、不上传。请把 `config.json` 加进 `.gitignore`（本项目已默认忽略）。
2. **绝不经过第三方中转站聚合 API**。CISPA 2026 报告显示 **45.83% 的中转站存在「模型掉包」**（你以为在调 GPT，实际返回的是别的模型）。本项目只做本机直连各家官方接口或你自己的网关。
3. **免费额度用完后可能自动从绑定的支付方式扣费**。请在各家控制台设置用量警报；本项目不做任何付费调用。

---

## 与巨头的关系（我们补什么，不抢什么）

| 项目 | 它做（精华，我们借用） | 它缺（我们补） |
|---|---|---|
| FreeLLMAPI（27K★） | 路由 / 接力 / 冷却 / 限流 / 桌面+手机版 | 中文界面、开箱启动、面向聊天 |
| OmniRoute（74K★） | 290+ 家、90+ 免费档、token 压缩 | 国内小白用不起它那套手动流程 |
| new-api（40K★） | 通用企业网关、跨格式转换 | 非白嫖专用、AGPL |

**FreeQuota 的空白位：给不懂编程的中国人，中文界面、双击即用、自动接力、面向聊天——站在巨人肩膀上，不重复造轮子。**

---

## 路线图

- [x] 中文聊天界面 + 额度油表（v1）
- [x] 极简模式：内置轻量路由，国内免费 Key 直接填
- [x] 进阶模式：可指向 FreeLLMAPI / OmniRoute 网关端点
- [x] 一键打包成 Windows .exe，彻底告别命令行（开箱即用最后一环）
- [ ] 国内免费额度一键检测 / 申请向导
- [ ] 难度分诊台：按提问难度自动选性价比最高的模型

---

## 许可证

MIT —— 随便用、随便改、随便拿去发。只要保留署名。

---

## 免责声明

本项目仅聚合各模型厂商**官方免费额度**，不破解、不盗用、不绕过任何付费机制。
使用者需自行遵守各家平台的免费额度使用条款。本项目不对因违规使用导致的封号或扣费负责。
