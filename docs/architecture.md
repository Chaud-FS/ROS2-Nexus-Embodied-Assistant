# 系统架构详解

本文档描述 ROS2 Nexus Embodied Assistant 的内部架构与模块交互。

## 1. 顶层数据流

系统围绕一条**具身智能闭环**组织：

```
用户语音 ──STT──▶ 文本指令
                         │
相机图像 ──Qwen-VL──▶ 场景描述(物体+位姿)
                         │
                   ┌─────▼─────┐
                   │  LLM 大脑  │  上下文 = 指令 + 视觉 + 机械臂状态
                   └─────┬─────┘
                         │  结构化计划(JSON)
                   ┌─────▼─────┐
                   │  编排器     │  计划 → MoveIt2 动作
                   └─────┬─────┘
                         │  轨迹
                   ┌─────▼─────┐
                   │ MoveIt2    │  规划 + 执行
                   └─────┬─────┘
                         │  关节指令
                   ┌─────▼─────┐
                   │  Gazebo    │  物理仿真
                   └─────┬─────┘
                         │  执行结果
                   ┌─────▼─────┐
                   │  LLM 大脑  │  生成自然语言反馈
                   └─────┬─────┘
                         │
                   ┌─────▼─────┐
                   │   TTS      │  语音播报
                   └───────────┘
```

## 2. 功能包职责

| 包名 | 语言 | 职责 |
|------|------|------|
| `nexus_description` | Xacro/URDF | 6-DOF 机械臂建模、Gazebo 插件、控制器配置、生成世界 |
| `nexus_moveit_config` | YAML/Launch | SRDF、运动学求解器、关节限位、MoveIt 控制器桥接 |
| `nexus_perception` | Python | 订阅相机话题 → 调用 Qwen-VL → 发布 `PerceptionResult` |
| `nexus_voice` | Python | STT（语音→文本）、TTS（文本→语音） |
| `nexus_brain` | Python | 组装上下文、调用 LLM、解析结构化计划、生成反馈 |
| `nexus_orchestrator` | Python | 状态机编排、把计划转为 MoveIt2 动作、回传结果 |

## 3. 关键话题（Topics）

| 话题 | 类型 | 发布者 | 订阅者 |
|------|------|--------|--------|
| `/nexus/voice/text` | `std_msgs/String` | voice(STT) | orchestrator |
| `/nexus/perception/result` | `nexus_interfaces/PerceptionResult` | perception | orchestrator |
| `/nexus/brain/plan` | `nexus_interfaces/TaskPlan` | brain | orchestrator |
| `/nexus/brain/feedback` | `std_msgs/String` | brain | voice(TTS) |
| `/nexus/arm/state` | `sensor_msgs/JointState` | gazebo/controllers | orchestrator |
| `/nexus/command/execute` | `nexus_interfaces/ExecuteGoal` | orchestrator | moveit action |

## 4. LLM 结构化计划格式

`TaskPlan` 示例：

```json
{
  "task_id": "t_001",
  "intent": "pick_and_place",
  "steps": [
    {"action": "move_to", "target": "red_cube", "frame": "base_link"},
    {"action": "grasp",   "target": "red_cube"},
    {"action": "move_to", "target": "blue_box",  "frame": "base_link"},
    {"action": "release", "target": "blue_box"}
  ],
  "rationale": "用户要求把红色方块放进蓝色盒子。"
}
```

编排器逐条把 `action` 翻译为 MoveIt2 的 `MoveGroupInterface` 调用，
并将执行成功/失败回传大脑以生成反馈。

## 5. 仿真与真实解耦

所有硬件相关逻辑（相机、控制器）通过 ROS 接口抽象，
`nexus_description` 仅在仿真中提供 Gazebo 插件与控制器。
若日后接入实体机械臂，只需替换 `nexus_moveit_config` 的控制器映射，
上层 `brain` / `orchestrator` 无需改动。
