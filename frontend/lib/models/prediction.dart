class Prediction {
  final String id;
  final String animalId;
  final double diseaseProbability;
  final String riskLevel;
  final double healthScore;
  final String explanation;
  final String recommendedAction;
  final double confidence;
  final Map<String, dynamic>? inputFactors;
  final DateTime predictedAt;

  Prediction({
    required this.id,
    required this.animalId,
    required this.diseaseProbability,
    required this.riskLevel,
    required this.healthScore,
    required this.explanation,
    required this.recommendedAction,
    this.confidence = 0.0,
    this.inputFactors,
    required this.predictedAt,
  });

  factory Prediction.fromJson(Map<String, dynamic> json) {
    return Prediction(
      id: json['id'] ?? '',
      animalId: json['animal_id'] ?? '',
      diseaseProbability: (json['disease_probability'] ?? 0.0).toDouble(),
      riskLevel: json['risk_level'] ?? 'Low',
      healthScore: (json['health_score'] ?? 100.0).toDouble(),
      explanation: json['explanation'] ?? '',
      recommendedAction: json['recommended_action'] ?? '',
      confidence: (json['confidence'] ?? 0.0).toDouble(),
      inputFactors: json['input_factors'],
      predictedAt: json['predicted_at'] != null 
          ? DateTime.parse(json['predicted_at']) 
          : DateTime.now(),
    );
  }

  Map<String, dynamic> toJson() {
    return {
      'id': id,
      'animal_id': animalId,
      'disease_probability': diseaseProbability,
      'risk_level': riskLevel,
      'health_score': healthScore,
      'explanation': explanation,
      'recommended_action': recommendedAction,
      'confidence': confidence,
      'input_factors': inputFactors,
      'predicted_at': predictedAt.toIso8601String(),
    };
  }
}

class FarmSummary {
  final String farmId;
  final double overallHealthScore;
  final int highRiskCount;
  final int mediumRiskCount;
  final int lowRiskCount;
  final double outbreakProbability;
  final String feedQualityStatus;
  final int vaccinationOverdueCount;
  final List<String> aiRecommendations;
  final DateTime generatedAt;

  FarmSummary({
    required this.farmId,
    required this.overallHealthScore,
    required this.highRiskCount,
    required this.mediumRiskCount,
    required this.lowRiskCount,
    required this.outbreakProbability,
    required this.feedQualityStatus,
    required this.vaccinationOverdueCount,
    required this.aiRecommendations,
    required this.generatedAt,
  });

  factory FarmSummary.fromJson(Map<String, dynamic> json) {
    return FarmSummary(
      farmId: json['farm_id'] ?? '',
      overallHealthScore: (json['overall_health_score'] ?? 0.0).toDouble(),
      highRiskCount: json['high_risk_count'] ?? 0,
      mediumRiskCount: json['medium_risk_count'] ?? 0,
      lowRiskCount: json['low_risk_count'] ?? 0,
      outbreakProbability: (json['outbreak_probability'] ?? 0.0).toDouble(),
      feedQualityStatus: json['feed_quality_status'] ?? 'Good',
      vaccinationOverdueCount: json['vaccination_overdue_count'] ?? 0,
      aiRecommendations: json['ai_recommendations'] != null
          ? List<String>.from(json['ai_recommendations'])
          : [],
      generatedAt: json['generated_at'] != null 
          ? DateTime.parse(json['generated_at']) 
          : DateTime.now(),
    );
  }
}
