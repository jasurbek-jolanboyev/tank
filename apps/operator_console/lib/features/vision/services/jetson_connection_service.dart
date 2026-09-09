import 'dart:async';
import 'dart:io';

import 'package:flutter/foundation.dart';

import '../models/vision_packet.dart';

enum JetsonConnectionState { disconnected, connecting, connected, error }

class JetsonConnectionService extends ChangeNotifier {
  JetsonConnectionService({this.reconnectDelay = const Duration(seconds: 2)});

  final Duration reconnectDelay;
  WebSocket? _socket;
  StreamSubscription<dynamic>? _subscription;
  Timer? _retryTimer;
  int _retryAttempt = 0;
  bool _closed = false;
  Uri? _uri;

  JetsonConnectionState state = JetsonConnectionState.disconnected;
  String? errorMessage;

  VisionDetection? latestDetection;
  final Map<String, VisionDetection> detections = {};
  final Map<String, CameraHealthPacket> cameras = {};
  SystemHealthPacket? health;
  final Map<String, SectorStatePacket> sectors = {};
  final List<EventPacket> events = [];

  Future<void> connect(Uri uri) async {
    _closed = false;
    _uri = uri;
    _retryTimer?.cancel();

    // Eski soketni tozalash
    await _cleanupSocket();

    state = JetsonConnectionState.connecting;
    errorMessage = null;
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
      _retryAttempt = 0;
      state = JetsonConnectionState.connected;
      errorMessage = null;
      notifyListeners();

      _subscription = socket.listen(
        _onMessage,
        onError: (dynamic err) =>
            _onDisconnected(error: true, message: err.toString()),
        onDone: () => _onDisconnected(error: false),
        cancelOnError: true,
      );
    } catch (error) {
      _onDisconnected(error: true, message: 'Ulanishda xatolik: $error');
    }
  }

  Future<void> connectToHost(String host) {
    var rawHost = host.trim();
    if (rawHost.isEmpty) {
      rawHost = '127.0.0.1';
    }

    // Scheme-larni olib tashlash
    final normalized = rawHost
        .replaceFirst(RegExp(r'^https?://'), '')
        .replaceFirst(RegExp(r'^wss?://'), '');

    // Port kiritilmagan bo'lsa default 8081 portni biriktirish
    final uriString = normalized.contains(':')
        ? 'ws://$normalized/ws'
        : 'ws://$normalized:8081/ws';
    return connect(Uri.parse(uriString));
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
      // Ishlov berilmagan paketlarni e'tiborsiz qoldirish
    } catch (e) {
      debugPrint('Packet parse error: $e');
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

  void _onDisconnected({bool error = false, String? message}) {
    _subscription?.cancel();
    _subscription = null;
    _socket = null;

    state = error
        ? JetsonConnectionState.error
        : JetsonConnectionState.disconnected;
    errorMessage = message ?? (error ? 'Server bilan aloqa uzildi' : null);
    notifyListeners();

    if (!_closed && _uri != null) {
      // Exponential Backoff calculation (max 30s)
      final backoffFactor = 1 << _retryAttempt.clamp(0, 4);
      final seconds = (reconnectDelay.inSeconds * backoffFactor).clamp(2, 30);
      _retryAttempt = (_retryAttempt + 1).clamp(0, 4);

      _retryTimer?.cancel();
      _retryTimer = Timer(Duration(seconds: seconds), () {
        if (!_closed && _uri != null) {
          connect(_uri!);
        }
      });
    }
  }

  Future<void> _cleanupSocket() async {
    await _subscription?.cancel();
    _subscription = null;
    try {
      await _socket?.close();
    } catch (_) {}
    _socket = null;
  }

  Future<void> disconnect() async {
    _closed = true;
    _retryTimer?.cancel();
    await _cleanupSocket();
    state = JetsonConnectionState.disconnected;
    errorMessage = null;
    notifyListeners();
  }

  @override
  void dispose() {
    _closed = true;
    _retryTimer?.cancel();
    _subscription?.cancel();
    _socket?.close();
    super.dispose();
  }
}
