import 'package:flutter/material.dart';
import 'features/vision/presentation/vision_dashboard.dart';

void main() => runApp(const TankOperatorApp());

class TankOperatorApp extends StatelessWidget {
  const TankOperatorApp({super.key});
  @override
  Widget build(BuildContext context) => MaterialApp(
    debugShowCheckedModeBanner: false,
    theme: ThemeData.dark(
      useMaterial3: true,
    ).copyWith(scaffoldBackgroundColor: const Color(0xff081018)),
    home: const VisionDashboard(),
  );
}
