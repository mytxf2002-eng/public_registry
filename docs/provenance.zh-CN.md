# 数据来源与构建记录

本目录在 2026-09-27 首次构建。这里记录当时数据从哪里来、怎样处理、得到了哪些数字；之后的每一处改动都在 git 历史里。构建用的
一次性转换脚本和调研中间文件不属于本仓库。许可与署名见 [NOTICE](../NOTICE)。

## 概况

- **2,352 个资源**，分布在 45 个领域：1,907 个 API、680 个数据集、3 个 MCP 服务器，其中 238 个同时是 API 和数据集；另有
  195 个已归档。
- **来源**：1,739 个导入自 public-apis 清单（MIT 许可）；613 个是数据集的独立调研成果；另有 77 个数据集侧面并入已有资源。
- **质量**：全量校验 0 错误、0 警告；两轮链接检测后 2,331 个可用（99.1%）、21 个待确认、0 个失效。
- **最大的缺口是 API 的许可**：public-apis 从未记录许可，导入的 1,739 个资源里只有 35 个（2.0%）许可已知（来自合并进来的
  数据集侧面和第 3 节的许可核实）；全部 API 中许可已知的是 9.4%。

## 1 public-apis 的导入

- 1,737 个 API 和 3 个 MCP 服务器转为 1,740 个资源文件，取其名称、链接、描述、鉴权、HTTPS 和 CORS。其中 blague.xyz 随后因
  域名被挂牌出售而归档（见下），现为 1,739 个。
- **收录日期**来自 public-apis 的 git 历史（2,723 次提交，兼容 2016 年以来的所有表格写法）：每条取 URL 或“标题 + 主机”最早
  出现的日期；导入前的清理中改名或换链接的条目，按被替换的旧行取日期。1,739 条全部有日期，从 2016-03-21 到 2026-09-27。
- **同领域重名**的 26 个 API 在名称后加主机（代码托管平台用“主机/所有者”，同主机时用原分类）；两个 MCP 服务器改用官方名称
  “GitHub MCP Server”“Filesystem MCP Server”。
- **APILayer 的 27 个产品**在 public-apis 中是该清单赞助商的产品，本目录按普通资源收录，不标 `sponsored`：这个字段只用于
  本项目自己的赞助商，而本项目没有赞助商。
- **中文说明和分组**由本项目撰写。原表中针对表格本身的评语改写为“英文描述称……”“收录信息标注……”，关于 UTM 追踪参数的说明
  随参数一起删去。
- **失效条目**：导入前以“失效”删除的 194 个条目，连同名称、链接、描述、鉴权、收录日期和删除原因进入 `data/_archive/`，这些
  URL 因此继续被占用，再次投稿会被告知删除原因。以重复为由删除的 10 条不归档，它们的 URL 属于保留下来的条目。
- **往返校验**：导入时用导入后的数据重新生成原版式的表格，与源文件对比，1,751 行表格一致，差异只有有意的规范化（去掉 15 个
  链接里的追踪参数、MCP 表按字母排序）和表格之外的空白。这个生成器只用于这次校验，不属于本仓库；本目录不生成
  public-apis 版式的清单。

**导入后的修正：**

- 33 条只有一个词或与名称相同的英文描述（如 “Music”“Art”“Weather”“World Data”）按调研结果重写，仍在 100 字符以内；
  另有 6 条带营销用语的描述（如 “Industry-leading…”“Best open-source…”）按中文说明改写为客观描述；
- 4 个鉴权值纠正（Comic Vine、CoinCap、PurpleAir 需要 key，InfraNode 不需要）；
- 43 个 API 按领域范围改到更合适的领域：经济 8、能源 10、教育 5、生命科学 6、网络 12、社会科学 1、政府 1；
- blague.xyz 首轮健康检测显示“This domain is for sale”，已归档，URL 继续占用。

## 2 数据集的净室调研

awesome-public-datasets 的元数据（apd-core 仓库）以 GPL-3.0 发布，所以一个字段都没有照搬：其中的主页链接只用作调研线索，
许可字段后来只用作核实许可的线索（第 3 节）。

