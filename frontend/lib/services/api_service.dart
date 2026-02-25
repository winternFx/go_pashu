import 'dart:convert';
import 'dart:io';
import 'dart:async';
import 'package:http/http.dart' as http;
import '../models/user.dart';
import '../models/farm.dart';
import '../models/animal.dart';
import '../models/prediction.dart';
import '../utils/api_constants.dart';
import 'auth_service.dart';

class ApiService {
  static final AuthService _authService = AuthService();

  // Get headers with auth token
  static Future<Map<String, String>> _getHeaders() async {
    final token = await _authService.getToken();
    return {
      'Content-Type': 'application/json',
      if (token != null) 'Authorization': 'Bearer $token',
    };
  }

  // Handle HTTP response errors
  static Map<String, dynamic> _handleError(http.Response response) {
    try {
      final data = jsonDecode(response.body);
      return {
        'success': false,
        'error': data['error'] ?? data['message'] ?? 'Request failed with status ${response.statusCode}'
      };
    } catch (e) {
      return {
        'success': false,
        'error': 'Request failed with status ${response.statusCode}'
      };
    }
  }

  // ========== AUTH ENDPOINTS ==========
  
  static Future<Map<String, dynamic>> signup({
    required String name,
    required String email,
    required String password,
    String? phone,
    String? location,
  }) async {
    try {
      final response = await http
          .post(
            Uri.parse(ApiConstants.signupUrl),
            headers: {'Content-Type': 'application/json'},
            body: jsonEncode({
              'name': name,
              'email': email,
              'password': password,
              if (phone != null) 'phone': phone,
              if (location != null) 'location': location,
            }),
          )
          .timeout(ApiConstants.connectionTimeout);

      final data = jsonDecode(response.body);

      if (response.statusCode == 201 || response.statusCode == 200) {
        // Save token
        if (data['token'] != null) {
          await _authService.saveToken(data['token']);
        }
        return {'success': true, 'user': User.fromJson(data['user'])};
      } else {
        return _handleError(response);
      }
    } on SocketException {
      return {'success': false, 'error': 'No internet connection. Please check your network.'};
    } on TimeoutException {
      return {'success': false, 'error': 'Connection timeout. Please try again.'};
    } on FormatException {
      return {'success': false, 'error': 'Invalid response from server.'};
    } catch (e) {
      return {'success': false, 'error': 'Network error: ${e.toString()}'};
    }
  }

  static Future<Map<String, dynamic>> login({
    required String email,
    required String password,
  }) async {
    try {
      final response = await http
          .post(
            Uri.parse(ApiConstants.loginUrl),
            headers: {'Content-Type': 'application/json'},
            body: jsonEncode({
              'email': email,
              'password': password,
            }),
          )
          .timeout(ApiConstants.connectionTimeout);

      final data = jsonDecode(response.body);

      if (response.statusCode == 200) {
        // Save token
        if (data['token'] != null) {
          await _authService.saveToken(data['token']);
        }
        return {'success': true, 'user': User.fromJson(data['user'])};
      } else {
        return _handleError(response);
      }
    } on SocketException {
      return {'success': false, 'error': 'No internet connection. Please check your network.'};
    } on TimeoutException {
      return {'success': false, 'error': 'Connection timeout. Please try again.'};
    } on FormatException {
      return {'success': false, 'error': 'Invalid response from server.'};
    } catch (e) {
      return {'success': false, 'error': 'Network error: ${e.toString()}'};
    }
  }

  static Future<Map<String, dynamic>> getProfile() async {
    try {
      final headers = await _getHeaders();
      final response = await http
          .get(
            Uri.parse(ApiConstants.profileUrl),
            headers: headers,
          )
          .timeout(ApiConstants.connectionTimeout);

      final data = jsonDecode(response.body);

      if (response.statusCode == 200) {
        return {'success': true, 'user': User.fromJson(data['user'])};
      } else {
        return _handleError(response);
      }
    } on SocketException {
      return {'success': false, 'error': 'No internet connection. Please check your network.'};
    } on TimeoutException {
      return {'success': false, 'error': 'Connection timeout. Please try again.'};
    } on FormatException {
      return {'success': false, 'error': 'Invalid response from server.'};
    } catch (e) {
      return {'success': false, 'error': 'Network error: ${e.toString()}'};
    }
  }

