# 角色参数与评估矩阵

配置候选见 `configs/role_parameter_matrix.json`。该矩阵是待运行实验设计，不是性能结果。

| 层级 | 真实输入 | 输出/日志 | 通过门槛 | 当前状态 |
|---|---|---|---|---|
| P1 感知 | 每台 NAO 的 CameraTop/CameraBottom RGB | detection、bearing/range、估计位置、GT 评估标签 | 控制器不读 GT；检测日志完整 | 已接入；8s 基线 261/1000 检测样本，26.1% |
| P2 定位 | GPS、IMU、相机球估计 | 自位姿/球相对估计 | 加入噪声、里程计/EKF 后再称定位基线 | GPS/IMU 基线已用；EKF 未完成 |
| P3 全身/接触 | 关节位置、足尖碰撞、足底力 | 关节曲线、触球窗口、球速度/位移 | P3_KICK_CALIBRATION_REPORT 的四项门槛 | 未通过，阻止团队结果统计 |
| P4 多智能体 | 角色状态、队友位置、传球路线 | 追球队员、跑位、传球/射门动作事件 | 物理传球或射门先通过 P3 | 决策事件已记录，物理效果未验证 |
| 比赛 | 4v4、固定场地、固定种子和相同时间窗 | 进球、扑救、拦截、控球、摔倒、出界、感知丢失 | 每项须有原始遥测；报告中位数和区间 | P3 阻塞，尚未启动 |

## 待执行的 P0 设计

| 角色 | 参数组 | 主指标 | 保护指标 | 固定条件 |
|---|---|---|---|---|
| goalkeeper | interception radius, boundary margin, recovery height | save rate, intercept latency | falls/min, boundary violations | 同场地、同对手策略、≥3 seed |
| defender | chase distance, interception radius, pass clearance | interceptions/5min, lane blocks | teammate collisions, falls/min | 同上 |
| forward | chase/support distance, strike standoff, kick alignment | shots-on-target, possession-to-shot time | off-target kicks, collisions | 同上 |

当 P3 门通过后：先做每候选参数集的 5 分钟固定条件多 seed，再做 15 分钟 4v4 对抗。报告只可写实际汇总值；用户给出的 1.2→1.7、5.4→6.8、0.41→0.60 是目标格式示例，未写入任何结果。
