import 'dart:async';

import 'package:flutter/material.dart';
import '../models/vision_packet.dart';
import '../services/jetson_connection_service.dart' as jetson;

enum ControlMode { manual, auto }

class VisionDashboard extends StatefulWidget {
  const VisionDashboard({super.key});
  @override
  State<VisionDashboard> createState() => _VisionDashboardState();
}

class _VisionDashboardState extends State<VisionDashboard> {
  static const serverHost = String.fromEnvironment(
    'TANK_SERVER_HOST',
    defaultValue: '172.16.246.172',
  );
  ControlMode mode = ControlMode.auto;
  int cameraCount = 1;
  late final jetson.JetsonConnectionService connection;
  Timer? previewTimer;
  int previewTick = 0;
  static const sectors = [
    'TOP_1',
    'TOP_2',
    'TOP_3',
    'FRONT_1',
    'FRONT_2',
    'REAR_1',
    'REAR_2',
    'LEFT_1',
    'LEFT_2',
    'RIGHT_1',
    'RIGHT_2',
  ];
  @override
  void initState() {
    super.initState();
    connection = jetson.JetsonConnectionService()..addListener(_refresh);
    connection.connect(Uri.parse('ws://$serverHost:8081/ws'));
    previewTimer = Timer.periodic(const Duration(milliseconds: 500), (_) {
      if (mounted) setState(() => previewTick++);
    });
  }

  void _refresh() {
    if (mounted) setState(() {});
  }

  @override
  void dispose() {
    connection.removeListener(_refresh);
    previewTimer?.cancel();
    connection.dispose();
    super.dispose();
  }

  Color? _sectorColor(String sector) =>
      switch (connection.sectors[sector]?.state) {
        'RED' => Colors.red,
        'WHITE' => Colors.white,
        'ERROR' || 'OFFLINE' => Colors.orange,
        _ => null,
      };