  static Future<Map<String, dynamic>> updateProfile({
    String? name,
    String? phone,
    String? location,
  }) async {
    try {
      final headers = await _getHeaders();
      final response = await http
          .put(
            Uri.parse(ApiConstants.profileUrl),
            headers: headers,
            body: jsonEncode({
              if (name != null) 'name': name,
              if (phone != null) 'phone': phone,
              if (location != null) 'location': location,
            }),
          )
          .timeout(ApiConstants.connectionTimeout);

      final data = jsonDecode(response.body);

      if (response.statusCode == 200) {
        return {'success': true, 'user': User.fromJson(data['user'])};
      } else {
        return _handleError(response);
      }
    } on SocketException {
      return {'success': false, 'error': 'No internet connection. Please check your network.'};
    } on TimeoutException {
      return {'success': false, 'error': 'Connection timeout. Please try again.'};
    } on FormatException {
      return {'success': false, 'error': 'Invalid response from server.'};
    } catch (e) {
      return {'success': false, 'error': 'Network error: ${e.toString()}'};
    }
  }

  static Future<void> logout() async {
    await _authService.deleteToken();
  }

  // ========== FARM ENDPOINTS ==========

  static Future<Map<String, dynamic>> getFarms() async {
    try {
      final headers = await _getHeaders();
      final response = await http
          .get(
            Uri.parse(ApiConstants.farmsUrl),
            headers: headers,
          )
          .timeout(ApiConstants.connectionTimeout);

      final data = jsonDecode(response.body);

      if (response.statusCode == 200) {
        final farms = (data['farms'] as List)
            .map((farm) => Farm.fromJson(farm))
            .toList();
        return {'success': true, 'farms': farms};
      } else {
        return _handleError(response);
      }
    } on SocketException {
      return {'success': false, 'error': 'No internet connection. Please check your network.'};
    } on TimeoutException {
      return {'success': false, 'error': 'Connection timeout. Please try again.'};
    } on FormatException {
      return {'success': false, 'error': 'Invalid response from server.'};
    } catch (e) {
      return {'success': false, 'error': 'Network error: ${e.toString()}'};
    }
  }

  static Future<Map<String, dynamic>> getFarm(String farmId) async {
    try {
      final headers = await _getHeaders();
      final response = await http
          .get(
            Uri.parse(ApiConstants.farmDetailUrl(farmId)),
            headers: headers,
          )
          .timeout(ApiConstants.connectionTimeout);

      final data = jsonDecode(response.body);

      if (response.statusCode == 200) {
        return {'success': true, 'farm': Farm.fromJson(data['farm'])};
      } else {
        return _handleError(response);
      }
    } on SocketException {
      return {'success': false, 'error': 'No internet connection. Please check your network.'};
    } on TimeoutException {
      return {'success': false, 'error': 'Connection timeout. Please try again.'};
    } on FormatException {
      return {'success': false, 'error': 'Invalid response from server.'};
    } catch (e) {
      return {'success': false, 'error': 'Network error: ${e.toString()}'};
    }
  }

  static Future<Map<String, dynamic>> createFarm({
    required String farmName,
    String? location,
  }) async {
    try {
      final headers = await _getHeaders();
      final response = await http
          .post(
            Uri.parse(ApiConstants.farmsUrl),
            headers: headers,
            body: jsonEncode({
              'farm_name': farmName,
              if (location != null) 'location': location,
            }),
          )
          .timeout(ApiConstants.connectionTimeout);

      final data = jsonDecode(response.body);

      if (response.statusCode == 201 || response.statusCode == 200) {
        return {'success': true, 'farm': Farm.fromJson(data['farm'])};
      } else {
        return _handleError(response);
      }
    } on SocketException {
      return {'success': false, 'error': 'No internet connection. Please check your network.'};
    } on TimeoutException {
      return {'success': false, 'error': 'Connection timeout. Please try again.'};
    } on FormatException {
      return {'success': false, 'error': 'Invalid response from server.'};
    } catch (e) {
      return {'success': false, 'error': 'Network error: ${e.toString()}'};
    }
  }

  static Future<Map<String, dynamic>> updateFarm({
    required String farmId,
    String? farmName,
    String? location,
  }) async {
    try {
      final headers = await _getHeaders();
      final response = await http
          .put(
            Uri.parse(ApiConstants.farmDetailUrl(farmId)),
            headers: headers,
            body: jsonEncode({
              if (farmName != null) 'farm_name': farmName,
              if (location != null) 'location': location,
            }),
          )
          .timeout(ApiConstants.connectionTimeout);

      final data = jsonDecode(response.body);

      if (response.statusCode == 200) {
        return {'success': true, 'farm': Farm.fromJson(data['farm'])};
      } else {
        return _handleError(response);
      }
    } on SocketException {
      return {'success': false, 'error': 'No internet connection. Please check your network.'};
    } on TimeoutException {
      return {'success': false, 'error': 'Connection timeout. Please try again.'};
    } on FormatException {
      return {'success': false, 'error': 'Invalid response from server.'};
    } catch (e) {
      return {'success': false, 'error': 'Network error: ${e.toString()}'};
    }
  }

