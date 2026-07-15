# ROS2 Nexus Embodied Assistant

> 一个纯仿真的多模态具身智能机器人项目：基于 Gazebo 仿真环境、MoveIt2 运动规划、Qwen-VL 视觉识别、语音交互，并由 LLM 作为核心决策与控制大脑，实现"看—听—想—做"的闭环具身交互。

---

## 📖 项目简介

**ROS2 Nexus Embodied Assistant** 是一个完全在仿真环境中运行的具身智能机器人系统，无需任何实体硬件即可体验完整的"感知—决策—执行"闭环。系统以一个 6 自由度（6-DOF）机械臂为核心载体，整合了：

- **仿真环境**：使用 `Gazebo` 搭建桌面场景，提供物理引擎与传感器（RGB-D 相机）仿真。
- **运动规划**：基于 `ROS2 + MoveIt2` 实现机械臂逆运动学（IK）、运动规划与轨迹执行。
- **视觉感知**：接入 **Qwen-VL** 多模态大模型，对相机图像进行目标识别、定位与语义理解。
- **语音交互**：集成语音识别（STT）与语音合成（TTS），实现自然语言对话。
- **决策大脑**：以大语言模型（LLM）作为核心控制器，将视觉、语音、运动状态统一为上下文，输出结构化的任务计划与机械臂动作指令。

整个系统通过 `nexus_orchestrator` 节点进行多模态编排，把分散的能力串成一条可端到端运行的具身智能链路。

---

## 🏗️ 系统架构

```
                         ┌─────────────────────────────┐
                         │      nexus_orchestrator      │
                         │     (多模态编排 / 状态机)      │
                         └──────────────┬──────────────┘
                                        │
            ┌───────────────┬───────────┼───────────────┬───────────────┐
            ▼               ▼           ▼               ▼               ▼
     ┌────────────┐ ┌────────────┐ ┌──────────┐ ┌────────────┐ ┌──────────────┐
     │  nexus_    │ │ nexus_     │ │ nexus_   │ │ nexus_     │ │ nexus_       │
     │  brain     │ │ perception │ │  voice   │ │ moveit_    │ │ description  │
     │ (LLM 大脑) │ │(Qwen-VL)   │ │(STT/TTS) │ │ config     │ │ (URDF/Gazebo)│
     └────────────┘ └────────────┘ └──────────┘ └────────────┘ └──────────────┘
            │               │           │               │
            └───────────────┴───────────┴───────┬───────┴──────────────┘
                                                 ▼
                                    ┌─────────────────────────┐
                                    │  ROS2 Humble + Gazebo   │
                                    │  + MoveIt2 (仿真)        │
                                    └─────────────────────────┘
```

数据流（具身闭环）：
1. **听**：`nexus_voice` 通过 STT 将用户语音转为文本指令。
2. **看**：`nexus_perception` 用 Qwen-VL 分析相机图像，输出可见物体及其位置。
3. **想**：`nexus_brain` 把语音指令 + 视觉结果 + 机械臂状态组装成 prompt，调用 LLM，生成结构化计划（含目标位姿 / 抓取语义）。
4. **做**：`nexus_orchestrator` 将计划翻译为 MoveIt2 规划请求，驱动机械臂在 Gazebo 中执行抓取 / 放置。
5. **说**：执行结果回传给 `nexus_brain`，生成自然语言反馈，由 TTS 播报。

详见 [docs/architecture.md](docs/architecture.md)。

---

## 📦 功能包结构

```
src/
├── nexus_description/       # URDF/Xacro 机械臂建模 + Gazebo 启动
├── nexus_moveit_config/     # MoveIt2 配置（SRDF、动力学、控制器）
├── nexus_perception/        # Qwen-VL 视觉识别节点
├── nexus_voice/             # 语音识别(STT) + 语音合成(TTS)
├── nexus_brain/             # LLM 核心决策大脑节点
└── nexus_orchestrator/      # 多模态编排与端到端闭环
```

---

## 🚀 快速开始

### 环境要求
- Ubuntu 22.04
- ROS2 Humble
- Gazebo (ROS2 版)
- MoveIt2
- Python 3.10+
- 可选：NVIDIA GPU + CUDA（用于本地运行 Qwen-VL，否则走云端 API）

### 安装依赖
```bash
# 安装 ROS2 / Gazebo / MoveIt2（如未安装，参见 docs/installation.md）
sudo apt update
sudo apt install -y ros-humble-desktop ros-humble-moveit \
    ros-humble-gazebo-ros-pkgs ros-humble-ros2-control \
    ros-humble-ros2-controllers

# 克隆并编译
cd ~/<your_ws>
git clone https://github.com/Chaud-FS/ROS2-Nexus-Embodied-Assistant.git src/ROS2-Nexus-Embodied-Assistant
rosdep install --from-paths src --ignore-src -r -y
colcon build --symlink-install
source install/setup.bash
```

### 一键启动（完整系统）
```bash
ros2 launch nexus_orchestrator nexus.launch.py
```

### 分步启动
```bash
# 1. 启动 Gazebo 仿真 + 机械臂
ros2 launch nexus_description gazebo.launch.py

# 2. 启动 MoveIt2（新终端）
ros2 launch nexus_moveit_config moveit.launch.py

# 3. 启动视觉感知（需配置 Qwen-VL API Key）
ros2 launch nexus_perception perception.launch.py

# 4. 启动语音模块
ros2 launch nexus_voice voice.launch.py

# 5. 启动 LLM 大脑
ros2 launch nexus_brain brain.launch.py

# 6. 启动编排器
ros2 launch nexus_orchestrator nexus.launch.py
```

---

## ⚙️ 配置说明

| 模块 | 配置文件 | 关键参数 |
|------|----------|----------|
| Qwen-VL | `nexus_perception/config/params.yaml` | `api_key`, `model`, `image_topic` |
| LLM 大脑 | `nexus_brain/config/params.yaml` | `api_key`, `model`, `system_prompt` |
| 语音 | `nexus_voice` 节点参数 | `stt_engine`, `tts_engine`, `language` |
| 机械臂 | `nexus_description/config/nexus_controllers.yaml` | PID 增益、关节限位 |

> 注意：调用 Qwen / LLM 云端 API 需要在 `~/.bashrc` 或启动环境中设置 `DASHSCOPE_API_KEY`（或对应 `OPENAI_API_KEY`）。

---

## 🧪 测试

```bash
colcon test --packages-select nexus_brain nexus_perception nexus_orchestrator
colcon test-result --verbose
```

CI 工作流见 [.github/workflows/ci.yml](.github/workflows/ci.yml)。

---

## 🤝 贡献

欢迎提交 Issue 与 Pull Request！请先阅读 [CONTRIBUTING.md](CONTRIBUTING.md)。

---

## 📄 许可证

本项目基于 [Apache License 2.0](LICENSE) 开源。

---

## 🔗 相关技术

- [ROS2 Humble](https://docs.ros.org/en/humble/)
- [MoveIt2](https://moveit.ros.org/)
- [Gazebo](https://gazebosim.org/)
- [Qwen-VL](https://github.com/QwenLM/Qwen-VL)
- [LangChain / OpenAI Python SDK](https://github.com/openai/openai-python)
