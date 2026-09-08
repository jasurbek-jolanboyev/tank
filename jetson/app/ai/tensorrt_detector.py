class TensorRTDetector:
    name = "tensorrt-detector"

    def __init__(self, engine_path: str):
        try:
            import tensorrt  # type: ignore  # noqa: F401
        except ImportError as exc:
            raise RuntimeError("TensorRTDetector requires NVIDIA JetPack/TensorRT") from exc
        self.engine_path = engine_path
        raise NotImplementedError("engine bindings depend on the selected exported detector")