  static Future<Map<String, dynamic>> deleteFarm(String farmId) async {
    try {
      final headers = await _getHeaders();
      final response = await http
          .delete(
            Uri.parse(ApiConstants.farmDetailUrl(farmId)),
            headers: headers,
          )
          .timeout(ApiConstants.connectionTimeout);

      final data = jsonDecode(response.body);

      if (response.statusCode == 200) {
        return {'success': true, 'message': data['message']};
      } else {
        return _handleError(response);
      }
    } on SocketException {
      return {'success': false, 'error': 'No internet connection. Please check your network.'};
    } on TimeoutException {
      return {'success': false, 'error': 'Connection timeout. Please try again.'};
    } on FormatException {
      return {'success': false, 'error': 'Invalid response from server.'};
    } catch (e) {
      return {'success': false, 'error': 'Network error: ${e.toString()}'};
    }
  }

  static Future<Map<String, dynamic>> getFarmSummary(String farmId) async {
    try {
      final headers = await _getHeaders();
      final response = await http
          .get(
            Uri.parse(ApiConstants.farmSummaryUrl(farmId)),
            headers: headers,
          )
          .timeout(ApiConstants.connectionTimeout);

      final data = jsonDecode(response.body);

      if (response.statusCode == 200) {
        return {'success': true, 'summary': FarmSummary.fromJson(data['summary'])};
      } else {
        return _handleError(response);
      }
    } on SocketException {
      return {'success': false, 'error': 'No internet connection. Please check your network.'};
    } on TimeoutException {
      return {'success': false, 'error': 'Connection timeout. Please try again.'};
    } on FormatException {
      return {'success': false, 'error': 'Invalid response from server.'};
    } catch (e) {
      return {'success': false, 'error': 'Network error: ${e.toString()}'};
    }
  }

  // ========== ANIMAL ENDPOINTS ==========

  static Future<Map<String, dynamic>> getAnimals({String? farmId}) async {
    try {
      final headers = await _getHeaders();
      var url = ApiConstants.animalsUrl;
      if (farmId != null) {
        url += '?farm_id=$farmId';
      }

      final response = await http
          .get(
            Uri.parse(url),
            headers: headers,
          )
          .timeout(ApiConstants.connectionTimeout);

      final data = jsonDecode(response.body);

      if (response.statusCode == 200) {
        final animals = (data['animals'] as List)
            .map((animal) => Animal.fromJson(animal))
            .toList();
        return {'success': true, 'animals': animals};
      } else {
        return _handleError(response);
      }
    } on SocketException {
      return {'success': false, 'error': 'No internet connection. Please check your network.'};
    } on TimeoutException {
      return {'success': false, 'error': 'Connection timeout. Please try again.'};
    } on FormatException {
      return {'success': false, 'error': 'Invalid response from server.'};
    } catch (e) {
      return {'success': false, 'error': 'Network error: ${e.toString()}'};
    }
  }

  static Future<Map<String, dynamic>> getAnimal(String animalId) async {
    try {
      final headers = await _getHeaders();
      final response = await http
          .get(
            Uri.parse(ApiConstants.animalDetailUrl(animalId)),
            headers: headers,
          )
          .timeout(ApiConstants.connectionTimeout);

      final data = jsonDecode(response.body);

      if (response.statusCode == 200) {
        return {'success': true, 'animal': Animal.fromJson(data['animal'])};
      } else {
        return _handleError(response);
      }
    } on SocketException {
      return {'success': false, 'error': 'No internet connection. Please check your network.'};
    } on TimeoutException {
      return {'success': false, 'error': 'Connection timeout. Please try again.'};
    } on FormatException {
      return {'success': false, 'error': 'Invalid response from server.'};
    } catch (e) {
      return {'success': false, 'error': 'Network error: ${e.toString()}'};
    }
  }

