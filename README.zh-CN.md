# Public Registry：公共 API 与数据集目录

把公开的 **API**、可下载的**数据集**和 **MCP 服务器**收在一个目录里。每个资源是一个 YAML 文件，经 JSON Schema
校验，写明获取方式和已知的自身许可，链接每天检测一次。清单、网站、导出文件和只读接口都由 `data/` 生成，不手工编辑。

[English](README.md)

| 截至 2026-09-27 | |
|---|---|
| 资源 | 2,352 个，分布在 45 个领域（1,907 个 API、680 个数据集、3 个 MCP 服务器；其中 238 个同时是 API 和数据集），另有 195 个已归档 |
| 链接可用 | 已检测资源中 99.4% 可用（15 个尚未检测成功，没有判为失效的） |
| 许可已知 | 数据集 74.4%，API 9.4%（public-apis 原表从未记录许可） |
| 中文说明 | 100% |

## 怎么用

- **网站**：<https://reg.cugeng.com/>。按领域、类型、许可、获取方式、鉴权和链接状态检索筛选，
  另有质量看板。想在本地查看，运行 `python -m registry_kit build` 后打开 `build/site/index.html`。
- **下载**：网站根目录下的 `export/resources.csv`、`export/resources.json`、`export/registry.sqlite`。
- **只读接口**：`api/v1/index.json`、`api/v1/resources/{id}.json`、`api/v1/domains/{domain}.json`、
  `api/v1/kinds/{kind}.json`，都是静态 JSON，无需 key，不限流。
- **Markdown 清单**：`build/docs/zh-CN/` 和 `build/docs/en/`，每个领域一页。

## 仓库结构

| 路径 | 内容 | 由谁修改 |
|---|---|---|
| `data/<领域>/<id>.yml` | 一个文件一个资源，文件名就是永久 id | 贡献者，经拉取请求 |
| `data/_archive/<id>.yml` | 已失效的资源，附日期和原因；其 URL 仍然被占用 | 链接检测任务（开拉取请求）或维护者 |
| `i18n/zh-CN/<id>.yml` | 资源的中文名称、说明和分组 | 译者 |
| `vocab/` | 领域、许可（SPDX 标识加 6 个 `LicenseRef-` 取值）和格式词表 | 维护者 |
| `schema/` | 由 `vocab/` 生成的 JSON Schema（`registry_kit schema`） | 不手改 |
| `registry_kit/` | 引擎：校验、规范化、健康检测、渲染、导出、网站 | 维护者 |
| `health/` | 维护者手工确认无害的链接信号；每日状态存放在 `health-data` 分支 | 维护者（链接检测任务只写 `health-data` 分支） |
| `tools/` | 一次性的 GitHub 设置脚本，以及许可核查辅助脚本 | 维护者 |
| `docs/` | [数据来源与构建记录](docs/provenance.zh-CN.md)、[个人维护手册](docs/maintaining.zh-CN.md)和资源模板 | 维护者 |

字段规则见 [CONTRIBUTING.md](CONTRIBUTING.md)，机器可读的约定是 `schema/resource.schema.json`。资源文件里不写任何链接
状态。

## 命令

```
python -m pip install -r requirements.txt
python -m registry_kit validate            # 所有规则、所有文件，一次列出全部问题
python -m registry_kit format              # 规范格式，改写许可和格式别名，去掉追踪参数
python -m registry_kit health              # 检测链接，更新 health/status.json（连续 3 次失败且满 7 天才算失效）
python -m registry_kit build               # 网站、导出、只读接口和 Markdown 清单
python -m registry_kit stats               # 数量与完整度
python -m unittest discover -s tests -t .  # 引擎测试，以及针对真实数据的回归测试
```

## 变更如何进入

1. **拉取请求门禁**（`pr-gate.yml`）：Schema、规范格式、规范化 URL 在全部资源（含已归档）中唯一、受控取值、占位文本，
   并实时检测新链接。新增的文件还必须写明许可及其出处页面，以及发布方。任何一项失败都不会跳过其他检查，
   `pr-comment.yml` 用一条评论列出全部问题。测试在 Linux 和 Windows 上都跑。
2. **合并门禁**（`.github/rulesets/main.json`）：所有改动，包括维护者自己的，都必须经拉取请求进入 `main`；分支必须与
   `main` 同步，并且 `validate` 和 Linux、Windows 两个 `tests` 都通过之后才能合并，所以两个拉取请求不会加进同一个链接。
   含有无法关联到 GitHub 账号的提交的拉取请求，还需要一个批准。禁止直接推送和强制推送，只允许 squash 合并；只有维护者能合并。
3. **链接健康**（`health.yml`，每日）：每个主机最多 2 个并发请求，超时和 5xx 重试，401/403/429 算可用。连续 3 次失败且
   跨度至少 7 天才判为失效；跨站跳转、停放页或博彩页面标为待核实。首次失败满 30 天，检测任务开拉取请求把它移入
   `data/_archive/`（同一时间只开一个）。由工作流开的拉取请求，GitHub 会先暂停它的检查，等维护者在拉取请求页面批准后才运行。
4. **发布**（`publish.yml`）：同一并发组，只有最新一次运行会发布；构建任务先校验数据，只有读权限；Pages 用 OIDC
   部署，部署后等待只读接口报告出本次构建所用的提交才算完成。

## 许可

代码：[MIT](LICENSE)。目录数据：[CC BY 4.0](LICENSE-DATA)。每个资源的 license 字段描述的是该资源本身，而不是本目录。
2026 年 9 月收录的资源中，1,739 个导入自 public-apis 清单（MIT），613 个为独立调研所得，详见 [NOTICE](NOTICE) 和
[数据来源与构建记录](docs/provenance.zh-CN.md)。

## 维护方式

本仓库由一人维护。任何人都可以通过拉取请求贡献：自动检查几分钟内给出结果（首次贡献者需等维护者批准运行），维护者
通常在几天内处理。规则对维护者同样
生效，每一处改动都以相同方式检查和留痕。仓库包含运行所需的一切（数据、引擎、流水线，以及 `health-data` 分支上的链接
状态历史），任何人都可以随时 fork 接手。以后如果有协作者加入，添加 `.github/CODEOWNERS` 并提高规则集里的批准人数即可。日常维护流程见
[个人维护手册](docs/maintaining.zh-CN.md)。

## 需要在 GitHub 上完成的设置

第一次推送后，用仓库所有者身份登录 GitHub CLI（`gh auth login`），运行一次：

```
bash tools/github_setup.sh 所有者/仓库名 [域名]
```

它会完成这些设置：只允许 squash 合并；导入 `.github/rulesets/main.json` 作为默认分支的规则集；Pages 由 Actions 部署；
允许工作流开归档拉取请求；首次贡献者的工作流需维护者批准后才运行；开启 Dependabot 警报与安全更新、私密漏洞报告；创建
标签；用当前链接状态初始化 `health-data` 分支。任何一步通过接口设置失败，都会提示在网页上的哪里手动设置。

可选的“域名”参数让网站改用自定义域名，并启用 HTTPS，原来的 `所有者.github.io/仓库名` 会自动跳转过去。运行前先在
域名服务商把域名指向 GitHub：子域名加一条指向 `所有者.github.io` 的 CNAME 记录；根域名加 GitHub Pages 的 A 和 AAAA
记录。本目录的网站在 `reg.cugeng.com`。
