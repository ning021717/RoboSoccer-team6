# P0 相机 4v4 固定窗口：真实回归报告

所有结果来自 `evidence/` 下实际完成的 Webots 运行。它们是单次固定条件窗口，不是多 seed 统计，也不代表角色能力提升。

| 运行 | 相机检测 | 比分 | 移动角色越界采样 | 动作结论 |
|---|---:|---:|---:|---|
| `p0_fixed_4v4_camera_300s` | 0 / 37,379 (0.00%) | 0–0 | 846 | 丢球后直线前冲，未形成射传请求 |
| `p0_fixed_4v4_camera_60s_boundary_search_r1` | 9 / 7,379 (0.12%) | 0–0 | 0 | 1,681 次 `search_ball`；未形成射传请求 |

第二次运行仅改变了前锋丢球处理：`search_ball_motion()` 原地交替转向，
`boundary_recovery_motion()` 以 GPS/IMU 朝场地中心返回。守门员固定在门线附近，
因此不计入“移动角色越界”指标。

## 结论

边界安全回归通过，但感知召回远低于可支持比赛级闭环的水平。不能以此运行比较
striker goals、defender interceptions 或 goalkeeper save rate，也不会启动 15 分钟
4v4 参数排名。下一步是建立多距离、多方位、遮挡和光照条件的相机球检测评估，并在
连续相机追踪稳定后才进行多 seed 角色实验。

原始 `fixed_window_summary.json` 与 `robot_metrics.csv` 位于对应 evidence 目录。
