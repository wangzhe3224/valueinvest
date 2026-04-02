## 编码规则

Code that leverage valueinvest library put into scripts folder, not root folder or valueinvest folder.
Example code put into example folder

每次有新的 feature 更新，同时更新 readme 如果需要的话；具体的变化放入 changelog.md 不要放在 README
changelog should be concise and short.

测试运行代码使用本地的 `.venv`

Do not create scripts file just for analysis 1 stock, just use bash or /tmp to store temp analysis py files or data

如果代码变化，检查是否需要更新 readme 文件或相关说明。同时更新changelog

代码保持低耦合性、可组合性。

use uv to manage python env and package.
