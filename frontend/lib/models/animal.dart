class Animal {
  final String id;
  final String farmId;
  final String animalName;
  final String? breed;
  final String? tagId;
  final String vaccinationStatus;
  final String? medicationHistory;
  final String feedQuality;
  final List<String> symptoms;
  final double riskPercentage;
  final String riskLevel;
  final double healthScore;
  final String? imagePath;
  final String? audioPath;
  final DateTime createdAt;

  Animal({
    required this.id,
    required this.farmId,
    required this.animalName,
    this.breed,
    this.tagId,
    this.vaccinationStatus = 'Up to date',
    this.medicationHistory,
    this.feedQuality = 'Good',
    this.symptoms = const [],
    this.riskPercentage = 0.0,
    this.riskLevel = 'Low',
    this.healthScore = 100.0,
    this.imagePath,
    this.audioPath,
    required this.createdAt,
  });

  factory Animal.fromJson(Map<String, dynamic> json) {
    return Animal(
      id: json['id'] ?? '',
      farmId: json['farm_id'] ?? '',
      animalName: json['animal_name'] ?? '',
      breed: json['breed'],
      tagId: json['tag_id'],
      vaccinationStatus: json['vaccination_status'] ?? 'Up to date',
      medicationHistory: json['medication_history'],
      feedQuality: json['feed_quality'] ?? 'Good',
      symptoms: json['symptoms'] != null 
          ? List<String>.from(json['symptoms']) 
          : [],
      riskPercentage: (json['risk_percentage'] ?? 0.0).toDouble(),
      riskLevel: json['risk_level'] ?? 'Low',
      healthScore: (json['health_score'] ?? 100.0).toDouble(),
      imagePath: json['image_path'],
      audioPath: json['audio_path'],
      createdAt: json['created_at'] != null 
          ? DateTime.parse(json['created_at']) 
          : DateTime.now(),
    );
  }

  Map<String, dynamic> toJson() {
    return {
      'id': id,
      'farm_id': farmId,
      'animal_name': animalName,
      'breed': breed,
      'tag_id': tagId,
      'vaccination_status': vaccinationStatus,
      'medication_history': medicationHistory,
      'feed_quality': feedQuality,
      'symptoms': symptoms,
      'risk_percentage': riskPercentage,
      'risk_level': riskLevel,
      'health_score': healthScore,
      'image_path': imagePath,
      'audio_path': audioPath,
      'created_at': createdAt.toIso8601String(),
    };
  }
}
