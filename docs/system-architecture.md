# System architecture

```mermaid
flowchart LR
  C1[Camera workers] --> Q[Bounded latest-frame queues]
  Q --> AI[Jetson detector]
  AI --> T[Multi-object tracker]
  E[ESP32 range and health] --> F[Timestamped fusion]
  T --> F --> S[Sector state]
  S --> E
  S --> W[REST and WebSocket]
  W --> UI[Flutter console]
  S --> R[Rotating recording]
```

Ubuntu Server (or a future Jetson backend) owns detection, tracks, fusion and policy. ESP32 owns physical range I/O
and logic-level indicators. Flutter owns presentation only. Loss of Flutter does
not stop processing. Loss of Jetson causes ESP32 to stop creating new decisions
and use deterministic fallback.

```mermaid
flowchart TB
  subgraph Jetson
    CW1[CAM 1 worker] --> A[AI scheduler]
    CW2[CAM 2 worker] --> A
    CWN[CAM N worker] --> A
  end
  A --> Track[Stable tracks] --> Fusion[Range fusion]
```
