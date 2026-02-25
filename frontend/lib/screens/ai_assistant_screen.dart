import 'dart:io';

import 'package:flutter/material.dart';
import 'package:image_picker/image_picker.dart';
import 'package:file_picker/file_picker.dart';
import 'package:provider/provider.dart';

import '../services/api_service.dart';
import '../services/app_state.dart';
import '../models/animal.dart';

class AIAssistantScreen extends StatefulWidget {
  const AIAssistantScreen({super.key});

  @override
  State<AIAssistantScreen> createState() => _AIAssistantScreenState();
}

class _AIAssistantScreenState extends State<AIAssistantScreen> {
  final ImagePicker _imagePicker = ImagePicker();
  bool _isProcessing = false;
  Animal? _selectedAnimal;

  @override
  void initState() {
    super.initState();
    WidgetsBinding.instance.addPostFrameCallback((_) {
      context.read<AppState>().loadAnimals();
    });
  }

  Future<void> _pickDiseaseImageAndDetect() async {
    if (_selectedAnimal == null) {
      ScaffoldMessenger.of(context).showSnackBar(
        const SnackBar(content: Text('Please select a cow first')),
      );
      return;
    }

    final pickedFile = await _imagePicker.pickImage(source: ImageSource.camera);
    if (pickedFile == null) return;

    setState(() => _isProcessing = true);

    final result = await ApiService.detectDiseaseFromImage(
      imageFile: File(pickedFile.path),
      animalId: _selectedAnimal!.id,
    );

    setState(() => _isProcessing = false);

    if (!mounted) return;

    if (result['success']) {
      final data = result['result'] as Map<String, dynamic>;
      final hasDisease = data['has_disease'] == true;
      final probability = (data['probability'] ?? 0.0) * 100;
      final message = data['message'] ?? '';

      showDialog(
        context: context,
        builder: (_) => AlertDialog(
          title: Text(hasDisease ? 'Foot & Mouth Detected' : 'No Strong FMD Signs'),
          content: Text(
            'Confidence: ${probability.toStringAsFixed(1)}%\n\n$message',
          ),
          actions: [
            TextButton(
              onPressed: () => Navigator.of(context).pop(),
              child: const Text('OK'),
            ),
          ],
        ),
      );
    } else {
      ScaffoldMessenger.of(context).showSnackBar(
        SnackBar(
          content: Text(result['error'] ?? 'Disease detection failed'),
          backgroundColor: Colors.red,
        ),
      );
    }
  }

  Future<void> _pickImageAndIdentifyCow() async {
    final pickedFile = await _imagePicker.pickImage(source: ImageSource.camera);
    if (pickedFile == null) return;

    setState(() => _isProcessing = true);

    final result = await ApiService.identifyCowFromImage(
      imageFile: File(pickedFile.path),
    );

    setState(() => _isProcessing = false);

    if (!mounted) return;

    if (result['success']) {
      final data = result['result'] as Map<String, dynamic>;
      final matchFound = data['match_found'] == true;
      final similarity = (data['similarity'] ?? 0.0) * 100;
      final message = data['message'] ?? '';
      final animal = data['animal'] as Map<String, dynamic>?;
      final name = animal != null ? (animal['animal_name'] ?? 'Unknown') : 'Unknown';

      showDialog(
        context: context,
        builder: (_) => AlertDialog(
          title: Text(matchFound ? 'Cow Identified' : 'No Confident Match'),
          content: Text(
            'Match: $name\nSimilarity: ${similarity.toStringAsFixed(1)}%\n\n$message',
          ),
          actions: [
            TextButton(
              onPressed: () => Navigator.of(context).pop(),
              child: const Text('OK'),
            ),
          ],
        ),
      );
    } else {
      ScaffoldMessenger.of(context).showSnackBar(
        SnackBar(
          content: Text(result['error'] ?? 'Face identification failed'),
          backgroundColor: Colors.red,
        ),
      );
    }
  }