  static Future<Map<String, dynamic>> createAnimal({
    required String farmId,
    required String animalName,
    String? breed,
    String? tagId,
    String? vaccinationStatus,
    String? feedQuality,
    String? medicationHistory,
    File? imageFile,
  }) async {
    try {
      final token = await _authService.getToken();
      
      if (token == null) {
        return {'success': false, 'error': 'Authentication token not found. Please login again.'};
      }

      var request = http.MultipartRequest(
        'POST',
        Uri.parse(ApiConstants.animalsUrl),
      );

      // Set headers properly
      request.headers['Authorization'] = 'Bearer $token';

      // Add fields
      request.fields['farm_id'] = farmId;
      request.fields['animal_name'] = animalName;
      if (breed != null) request.fields['breed'] = breed;
      if (tagId != null) request.fields['tag_id'] = tagId;
      if (vaccinationStatus != null) request.fields['vaccination_status'] = vaccinationStatus;
      if (feedQuality != null) request.fields['feed_quality'] = feedQuality;
      if (medicationHistory != null) request.fields['medication_history'] = medicationHistory;

      // Add image file if provided
      if (imageFile != null) {
        request.files.add(await http.MultipartFile.fromPath('image', imageFile.path));
      }

      final streamedResponse = await request.send().timeout(ApiConstants.connectionTimeout);
      final response = await http.Response.fromStream(streamedResponse);
      final data = jsonDecode(response.body);

      if (response.statusCode == 201 || response.statusCode == 200) {
        return {'success': true, 'animal': Animal.fromJson(data['animal'])};
      } else {
        return _handleError(response);
      }
    } on SocketException {
      return {'success': false, 'error': 'No internet connection. Please check your network.'};
    } on TimeoutException {
      return {'success': false, 'error': 'Connection timeout. Please try again.'};
    } on FormatException {
      return {'success': false, 'error': 'Invalid response from server.'};
    } catch (e) {
      return {'success': false, 'error': 'Network error: ${e.toString()}'};
    }
  }

  static Future<Map<String, dynamic>> deleteAnimal(String animalId) async {
    try {
      final headers = await _getHeaders();
      final response = await http
          .delete(
            Uri.parse(ApiConstants.animalDetailUrl(animalId)),
            headers: headers,
          )
          .timeout(ApiConstants.connectionTimeout);

      final data = jsonDecode(response.body);

      if (response.statusCode == 200) {
        return {'success': true, 'message': data['message']};
      } else {
        return _handleError(response);
      }
    } on SocketException {
      return {'success': false, 'error': 'No internet connection. Please check your network.'};
    } on TimeoutException {
      return {'success': false, 'error': 'Connection timeout. Please try again.'};
    } on FormatException {
      return {'success': false, 'error': 'Invalid response from server.'};
    } catch (e) {
      return {'success': false, 'error': 'Network error: ${e.toString()}'};
    }
  }

  // ========== PREDICTION ENDPOINTS ==========

  static Future<Map<String, dynamic>> runPrediction({
    required String animalId,
    required List<String> symptoms,
    String? vaccinationStatus,
    String? feedQuality,
    String? breed,
    int? ageMonths,
    String? medicationHistory,
  }) async {
    try {
      final headers = await _getHeaders();
      final response = await http
          .post(
            Uri.parse(ApiConstants.predictUrl),
            headers: headers,
            body: jsonEncode({
              'animal_id': animalId,
              'symptoms': symptoms,
              if (vaccinationStatus != null) 'vaccination_status': vaccinationStatus,
              if (feedQuality != null) 'feed_quality': feedQuality,
              if (breed != null) 'breed': breed,
              if (ageMonths != null) 'age_months': ageMonths,
              if (medicationHistory != null) 'medication_history': medicationHistory,
            }),
          )
          .timeout(ApiConstants.connectionTimeout);

      final data = jsonDecode(response.body);

      if (response.statusCode == 200) {
        return {'success': true, 'prediction': data['prediction']};
      } else {
        return _handleError(response);
      }
    } on SocketException {
      return {'success': false, 'error': 'No internet connection. Please check your network.'};
    } on TimeoutException {
      return {'success': false, 'error': 'Connection timeout. Please try again.'};
    } on FormatException {
      return {'success': false, 'error': 'Invalid response from server.'};
    } catch (e) {
      return {'success': false, 'error': 'Network error: ${e.toString()}'};
    }
  }

