import 'package:flutter/material.dart';
import 'package:image_picker/image_picker.dart';
import 'dart:io';
import '../services/api_service.dart';

class AddAnimalScreen extends StatefulWidget {
  final String farmId;

  const AddAnimalScreen({super.key, required this.farmId});

  @override
  State<AddAnimalScreen> createState() => _AddAnimalScreenState();
}

class _AddAnimalScreenState extends State<AddAnimalScreen> {
  final _formKey = GlobalKey<FormState>();
  final _nameController = TextEditingController();
  final _breedController = TextEditingController();
  final _tagIdController = TextEditingController();
  final _medicationController = TextEditingController();
  
  String _vaccinationStatus = 'Up to date';
  String _feedQuality = 'Good';
  File? _imageFile;
  bool _isLoading = false;

  @override
  void dispose() {
    _nameController.dispose();
    _breedController.dispose();
    _tagIdController.dispose();
    _medicationController.dispose();
    super.dispose();
  }

  Future<void> _pickImage() async {
    final picker = ImagePicker();
    final pickedFile = await picker.pickImage(source: ImageSource.camera);
    
    if (pickedFile != null) {
      setState(() => _imageFile = File(pickedFile.path));
    }
  }

  Future<void> _handleSubmit() async {
    if (!_formKey.currentState!.validate()) return;

    setState(() => _isLoading = true);

    final result = await ApiService.createAnimal(
      farmId: widget.farmId,
      animalName: _nameController.text.trim(),
      breed: _breedController.text.trim().isEmpty ? null : _breedController.text.trim(),
      tagId: _tagIdController.text.trim().isEmpty ? null : _tagIdController.text.trim(),
      vaccinationStatus: _vaccinationStatus,
      feedQuality: _feedQuality,
      medicationHistory: _medicationController.text.trim().isEmpty 
          ? null 
          : _medicationController.text.trim(),
      imageFile: _imageFile,
    );

    setState(() => _isLoading = false);

    if (result['success'] && mounted) {
      Navigator.of(context).pop();
      ScaffoldMessenger.of(context).showSnackBar(
        const SnackBar(content: Text('Animal added successfully')),
      );
    } else if (mounted) {
      ScaffoldMessenger.of(context).showSnackBar(
        SnackBar(
          content: Text(result['error'] ?? 'Failed to add animal'),
          backgroundColor: Colors.red,
        ),
      );
    }
  }

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      appBar: AppBar(title: const Text('Add Animal')),
      body: SingleChildScrollView(
        padding: const EdgeInsets.all(24.0),
        child: Form(
          key: _formKey,
          child: Column(
            crossAxisAlignment: CrossAxisAlignment.stretch,
            children: [
              // Image Picker
              GestureDetector(
                onTap: _pickImage,
                child: Container(
                  height: 200,
                  decoration: BoxDecoration(
                    color: Colors.grey.shade200,
                    borderRadius: BorderRadius.circular(12),
                  ),
                  child: _imageFile != null
                      ? ClipRRect(
                          borderRadius: BorderRadius.circular(12),
                          child: Image.file(_imageFile!, fit: BoxFit.cover),
                        )
                      : Column(
                          mainAxisAlignment: MainAxisAlignment.center,
                          children: [
                            Icon(Icons.camera_alt, size: 48, color: Colors.grey),
                            const SizedBox(height: 8),
                            Text('Tap to add photo', style: TextStyle(color: Colors.grey)),
                          ],
                        ),
                ),
              ),
              const SizedBox(height: 24),
              TextFormField(
                controller: _nameController,
                decoration: const InputDecoration(
                  labelText: 'Animal Name *',
                  prefixIcon: Icon(Icons.pets),
                ),
                validator: (v) => v?.isEmpty ?? true ? 'Required' : null,
              ),
              const SizedBox(height: 16),
              TextFormField(
                controller: _breedController,
                decoration: const InputDecoration(
                  labelText: 'Breed',
                  prefixIcon: Icon(Icons.category),
                ),
              ),
              const SizedBox(height: 16),
              TextFormField(
                controller: _tagIdController,
                decoration: const InputDecoration(
                  labelText: 'Tag ID',
                  prefixIcon: Icon(Icons.tag),
                ),
              ),
              const SizedBox(height: 16),
              DropdownButtonFormField<String>(
                value: _vaccinationStatus,
                decoration: const InputDecoration(
                  labelText: 'Vaccination Status',
                  prefixIcon: Icon(Icons.vaccines),
                ),
                items: ['Up to date', 'Overdue', 'Not vaccinated']
                    .map((s) => DropdownMenuItem(value: s, child: Text(s)))
                    .toList(),
                onChanged: (v) => setState(() => _vaccinationStatus = v!),
              ),
              const SizedBox(height: 16),
              DropdownButtonFormField<String>(
                value: _feedQuality,
                decoration: const InputDecoration(
                  labelText: 'Feed Quality',
                  prefixIcon: Icon(Icons.grass),
                ),
                items: ['Good', 'Average', 'Poor']
                    .map((s) => DropdownMenuItem(value: s, child: Text(s)))
                    .toList(),
                onChanged: (v) => setState(() => _feedQuality = v!),
              ),
              const SizedBox(height: 16),
              TextFormField(
                controller: _medicationController,
                maxLines: 3,
                decoration: const InputDecoration(
                  labelText: 'Medication History',
                  prefixIcon: Icon(Icons.medication),
                ),
              ),
              const SizedBox(height: 32),
              SizedBox(
                height: 50,
                child: ElevatedButton(
                  onPressed: _isLoading ? null : _handleSubmit,
                  child: _isLoading
                      ? const CircularProgressIndicator(color: Colors.white)
                      : const Text('Add Animal'),
                ),
              ),
            ],
          ),
        ),
      ),
    );
  }
}