  Future<void> _pickAudioAndIdentifyCow() async {
    final picked = await FilePicker.platform.pickFiles(
      type: FileType.custom,
      allowedExtensions: ['wav', 'mp3', 'm4a'],
    );
    if (picked == null || picked.files.single.path == null) return;

    final file = File(picked.files.single.path!);

    setState(() => _isProcessing = true);

    final result = await ApiService.identifyCowFromVoice(audioFile: file);

    setState(() => _isProcessing = false);

    if (!mounted) return;

    if (result['success']) {
      final data = result['result'] as Map<String, dynamic>;
      final matchFound = data['match_found'] == true;
      final similarity = (data['similarity'] ?? 0.0) * 100;
      final message = data['message'] ?? '';
      final animal = data['animal'] as Map<String, dynamic>?;
      final name = animal != null ? (animal['animal_name'] ?? 'Unknown') : 'Unknown';

      showDialog(
        context: context,
        builder: (_) => AlertDialog(
          title: Text(matchFound ? 'Cow Identified by Voice' : 'No Confident Voice Match'),
          content: Text(
            'Match: $name\nSimilarity: ${similarity.toStringAsFixed(1)}%\n\n$message',
          ),
          actions: [
            TextButton(
              onPressed: () => Navigator.of(context).pop(),
              child: const Text('OK'),
            ),
          ],
        ),
      );
    } else {
      ScaffoldMessenger.of(context).showSnackBar(
        SnackBar(
          content: Text(result['error'] ?? 'Voice identification failed'),
          backgroundColor: Colors.red,
        ),
      );
    }
  }

  @override
  Widget build(BuildContext context) {
    final appState = context.watch<AppState>();
    final animals = appState.animals;

    return Scaffold(
      appBar: AppBar(title: const Text('AI Assistant')),
      body: Padding(
        padding: const EdgeInsets.all(16.0),
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.stretch,
          children: [
            Row(
              children: [
                Icon(Icons.psychology,
                    size: 40, color: Theme.of(context).colorScheme.primary),
                const SizedBox(width: 12),
                Expanded(
                  child: Text(
                    'Use AI to detect diseases and identify your cows by face or voice.',
                    style: Theme.of(context).textTheme.bodyMedium,
                  ),
                ),
              ],
            ),
            const SizedBox(height: 16),
            if (animals.isNotEmpty) ...[
              DropdownButtonFormField<Animal>(
                value: _selectedAnimal,
                decoration: const InputDecoration(
                  labelText: 'Select Cow (for disease scan)',
                  prefixIcon: Icon(Icons.pets),
                ),
                items: animals
                    .map(
                      (a) => DropdownMenuItem(
                        value: a,
                        child: Text(a.animalName),
                      ),
                    )
                    .toList(),
                onChanged: (value) => setState(() => _selectedAnimal = value),
              ),
              const SizedBox(height: 16),
            ] else ...[
              const Text(
                'Add some animals first to get the best AI experience.',
                style: TextStyle(color: Colors.grey),
              ),
              const SizedBox(height: 16),
            ],
            Expanded(
              child: ListView(
                children: [
                  _buildActionCard(
                    icon: Icons.coronavirus,
                    title: 'Foot & Mouth Disease Scan',
                    description:
                        'Use the camera to scan a cow and estimate the probability of Foot and Mouth Disease.',
                    onPressed: _isProcessing ? null : _pickDiseaseImageAndDetect,
                  ),
                  _buildActionCard(
                    icon: Icons.face_retouching_natural,
                    title: 'Identify Cow by Face',
                    description:
                        'Capture a face image and match it to your registered cows.',
                    onPressed: _isProcessing ? null : _pickImageAndIdentifyCow,
                  ),
                  _buildActionCard(
                    icon: Icons.graphic_eq,
                    title: 'Identify Cow by Voice',
                    description:
                        'Pick or record a cow sound and match it against stored voice samples.',
                    onPressed: _isProcessing ? null : _pickAudioAndIdentifyCow,
                  ),
                ],
              ),
            ),
            if (_isProcessing)
              const LinearProgressIndicator(),
          ],
        ),
      ),
    );
  }

  Widget _buildActionCard({
    required IconData icon,
    required String title,
    required String description,
    required VoidCallback? onPressed,
  }) {
    return Card(
      margin: const EdgeInsets.only(bottom: 12),
      child: Padding(
        padding: const EdgeInsets.all(16),
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            Row(
              children: [
                Icon(icon, color: Theme.of(context).colorScheme.primary),
                const SizedBox(width: 8),
                Expanded(
                  child: Text(
                    title,
                    style: Theme.of(context)
                        .textTheme
                        .titleMedium
                        ?.copyWith(fontWeight: FontWeight.bold),
                  ),
                ),
              ],
            ),
            const SizedBox(height: 8),
            Text(
              description,
              style: const TextStyle(color: Colors.grey),
            ),
            const SizedBox(height: 12),
            Align(
              alignment: Alignment.centerRight,
              child: ElevatedButton(
                onPressed: onPressed,
                child: const Text('Start'),
              ),
            ),
          ],
        ),
      ),
    );
  }
}
