import 'dart:async';
import 'dart:io';

import 'package:flutter/foundation.dart';

import '../models/vision_packet.dart';

enum ConnectionState { disconnected, connecting, connected, error }

class JetsonConnectionService extends ChangeNotifier {
  JetsonConnectionService({this.reconnectDelay = const Duration(seconds: 2)});

  final Duration reconnectDelay;
  WebSocket? _socket;
  StreamSubscription<dynamic>? _subscription;
  Timer? _retry;
  bool _closed = false;
  Uri? _uri;
  ConnectionState state = ConnectionState.disconnected;
  VisionDetection? latestDetection;
  final Map<String, VisionDetection> detections = {};
  final Map<String, CameraHealthPacket> cameras = {};
  SystemHealthPacket? health;
  final Map<String, SectorStatePacket> sectors = {};
  final List<EventPacket> events = [];

  Future<void> connect(Uri uri) async {
    _uri = uri;
    _retry?.cancel();
    state = ConnectionState.connecting;
    notifyListeners();
    try {
      final socket = await WebSocket.connect(
        uri.toString(),
      ).timeout(const Duration(seconds: 5));
      if (_closed) {
        await socket.close();
        return;
      }
      _socket = socket;
      state = ConnectionState.connected;
      notifyListeners();
      _subscription = socket.listen(
        _onMessage,
        onError: (_) => _onDisconnected(error: true),
        onDone: _onDisconnected,
        cancelOnError: true,
      );
    } catch (_) {
      _onDisconnected(error: true);
    }
  }

  void _onMessage(dynamic data) {
    if (data is! String) return;
    try {
      final packet = decodeVisionPacket(data);
      switch (packet) {
        case VisionDetection detection:
          latestDetection = detection;
          detections[detection.cameraId] = detection;
        case CameraHealthPacket camera:
          cameras[camera.cameraId] = camera;
        case SectorStatePacket sector:
          sectors[sector.sector] = sector;
        case SystemHealthPacket systemHealth:
          health = systemHealth;
        case EventPacket event:
          events.insert(0, event);
          if (events.length > 200) events.removeLast();
      }
      notifyListeners();
    } on FormatException {
      // Bad/unknown packets are isolated and do not terminate the connection.
    }
  }

  Uri previewUri(String cameraId, int cacheBuster) {
    final source = _uri ?? Uri.parse('ws://127.0.0.1:8081/ws');
    return Uri(
      scheme: source.scheme == 'wss' ? 'https' : 'http',
      host: source.host,
      port: 8080,
      path: '/preview/$cameraId.jpg',
      queryParameters: {'t': '$cacheBuster'},
    );
  }

  void _onDisconnected({bool error = false}) {
    _subscription?.cancel();
    _subscription = null;
    _socket = null;
    state = error ? ConnectionState.error : ConnectionState.disconnected;
    notifyListeners();
    if (!_closed && _uri != null) {
      _retry = Timer(reconnectDelay, () => connect(_uri!));
    }
  }

  Future<void> disconnect() async {
    _closed = true;
    _retry?.cancel();
    await _subscription?.cancel();
    await _socket?.close();
    state = ConnectionState.disconnected;
    notifyListeners();
  }

  @override
  void dispose() {
    _closed = true;
    _retry?.cancel();
    _subscription?.cancel();
    _socket?.close();
    super.dispose();
  }
}
