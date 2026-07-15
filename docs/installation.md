# 安装与配置指南

## 1. 操作系统

推荐 **Ubuntu 22.04 LTS**（与 ROS2 Humble 匹配）。其他平台（如 macOS / Windows）
可通过 Docker 运行，下文以原生 Ubuntu 为主。

## 2. 安装 ROS2 Humble

```bash
# 设置 locale
sudo apt update && sudo apt install -y locales
sudo locale-gen en_US en_US.UTF-8
sudo update-locale LC_ALL=en_US.UTF-8 LANG=en_US.UTF-8

# 添加 ROS2 apt 源
sudo apt install -y software-properties-common
sudo add-apt-repository universe
sudo apt update && sudo apt install -y curl gnupg lsb-release
sudo curl -sSL https://raw.githubusercontent.com/ros/rosdistro/master/ros.key -o /usr/share/keyrings/ros-archive-keyring.gpg
echo "deb [arch=$(dpkg --print-architecture) signed-by=/usr/share/keyrings/ros-archive-keyring.gpg] http://packages.ros.org/ros2/ubuntu $(. /etc/os-release && echo $UBUNTU_CODENAME) main" | sudo tee /etc/apt/sources.list.d/ros2.list > /dev/null

sudo apt update
sudo apt install -y ros-humble-desktop
```

## 3. 安装 Gazebo 与 MoveIt2

```bash
sudo apt install -y \
    ros-humble-gazebo-ros-pkgs \
    ros-humble-ros2-control \
    ros-humble-ros2-controllers \
    ros-humble-moveit \
    ros-humble-moveit-planners \
    python3-colcon-common-extensions
```

## 4. 安装本项目

```bash
mkdir -p ~/nexus_ws/src
cd ~/nexus_ws/src
git clone https://github.com/Chaud-FS/ROS2-Nexus-Embodied-Assistant.git

cd ~/nexus_ws
rosdep update
rosdep install --from-paths src --ignore-src -r -y
colcon build --symlink-install
echo "source ~/nexus_ws/install/setup.bash" >> ~/.bashrc
```

## 5. 配置大模型密钥

系统依赖两类大模型服务：

- **Qwen-VL**（视觉）：阿里云百炼 / DashScope
- **LLM 大脑**（决策）：兼容 OpenAI 接口或 DashScope 文本模型

在 `~/.bashrc` 末尾添加（请勿提交到仓库）：

```bash
export DASHSCOPE_API_KEY="sk-xxxxxxxxxxxxxxxx"
export OPENAI_API_KEY="sk-xxxxxxxxxxxxxxxx"   # 如使用 OpenAI 兼容接口
```

重新打开终端或 `source ~/.bashrc` 使其生效。

## 6. 验证安装

```bash
source ~/nexus_ws/install/setup.bash
ros2 launch nexus_description gazebo.launch.py
# 另开终端
ros2 topic list | grep nexus
```

若能看到 `/nexus/arm/state` 等话题，说明仿真环境已就绪。
