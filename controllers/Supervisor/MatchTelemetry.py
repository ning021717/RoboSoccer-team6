"""Evidence recorder for actual Webots match runs."""

import json
import os
from pathlib import Path


class MatchTelemetry:
    def __init__(self, root, sample_every=8):
        self.root = Path(root)
        self.root.mkdir(parents=True, exist_ok=True)
        self.path = self.root / "supervisor_match_truth.jsonl"
        self.handle = self.path.open("w", encoding="utf-8")
        self.sample_every = max(1, int(sample_every))
        self.frame = 0
        # Feet are deliberately queried only by the Supervisor.  They are
        # evaluation instrumentation, never a control input sent to players.
        self.feet = {}

    def _foot_position(self, robot, foot_def):
        """Return a world-frame foot position when the world exposes it.

        The bundled NAO is an embedded hierarchy in some Webots builds and a
        PROTO in others.  ``getFromProtoDef`` is therefore treated as an
        optional capability rather than an assumption; calibration stays
        honest by emitting ``null`` if a foot node cannot be resolved.
        """
        key = (robot.getDef(), foot_def)
        if key not in self.feet:
            self.feet[key] = robot.getFromProtoDef(foot_def)
        node = self.feet[key]
        return [round(value, 5) for value in node.getPosition()] if node else None

    def sample(self, supervisor, scoreboard):
        self.frame += 1
        if self.frame % self.sample_every:
            return
        ball = supervisor.getBallPosition()
        ball_velocity = supervisor.ball.getVelocity()
        feet = {
            name: {
                "right": self._foot_position(node, "RIGHT_FOOT_SLOT"),
                "left": self._foot_position(node, "LEFT_FOOT_SLOT"),
            }
            for name, node in supervisor.robots.items()
        }
        record = {
            "kind": "truth_sample",
            "time_s": round(supervisor.getTime(), 4),
            "frame": self.frame,
            "ball_gt": [round(value, 5) for value in ball],
            "ball_velocity_gt_mps": [round(value, 5) for value in ball_velocity[:3]],
            "robots_gt": {
                name: [round(value, 5) for value in supervisor.getRobotPosition(name)]
                for name in supervisor.robots
            },
            "score": {"red": scoreboard.redTeamScore, "blue": scoreboard.blueTeamScore},
            "feet_gt": feet,
        }
        self._write(record)

    def event(self, event):
        self._write({"kind": "match_event", **event})

    def _write(self, record):
        self.handle.write(json.dumps(record, ensure_ascii=False, sort_keys=True) + "\n")
        self.handle.flush()

    def close(self):
        if not self.handle.closed:
            self.handle.close()
