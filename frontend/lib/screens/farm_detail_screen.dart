import 'package:flutter/material.dart';
import '../services/api_service.dart';
import '../models/farm.dart';
import '../models/animal.dart';
import '../models/prediction.dart';
import '../utils/app_theme.dart';
import 'add_animal_screen.dart';
import 'animal_detail_screen.dart';

class FarmDetailScreen extends StatefulWidget {
  final String farmId;

  const FarmDetailScreen({super.key, required this.farmId});

  @override
  State<FarmDetailScreen> createState() => _FarmDetailScreenState();
}

class _FarmDetailScreenState extends State<FarmDetailScreen> {
  Farm? _farm;
  List<Animal> _animals = [];
  FarmSummary? _summary;
  bool _isLoading = true;

  @override
  void initState() {
    super.initState();
    _loadData();
  }

  Future<void> _loadData() async {
    setState(() => _isLoading = true);
    
    final farmResult = await ApiService.getFarm(widget.farmId);
    final animalsResult = await ApiService.getAnimals(farmId: widget.farmId);
    final summaryResult = await ApiService.getFarmSummary(widget.farmId);

    if (mounted) {
      setState(() {
        if (farmResult['success']) _farm = farmResult['farm'];
        if (animalsResult['success']) _animals = animalsResult['animals'];
        if (summaryResult['success']) _summary = summaryResult['summary'];
        _isLoading = false;
      });
    }
  }

  @override
  Widget build(BuildContext context) {
    if (_isLoading) {
      return Scaffold(
        appBar: AppBar(title: const Text('Farm Details')),
        body: const Center(child: CircularProgressIndicator()),
      );
    }

    if (_farm == null) {
      return Scaffold(
        appBar: AppBar(title: const Text('Farm Details')),
        body: const Center(child: Text('Farm not found')),
      );
    }

    return Scaffold(
      appBar: AppBar(
        title: Text(_farm!.farmName),
        actions: [
          IconButton(
            icon: const Icon(Icons.refresh),
            onPressed: _loadData,
          ),
        ],
      ),
      body: RefreshIndicator(
        onRefresh: _loadData,
        child: ListView(
          padding: const EdgeInsets.all(16),
          children: [
            _buildSummaryCard(),
            const SizedBox(height: 16),
            _buildRecommendationsCard(),
            const SizedBox(height: 16),
            _buildAnimalsSection(),
          ],
        ),
      ),
      floatingActionButton: FloatingActionButton(
        onPressed: () {
          Navigator.of(context).push(
            MaterialPageRoute(
              builder: (_) => AddAnimalScreen(farmId: widget.farmId),
            ),
          ).then((_) => _loadData());
        },
        child: const Icon(Icons.add),
      ),
    );
  }

  Widget _buildSummaryCard() {
    return Card(
      child: Padding(
        padding: const EdgeInsets.all(16),
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            Text(
              'Farm Overview',
              style: Theme.of(context).textTheme.titleLarge?.copyWith(
                    fontWeight: FontWeight.bold,
                  ),
            ),
            const Divider(height: 24),
            _buildStatRow('Total Animals', _farm!.totalAnimals.toString()),
            _buildStatRow('Health Score', '${_farm!.healthScore.toInt()}%'),
            _buildStatRow('Risk Level', _farm!.riskLevel, 
                color: AppTheme.getRiskColor(_farm!.riskLevel)),
            if (_summary != null) ...[
              _buildStatRow('Outbreak Probability', 
                  '${_summary!.outbreakProbability.toInt()}%'),
              _buildStatRow('High Risk Animals', 
                  _summary!.highRiskCount.toString()),
            ],
          ],
        ),
      ),
    );
  }

  Widget _buildStatRow(String label, String value, {Color? color}) {
    return Padding(
      padding: const EdgeInsets.symmetric(vertical: 8),
      child: Row(
        mainAxisAlignment: MainAxisAlignment.spaceBetween,
        children: [
          Text(label, style: const TextStyle(color: Colors.grey)),
          Text(
            value,
            style: TextStyle(
              fontWeight: FontWeight.bold,
              fontSize: 16,
              color: color,
            ),
          ),
        ],
      ),
    );
  }

  Widget _buildRecommendationsCard() {
    if (_summary == null || _summary!.aiRecommendations.isEmpty) {
      return const SizedBox.shrink();
    }

    return Card(
      child: Padding(
        padding: const EdgeInsets.all(16),
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            Row(
              children: [
                const Icon(Icons.psychology, color: Colors.orange),
                const SizedBox(width: 8),
                Text(
                  'AI Recommendations',
                  style: Theme.of(context).textTheme.titleLarge?.copyWith(
                        fontWeight: FontWeight.bold,
                      ),
                ),
              ],
            ),
            const Divider(height: 24),
            ..._summary!.aiRecommendations.map((rec) => Padding(
                  padding: const EdgeInsets.only(bottom: 12),
                  child: Row(
                    crossAxisAlignment: CrossAxisAlignment.start,
                    children: [
                      const Icon(Icons.arrow_right, size: 20),
                      const SizedBox(width: 8),
                      Expanded(child: Text(rec)),
                    ],
                  ),
                )),
          ],
        ),
      ),
    );
  }

  Widget _buildAnimalsSection() {
    return Column(
      crossAxisAlignment: CrossAxisAlignment.start,
      children: [
        Text(
          'Animals (${_animals.length})',
          style: Theme.of(context).textTheme.titleLarge?.copyWith(
                fontWeight: FontWeight.bold,
              ),
        ),
        const SizedBox(height: 12),
        if (_animals.isEmpty)
          Card(
            child: Padding(
              padding: const EdgeInsets.all(32),
              child: Center(
                child: Column(
                  children: [
                    Icon(Icons.pets, size: 48, color: Colors.grey.shade300),
                    const SizedBox(height: 8),
                    Text('No animals yet', style: TextStyle(color: Colors.grey)),
                  ],
                ),
              ),
            ),
          )
        else
          ..._animals.map((animal) => Card(
                margin: const EdgeInsets.only(bottom: 12),
                child: ListTile(
                  leading: CircleAvatar(
                    backgroundColor: AppTheme.getRiskColor(animal.riskLevel)
                        .withOpacity(0.2),
                    child: Icon(
                      Icons.pets,
                      color: AppTheme.getRiskColor(animal.riskLevel),
                    ),
                  ),
                  title: Text(animal.animalName),
                  subtitle: Text(animal.breed ?? 'No breed specified'),
                  trailing: Container(
                    padding: const EdgeInsets.symmetric(horizontal: 8, vertical: 4),
                    decoration: BoxDecoration(
                      color: AppTheme.getRiskColor(animal.riskLevel)
                          .withOpacity(0.1),
                      borderRadius: BorderRadius.circular(12),
                    ),
                    child: Text(
                      animal.riskLevel,
                      style: TextStyle(
                        color: AppTheme.getRiskColor(animal.riskLevel),
                        fontWeight: FontWeight.bold,
                        fontSize: 12,
                      ),
                    ),
                  ),
                  onTap: () {
                    Navigator.of(context).push(
                      MaterialPageRoute(
                        builder: (_) => AnimalDetailScreen(animalId: animal.id),
                      ),
                    ).then((_) => _loadData());
                  },
                ),
              )),
      ],
    );
  }
}