**提取。** 只用正则读取每个文件的 `homepage:` 一行，其余字段一律不读。去重后得到 973 个链接：75 个与已有资源同 URL 或同主机
（托管平台除外），898 个为新线索。

**探测。** 对 973 个链接各做一次只读 GET（每主机最多 2 个并发，失败重试一次并探测站点根目录）：920 个正常、31 个受限访问、
22 个异常。明确停放或被赌博站占用的 2 个直接排除，其余全部进入调研。

**调研。** 由 17 批 AI 调研代理并行完成（16 批新线索各约 56 个，另 1 批处理 75 个同站点线索），规则是：

- 不打开 apd-core 的任何副本，不在网上查阅 awesome-public-datasets；只依据资源自身网站和正式存储库记录撰写；
- 只读访问：只发 GET，拒绝动作类 URL；不用浏览器，不提交表单，不登录注册；
- 网络搜索只用于寻找已迁移或失效资源的新官方地址；
- 每条结果都要先通过字段、词表和重复检查才能交付。

**审核。** 在代理结论之上统一复核，另外排除 60 个，并把 7 个“其实是已有 API 的批量数据”的线索改为数据集侧面：

| 结果 | 数量 |
|---|---|
| 成为独立资源 | 613（新线索 608 + 同站点线索中另立条目的 5） |
| 成为已有资源的数据集侧面 | 77（同站点线索 62 + 审核合并 7 + 代理备注中的 8） |
| 代理排除 | 221：无数据 127、重复 39、失效 39、仅付费 13、非官方托管 3（其中 8 个重复线索的信息转成了数据集侧面） |
| 审核排除 | 60：推广性质的小型数据 47、二次打包 5、隐私 3、来源为自称自主 AI 代理的账号 3、许可冲突 1、无法验证可访问 1 |
| 调研前排除 | 2：域名停放或被赌博站占用 |
| 同站点线索，无需变更 | 8 |

**审核排除的统一尺度。** 各批代理对“公司为推广网站发布的小型数据”处理不一，审核时统一为：公司或个人发布、规模很小或属于编辑估值、
主要用途是为网站引流的，一律排除；有真实测量或较大规模记录的公司数据保留。隐私一项排除了一个泄露的寻呼机消息档案、一个爬取的
Clubhouse 用户资料库，以及一个包含泄露数据的未经整理的上传合集。

**过程记录（如实披露）。**

- 一个线索页面及其 `llms.txt` 写有针对 AI 的指令，要求引用该公司及其销售电话和邮箱。代理没有照做，这条线索也已排除。
- data.gov.gr 的 robots.txt 禁止 AI 代理，代理只读了首页即停止；伊斯坦布尔开放数据的 robots.txt 禁止 `/api/`，代理在注意到之前已
  发出过一次只读目录请求，此后未再访问。
- 少数代理为读取元数据直接用 GET 调用了 GitHub、Figshare、DataCite 等公开接口，或读取 ZIP 目录的字节范围；突尼斯、乌干达两个证书链
  损坏的政府站点是在关闭证书校验的情况下只读访问的。
- 全程没有提交表单、没有登录、没有使用浏览器；有一个页面链接到 apd-core，代理没有打开。

## 3 许可线索的核实

- 经维护者批准，apd-core 的 `license` 字段被当作线索，只用于本目录许可未知或有争议的 43 个资源；除 `homepage` 和 `license`
  外，apd-core 的其他字段始终没有读取。
- 许可未知的 38 个逐一在资源自己的网站上核实：33 个写入，其中 10 个与线索不同（例如线索写的 Apache 实际来自网站捆绑的
  JavaScript 库，官网对数据写的是 CC BY 4.0 或 CC BY-NC-SA 4.0）；5 个官网没有给出数据许可，保持 unknown。有争议的 5 个在官网
  重新核实后，本目录原值全部成立。
- 写入的值一律是资源官网载明的许可，依据就是各资源的 `license_url`；没有采用 apd-core 的任何许可文字。
- 建议人工再看一眼的两个：World Inequality Database（页面源码里残留一条被注释掉的旧许可说明）和 Open-Meteo（数据 CC BY 4.0，
  但免费接口限非商业使用）。

