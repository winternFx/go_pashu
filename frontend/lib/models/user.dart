class User {
  final String id;
  final String name;
  final String email;
  final String? phone;
  final String? location;
  final DateTime createdAt;
  final int totalFarms;
  final int totalAnimals;
  final int highRiskAnimals;

  User({
    required this.id,
    required this.name,
    required this.email,
    this.phone,
    this.location,
    required this.createdAt,
    this.totalFarms = 0,
    this.totalAnimals = 0,
    this.highRiskAnimals = 0,
  });

  factory User.fromJson(Map<String, dynamic> json) {
    return User(
      id: json['id'] ?? '',
      name: json['name'] ?? '',
      email: json['email'] ?? '',
      phone: json['phone'],
      location: json['location'],
      createdAt: json['created_at'] != null 
          ? DateTime.parse(json['created_at']) 
          : DateTime.now(),
      totalFarms: json['total_farms'] ?? 0,
      totalAnimals: json['total_animals'] ?? 0,
      highRiskAnimals: json['high_risk_animals'] ?? 0,
    );
  }

  Map<String, dynamic> toJson() {
    return {
      'id': id,
      'name': name,
      'email': email,
      'phone': phone,
      'location': location,
      'created_at': createdAt.toIso8601String(),
      'total_farms': totalFarms,
      'total_animals': totalAnimals,
      'high_risk_animals': highRiskAnimals,
    };
  }
}
