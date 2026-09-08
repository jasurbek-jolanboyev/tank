import 'package:flutter_test/flutter_test.dart';
import 'package:tank_operator/features/vision/models/vision_packet.dart';

void main() {
  test('parses simulated detection packet', () {
    final detection = VisionDetection.decode(
      '{"type":"vision_detection","timestamp":1,"nodeId":"NODE-1","cameraId":"CAM-1","sector":"RIGHT_1","trackId":17,"class":"drone","confidence":0.91,"confirmed":true,"simulated":true}',
    );
    expect(detection.objectClass, ObjectClass.drone);
    expect(detection.sector, 'RIGHT_1');
    expect(detection.simulated, isTrue);
  });
  test(
    'rejects invalid confidence',
    () => expect(
      () => VisionDetection.decode(
        '{"type":"vision_detection","timestamp":1,"nodeId":"N","cameraId":"C","sector":"TOP_1","trackId":1,"class":"bird","confidence":2}',
      ),
      throwsFormatException,
    ),
  );
  test('parses bbox range and indicator', () {
    final packet =
        decodeVisionPacket(
              '{"protocolVersion":1,"type":"vision_detection","timestamp":3,"nodeId":"J","cameraId":"C","sector":"FRONT_1","trackId":2,"class":"drone","confidence":0.8,"bbox":{"x":0.1,"y":0.2,"w":0.3,"h":0.2},"distanceMeters":19,"rangeClass":"NEAR","distanceEstimated":false,"approaching":true,"indicator":"RED"}',
            )
            as VisionDetection;
    expect(packet.bbox?.width, 0.3);
    expect(packet.distanceMeters, 19);
    expect(packet.rangeClass, RangeClass.near);
    expect(packet.indicator, 'RED');
  });
  test('parses sector health and event packets', () {
    expect(
      decodeVisionPacket(
        '{"protocolVersion":1,"type":"sector_state","timestamp":1,"sector":"RIGHT_1","state":"RED","trackId":7}',
      ),
      isA<SectorStatePacket>(),
    );
    expect(
      decodeVisionPacket(
        '{"protocolVersion":1,"type":"system_health","timestamp":1,"status":"ok","mode":"DEV_MACOS_MODE","cameraCount":1,"esp32Count":1}',
      ),
      isA<SystemHealthPacket>(),
    );
    expect(
      decodeVisionPacket(
        '{"protocolVersion":1,"type":"event","timestamp":1,"event":"DRONE_CONFIRMED","sector":"RIGHT_1","track_id":7}',
      ),
      isA<EventPacket>(),
    );
  });
}
