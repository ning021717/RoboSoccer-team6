"""Create non-destructive NAO motion variants without unsupported hand joints."""

import json
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
SOURCE = ROOT / "motions"
DESTINATION = SOURCE / "retargeted"
UNSUPPORTED = {"LHand", "RHand"}


def convert(source, destination):
    lines = source.read_text(encoding="utf-8").splitlines()
    if not lines or not lines[0].startswith("#WEBOTS_MOTION,V1.0,"):
        return None
    header = lines[0].split(",")
    joints = header[2:]
    keep = [index for index, joint in enumerate(joints) if joint not in UNSUPPORTED]
    removed = [joint for joint in joints if joint in UNSUPPORTED]
    output = [",".join(header[:2] + [joints[index] for index in keep])]
    for line in lines[1:]:
        if not line.strip() or line.startswith("#"):
            output.append(line)
            continue
        fields = line.split(",")
        if len(fields) != len(joints) + 2:
            raise ValueError(f"Unexpected keyframe column count in {source}: {len(fields)}")
        output.append(",".join(fields[:2] + [fields[2 + index] for index in keep]))
    destination.write_text("\n".join(output) + "\n", encoding="utf-8")
    return {"file": source.name, "removed_joints": removed, "keyframes": len(lines) - 1}


def main():
    DESTINATION.mkdir(exist_ok=True)
    manifest = []
    for source in sorted(SOURCE.glob("*.motion")):
        result = convert(source, DESTINATION / source.name)
        if result:
            manifest.append(result)
    (DESTINATION / "motion_retarget_manifest.json").write_text(json.dumps(manifest, indent=2), encoding="utf-8")
    print(f"Retargeted {len(manifest)} motions into {DESTINATION}")


if __name__ == "__main__":
    main()
