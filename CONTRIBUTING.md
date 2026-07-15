# Contributing to ROS2 Nexus Embodied Assistant

感谢你对本项目的关注！在提交贡献前请阅读以下约定。

## 开发流程

1. Fork 本仓库并克隆到本地。
2. 基于 `humble` 分支创建特性分支：`git checkout -b feat/your-feature`。
3. 在 ROS2 Humble 环境中编译并自测：`colcon build --symlink-install && colcon test`。
4. 提交信息遵循 [Conventional Commits](https://www.conventionalcommits.org/)：
   - `feat:` 新功能
   - `fix:` 修复
   - `docs:` 文档
   - `refactor:` 重构
   - `test:` 测试
5. 推送并发起 Pull Request，描述改动动机与验证方式。

## 代码规范

- Python 节点遵循 `flake8` / `black` 风格，导入顺序规范。
- 每个功能包必须包含 `package.xml` 与 `CMakeLists.txt`（或纯 Python 包用 `setup.py` + `setup.cfg`）。
- 启动文件、配置参数应集中放在 `launch/` 与 `config/` 目录。
- 涉及密钥（API Key）一律通过环境变量或 `params.yaml`（已 gitignore）注入，禁止硬编码。

## 报告问题

提交 Issue 时请附上：ROS2 版本、系统环境、复现步骤与日志片段。