  @override
  Widget build(BuildContext context) => Scaffold(
    appBar: AppBar(
      title: const Text('PASSIVE VISION MONITOR'),
      actions: [
        SegmentedButton<ControlMode>(
          segments: const [
            ButtonSegment(value: ControlMode.manual, label: Text('MANUAL')),
            ButtonSegment(value: ControlMode.auto, label: Text('AUTO')),
          ],
          selected: {mode},
          onSelectionChanged: (v) => setState(() => mode = v.first),
        ),
        const SizedBox(width: 16),
        Chip(label: Text(connection.state.name.toUpperCase())),
        const SizedBox(width: 16),
      ],
    ),
    body: Padding(
      padding: const EdgeInsets.all(12),
      child: Row(
        children: [
          Expanded(
            flex: 3,
            child: Column(
              children: [
                Row(
                  children: [
                    const Text('CAMERAS'),
                    const Spacer(),
                    DropdownButton<int>(
                      value: cameraCount,
                      items: [1, 2, 4, 8, 9, 12]
                          .map(
                            (n) =>
                                DropdownMenuItem(value: n, child: Text('$n')),
                          )
                          .toList(),
                      onChanged: (n) => setState(() => cameraCount = n!),
                    ),
                  ],
                ),
                Expanded(
                  child: GridView.builder(
                    gridDelegate: SliverGridDelegateWithFixedCrossAxisCount(
                      crossAxisCount: cameraCount == 1
                          ? 1
                          : cameraCount <= 4
                          ? 2
                          : cameraCount <= 9
                          ? 3
                          : 4,
                      childAspectRatio: 16 / 9,
                    ),
                    itemCount: cameraCount,
                    itemBuilder: (context, index) {
                      final knownIds = connection.cameras.keys.toList()..sort();
                      final cameraId = index < knownIds.length
                          ? knownIds[index]
                          : 'CAM_${index + 1}';
                      final health = connection.cameras[cameraId];
                      final detection = connection.detections[cameraId];
                      return Card(
                        child: InkWell(
                          onTap: mode == ControlMode.manual
                              ? () =>
                                    ScaffoldMessenger.of(context).showSnackBar(
                                      SnackBar(
                                        content: Text(
                                          'Camera ${index + 1}: ROI tanlash',
                                        ),
                                      ),
                                    )
                              : null,
                          child: Stack(
                            children: [
                              if (health?.online ?? false)
                                Positioned.fill(
                                  child: Image.network(
                                    connection
                                        .previewUri(cameraId, previewTick)
                                        .toString(),
                                    fit: BoxFit.contain,
                                    gaplessPlayback: true,
                                    errorBuilder: (_, _, _) => const Center(
                                      child: Text('FRAME UNAVAILABLE'),
                                    ),
                                  ),
                                )
                              else
                                const Center(child: Text('OFFLINE')),
                              Positioned(
                                left: 8,
                                top: 8,
                                child: Text(cameraId),
                              ),
                              if (detection?.bbox != null)
                                Positioned.fill(
                                  child: CustomPaint(
                                    painter: _DetectionOverlayPainter(
                                      detection!,
                                    ),
                                  ),
                                ),
                              Positioned(
                                left: 8,
                                bottom: 8,
                                child: Text(
                                  health == null
                                      ? 'NO HEALTH'
                                      : '${health.captureFps.toStringAsFixed(1)} capture · '
                                            '${health.processingFps.toStringAsFixed(1)} AI · drop ${health.droppedFrames}',
                                  style: const TextStyle(
                                    backgroundColor: Colors.black87,
                                  ),
                                ),
                              ),
                            ],
                          ),
                        ),
                      );
                    },
                  ),
                ),
              ],
            ),
          ),
          const VerticalDivider(),
          Expanded(
            flex: 2,
            child: Column(
              crossAxisAlignment: CrossAxisAlignment.stretch,
              children: [
                const Text('SECTORS'),
                Wrap(
                  children: sectors
                      .map(
                        (s) => Padding(
                          padding: const EdgeInsets.all(3),
                          child: Chip(
                            backgroundColor: _sectorColor(s),
                            label: Text(
                              s,
                              style: TextStyle(
                                color: _sectorColor(s) == Colors.white
                                    ? Colors.black
                                    : null,
                              ),
                            ),
                          ),
                        ),
                      )
                      .toList(),
                ),
                const Divider(),
                const Text('LATEST DETECTION'),
                ListTile(
                  title: Text(
                    connection.latestDetection?.objectClass.name
                            .toUpperCase() ??
                        'NO OBJECT',
                  ),
                  subtitle: Text(
                    connection.latestDetection == null
                        ? 'AI telemetry unavailable'
                        : 'Track #${connection.latestDetection!.trackId} · '
                              '${(connection.latestDetection!.confidence * 100).toStringAsFixed(1)}% · '
                              '${connection.latestDetection!.distanceMeters?.toStringAsFixed(1) ?? '—'} m · '
                              '${connection.latestDetection!.sector}',
                  ),
                ),
                const Divider(),
                const Text('NODE HEALTH'),
                ListTile(
                  title: Text(
                    connection.health?.status.toUpperCase() ?? 'OFFLINE',
                  ),
                  subtitle: Text(
                    connection.health == null
                        ? 'Camera —  AI —  ESP32 —'
                        : '${connection.health!.mode} · Cameras ${connection.health!.cameraCount} · ESP32 ${connection.health!.esp32Count}',
                  ),
                ),
                const Divider(),
                const Text('EVENT HISTORY'),
                Expanded(
                  child: connection.events.isEmpty
                      ? const Center(child: Text('No events'))
                      : ListView.builder(
                          itemCount: connection.events.length,
                          itemBuilder: (_, index) {
                            final event = connection.events[index];
                            return ListTile(
                              dense: true,
                              title: Text(event.event),
                              subtitle: Text(
                                '${event.sector} · #${event.trackId ?? '—'}',
                              ),
                            );
                          },
                        ),
                ),
              ],
            ),
          ),
        ],
      ),
    ),
  );
}

class _DetectionOverlayPainter extends CustomPainter {
  const _DetectionOverlayPainter(this.detection);
  final VisionDetection detection;

  @override
  void paint(Canvas canvas, Size size) {
    final box = detection.bbox!;
    final rect = Rect.fromLTWH(
      box.x * size.width,
      box.y * size.height,
      box.width * size.width,
      box.height * size.height,
    );
    final color = detection.indicator == 'RED' ? Colors.red : Colors.white;
    canvas.drawRect(
      rect,
      Paint()
        ..color = color
        ..style = PaintingStyle.stroke
        ..strokeWidth = 2,
    );
    final range = detection.distanceMeters == null
        ? detection.rangeClass.name.toUpperCase()
        : '${detection.distanceMeters!.toStringAsFixed(1)} m';
    final painter = TextPainter(
      text: TextSpan(
        style: TextStyle(color: color, backgroundColor: Colors.black87),
        text:
            '${detection.objectClass.name.toUpperCase()} '
            '${(detection.confidence * 100).toStringAsFixed(0)}%  '
            '#${detection.trackId}  $range  ${detection.sector}',
      ),
      textDirection: TextDirection.ltr,
    )..layout(maxWidth: size.width);
    painter.paint(
      canvas,
      Offset(rect.left, (rect.top - painter.height).clamp(0, size.height)),
    );
  }

  @override
  bool shouldRepaint(covariant _DetectionOverlayPainter oldDelegate) =>
      oldDelegate.detection.timestamp != detection.timestamp;
}
