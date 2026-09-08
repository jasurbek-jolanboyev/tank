"""Train a full-frame detector; requires the optional Ultralytics host environment."""
from __future__ import annotations

import argparse
import json
import random
from pathlib import Path

import yaml


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--config", type=Path, default=Path("ml/configs/jetson_detector.yaml"))
    parser.add_argument("--epochs", type=int, help="explicit smoke/experiment override")
    parser.add_argument("--batch", type=int, help="explicit host-memory override")
    parser.add_argument("--fraction", type=float, default=1.0,
                        help="training subset for a smoke run; production default is 1.0")
    parser.add_argument("--input-size", type=int, help="explicit smoke/benchmark override")
    args = parser.parse_args()
    config = yaml.safe_load(args.config.read_text())
    random.seed(config["seed"])
    try:
        from ultralytics import YOLO
    except ImportError as exc:
        raise SystemExit("ULTRALYTICS_REQUIRED: install the documented optional training dependencies") from exc
    data_yaml = (args.config.parent / config["datasetConfig"]).resolve()
    if not data_yaml.exists():
        raise SystemExit(f"DATASET_CONFIG_REQUIRED: {data_yaml}")
    model = YOLO(f"{config['architecture']}.pt")
    output = (args.config.parent / config["output"]).resolve()
    output.mkdir(parents=True, exist_ok=True)
    dataset = yaml.safe_load(data_yaml.read_text())
    dataset["path"] = str((data_yaml.parent / dataset["path"]).resolve())
    runtime_data_yaml = output / "dataset.resolved.yaml"
    runtime_data_yaml.write_text(yaml.safe_dump(dataset, sort_keys=False))
    epochs = args.epochs if args.epochs is not None else config["epochs"]
    batch = args.batch if args.batch is not None else config["batch"]
    input_size = args.input_size if args.input_size is not None else config["inputSize"]
    result = model.train(data=str(runtime_data_yaml), imgsz=input_size, epochs=epochs,
                         batch=batch, seed=config["seed"], deterministic=True,
                         fraction=args.fraction, project=str(output),
                         name=f"train-e{epochs}-f{args.fraction:g}-s{input_size}", exist_ok=True)
    (output / "training_invocation.json").write_text(json.dumps({
        "config": config, "effectiveEpochs": epochs, "effectiveBatch": batch,
        "effectiveFraction": args.fraction, "effectiveInputSize": input_size,
        "resultDirectory": str(result.save_dir)
    }, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