  static Future<Map<String, dynamic>> detectDiseaseFromImage({
    required File imageFile,
    String? animalId,
  }) async {
    try {
      final token = await _authService.getToken();
      
      if (token == null) {
        return {'success': false, 'error': 'Authentication token not found. Please login again.'};
      }

      var request = http.MultipartRequest(
        'POST',
        Uri.parse(ApiConstants.detectDiseaseImageUrl),
      );

      // Set headers properly
      request.headers['Authorization'] = 'Bearer $token';

      // Add fields
      if (animalId != null) request.fields['animal_id'] = animalId;

      // Add image file
      request.files.add(await http.MultipartFile.fromPath('image', imageFile.path));

      final streamedResponse = await request.send().timeout(ApiConstants.connectionTimeout);
      final response = await http.Response.fromStream(streamedResponse);
      final data = jsonDecode(response.body);

      if (response.statusCode == 200) {
        return {'success': true, 'result': data};
      } else {
        return _handleError(response);
      }
    } on SocketException {
      return {'success': false, 'error': 'No internet connection. Please check your network.'};
    } on TimeoutException {
      return {'success': false, 'error': 'Connection timeout. Please try again.'};
    } on FormatException {
      return {'success': false, 'error': 'Invalid response from server.'};
    } catch (e) {
      return {'success': false, 'error': 'Network error: ${e.toString()}'};
    }
  }

  static Future<Map<String, dynamic>> identifyCowFromImage({
    required File imageFile,
  }) async {
    try {
      final token = await _authService.getToken();

      if (token == null) {
        return {'success': false, 'error': 'Authentication token not found. Please login again.'};
      }

      var request = http.MultipartRequest(
        'POST',
        Uri.parse(ApiConstants.identifyCowImageUrl),
      );

      request.headers['Authorization'] = 'Bearer $token';
      request.files.add(await http.MultipartFile.fromPath('image', imageFile.path));

      final streamedResponse = await request.send().timeout(ApiConstants.connectionTimeout);
      final response = await http.Response.fromStream(streamedResponse);
      final data = jsonDecode(response.body);

      if (response.statusCode == 200) {
        return {'success': true, 'result': data};
      } else {
        return _handleError(response);
      }
    } on SocketException {
      return {'success': false, 'error': 'No internet connection. Please check your network.'};
    } on TimeoutException {
      return {'success': false, 'error': 'Connection timeout. Please try again.'};
    } on FormatException {
      return {'success': false, 'error': 'Invalid response from server.'};
    } catch (e) {
      return {'success': false, 'error': 'Network error: ${e.toString()}'};
    }
  }

  static Future<Map<String, dynamic>> identifyCowFromVoice({
    required File audioFile,
  }) async {
    try {
      final token = await _authService.getToken();

      if (token == null) {
        return {'success': false, 'error': 'Authentication token not found. Please login again.'};
      }

      var request = http.MultipartRequest(
        'POST',
        Uri.parse(ApiConstants.identifyCowVoiceUrl),
      );

      request.headers['Authorization'] = 'Bearer $token';
      request.files.add(await http.MultipartFile.fromPath('audio', audioFile.path));

      final streamedResponse = await request.send().timeout(ApiConstants.connectionTimeout);
      final response = await http.Response.fromStream(streamedResponse);
      final data = jsonDecode(response.body);

      if (response.statusCode == 200) {
        return {'success': true, 'result': data};
      } else {
        return _handleError(response);
      }
    } on SocketException {
      return {'success': false, 'error': 'No internet connection. Please check your network.'};
    } on TimeoutException {
      return {'success': false, 'error': 'Connection timeout. Please try again.'};
    } on FormatException {
      return {'success': false, 'error': 'Invalid response from server.'};
    } catch (e) {
      return {'success': false, 'error': 'Network error: ${e.toString()}'};
    }
  }

  static Future<Map<String, dynamic>> getPredictionHistory(String animalId) async {
    try {
      final headers = await _getHeaders();
      final response = await http
          .get(
            Uri.parse(ApiConstants.predictionHistoryUrl(animalId)),
            headers: headers,
          )
          .timeout(ApiConstants.connectionTimeout);

      final data = jsonDecode(response.body);

      if (response.statusCode == 200) {
        final predictions = (data['predictions'] as List)
            .map((pred) => Prediction.fromJson(pred))
            .toList();
        return {'success': true, 'predictions': predictions};
      } else {
        return _handleError(response);
      }
    } on SocketException {
      return {'success': false, 'error': 'No internet connection. Please check your network.'};
    } on TimeoutException {
      return {'success': false, 'error': 'Connection timeout. Please try again.'};
    } on FormatException {
      return {'success': false, 'error': 'Invalid response from server.'};
    } catch (e) {
      return {'success': false, 'error': 'Network error: ${e.toString()}'};
    }
  }
}