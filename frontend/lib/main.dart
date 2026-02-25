import 'package:flutter/material.dart';
import 'package:provider/provider.dart';
import 'services/app_state.dart';
import 'utils/app_theme.dart';
import 'screens/splash_screen.dart';

void main() {
  runApp(const GoPashuApp());
}

class GoPashuApp extends StatelessWidget {
  const GoPashuApp({super.key});

  @override
  Widget build(BuildContext context) {
    return ChangeNotifierProvider(
      create: (_) => AppState(),
      child: MaterialApp(
        title: 'GoPashu - AI Livestock Management',
        debugShowCheckedModeBanner: false,
        theme: AppTheme.lightTheme,
        home: const SplashScreen(),
      ),
    );
  }
}
