# Webots continuation: real evidence report

## What was verified on this supplied project

This report refers to the original, live-renderable `worlds/nao_soccer.wbt`
with its embedded NAO assets. It is not the earlier vendored-world variant.
All measurements below come from retained Webots JSONL, action streams and
MP4 files under `evidence/`; no position, score or perception rows were
invented.

## Video capture repaired and verified

`Supervisor.movieStartRecording` is now paired with `movieStopRecording`.
Webots returns `None` on a successful Python start call, so treating its return
value as a Boolean had previously skipped the stop/finalisation step. The fix
uses exception-free completion instead.

- `evidence/baseline_supervisor_video_8s/match.mp4`: real eight-second match
  capture, 10,902,897 bytes.
- `evidence/baseline_supervisor_video_8s/frame_4s.png`: decoded frame visibly
  contains the grass pitch, ball and red/blue NAO players. It is valid visual
  evidence, unlike the black-frame result from the other world path.
- `evidence/p1_camera_only_8s_r2/match.mp4`: camera-only controller run with
  the same capture lifecycle.

## P1 camera-only ball perception

`controllers/Utils/BallPerception.py` implements a pure RGB orange-ball
segmentation baseline using the existing `CameraTop` and `CameraBottom`, then
projects bearing/range into GPS/IMU world coordinates. `ROBOCUP_BALL_SOURCE`
has three explicit modes:

- `supervisor`: legacy playable behaviour; Supervisor ball position is used.
- `camera`: controller behaviour receives only camera estimate or loss; the
  separately decoded Supervisor value is written only as labelled evaluation
  truth in the evidence stream.
- `fused`: camera when available, otherwise legacy truth. It is useful for
  regression, but is not a P1 result.

The r2 camera-only run completed 1,000 controller samples without a traceback:

| Robot | samples | detections | detection rate | position MAE |
| --- | ---: | ---: | ---: | ---: |
| BLUE_DEF | 125 | 9 | 7.2% | 1.66 m |
| BLUE_FW_L | 125 | 45 | 36.0% | 2.96 m |
| BLUE_FW_R | 125 | 3 | 2.4% | 3.38 m |
| BLUE_GK | 125 | 0 | 0.0% | — |
| RED_DEF_L | 125 | 54 | 43.2% | 1.99 m |
| RED_DEF_R | 125 | 30 | 24.0% | 2.25 m |
| RED_FW | 125 | 120 | 96.0% | 0.66 m |
| RED_GK | 125 | 0 | 0.0% | — |

The aggregate detection rate is **26.1% (261/1,000)**. This is an actual
baseline, not an acceptable final perception result: goalkeeper visibility and
metric error require head scanning, temporal tracking, camera calibration and
occlusion/distance scenarios before any reliability claim.

`tools/analyze_camera_perception.py` derives the CSV, JSON and SVG from the
retained JSONL and fails rather than creating a report if no observations exist.

## P3/P4 action evidence and current physical blocker

The controller now logs action requests separately from Supervisor ball truth.
It adds explicit pass selection (`pass_to_<robot>`) when a progressing teammate
has a clear opponent corridor. The action-to-physics analyser applies the rule:

> A requested kick is not considered completed unless truth records more than
> 0.10 m ball displacement.

Real fixtures produced the following:

| Fixture | Actual controller decision | Ball displacement | Goal | Conclusion |
| --- | --- | ---: | ---: | --- |
| `p3_red_penalty_shot_6s` | 57 `shoot` requests | 0.00 m | 0 | Shot motion requested; kick contact not proven |
| `p3_red_right_foot_shot_6s` | 34 `shoot` requests | 0.00 m | 0 | Right-foot placement still did not contact ball |
| `p4_red_pass_clear_6s` | 28 `pass_to_RED_DEF_L` requests | 0.00 m | 0 | Pass selection works; physical pass not proven |

Therefore the project now has verified sensing, approach/alignment decisions,
shoot/pass decision branches, action logs, score truth and reset logic, but it
**does not yet have a verified physical kick, pass completion, goal or full
match**. The next valid P3 task is to calibrate the motion's foot trajectory
against the ball contact point, not to inject ball velocity from Supervisor.

## Motion compatibility repair

`tools/retarget_motion_assets.py` generates 26 files in `motions/retargeted/`
without `LHand`/`RHand` columns and leaves every source `.motion` untouched.
Controllers default to these generated assets; set
`ROBOCUP_USE_RETARGETED_MOTIONS=0` only to reproduce the old warning path.
The actual `evidence/retargeted_smoke_3s/webots.log` starts all eight
controllers and contains no missing-hand warnings.

## Reproduce

Open `worlds/nao_soccer.wbt` in Webots for the normal real-time pitch. For a
bounded evidence run in PowerShell from the project root:

```powershell
$env:ROBOCUP_MATCH_SECONDS = '8'
$env:ROBOCUP_BALL_SOURCE = 'camera'
$env:ROBOCUP_SCENARIO = 'kickoff'
$env:ROBOCUP_EVIDENCE_DIR = "$PWD\evidence\my_camera_run"
$env:ROBOCUP_MOVIE_PATH = "$PWD\evidence\my_camera_run\match.mp4"
& 'C:\Program Files\Webots\msys64\mingw64\bin\webots.exe' --mode=fast --stdout --stderr "$PWD\worlds\nao_soccer.wbt"
python tools\analyze_camera_perception.py evidence\my_camera_run
```

For physical action fixtures, use `red_penalty_shot`, `red_right_foot_shot` or
`red_pass_clear` as `ROBOCUP_SCENARIO`, then run
`python tools\analyze_match_actions.py evidence\<run>`. The analyser makes a
zero-displacement kick failure explicit.
