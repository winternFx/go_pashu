import 'package:flutter/material.dart';
import '../services/api_service.dart';
import '../models/animal.dart';
import '../models/prediction.dart';
import '../utils/app_theme.dart';

class AnimalDetailScreen extends StatefulWidget {
  final String animalId;
  const AnimalDetailScreen({super.key, required this.animalId});

  @override
  State<AnimalDetailScreen> createState() => _AnimalDetailScreenState();
}

class _AnimalDetailScreenState extends State<AnimalDetailScreen> {
  Animal? _animal;
  List<Prediction> _predictions = [];
  bool _isLoading = true;

  @override
  void initState() {
    super.initState();
    _loadData();
  }

  Future<void> _loadData() async {
    setState(() => _isLoading = true);
    
    final animalResult = await ApiService.getAnimal(widget.animalId);
    final predictionsResult = await ApiService.getPredictionHistory(widget.animalId);

    if (mounted) {
      setState(() {
        if (animalResult['success']) _animal = animalResult['animal'];
        if (predictionsResult['success']) _predictions = predictionsResult['predictions'];
        _isLoading = false;
      });
    }
  }

  Future<void> _runPrediction() async {
    if (_animal == null) return;

    setState(() => _isLoading = true);
    
    final result = await ApiService.runPrediction(
      animalId: widget.animalId,
      symptoms: _animal!.symptoms,
      vaccinationStatus: _animal!.vaccinationStatus,
      feedQuality: _animal!.feedQuality,
      breed: _animal!.breed,
    );

    if (mounted) {
      if (result['success']) {
        ScaffoldMessenger.of(context).showSnackBar(
          const SnackBar(content: Text('Prediction completed')),
        );
        _loadData();
      } else {
        ScaffoldMessenger.of(context).showSnackBar(
          SnackBar(
            content: Text(result['error'] ?? 'Prediction failed'),
            backgroundColor: Colors.red,
          ),
        );
        setState(() => _isLoading = false);
      }
    }
  }

  @override
  Widget build(BuildContext context) {
    if (_isLoading || _animal == null) {
      return Scaffold(
        appBar: AppBar(title: const Text('Animal Details')),
        body: const Center(child: CircularProgressIndicator()),
      );
    }

    return Scaffold(
      appBar: AppBar(
        title: Text(_animal!.animalName),
        actions: [
          IconButton(icon: const Icon(Icons.refresh), onPressed: _loadData),
        ],
      ),
      body: ListView(
        padding: const EdgeInsets.all(16),
        children: [
          _buildInfoCard(),
          const SizedBox(height: 16),
          _buildHealthCard(),
          const SizedBox(height: 16),
          _buildPredictionsCard(),
        ],
      ),
    );
  }

  Widget _buildInfoCard() {
    return Card(
      child: Padding(
        padding: const EdgeInsets.all(16),
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            Text('Information', style: Theme.of(context).textTheme.titleLarge?.copyWith(fontWeight: FontWeight.bold)),
            const Divider(height: 24),
            _buildInfoRow('Name', _animal!.animalName),
            _buildInfoRow('Breed', _animal!.breed ?? 'Not specified'),
            _buildInfoRow('Tag ID', _animal!.tagId ?? 'Not specified'),
            _buildInfoRow('Vaccination', _animal!.vaccinationStatus),
            _buildInfoRow('Feed Quality', _animal!.feedQuality),
          ],
        ),
      ),
    );
  }

  Widget _buildHealthCard() {
    return Card(
      child: Padding(
        padding: const EdgeInsets.all(16),
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            Text('Health Status', style: Theme.of(context).textTheme.titleLarge?.copyWith(fontWeight: FontWeight.bold)),
            const Divider(height: 24),
            Row(
              children: [
                Expanded(
                  child: _buildStatBox('Health Score', '${_animal!.healthScore.toInt()}%', Colors.blue),
                ),
                const SizedBox(width: 12),
                Expanded(
                  child: _buildStatBox('Risk Level', _animal!.riskLevel, AppTheme.getRiskColor(_animal!.riskLevel)),
                ),
              ],
            ),
            if (_animal!.symptoms.isNotEmpty) ...[
              const SizedBox(height: 16),
              Text('Symptoms:', style: const TextStyle(fontWeight: FontWeight.bold)),
              const SizedBox(height: 8),
              Wrap(
                spacing: 8,
                runSpacing: 8,
                children: _animal!.symptoms.map((s) => Chip(label: Text(s))).toList(),
              ),
            ],
            const SizedBox(height: 16),
            SizedBox(
              width: double.infinity,
              child: ElevatedButton.icon(
                onPressed: _runPrediction,
                icon: const Icon(Icons.psychology),
                label: const Text('Run AI Prediction'),
              ),
            ),
          ],
        ),
      ),
    );
  }

  Widget _buildPredictionsCard() {
    return Card(
      child: Padding(
        padding: const EdgeInsets.all(16),
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            Text('Prediction History', style: Theme.of(context).textTheme.titleLarge?.copyWith(fontWeight: FontWeight.bold)),
            const Divider(height: 24),
            if (_predictions.isEmpty)
              const Text('No predictions yet')
            else
              ..._predictions.take(3).map((p) => ListTile(
                    leading: Icon(AppTheme.getRiskIcon(p.riskLevel), color: AppTheme.getRiskColor(p.riskLevel)),
                    title: Text(p.riskLevel),
                    subtitle: Text('${(p.diseaseProbability * 100).toInt()}% risk'),
                    trailing: Text(
                      '${p.predictedAt.day}/${p.predictedAt.month}',
                      style: const TextStyle(color: Colors.grey, fontSize: 12),
                    ),
                  )),
          ],
        ),
      ),
    );
  }

  Widget _buildInfoRow(String label, String value) {
    return Padding(
      padding: const EdgeInsets.symmetric(vertical: 8),
      child: Row(
        mainAxisAlignment: MainAxisAlignment.spaceBetween,
        children: [
          Text(label, style: const TextStyle(color: Colors.grey)),
          Text(value, style: const TextStyle(fontWeight: FontWeight.w600)),
        ],
      ),
    );
  }

  Widget _buildStatBox(String label, String value, Color color) {
    return Container(
      padding: const EdgeInsets.all(16),
      decoration: BoxDecoration(
        color: color.withOpacity(0.1),
        borderRadius: BorderRadius.circular(12),
      ),
      child: Column(
        children: [
          Text(label, style: TextStyle(color: Colors.grey.shade700, fontSize: 12)),
          const SizedBox(height: 4),
          Text(value, style: TextStyle(color: color, fontSize: 20, fontWeight: FontWeight.bold)),
        ],
      ),
    );
  }
}
