class ApiConstants {
  // Android emulator: 10.0.2.2.  Physical phone (same WiFi): your PC's IPv4 from ipconfig (e.g. 192.168.1.5). Change below as needed.
  static const String baseUrl = "http://10.22.86.47:5000";

  // Auth endpoints
  static const String signupUrl = "$baseUrl/api/auth/signup";
  static const String loginUrl = "$baseUrl/api/auth/login";
  static const String profileUrl = "$baseUrl/api/auth/me";
  static const String logoutUrl = "$baseUrl/api/auth/logout";

  // Farm endpoints
  static const String farmsUrl = "$baseUrl/api/farms";
  static String farmDetailUrl(String farmId) =>
      "$baseUrl/api/farms/$farmId";
  static String farmSummaryUrl(String farmId) =>
      "$baseUrl/api/farms/$farmId/summary";

  // Animal endpoints
  static const String animalsUrl = "$baseUrl/api/animals";
  static String animalDetailUrl(String animalId) =>
      "$baseUrl/api/animals/$animalId";

  // Prediction endpoints
  static const String predictUrl =
      "$baseUrl/api/predictions/predict";
  static const String detectDiseaseImageUrl =
      "$baseUrl/api/predictions/detect-disease-image";
  static const String identifyCowImageUrl =
      "$baseUrl/api/predictions/identify-cow-image";
  static const String identifyCowVoiceUrl =
      "$baseUrl/api/predictions/identify-cow-voice";
  static const String detectDiseaseSymptomsUrl =
      "$baseUrl/api/predictions/detect-disease-symptoms";
  static String predictionHistoryUrl(String animalId) =>
      "$baseUrl/api/predictions/$animalId/history";

  // Timeouts
  static const Duration connectionTimeout = Duration(seconds: 30);
  static const Duration receiveTimeout = Duration(seconds: 30);
}