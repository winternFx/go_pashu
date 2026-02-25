class Farm {
  final String id;
  final String userId;
  final String farmName;
  final String? location;
  final int totalAnimals;
  final double healthScore;
  final String riskLevel;
  final DateTime createdAt;

  Farm({
    required this.id,
    required this.userId,
    required this.farmName,
    this.location,
    this.totalAnimals = 0,
    this.healthScore = 100.0,
    this.riskLevel = 'Low',
    required this.createdAt,
  });

  factory Farm.fromJson(Map<String, dynamic> json) {
    return Farm(
      id: json['id'] ?? '',
      userId: json['user_id'] ?? '',
      farmName: json['farm_name'] ?? '',
      location: json['location'],
      totalAnimals: json['total_animals'] ?? 0,
      healthScore: (json['health_score'] ?? 100.0).toDouble(),
      riskLevel: json['risk_level'] ?? 'Low',
      createdAt: json['created_at'] != null 
          ? DateTime.parse(json['created_at']) 
          : DateTime.now(),
    );
  }

  Map<String, dynamic> toJson() {
    return {
      'id': id,
      'user_id': userId,
      'farm_name': farmName,
      'location': location,
      'total_animals': totalAnimals,
      'health_score': healthScore,
      'risk_level': riskLevel,
      'created_at': createdAt.toIso8601String(),
    };
  }
}