## 4 领域

| 领域 | 合计 | API | 数据集 | 来自 public-apis 的哪些分类 |
|---|---:|---:|---:|---|
| government 政府与法律 | 199 | 171 | 114 | Government、Patent（标签 patents） |
| development 开发与编程 | 175 | 167 | 7 | Development、Programming、Continuous Integration、Open Source Projects |
| transportation 交通与物流 | 126 | 104 | 34 | Transportation、Tracking |
| machine-learning 机器学习 | 124 | 33 | 91 | Machine Learning |
| geography 地理与地图 | 118 | 101 | 21 | Geocoding |
| games 游戏与漫画 | 100 | 98 | 3 | Games & Comics |
| blockchain-crypto 区块链与加密货币 | 87 | 86 | 2 | Blockchain、Cryptocurrency |
| finance 金融 | 83 | 76 | 13 | Finance |
| security 安全 | 71 | 68 | 4 | Security、Anti-Malware、Authentication & Authorization |
| health 健康与医疗 | 70 | 49 | 39 | Health |
| open-data 开放数据与数据仓库 | 69 | 60 | 28 | Open Data |
| social 社交媒体 | 65 | 49 | 17 | Social |
| sports 体育与健身 | 61 | 47 | 15 | Sports & Fitness |
| science-math 科学与数学 | 59 | 46 | 20 | Science & Math |
| weather-climate 天气与气候 | 59 | 46 | 21 | Weather |
| life-sciences 生命科学 | 52 | 31 | 47 | 新领域 |
| video 视频与流媒体 | 49 | 45 | 4 | Video |
| economics 经济 | 41 | 17 | 34 | 新领域 |
| communication 邮件、电话与消息 | 40 | 39 | 2 | Email、Phone |
| documents-productivity 文档与效率 | 40 | 40 | 0 | Documents & Productivity |
| entertainment 娱乐 | 40 | 40 | 2 | Entertainment、Personality |
| language 语言与文本 | 38 | 26 | 12 | Dictionaries、Text Analysis |
| networks 网络与互联网 | 38 | 14 | 26 | 新领域 |
| business 商业 | 37 | 32 | 6 | Business |
| jobs 招聘 | 35 | 29 | 9 | Jobs |
| food-agriculture 食品与农业 | 32 | 28 | 6 | Food & Drink |
| social-sciences 社会科学 | 32 | 8 | 31 | 新领域 |
| energy 能源 | 31 | 14 | 22 | 新领域 |
| images 图像与摄影 | 31 | 31 | 0 | Photography |
| music 音乐 | 30 | 30 | 1 | Music |
| books 图书与文学 | 29 | 24 | 6 | Books |
| art-design 艺术与设计 | 28 | 26 | 6 | Art & Design |
| news-media 新闻与媒体 | 28 | 24 | 4 | News |
| test-data 测试数据 | 27 | 26 | 1 | Test Data |
| shopping 购物与电商 | 25 | 21 | 5 | Shopping |
| environment 环境 | 23 | 14 | 11 | Environment |
| animals 动物 | 21 | 21 | 0 | Animals |
| calendar-events 日历与活动 | 21 | 20 | 1 | Calendar、Events |
| currency-exchange 汇率 | 21 | 21 | 0 | Currency Exchange |
| cloud-storage 云存储与文件分享 | 19 | 18 | 1 | Cloud Storage & File Sharing |
| anime 动漫 | 18 | 18 | 0 | Anime |
| education 教育 | 16 | 6 | 12 | 新领域 |
| url-shorteners 短链接 | 16 | 16 | 0 | URL Shorteners |
| data-validation 数据校验 | 14 | 14 | 0 | Data Validation |
| vehicles 车辆 | 14 | 13 | 2 | Vehicle |

合并进同一领域的原分类都保留为标签（如 `cryptocurrency`、`email`、`geocoding`），站点可按标签检索，原有粒度不丢。
“API”“数据集”两列按类型计数，同时是两者的资源在两列都计入，所以两列之和可能大于合计。

