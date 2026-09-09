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
  static const defaultServerHost = String.fromEnvironment(
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
    connection.connectToHost(defaultServerHost);

    previewTimer = Timer.periodic(const Duration(milliseconds: 500), (_) {
      if (mounted &&
          connection.state == jetson.JetsonConnectionState.connected) {
        setState(() => previewTick++);
      }
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

  Color _statusColor(jetson.JetsonConnectionState state) => switch (state) {
    jetson.JetsonConnectionState.connected => Colors.green,
    jetson.JetsonConnectionState.connecting => Colors.orange,
    jetson.JetsonConnectionState.error => Colors.red,
    jetson.JetsonConnectionState.disconnected => Colors.grey,
  };

  Future<void> _showConnectDialog() async {
    final controller = TextEditingController(text: defaultServerHost);
    final result = await showDialog<String>(
      context: context,
      builder: (ctx) => AlertDialog(
        title: const Text('Jetson Xostiga Ulanish'),
        content: TextField(
          controller: controller,
          decoration: const InputDecoration(
            labelText: 'IP Manzil yoki Xost',
            hintText: '192.168.1.100',
          ),
          autofocus: true,
        ),
        actions: [
          TextButton(
            onPressed: () => Navigator.pop(ctx),
            child: const Text('BEKOR QILISH'),
          ),
          ElevatedButton(
            onPressed: () => Navigator.pop(ctx, controller.text.trim()),
            child: const Text('ULANISH'),
          ),
        ],
      ),
    );

    if (result != null && result.isNotEmpty) {
      connection.connectToHost(result);
    }
  }

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
        ActionChip(
          avatar: Icon(
            Icons.circle,
            size: 12,
            color: _statusColor(connection.state),
          ),
          label: Text(connection.state.name.toUpperCase()),
          onPressed: _showConnectDialog,
        ),
        const SizedBox(width: 16),
      ],
    ),
    body: Padding(
      padding: const EdgeInsets.all(12),
      child: Column(
        children: [
          if (connection.errorMessage != null)
            Container(
              width: double.infinity,
              margin: const EdgeInsets.only(bottom: 8),
              padding: const EdgeInsets.all(10),
              color: Colors.red.shade900,
              child: Row(
                children: [
                  const Icon(Icons.error_outline),
                  const SizedBox(width: 8),
                  Expanded(child: Text(connection.errorMessage!)),
                  TextButton(
                    onPressed: _showConnectDialog,
                    child: const Text('QAYTA ULASH'),
                  ),
                ],
              ),
            ),
          Expanded(
            child: Row(
              children: [
          Expanded(
            flex: 3,
            child: Column(
              children: [
                Row(
                  children: [
                    const Text(
                      'CAMERAS',
                      style: TextStyle(fontWeight: FontWeight.bold),
                    ),
                    const Spacer(),
                    DropdownButton<int>(
                      value: cameraCount,
                      items: [1, 2, 4, 8, 9, 12]
                          .map(
                            (n) => DropdownMenuItem(
                              value: n,
                              child: Text('$n Kamera'),
                            ),
                          )
                          .toList(),
                      onChanged: (n) {
                        if (n != null) setState(() => cameraCount = n);
                      },
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
                        clipBehavior: Clip.antiAlias,
                        child: InkWell(
                          onTap: mode == ControlMode.manual
                              ? () =>
                                    ScaffoldMessenger.of(context).showSnackBar(
                                      SnackBar(
                                        content: Text(
                                          'Kamera $cameraId: ROI Sozlash',
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
                                      child: Text(
                                        'KADR MAVJUD EMAS',
                                        style: TextStyle(color: Colors.red),
                                      ),
                                    ),
                                  ),
                                )
                              else
                                const Center(
                                  child: Text(
                                    'OFFLINE',
                                    style: TextStyle(color: Colors.grey),
                                  ),
                                ),
                              Positioned(
                                left: 8,
                                top: 8,
                                child: Container(
                                  padding: const EdgeInsets.symmetric(
                                    horizontal: 6,
                                    vertical: 2,
                                  ),
                                  color: Colors.black87,
                                  child: Text(
                                    cameraId,
                                    style: const TextStyle(
                                      color: Colors.white,
                                      fontWeight: FontWeight.bold,
                                    ),
                                  ),
                                ),
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
                                child: Container(
                                  padding: const EdgeInsets.symmetric(
                                    horizontal: 6,
                                    vertical: 2,
                                  ),
                                  color: Colors.black87,
                                  child: Text(
                                    health == null
                                        ? 'NO HEALTH'
                                        : '${health.captureFps.toStringAsFixed(1)} FPS · '
                                              '${health.processingFps.toStringAsFixed(1)} AI · '
                                              'Drop: ${health.droppedFrames}',
                                    style: const TextStyle(
                                      color: Colors.white,
                                      fontSize: 11,
                                    ),
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
                const Text(
                  'SECTORS',
                  style: TextStyle(fontWeight: FontWeight.bold),
                ),
                const SizedBox(height: 6),
                Wrap(
                  spacing: 4,
                  runSpacing: 4,
                  children: sectors
                      .map(
                        (s) => Chip(
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
                      )
                      .toList(),
                ),
                const Divider(),
                const Text(
                  'LATEST DETECTION',
                  style: TextStyle(fontWeight: FontWeight.bold),
                ),
                ListTile(
                  dense: true,
                  title: Text(
                    connection.latestDetection?.objectClass.name
                            .toUpperCase() ??
                        'NO OBJECT',
                    style: const TextStyle(fontWeight: FontWeight.bold),
                  ),
                  subtitle: Text(
                    connection.latestDetection == null
                        ? 'AI Telemetriya mavjud emas'
                        : 'Track #${connection.latestDetection!.trackId} · '
                              '${(connection.latestDetection!.confidence * 100).toStringAsFixed(1)}% · '
                              '${connection.latestDetection!.distanceMeters?.toStringAsFixed(1) ?? '—'} m · '
                              'Sektor: ${connection.latestDetection!.sector}',
                  ),
                ),
                const Divider(),
                const Text(
                  'NODE HEALTH',
                  style: TextStyle(fontWeight: FontWeight.bold),
                ),
                ListTile(
                  dense: true,
                  title: Text(
                    connection.health?.status.toUpperCase() ?? 'OFFLINE',
                  ),
                  subtitle: Text(
                    connection.health == null
                        ? 'Kamera —  AI —  ESP32 —'
                        : '${connection.health!.mode} · Kameralar: ${connection.health!.cameraCount} · ESP32: ${connection.health!.esp32Count}',
                  ),
                ),
                const Divider(),
                const Text(
                  'EVENT HISTORY',
                  style: TextStyle(fontWeight: FontWeight.bold),
                ),
                Expanded(
                  child: connection.events.isEmpty
                      ? const Center(child: Text('Hodisalar yo\'q'))
                      : ListView.builder(
                          itemCount: connection.events.length,
                          itemBuilder: (_, index) {
                            final event = connection.events[index];
                            return ListTile(
                              dense: true,
                              title: Text(event.event),
                              subtitle: Text(
                                'Sektor: ${event.sector} · ID: #${event.trackId ?? '—'}',
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
    final box = detection.bbox;
    if (box == null) return;

    // Normallashtirilgan koordinatalarni kadr o'lchamiga o'tkazish va chegaralarni tekshirish
    final rect = Rect.fromLTWH(
      (box.x * size.width).clamp(0.0, size.width),
      (box.y * size.height).clamp(0.0, size.height),
      (box.width * size.width).clamp(0.0, size.width),
      (box.height * size.height).clamp(0.0, size.height),
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

    final textSpan = TextSpan(
      style: TextStyle(
        color: color,
        backgroundColor: Colors.black87,
        fontSize: 11,
      ),
      text:
          '${detection.objectClass.name.toUpperCase()} '
          '${(detection.confidence * 100).toStringAsFixed(0)}%  '
          '#${detection.trackId}  $range  ${detection.sector}',
    );

    final painter = TextPainter(
      text: textSpan,
      textDirection: TextDirection.ltr,
    )..layout(maxWidth: size.width);

    final textOffset = Offset(
      rect.left.clamp(0.0, size.width - painter.width),
      (rect.top - painter.height).clamp(0.0, size.height - painter.height),
    );

    painter.paint(canvas, textOffset);
  }

  @override
  bool shouldRepaint(covariant _DetectionOverlayPainter oldDelegate) =>
      oldDelegate.detection.timestamp != detection.timestamp;
}
