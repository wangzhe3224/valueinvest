## 编码规则

Code that leverage valueinvest library put into scripts folder, not root folder or valueinvest folder.
Example code put into example folder

每次有新的 feature 更新，同时更新 readme 如果需要的话；具体的变化放入 changelog.md 不要放在 README
changelog should be concise and short.

测试运行代码使用本地的 `.venv`

Do not create scripts file just for analysis 1 stock, just use bash or /tmp to store temp analysis py files or data

如果代码变化，检查是否需要更新 readme 文件或相关说明。同时更新changelog

## 报告规则

运行代码中生成报告过程中，如果出现问题，及时修复源代码。

报告中的数据应该使用 API 收集最新数据，如果缺少应该上网搜索尝试获得

写md报告时候，开头结尾都加对本库的引用: https://github.com/wangzhe3224/valueinvest

md报告写入`reports` 文件夹，如果有股票 ticker，放入对应的 ticker 文件夹