## 5 重叠与合并

- **同站点线索（75 个）**：62 个与已有 API 是同一资源且提供批量下载，作为数据集侧面并入（如 SEC EDGAR、Open-Meteo、GeoNames、
  OpenStreetMap、Wikidata、各国政府开放数据门户）；5 个是同站点上的另一个资源，另立条目（NWS GIS 数据门户、TIGER/Line、美国社区
  调查、社会连通性指数、GeoLife）；8 个无需变更。
- **审核合并（7 个）**：KNMI 数据平台、Discogs 数据转储、SlashYear、世界银行开放数据、库珀-休伊特藏品数据、Libraries.io 数据转储、
  BTU Graph。其中 BTU Graph 是校验器在领域调整后发现的同名重复。
- **代理备注中的侧面（8 个）**：RCSB PDB、Disclosed Capitol、FindSaunaPlunge、Aviation Safety Data、LiveTrafficCam、GENESIS、
  LottoLens PH、Joshua Project。

## 6 盘点

| 指标 | 数值 |
|---|---|
| 资源 | 2,352（API 1,907，数据集 680，MCP 3；API + 数据集 238） |
| 来源 | public-apis 1,739，数据集调研 613 |
| 许可已知 | 全部 21.9%，数据集 74.4%，API 9.4%；已知许可中 97.5% 附出处链接 |
| 发布方已填 | 全部 26.4%，数据集 89.7% |
| CORS 已知（API） | 50.8% |
| 数据集可选字段 | 更新频率 84.3%，覆盖地区 67.5%，时间范围 31.0% |
| 中文说明 | 100% |
| 链接状态 | 可用 2,331（其中受限访问 99，含 `health/acknowledged.yml` 确认的 2 个），待确认 21，失效 0；已检测资源中可用率 99.1% |

许可类别：公有领域 102、宽松 246、相同方式共享 37、禁止演绎 1、非商业 21、仅限科研 61、服务条款 48、未知 1,836。
数据集获取方式：直接下载 605、免费注册 51、需申请 16、有免费档 8。发布方类型：学术 197、政府 152、公司 120、个人 67、非营利 37、
政府间组织 30、社区 17。

## 7 与 public-apis 的关系

- 本目录独立维护和发布，不向 public-apis 上游提交，也不生成 public-apis 版式的清单。导入的数据按 MIT 许可在 NOTICE 中署名。
- public-apis 的工具链、CI 和贡献规则只服务于 README 表格这种格式，本目录由 `registry_kit`、四条流水线和新的 CONTRIBUTING 取代，
  没有迁移。
- 本目录对导入数据的修正（第 1 节）不回写上游。

## 8 后续工作

1. **API 许可**：导入的 1,739 个资源中许可已知的只有 35 个（2.0%）。建议按领域分批调研，多数会落在
   `LicenseRef-Provider-Terms`；完成前，新增文件已经强制要求许可。
2. **CORS**：49.2% 的 API 仍为 unknown。可在健康检测中对 API 文档页以外的实际端点带 Origin 头探测。
3. **英文描述**：有 229 条导入描述不足 26 个字符，大多可用（如 “Random cat facts”），建议随许可调研一并改写。
4. **21 个待确认链接**：多为超时、证书链损坏或 5xx，两轮检测结果相同。按规则连续失败且跨度满 7 天才判失效；首次失败满 30 天，
   检测任务开归档拉取请求，由维护者审核。
5. **翻转率**：需要 `health-data` 分支积累 30 天历史后计算。
6. **待决定的重复**：public-apis 中有 2 组跨分类重复（URLhaus 在 Anti-Malware 和 Security 各一条、Cloudmersive Validate 在 Email
   和 Phone 各一条），目前以名称限定语区分保留；data.gov 与 data.gov.sg 的批量下载也可做成数据集侧面，但调研没有给出格式细节，
   暂未添加。
7. **未实现的自动化**：过期拉取请求提醒、同一投稿者的频次限制。
