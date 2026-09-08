import 'dart:convert';

enum ObjectClass { drone, bird, aircraft, person, unknownAirObject }

enum RangeClass { unknown, far, medium, near }

class VisionDetection {
  const VisionDetection({
    required this.timestamp,
    required this.nodeId,
    required this.cameraId,
    required this.sector,
    required this.trackId,
    required this.objectClass,
    required this.confidence,
    required this.confirmed,
    required this.simulated,
    this.bbox,
    this.distanceMeters,
    this.rangeClass = RangeClass.unknown,
    this.distanceEstimated = true,
    this.approaching = false,
    this.indicator = 'OFF',
  });
  factory VisionDetection.decode(String source) {
    final json = jsonDecode(source) as Map<String, dynamic>;
    if (json['type'] != 'vision_detection') {
      throw const FormatException('Unexpected packet type');
    }
    final confidence = (json['confidence'] as num).toDouble();
    if (confidence < 0 || confidence > 1) {
      throw const FormatException('Invalid confidence');
    }
    return VisionDetection(
      timestamp: json['timestamp'] as int,
      nodeId: json['nodeId'] as String,
      cameraId: json['cameraId'] as String,
      sector: json['sector'] as String,
      trackId: json['trackId'] as int,
      objectClass: ObjectClass.values.byName(
        (json['class'] as String).replaceAll(
          'unknown_air_object',
          'unknownAirObject',
        ),
      ),
      confidence: confidence,
      confirmed: json['confirmed'] as bool? ?? false,
      simulated: json['simulated'] as bool? ?? false,
      bbox: json['bbox'] is Map<String, dynamic>
          ? NormalizedBox.fromJson(json['bbox'] as Map<String, dynamic>)
          : null,
      distanceMeters: (json['distanceMeters'] as num?)?.toDouble(),
      rangeClass: RangeClass.values.byName(
        (json['rangeClass'] as String? ?? 'UNKNOWN').toLowerCase(),
      ),
      distanceEstimated: json['distanceEstimated'] as bool? ?? true,
      approaching: json['approaching'] as bool? ?? false,
      indicator: json['indicator'] as String? ?? 'OFF',
    );
  }
  final int timestamp, trackId;
  final String nodeId, cameraId, sector;
  final ObjectClass objectClass;
  final double confidence;
  final bool confirmed, simulated;
  final NormalizedBox? bbox;
  final double? distanceMeters;
  final RangeClass rangeClass;
  final bool distanceEstimated, approaching;
  final String indicator;
}

class NormalizedBox {
  const NormalizedBox(this.x, this.y, this.width, this.height);
  factory NormalizedBox.fromJson(Map<String, dynamic> json) {
    final box = NormalizedBox(
      (json['x'] as num).toDouble(),
      (json['y'] as num).toDouble(),
      (json['w'] as num).toDouble(),
      (json['h'] as num).toDouble(),
    );
    if (box.x < 0 ||
        box.y < 0 ||
        box.width <= 0 ||
        box.height <= 0 ||
        box.x + box.width > 1 ||
        box.y + box.height > 1) {
      throw const FormatException('Invalid bounding box');
    }
    return box;
  }
  final double x, y, width, height;
}

class SectorStatePacket {
  const SectorStatePacket(this.sector, this.state, this.trackId);
  factory SectorStatePacket.fromJson(Map<String, dynamic> json) =>
      SectorStatePacket(
        json['sector'] as String,
        json['state'] as String? ?? 'OFF',
        json['trackId'] as int?,
      );
  final String sector, state;
  final int? trackId;
}

class SystemHealthPacket {
  const SystemHealthPacket(
    this.status,
    this.mode,
    this.cameraCount,
    this.esp32Count,
  );
  factory SystemHealthPacket.fromJson(Map<String, dynamic> json) =>
      SystemHealthPacket(
        json['status'] as String? ?? 'unknown',
        json['mode'] as String? ?? 'unknown',
        json['cameraCount'] as int? ?? 0,
        json['esp32Count'] as int? ?? 0,
      );
  final String status, mode;
  final int cameraCount, esp32Count;
}

class CameraHealthPacket {
  const CameraHealthPacket({
    required this.cameraId,
    required this.online,
    required this.captureFps,
    required this.processingFps,
    required this.droppedFrames,
    required this.reconnectCount,
    required this.sector,
    this.error,
  });
  factory CameraHealthPacket.fromJson(Map<String, dynamic> json) =>
      CameraHealthPacket(
        cameraId: json['cameraId'] as String,
        online: json['online'] as bool? ?? false,
        captureFps: (json['capture_fps'] as num? ?? 0).toDouble(),
        processingFps: (json['processing_fps'] as num? ?? 0).toDouble(),
        droppedFrames: json['dropped'] as int? ?? 0,
        reconnectCount: json['reconnect_count'] as int? ?? 0,
        sector: json['sector'] as String? ?? 'UNKNOWN',
        error: json['error'] as String?,
      );
  final String cameraId, sector;
  final bool online;
  final double captureFps, processingFps;
  final int droppedFrames, reconnectCount;
  final String? error;
}

class EventPacket {
  const EventPacket(this.event, this.timestamp, this.sector, this.trackId);
  factory EventPacket.fromJson(Map<String, dynamic> json) => EventPacket(
    json['event'] as String,
    json['timestamp'] as int,
    json['sector'] as String? ?? 'UNKNOWN',
    json['track_id'] as int? ?? json['trackId'] as int?,
  );
  final String event, sector;
  final int timestamp;
  final int? trackId;
}

Object decodeVisionPacket(String source) {
  final json = jsonDecode(source) as Map<String, dynamic>;
  if ((json['protocolVersion'] as int? ?? 1) != 1) {
    throw const FormatException('Unsupported protocol version');
  }
  return switch (json['type']) {
    'vision_detection' => VisionDetection.decode(source),
    'sector_state' => SectorStatePacket.fromJson(json),
    'system_health' || 'node_health' => SystemHealthPacket.fromJson(json),
    'camera_health' => CameraHealthPacket.fromJson(json),
    'event' => EventPacket.fromJson(json),
    _ => throw const FormatException('Unexpected packet type'),
  };
}
