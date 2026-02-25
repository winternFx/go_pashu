import 'package:flutter/material.dart';
import '../models/user.dart';
import '../models/farm.dart';
import '../models/animal.dart';
import '../services/api_service.dart';
import '../services/auth_service.dart';

class AppState extends ChangeNotifier {
  final AuthService _authService = AuthService();
  
  User? _currentUser;
  List<Farm> _farms = [];
  List<Animal> _animals = [];
  bool _isLoading = false;
  String? _error;

  User? get currentUser => _currentUser;
  List<Farm> get farms => _farms;
  List<Animal> get animals => _animals;
  bool get isLoading => _isLoading;
  String? get error => _error;
  bool get isLoggedIn => _currentUser != null;

  // Set loading state
  void setLoading(bool loading) {
    _isLoading = loading;
    notifyListeners();
  }

  // Set error
  void setError(String? error) {
    _error = error;
    notifyListeners();
  }

  // Clear error
  void clearError() {
    _error = null;
    notifyListeners();
  }

  // Initialize app - check if user is logged in
  Future<bool> initialize() async {
    try {
      final isLoggedIn = await _authService.isLoggedIn();
      if (isLoggedIn) {
        await loadUserProfile();
        return true;
      }
      return false;
    } catch (e) {
      return false;
    }
  }

  // Load user profile
  Future<void> loadUserProfile() async {
    try {
      setLoading(true);
      final result = await ApiService.getProfile();
      if (result['success']) {
        _currentUser = result['user'];
        await loadFarms();
      } else {
        setError(result['error']);
      }
    } catch (e) {
      setError('Failed to load profile: $e');
    } finally {
      setLoading(false);
    }
  }

  // Login
  Future<bool> login(String email, String password) async {
    try {
      setLoading(true);
      clearError();
      
      final result = await ApiService.login(email: email, password: password);
      
      if (result['success']) {
        _currentUser = result['user'];
        await loadFarms();
        notifyListeners();
        return true;
      } else {
        setError(result['error']);
        return false;
      }
    } catch (e) {
      setError('Login failed: $e');
      return false;
    } finally {
      setLoading(false);
    }
  }

  // Signup
  Future<bool> signup({
    required String name,
    required String email,
    required String password,
    String? phone,
    String? location,
  }) async {
    try {
      setLoading(true);
      clearError();
      
      final result = await ApiService.signup(
        name: name,
        email: email,
        password: password,
        phone: phone,
        location: location,
      );
      
      if (result['success']) {
        _currentUser = result['user'];
        notifyListeners();
        return true;
      } else {
        setError(result['error']);
        return false;
      }
    } catch (e) {
      setError('Signup failed: $e');
      return false;
    } finally {
      setLoading(false);
    }
  }

  // Logout
  Future<void> logout() async {
    await ApiService.logout();
    _currentUser = null;
    _farms = [];
    _animals = [];
    notifyListeners();
  }

  // Load farms
  Future<void> loadFarms() async {
    try {
      final result = await ApiService.getFarms();
      if (result['success']) {
        _farms = result['farms'];
        notifyListeners();
      }
    } catch (e) {
      print('Failed to load farms: $e');
    }
  }

  // Add farm
  Future<bool> addFarm(String farmName, String? location) async {
    try {
      setLoading(true);
      final result = await ApiService.createFarm(
        farmName: farmName,
        location: location,
      );
      
      if (result['success']) {
        await loadFarms();
        return true;
      } else {
        setError(result['error']);
        return false;
      }
    } catch (e) {
      setError('Failed to add farm: $e');
      return false;
    } finally {
      setLoading(false);
    }
  }

  // Delete farm
  Future<bool> deleteFarm(String farmId) async {
    try {
      setLoading(true);
      final result = await ApiService.deleteFarm(farmId);
      
      if (result['success']) {
        await loadFarms();
        return true;
      } else {
        setError(result['error']);
        return false;
      }
    } catch (e) {
      setError('Failed to delete farm: $e');
      return false;
    } finally {
      setLoading(false);
    }
  }

  // Load animals for a specific farm
  Future<void> loadAnimals({String? farmId}) async {
    try {
      final result = await ApiService.getAnimals(farmId: farmId);
      if (result['success']) {
        _animals = result['animals'];
        notifyListeners();
      }
    } catch (e) {
      print('Failed to load animals: $e');
    }
  }

  // Delete animal
  Future<bool> deleteAnimal(String animalId) async {
    try {
      setLoading(true);
      final result = await ApiService.deleteAnimal(animalId);
      
      if (result['success']) {
        _animals.removeWhere((a) => a.id == animalId);
        notifyListeners();
        return true;
      } else {
        setError(result['error']);
        return false;
      }
    } catch (e) {
      setError('Failed to delete animal: $e');
      return false;
    } finally {
      setLoading(false);
    }
  }

  // Refresh data
  Future<void> refresh() async {
    await loadUserProfile();
  }
}
