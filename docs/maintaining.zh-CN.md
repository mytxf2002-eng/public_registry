# 个人维护手册

本仓库由一人维护。机器能判断的规则都由流水线自动执行，维护者负责机器判断不了的事：资源值不值得收录、失效资源怎么处理。
规则对维护者本人同样生效：你自己的改动也要走拉取请求并通过检查。

## 一次性上线

1. 在 GitHub 上创建公开仓库，把本地仓库推上去（`main` 为默认分支）。这次推送会立刻触发 “Publish”，此时 Pages 还没启用，
   它会失败，属于正常现象。
2. 推送后尽快用仓库所有者身份登录 GitHub CLI（`gh auth login`），在仓库根目录运行 `bash tools/github_setup.sh 所有者/仓库名`。
   最好赶在当天 UTC 03:17（北京时间 11:17）的定时检测之前运行：否则定时检测会先建好 `health-data` 分支，脚本就不再导入
   本地已有的链接检测历史（不影响使用，只是从零开始积累）。
3. 在 Actions 页面手动运行一次 “Link health”，确认它成功，并且随后自动触发的 “Publish” 把网站部署到了 Pages。
4. 打开 `https://所有者.github.io/仓库名/`，确认网站、`export/` 下载和 `api/v1/index.json` 都能访问。

## 日常节奏

| 频率 | 事情 | 大约用时 |
|---|---|---|
| 每天 | 看新拉取请求的自动评论，审核通过的合并；看 “Link health” Issue 里新出现的条目 | 10–20 分钟 |
| 每周 | 把资源推荐 Issue 转成拉取请求或关闭；审阅检测任务开的归档拉取请求 | 半小时 |
| 每月 | 合并 Dependabot 的拉取请求；看网站 “质量” 页；抽查一个领域的条目 | 1 小时 |

暂停维护期间，链接检测和发布照常每天运行，网站保持更新；拉取请求会排队等你回来。注意：公开仓库连续 60 天没有活动时，
GitHub 可能自动停用定时工作流；回来后在 Actions → Link health 里点 “Enable workflow” 即可恢复。

## 审核一个投稿

自动评论全部通过后，再看这几点：

- **能免费用吗？** 直接下载、免费注册、免费申请或有实际可用的免费档才算。只有付费方案或“联系销售”的不收。
- **是官方页面吗？** 链接应指向发布方、项目或正式的存储库记录，而不是第三方转载或导航站。
- **是不是推广？** 公司或个人为网站引流而发布的小表格、编辑估值、产品规格一类，不收；有真实测量或较大规模记录的可以收。
- **许可可信吗？** 打开 `license_url` 看一眼，确认写的正是这份数据的许可，而不是网站代码或第三方库的许可。
- **领域和描述合适吗？** 领域按 `vocab/domains.yml` 的范围说明判断；描述要客观，不用宣传词。

需要修改时，在拉取请求里直接评论；贡献者推送后，自动评论会更新。合并一律用 squash。分支落后于 `main` 时，规则集不允许
合并：先点 “Update branch”，等检查重新通过再合并，这样两个同时提交的拉取请求不会加进同一个链接。

## 处理链接检测结果

| 状态 | 常见原因 | 怎么处理 |
|---|---|---|
| 待核实：跨站跳转 | 资源搬家；域名被转卖或劫持 | 搬家就提拉取请求更新 `url`；被劫持就用 `python -m registry_kit archive <id> --reason "…"` 归档 |
| 待核实：停放或博彩页面 | 域名过期或被占用 | 归档 |
| 待确认或失效：404、DNS 错误 | 页面改版或服务关闭 | 找到新地址就更新 `url`；确实关闭就等归档拉取请求，或提前手动归档 |
| 待确认或失效：超时、5xx、证书错误 | 临时故障，或网站屏蔽了机房地址 | 先等几天；用浏览器能打开但程序始终访问不了的，把结果写进 `health/acknowledged.yml` 并注明原因 |

首次失败满 30 天，检测任务会自动开归档拉取请求；同一时间只开一个，它合并或关闭之前不会再开新的。由工作流开的拉取请求，
GitHub 会先暂停它的检查：在拉取请求页面点 “Approve workflows to run”，检查通过后逐条核对再合并；其中有搬家的，改成更新
链接。资源恢复后，用 `python -m registry_kit restore <id>` 提拉取请求恢复；归档期间它的中文说明一直保留，恢复后原样可用。

## 自己改动数据或代码

```
git switch -c 修改说明
（修改文件）
python -m registry_kit format
python -m registry_kit validate
python -m unittest discover -s tests -t .
git push -u origin 修改说明      然后开拉取请求，检查通过后 squash 合并
```

改了 `vocab/` 之后要运行 `python -m registry_kit schema`，并把重新生成的 `schema/*.json` 一起提交。

## 出问题时

- **发布失败**：在 Actions 里看 “Publish” 的日志。多数是校验失败，说明有不合规的改动进了 `main`；修正后再合并一次即可。
- **链接检测失败**：看 “Link health” 的日志；网络故障的话手动重跑。
- **规则集挡住了紧急修复**：在 Settings → Rules 里临时把规则集改为 Disabled，修复后立即改回 Active。

## 增加协作者

1. **给对方权限。** 个人账号下的仓库：Settings → Collaborators → Add people，对方接受邀请后获得写权限。组织下的仓库：先邀请
   对方加入组织，再加入相应团队，在仓库的 Settings → Collaborators and teams 里给团队 Write 或 Maintain 权限。新人建议先给
   Triage（能处理 Issue 和标签，不能合并），有了稳定记录再升为 Write；不给 Admin。
2. **提一个拉取请求，同时改两个文件。** 新建 `.github/CODEOWNERS`（负责人必须有写权限）；把 `.github/rulesets/main.json`
   里的 `required_approving_review_count` 改为 1、`require_code_owner_review` 改为 true。测试会检查这两个文件是否一致。
3. **让规则生效。** 合并后运行一次 `bash tools/github_setup.sh 所有者/仓库名`，脚本会按新的 JSON 更新 GitHub 上的规则集。
4. **更新文档。** README 的“维护方式”、CONTRIBUTING、SECURITY、CODE_OF_CONDUCT 和本手册里“一人维护”的说法。

从此每个拉取请求，包括你自己的，都需要另一位负责人批准才能合并。
