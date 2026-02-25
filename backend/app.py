#!/usr/bin/env python3
"""
GoPashu Flask Backend
Complete livestock management system with PostgreSQL
"""

import os
import json
from datetime import datetime
from flask import Flask, request, jsonify, send_from_directory
from flask_cors import CORS
from werkzeug.utils import secure_filename
from dotenv import load_dotenv

from database import init_db_pool, execute_query, close_db_pool
from auth import hash_password, verify_password, generate_token, token_required

try:
    from ml_models import (
        predict_foot_mouth_disease,
        identify_cow_by_face,
        identify_cow_by_voice,
    )
except ImportError:
    predict_foot_mouth_disease = None
    identify_cow_by_face = None
    identify_cow_by_voice = None

load_dotenv()

# Initialize Flask app
app = Flask(__name__)
app.config['SECRET_KEY'] = os.getenv('JWT_SECRET_KEY', 'change-this-secret')
app.config['UPLOAD_FOLDER'] = os.getenv('UPLOAD_FOLDER', 'uploads')
app.config['MAX_CONTENT_LENGTH'] = int(os.getenv('MAX_FILE_SIZE', 5242880))

# Enable CORS
CORS(app)

# Create upload folder
os.makedirs(app.config['UPLOAD_FOLDER'], exist_ok=True)

# Allowed file extensions
ALLOWED_EXTENSIONS = {'png', 'jpg', 'jpeg', 'gif', 'mp3', 'wav', 'm4a'}

def allowed_file(filename):
    """Check if file extension is allowed"""
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS

# ============================================
# HELPER FUNCTIONS
# ============================================

def get_user_stats(user_id):
    """Get user statistics"""
    farms = execute_query(
        'SELECT COUNT(*) as total_farms FROM farms WHERE user_id = %s',
        (user_id,),
        fetch_one=True
    )
    
    animals = execute_query(
        """SELECT COUNT(*) as total_animals, 
                  COUNT(CASE WHEN risk_level = 'High' THEN 1 END) as high_risk_animals
           FROM animals 
           WHERE farm_id IN (SELECT id FROM farms WHERE user_id = %s)""",
        (user_id,),
        fetch_one=True
    )
    
    return {
        'total_farms': int(farms['total_farms'] or 0),
        'total_animals': int(animals['total_animals'] or 0),
        'high_risk_animals': int(animals['high_risk_animals'] or 0)
    }

def update_farm_stats(farm_id):
    """Update farm statistics after animal changes"""
    stats = execute_query(
        """SELECT 
            COUNT(*) as total_animals,
            AVG(health_score) as avg_health_score,
            COUNT(CASE WHEN risk_level = 'High' THEN 1 END) as high_risk_count
           FROM animals WHERE farm_id = %s""",
        (farm_id,),
        fetch_one=True
    )
    
    total = int(stats['total_animals'] or 0)
    avg_health = float(stats['avg_health_score'] or 100.0)
    high_risk = int(stats['high_risk_count'] or 0)
    
    risk_level = 'Low'
    if total > 0 and high_risk > 0:
        risk_percentage = (high_risk / total) * 100
        if risk_percentage >= 30:
            risk_level = 'High'
        elif risk_percentage >= 10:
            risk_level = 'Medium'
    
    execute_query(
        """UPDATE farms 
           SET total_animals = %s, health_score = %s, risk_level = %s
           WHERE id = %s""",
        (total, avg_health, risk_level, farm_id)
    )

def calculate_health_prediction(animal_data):
    """Calculate AI health prediction"""
    risk_score = 0
    factors = []
    
    # Vaccination status (0-30 points)
    vaccination = animal_data.get('vaccination_status', 'Up to date')
    if vaccination == 'Overdue':
        risk_score += 30
        factors.append('Vaccination overdue increases disease risk')
    elif vaccination == 'Partial':
        risk_score += 15
        factors.append('Incomplete vaccination coverage')
    else:
        factors.append('Vaccination status is up to date')
    
    # Feed quality (0-25 points)
    feed = animal_data.get('feed_quality', 'Good')
    if feed == 'Poor':
        risk_score += 25
        factors.append('Poor feed quality weakens immune system')
    elif feed == 'Fair':
        risk_score += 12
        factors.append('Fair feed quality may affect health')
    else:
        factors.append('Good feed quality supports health')
    
    # Symptoms (0-45 points)
    symptoms = animal_data.get('symptoms', [])
    symptom_count = len(symptoms)
    if symptom_count >= 5:
        risk_score += 45
        factors.append(f'Multiple symptoms detected ({symptom_count})')
    elif symptom_count >= 3:
        risk_score += 30
        factors.append(f'Several symptoms present ({symptom_count})')
    elif symptom_count >= 1:
        risk_score += 15
        factors.append(f'Some symptoms noted ({symptom_count})')
    else:
        factors.append('No symptoms reported')
    
    # Cap risk score
    risk_score = min(risk_score, 100)
    health_score = max(0, 100 - risk_score)
    
    # Determine risk level
    if risk_score >= 60:
        risk_level = 'High'
    elif risk_score >= 30:
        risk_level = 'Medium'
    else:
        risk_level = 'Low'
    
    # Generate explanation
    explanation = f"Based on analysis of {len(factors)} health factors, "
    if risk_level == 'High':
        explanation += "this animal requires immediate veterinary attention."
    elif risk_level == 'Medium':
        explanation += "this animal shows moderate risk factors that should be monitored."
    else:
        explanation += "this animal appears healthy with minimal risk factors."
    
    # Generate recommendations
    if risk_level == 'High':
        action = "URGENT: Contact veterinarian immediately. "
        if vaccination == 'Overdue':
            action += "Update vaccinations as priority. "
        if symptom_count > 0:
            action += "Address all symptoms promptly. "
        if feed == 'Poor':
            action += "Improve feed quality urgently."
    elif risk_level == 'Medium':
        action = "Schedule veterinary check-up within 48 hours. "
        if vaccination != 'Up to date':
            action += "Update vaccination schedule. "
        if feed != 'Good':
            action += "Improve feed quality. "
        action += "Monitor symptoms closely."
    else:
        action = "Continue regular monitoring and care. "
        action += "Maintain good nutrition and vaccination schedule. "
        action += "Schedule routine check-up as per normal schedule."
    
    # Calculate confidence
    confidence = 70.0
    if vaccination:
        confidence += 10
    if feed:
        confidence += 10
    if symptom_count > 0:
        confidence += 10
    confidence = min(confidence, 100)
    
    return {
        'disease_probability': risk_score,
        'risk_level': risk_level,
        'health_score': health_score,
        'explanation': explanation,
        'recommended_action': action,
        'confidence': confidence,
        'input_factors': {
            'vaccination_status': vaccination,
            'feed_quality': feed,
            'symptoms_count': symptom_count,
            'symptoms': symptoms
        }
    }

# ============================================
# ROUTES
# ============================================

@app.route('/health', methods=['GET'])
def health_check():
    """Health check endpoint"""
    return jsonify({
        'status': 'OK',
        'message': 'GoPashu Backend is running',
        'timestamp': datetime.utcnow().isoformat()
    })

# ============================================
# AUTHENTICATION ROUTES
# ============================================

@app.route('/api/auth/signup', methods=['POST'])
def signup():
    """Register new user"""
    try:
        data = request.get_json()
        
        # Validate input
        if not data.get('name') or not data.get('email') or not data.get('password'):
            return jsonify({
                'success': False,
                'error': 'Name, email, and password are required'
            }), 400
        
        # Check if user exists
        existing = execute_query(
            'SELECT id FROM users WHERE email = %s',
            (data['email'].lower(),),
            fetch_one=True
        )
        
        if existing:
            return jsonify({
                'success': False,
                'error': 'Email already registered'
            }), 400
        
        # Hash password
        hashed_pw = hash_password(data['password'])
        
        # Create user
        user = execute_query(
            """INSERT INTO users (name, email, password, phone, location)
               VALUES (%s, %s, %s, %s, %s)
               RETURNING id, name, email, phone, location, created_at""",
            (data['name'], data['email'].lower(), hashed_pw, 
             data.get('phone'), data.get('location')),
            fetch_one=True
        )
        
        # Generate token
        token = generate_token(user['id'], user['email'])
        
        # Get stats
        stats = get_user_stats(user['id'])
        
        return jsonify({
            'success': True,
            'token': token,
            'user': {
                'id': user['id'],
                'name': user['name'],
                'email': user['email'],
                'phone': user['phone'],
                'location': user['location'],
                'created_at': user['created_at'].isoformat(),
                **stats
            }
        }), 201
        
    except Exception as e:
        print(f"Signup error: {e}")
        return jsonify({
            'success': False,
            'error': 'Server error during signup'
        }), 500

@app.route('/api/auth/login', methods=['POST'])
def login():
    """User login"""
    try:
        data = request.get_json()
        
        # Validate input
        if not data.get('email') or not data.get('password'):
            return jsonify({
                'success': False,
                'error': 'Email and password are required'
            }), 400
        
        # Find user
        user = execute_query(
            'SELECT * FROM users WHERE email = %s',
            (data['email'].lower(),),
            fetch_one=True
        )
        
        if not user:
            return jsonify({
                'success': False,
                'error': 'Invalid email or password'
            }), 401
        
        # Verify password
        if not verify_password(data['password'], user['password']):
            return jsonify({
                'success': False,
                'error': 'Invalid email or password'
            }), 401
        
        # Generate token
        token = generate_token(user['id'], user['email'])
        
        # Get stats
        stats = get_user_stats(user['id'])
        
        return jsonify({
            'success': True,
            'token': token,
            'user': {
                'id': user['id'],
                'name': user['name'],
                'email': user['email'],
                'phone': user['phone'],
                'location': user['location'],
                'created_at': user['created_at'].isoformat(),
                **stats
            }
        })
        
    except Exception as e:
        print(f"Login error: {e}")
        return jsonify({
            'success': False,
            'error': 'Server error during login'
        }), 500

@app.route('/api/auth/me', methods=['GET'])
@token_required
def get_profile():
    """Get user profile"""
    try:
        user = execute_query(
            'SELECT id, name, email, phone, location, created_at FROM users WHERE id = %s',
            (request.user_id,),
            fetch_one=True
        )
        
        if not user:
            return jsonify({
                'success': False,
                'error': 'User not found'
            }), 404
        
        stats = get_user_stats(user['id'])
        
        return jsonify({
            'success': True,
            'user': {
                'id': user['id'],
                'name': user['name'],
                'email': user['email'],
                'phone': user['phone'],
                'location': user['location'],
                'created_at': user['created_at'].isoformat(),
                **stats
            }
        })
        
    except Exception as e:
        print(f"Get profile error: {e}")
        return jsonify({
            'success': False,
            'error': 'Server error'
        }), 500

@app.route('/api/auth/me', methods=['PUT'])
@token_required
def update_profile():
    """Update user profile"""
    try:
        data = request.get_json()
        
        updates = []
        values = []
        
        if 'name' in data:
            updates.append('name = %s')
            values.append(data['name'])
        if 'phone' in data:
            updates.append('phone = %s')
            values.append(data['phone'])
        if 'location' in data:
            updates.append('location = %s')
            values.append(data['location'])
        
        if not updates:
            return jsonify({
                'success': False,
                'error': 'No fields to update'
            }), 400
        
        values.append(request.user_id)
        
        user = execute_query(
            f"""UPDATE users SET {', '.join(updates)}
               WHERE id = %s
               RETURNING id, name, email, phone, location, created_at""",
            tuple(values),
            fetch_one=True
        )
        
        stats = get_user_stats(user['id'])
        
        return jsonify({
            'success': True,
            'user': {
                'id': user['id'],
                'name': user['name'],
                'email': user['email'],
                'phone': user['phone'],
                'location': user['location'],
                'created_at': user['created_at'].isoformat(),
                **stats
            }
        })
        
    except Exception as e:
        print(f"Update profile error: {e}")
        return jsonify({
            'success': False,
            'error': 'Server error'
        }), 500

@app.route('/api/auth/logout', methods=['POST'])
@token_required
def logout():
    """Logout user"""
    return jsonify({
        'success': True,
        'message': 'Logged out successfully'
    })

# ============================================
# FARM ROUTES
# ============================================

@app.route('/api/farms', methods=['GET'])
@token_required
def get_farms():
    """Get all farms for logged-in user"""
    try:
        farms = execute_query(
            """SELECT * FROM farms 
               WHERE user_id = %s 
               ORDER BY created_at DESC""",
            (request.user_id,),
            fetch=True
        )
        
        # Convert to dict list
        farms_list = []
        for farm in farms:
            farms_list.append({
                'id': farm['id'],
                'user_id': farm['user_id'],
                'farm_name': farm['farm_name'],
                'location': farm['location'],
                'total_animals': farm['total_animals'],
                'health_score': float(farm['health_score']),
                'risk_level': farm['risk_level'],
                'created_at': farm['created_at'].isoformat()
            })
        
        return jsonify({
            'success': True,
            'farms': farms_list
        })
        
    except Exception as e:
        print(f"Get farms error: {e}")
        return jsonify({
            'success': False,
            'error': 'Server error'
        }), 500

@app.route('/api/farms/<farm_id>', methods=['GET'])
@token_required
def get_farm(farm_id):
    """Get single farm details"""
    try:
        farm = execute_query(
            'SELECT * FROM farms WHERE id = %s AND user_id = %s',
            (farm_id, request.user_id),
            fetch_one=True
        )
        
        if not farm:
            return jsonify({
                'success': False,
                'error': 'Farm not found'
            }), 404
        
        return jsonify({
            'success': True,
            'farm': {
                'id': farm['id'],
                'user_id': farm['user_id'],
                'farm_name': farm['farm_name'],
                'location': farm['location'],
                'total_animals': farm['total_animals'],
                'health_score': float(farm['health_score']),
                'risk_level': farm['risk_level'],
                'created_at': farm['created_at'].isoformat()
            }
        })
        
    except Exception as e:
        print(f"Get farm error: {e}")
        return jsonify({
            'success': False,
            'error': 'Server error'
        }), 500

@app.route('/api/farms', methods=['POST'])
@token_required
def create_farm():
    """Create new farm"""
    try:
        data = request.get_json()
        
        if not data.get('farm_name'):
            return jsonify({
                'success': False,
                'error': 'Farm name is required'
            }), 400
        
        farm = execute_query(
            """INSERT INTO farms (user_id, farm_name, location)
               VALUES (%s, %s, %s)
               RETURNING *""",
            (request.user_id, data['farm_name'], data.get('location')),
            fetch_one=True
        )
        
        return jsonify({
            'success': True,
            'farm': {
                'id': farm['id'],
                'user_id': farm['user_id'],
                'farm_name': farm['farm_name'],
                'location': farm['location'],
                'total_animals': farm['total_animals'],
                'health_score': float(farm['health_score']),
                'risk_level': farm['risk_level'],
                'created_at': farm['created_at'].isoformat()
            }
        }), 201
        
    except Exception as e:
        print(f"Create farm error: {e}")
        return jsonify({
            'success': False,
            'error': 'Server error'
        }), 500

@app.route('/api/farms/<farm_id>', methods=['PUT'])
@token_required
def update_farm(farm_id):
    """Update farm"""
    try:
        # Verify ownership
        farm_check = execute_query(
            'SELECT id FROM farms WHERE id = %s AND user_id = %s',
            (farm_id, request.user_id),
            fetch_one=True
        )
        
        if not farm_check:
            return jsonify({
                'success': False,
                'error': 'Farm not found'
            }), 404
        
        data = request.get_json()
        updates = []
        values = []
        
        if 'farm_name' in data:
            updates.append('farm_name = %s')
            values.append(data['farm_name'])
        if 'location' in data:
            updates.append('location = %s')
            values.append(data['location'])
        
        if not updates:
            return jsonify({
                'success': False,
                'error': 'No fields to update'
            }), 400
        
        values.append(farm_id)
        
        farm = execute_query(
            f"""UPDATE farms SET {', '.join(updates)}
               WHERE id = %s
               RETURNING *""",
            tuple(values),
            fetch_one=True
        )
        
        return jsonify({
            'success': True,
            'farm': {
                'id': farm['id'],
                'user_id': farm['user_id'],
                'farm_name': farm['farm_name'],
                'location': farm['location'],
                'total_animals': farm['total_animals'],
                'health_score': float(farm['health_score']),
                'risk_level': farm['risk_level'],
                'created_at': farm['created_at'].isoformat()
            }
        })
        
    except Exception as e:
        print(f"Update farm error: {e}")
        return jsonify({
            'success': False,
            'error': 'Server error'
        }), 500

@app.route('/api/farms/<farm_id>', methods=['DELETE'])
@token_required
def delete_farm(farm_id):
    """Delete farm"""
    try:
        result = execute_query(
            'DELETE FROM farms WHERE id = %s AND user_id = %s RETURNING id',
            (farm_id, request.user_id),
            fetch_one=True
        )
        
        if not result:
            return jsonify({
                'success': False,
                'error': 'Farm not found'
            }), 404
        
        return jsonify({
            'success': True,
            'message': 'Farm deleted successfully'
        })
        
    except Exception as e:
        print(f"Delete farm error: {e}")
        return jsonify({
            'success': False,
            'error': 'Server error'
        }), 500

@app.route('/api/farms/<farm_id>/summary', methods=['GET'])
@token_required
def get_farm_summary(farm_id):
    """Get AI-generated farm summary"""
    try:
        # Verify ownership
        farm_check = execute_query(
            'SELECT * FROM farms WHERE id = %s AND user_id = %s',
            (farm_id, request.user_id),
            fetch_one=True
        )
        
        if not farm_check:
            return jsonify({
                'success': False,
                'error': 'Farm not found'
            }), 404
        
        # Get animal statistics
        stats = execute_query(
            """SELECT 
                COUNT(*) as total,
                COUNT(CASE WHEN risk_level = 'High' THEN 1 END) as high_risk,
                COUNT(CASE WHEN risk_level = 'Medium' THEN 1 END) as medium_risk,
                COUNT(CASE WHEN risk_level = 'Low' THEN 1 END) as low_risk,
                AVG(health_score) as avg_health,
                COUNT(CASE WHEN feed_quality = 'Poor' THEN 1 END) as poor_feed,
                COUNT(CASE WHEN vaccination_status = 'Overdue' THEN 1 END) as overdue_vaccination
               FROM animals WHERE farm_id = %s""",
            (farm_id,),
            fetch_one=True
        )
        
        total = int(stats['total'] or 0)
        high_risk = int(stats['high_risk'] or 0)
        medium_risk = int(stats['medium_risk'] or 0)
        low_risk = int(stats['low_risk'] or 0)
        avg_health = float(stats['avg_health'] or 100.0)
        
        # Calculate outbreak probability
        outbreak_prob = 0.0
        if total > 0:
            high_risk_pct = (high_risk / total) * 100
            outbreak_prob = min(high_risk_pct * 1.5, 100)
        
        # Generate recommendations
        recommendations = []
        if high_risk > 0:
            recommendations.append(f'Immediate attention needed: {high_risk} high-risk animal(s) detected')
        if int(stats['overdue_vaccination']) > 0:
            recommendations.append(f'Vaccination overdue for {stats["overdue_vaccination"]} animal(s)')
        if int(stats['poor_feed']) > 0:
            recommendations.append(f'Improve feed quality for {stats["poor_feed"]} animal(s)')
        if avg_health < 80:
            recommendations.append('Overall farm health is below optimal level')
        if not recommendations:
            recommendations.append('Farm health is good. Continue regular monitoring')
        
        # Feed quality status
        feed_status = 'Good'
        if total > 0 and int(stats['poor_feed']) / total > 0.3:
            feed_status = 'Poor'
        elif total > 0 and int(stats['poor_feed']) / total > 0.1:
            feed_status = 'Fair'
        
        summary = {
            'farm_id': farm_id,
            'overall_health_score': avg_health,
            'high_risk_count': high_risk,
            'medium_risk_count': medium_risk,
            'low_risk_count': low_risk,
            'outbreak_probability': outbreak_prob,
            'feed_quality_status': feed_status,
            'vaccination_overdue_count': int(stats['overdue_vaccination']),
            'ai_recommendations': recommendations,
            'generated_at': datetime.utcnow().isoformat()
        }
        
        return jsonify({
            'success': True,
            'summary': summary
        })
        
    except Exception as e:
        print(f"Get farm summary error: {e}")
        return jsonify({
            'success': False,
            'error': 'Server error'
        }), 500

# ============================================
# ANIMAL ROUTES
# ============================================

@app.route('/api/animals', methods=['GET'])
@token_required
def get_animals():
    """Get animals for logged-in user. If farm_id query param is set, only animals for that farm."""
    try:
        farm_id = request.args.get('farm_id')
        if farm_id:
            animals = execute_query(
                """SELECT a.* FROM animals a
                   INNER JOIN farms f ON a.farm_id = f.id
                   WHERE f.user_id = %s AND a.farm_id = %s
                   ORDER BY a.created_at DESC""",
                (request.user_id, farm_id),
                fetch=True
            )
        else:
            animals = execute_query(
                """SELECT a.* FROM animals a
                   INNER JOIN farms f ON a.farm_id = f.id
                   WHERE f.user_id = %s
                   ORDER BY a.created_at DESC""",
                (request.user_id,),
                fetch=True
            )
        
        animals_list = []
        for animal in animals:
            animals_list.append({
                'id': animal['id'],
                'farm_id': animal['farm_id'],
                'animal_name': animal['animal_name'],
                'breed': animal['breed'],
                'tag_id': animal['tag_id'],
                'vaccination_status': animal['vaccination_status'],
                'medication_history': animal['medication_history'],
                'feed_quality': animal['feed_quality'],
                'symptoms': list(animal['symptoms'] or []),
                'risk_percentage': float(animal['risk_percentage']),
                'risk_level': animal['risk_level'],
                'health_score': float(animal['health_score']),
                'image_path': animal['image_path'],
                'audio_path': animal['audio_path'],
                'created_at': animal['created_at'].isoformat()
            })
        
        return jsonify({
            'success': True,
            'animals': animals_list
        })
        
    except Exception as e:
        print(f"Get animals error: {e}")
        return jsonify({
            'success': False,
            'error': 'Server error'
        }), 500

@app.route('/api/animals/<animal_id>', methods=['GET'])
@token_required
def get_animal(animal_id):
    """Get single animal details"""
    try:
        animal = execute_query(
            """SELECT a.* FROM animals a
               INNER JOIN farms f ON a.farm_id = f.id
               WHERE a.id = %s AND f.user_id = %s""",
            (animal_id, request.user_id),
            fetch_one=True
        )
        
        if not animal:
            return jsonify({
                'success': False,
                'error': 'Animal not found'
            }), 404
        
        return jsonify({
            'success': True,
            'animal': {
                'id': animal['id'],
                'farm_id': animal['farm_id'],
                'animal_name': animal['animal_name'],
                'breed': animal['breed'],
                'tag_id': animal['tag_id'],
                'vaccination_status': animal['vaccination_status'],
                'medication_history': animal['medication_history'],
                'feed_quality': animal['feed_quality'],
                'symptoms': list(animal['symptoms'] or []),
                'risk_percentage': float(animal['risk_percentage']),
                'risk_level': animal['risk_level'],
                'health_score': float(animal['health_score']),
                'image_path': animal['image_path'],
                'audio_path': animal['audio_path'],
                'created_at': animal['created_at'].isoformat()
            }
        })
        
    except Exception as e:
        print(f"Get animal error: {e}")
        return jsonify({
            'success': False,
            'error': 'Server error'
        }), 500

@app.route('/api/animals', methods=['POST'])
@token_required
def create_animal():
    """Add new animal"""
    try:
        # Handle multipart form data
        farm_id = request.form.get('farm_id')
        animal_name = request.form.get('animal_name')
        
        if not farm_id or not animal_name:
            return jsonify({
                'success': False,
                'error': 'Farm ID and animal name are required'
            }), 400
        
        # Verify farm ownership
        farm_check = execute_query(
            'SELECT id FROM farms WHERE id = %s AND user_id = %s',
            (farm_id, request.user_id),
            fetch_one=True
        )
        
        if not farm_check:
            return jsonify({
                'success': False,
                'error': 'Farm not found'
            }), 404
        
        # Parse symptoms
        symptoms_str = request.form.get('symptoms', '[]')
        try:
            symptoms = json.loads(symptoms_str) if symptoms_str else []
        except:
            symptoms = [s.strip() for s in symptoms_str.split(',') if s.strip()]
        
        # Handle file uploads
        image_path = None
        audio_path = None
        
        if 'image' in request.files:
            image = request.files['image']
            if image and allowed_file(image.filename):
                filename = secure_filename(f"{datetime.now().timestamp()}_{image.filename}")
                image_path = os.path.join(app.config['UPLOAD_FOLDER'], filename)
                image.save(image_path)
        
        if 'audio' in request.files:
            audio = request.files['audio']
            if audio and allowed_file(audio.filename):
                filename = secure_filename(f"{datetime.now().timestamp()}_{audio.filename}")
                audio_path = os.path.join(app.config['UPLOAD_FOLDER'], filename)
                audio.save(audio_path)
        
        animal = execute_query(
            """INSERT INTO animals (
                farm_id, animal_name, breed, tag_id, vaccination_status,
                medication_history, feed_quality, symptoms, image_path, audio_path
            ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
            RETURNING *""",
            (
                farm_id, animal_name,
                request.form.get('breed'),
                request.form.get('tag_id'),
                request.form.get('vaccination_status', 'Up to date'),
                request.form.get('medication_history'),
                request.form.get('feed_quality', 'Good'),
                symptoms,
                image_path,
                audio_path
            ),
            fetch_one=True
        )
        
        # Update farm stats
        update_farm_stats(farm_id)
        
        return jsonify({
            'success': True,
            'animal': {
                'id': animal['id'],
                'farm_id': animal['farm_id'],
                'animal_name': animal['animal_name'],
                'breed': animal['breed'],
                'tag_id': animal['tag_id'],
                'vaccination_status': animal['vaccination_status'],
                'medication_history': animal['medication_history'],
                'feed_quality': animal['feed_quality'],
                'symptoms': list(animal['symptoms'] or []),
                'risk_percentage': float(animal['risk_percentage']),
                'risk_level': animal['risk_level'],
                'health_score': float(animal['health_score']),
                'image_path': animal['image_path'],
                'audio_path': animal['audio_path'],
                'created_at': animal['created_at'].isoformat()
            }
        }), 201
        
    except Exception as e:
        print(f"Create animal error: {e}")
        return jsonify({
            'success': False,
            'error': 'Server error'
        }), 500

@app.route('/api/animals/<animal_id>', methods=['PUT'])
@token_required
def update_animal(animal_id):
    """Update animal"""
    try:
        # Verify ownership
        animal_check = execute_query(
            """SELECT a.*, f.user_id FROM animals a
               INNER JOIN farms f ON a.farm_id = f.id
               WHERE a.id = %s""",
            (animal_id,),
            fetch_one=True
        )
        
        if not animal_check:
            return jsonify({
                'success': False,
                'error': 'Animal not found'
            }), 404
        
        if animal_check['user_id'] != request.user_id:
            return jsonify({
                'success': False,
                'error': 'Access denied'
            }), 403
        
        updates = []
        values = []
        
        # Handle form data
        if 'animal_name' in request.form:
            updates.append('animal_name = %s')
            values.append(request.form['animal_name'])
        if 'breed' in request.form:
            updates.append('breed = %s')
            values.append(request.form['breed'])
        if 'tag_id' in request.form:
            updates.append('tag_id = %s')
            values.append(request.form['tag_id'])
        if 'vaccination_status' in request.form:
            updates.append('vaccination_status = %s')
            values.append(request.form['vaccination_status'])
        if 'medication_history' in request.form:
            updates.append('medication_history = %s')
            values.append(request.form['medication_history'])
        if 'feed_quality' in request.form:
            updates.append('feed_quality = %s')
            values.append(request.form['feed_quality'])
        if 'symptoms' in request.form:
            symptoms_str = request.form['symptoms']
            try:
                symptoms = json.loads(symptoms_str) if symptoms_str else []
            except:
                symptoms = [s.strip() for s in symptoms_str.split(',') if s.strip()]
            updates.append('symptoms = %s')
            values.append(symptoms)
        
        # Handle file uploads
        if 'image' in request.files:
            image = request.files['image']
            if image and allowed_file(image.filename):
                filename = secure_filename(f"{datetime.now().timestamp()}_{image.filename}")
                image_path = os.path.join(app.config['UPLOAD_FOLDER'], filename)
                image.save(image_path)
                updates.append('image_path = %s')
                values.append(image_path)
        
        if 'audio' in request.files:
            audio = request.files['audio']
            if audio and allowed_file(audio.filename):
                filename = secure_filename(f"{datetime.now().timestamp()}_{audio.filename}")
                audio_path = os.path.join(app.config['UPLOAD_FOLDER'], filename)
                audio.save(audio_path)
                updates.append('audio_path = %s')
                values.append(audio_path)
        
        if not updates:
            return jsonify({
                'success': False,
                'error': 'No fields to update'
            }), 400
        
        values.append(animal_id)
        
        animal = execute_query(
            f"""UPDATE animals SET {', '.join(updates)}
               WHERE id = %s
               RETURNING *""",
            tuple(values),
            fetch_one=True
        )
        
        # Update farm stats
        update_farm_stats(animal['farm_id'])
        
        return jsonify({
            'success': True,
            'animal': {
                'id': animal['id'],
                'farm_id': animal['farm_id'],
                'animal_name': animal['animal_name'],
                'breed': animal['breed'],
                'tag_id': animal['tag_id'],
                'vaccination_status': animal['vaccination_status'],
                'medication_history': animal['medication_history'],
                'feed_quality': animal['feed_quality'],
                'symptoms': list(animal['symptoms'] or []),
                'risk_percentage': float(animal['risk_percentage']),
                'risk_level': animal['risk_level'],
                'health_score': float(animal['health_score']),
                'image_path': animal['image_path'],
                'audio_path': animal['audio_path'],
                'created_at': animal['created_at'].isoformat()
            }
        })
        
    except Exception as e:
        print(f"Update animal error: {e}")
        return jsonify({
            'success': False,
            'error': 'Server error'
        }), 500

@app.route('/api/animals/<animal_id>', methods=['DELETE'])
@token_required
def delete_animal(animal_id):
    """Delete animal"""
    try:
        # Verify ownership
        animal_check = execute_query(
            """SELECT a.farm_id, f.user_id FROM animals a
               INNER JOIN farms f ON a.farm_id = f.id
               WHERE a.id = %s""",
            (animal_id,),
            fetch_one=True
        )
        
        if not animal_check:
            return jsonify({
                'success': False,
                'error': 'Animal not found'
            }), 404
        
        if animal_check['user_id'] != request.user_id:
            return jsonify({
                'success': False,
                'error': 'Access denied'
            }), 403
        
        farm_id = animal_check['farm_id']
        
        execute_query('DELETE FROM animals WHERE id = %s', (animal_id,))
        
        # Update farm stats
        update_farm_stats(farm_id)
        
        return jsonify({
            'success': True,
            'message': 'Animal deleted successfully'
        })
        
    except Exception as e:
        print(f"Delete animal error: {e}")
        return jsonify({
            'success': False,
            'error': 'Server error'
        }), 500

# ============================================
# PREDICTION ROUTES
# ============================================

@app.route('/api/predictions/predict', methods=['POST'])
@token_required
def predict():
    """Run AI health prediction"""
    try:
        data = request.get_json()
        animal_id = data.get('animal_id')
        
        if not animal_id:
            return jsonify({
                'success': False,
                'error': 'Animal ID is required'
            }), 400
        
        # Get animal and verify ownership
        animal = execute_query(
            """SELECT a.*, f.user_id FROM animals a
               INNER JOIN farms f ON a.farm_id = f.id
               WHERE a.id = %s""",
            (animal_id,),
            fetch_one=True
        )
        
        if not animal:
            return jsonify({
                'success': False,
                'error': 'Animal not found'
            }), 404
        
        if animal['user_id'] != request.user_id:
            return jsonify({
                'success': False,
                'error': 'Access denied'
            }), 403
        
        # Calculate prediction
        animal_data = {
            'vaccination_status': animal['vaccination_status'],
            'feed_quality': animal['feed_quality'],
            'symptoms': list(animal['symptoms'] or [])
        }
        
        prediction = calculate_health_prediction(animal_data)
        
        # Save prediction
        pred_result = execute_query(
            """INSERT INTO predictions (
                animal_id, disease_probability, risk_level, health_score,
                explanation, recommended_action, confidence, input_factors
            ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
            RETURNING *""",
            (
                animal_id,
                prediction['disease_probability'],
                prediction['risk_level'],
                prediction['health_score'],
                prediction['explanation'],
                prediction['recommended_action'],
                prediction['confidence'],
                json.dumps(prediction['input_factors'])
            ),
            fetch_one=True
        )
        
        # Update animal metrics
        execute_query(
            """UPDATE animals 
               SET risk_percentage = %s, risk_level = %s, health_score = %s
               WHERE id = %s""",
            (
                prediction['disease_probability'],
                prediction['risk_level'],
                prediction['health_score'],
                animal_id
            )
        )
        
        # Update farm stats
        update_farm_stats(animal['farm_id'])
        
        return jsonify({
            'success': True,
            'prediction': {
                'id': pred_result['id'],
                'animal_id': pred_result['animal_id'],
                'disease_probability': float(pred_result['disease_probability']),
                'risk_level': pred_result['risk_level'],
                'health_score': float(pred_result['health_score']),
                'explanation': pred_result['explanation'],
                'recommended_action': pred_result['recommended_action'],
                'confidence': float(pred_result['confidence']),
                'input_factors': pred_result['input_factors'],
                'predicted_at': pred_result['predicted_at'].isoformat()
            }
        })
        
    except Exception as e:
        print(f"Prediction error: {e}")
        return jsonify({
            'success': False,
            'error': 'Server error'
        }), 500

@app.route('/api/predictions/<animal_id>/history', methods=['GET'])
@token_required
def get_prediction_history(animal_id):
    """Get prediction history for animal"""
    try:
        # Verify ownership
        animal_check = execute_query(
            """SELECT a.id FROM animals a
               INNER JOIN farms f ON a.farm_id = f.id
               WHERE a.id = %s AND f.user_id = %s""",
            (animal_id, request.user_id),
            fetch_one=True
        )
        
        if not animal_check:
            return jsonify({
                'success': False,
                'error': 'Animal not found'
            }), 404
        
        predictions = execute_query(
            """SELECT * FROM predictions
               WHERE animal_id = %s
               ORDER BY predicted_at DESC
               LIMIT 50""",
            (animal_id,),
            fetch=True
        )
        
        predictions_list = []
        for pred in predictions:
            predictions_list.append({
                'id': pred['id'],
                'animal_id': pred['animal_id'],
                'disease_probability': float(pred['disease_probability']),
                'risk_level': pred['risk_level'],
                'health_score': float(pred['health_score']),
                'explanation': pred['explanation'],
                'recommended_action': pred['recommended_action'],
                'confidence': float(pred['confidence']),
                'input_factors': pred['input_factors'],
                'predicted_at': pred['predicted_at'].isoformat()
            })
        
        return jsonify({
            'success': True,
            'predictions': predictions_list
        })
        
    except Exception as e:
        print(f"Get prediction history error: {e}")
        return jsonify({
            'success': False,
            'error': 'Server error'
        }), 500

@app.route('/api/predictions/detect-disease-image', methods=['POST'])
@token_required
def detect_disease_image():
    """Detect Foot and Mouth Disease from an image using a PyTorch model."""
    try:
        if 'image' not in request.files:
            return jsonify({
                'success': False,
                'error': 'Image file is required'
            }), 400
        
        animal_id = request.form.get('animal_id')
        if not animal_id:
            return jsonify({
                'success': False,
                'error': 'Animal ID is required'
            }), 400
        
        # Verify ownership
        animal_check = execute_query(
            """SELECT a.id FROM animals a
               INNER JOIN farms f ON a.farm_id = f.id
               WHERE a.id = %s AND f.user_id = %s""",
            (animal_id, request.user_id),
            fetch_one=True
        )
        
        if not animal_check:
            return jsonify({
                'success': False,
                'error': 'Animal not found'
            }), 404
        
        image = request.files['image']
        if image and allowed_file(image.filename):
            filename = secure_filename(f"{datetime.now().timestamp()}_{image.filename}")
            image_path = os.path.join(app.config['UPLOAD_FOLDER'], filename)
            image.save(image_path)

            # Run PyTorch Foot and Mouth disease detection (if available)
            if predict_foot_mouth_disease is None:
                model_result = {
                    'disease': 'Foot and Mouth Disease',
                    'probability': 0.0,
                    'has_disease': False,
                    'model_configured': False,
                    'message': 'ML module not available. Install: pip install torch torchvision Pillow',
                }
            else:
                model_result = predict_foot_mouth_disease(image_path)

            return jsonify({
                'success': True,
                'animal_id': animal_id,
                'image_path': image_path,
                'disease': model_result.get('disease'),
                'probability': model_result.get('probability'),
                'has_disease': model_result.get('has_disease'),
                'model_configured': model_result.get('model_configured'),
                'message': model_result.get('message'),
            })
        
        return jsonify({
            'success': False,
            'error': 'Invalid or unsupported image file'
        }), 400
        
    except Exception as e:
        print(f"Image detection error: {e}")
        return jsonify({
            'success': False,
            'error': 'Server error'
        }), 500

@app.route('/api/predictions/detect-disease-symptoms', methods=['POST'])
@token_required
def detect_disease_symptoms():
    """Detect disease from symptoms"""
    try:
        data = request.get_json()
        symptoms = data.get('symptoms', [])
        
        if not isinstance(symptoms, list):
            return jsonify({
                'success': False,
                'error': 'Symptoms must be an array'
            }), 400
        
        # Simple symptom-based detection
        diseases = []
        
        if any(s in symptoms for s in ['fever', 'high_temperature']):
            diseases.extend(['Foot and Mouth Disease', 'Mastitis'])
        if any(s in symptoms for s in ['cough', 'nasal_discharge']):
            diseases.append('Bovine Respiratory Disease')
        if any(s in symptoms for s in ['diarrhea', 'bloody_stool']):
            diseases.extend(['Salmonellosis', 'Coccidiosis'])
        if any(s in symptoms for s in ['lameness', 'swollen_joints']):
            diseases.extend(['Foot Rot', 'Arthritis'])
        if any(s in symptoms for s in ['loss_of_appetite', 'weight_loss']):
            diseases.extend(['Tuberculosis', 'Parasitic Infection'])
        
        if not diseases:
            diseases.append('Unable to determine specific disease. Consult veterinarian.')
        
        return jsonify({
            'success': True,
            'symptoms': symptoms,
            'possible_diseases': list(set(diseases)),
            'recommendation': 'These are preliminary assessments. Please consult a veterinarian for accurate diagnosis.'
        })
        
    except Exception as e:
        print(f"Symptom detection error: {e}")
        return jsonify({
            'success': False,
            'error': 'Server error'
        }), 500

@app.route('/api/predictions/identify-cow-voice', methods=['POST'])
@token_required
def identify_cow_voice():
    """Identify a cow by voice using a PyTorch model."""
    try:
        if 'audio' not in request.files:
            return jsonify({
                'success': False,
                'error': 'Audio file is required'
            }), 400
        
        audio = request.files['audio']
        if audio and allowed_file(audio.filename):
            filename = secure_filename(f"{datetime.now().timestamp()}_{audio.filename}")
            audio_path = os.path.join(app.config['UPLOAD_FOLDER'], filename)
            audio.save(audio_path)

            # Collect reference animals for this user that have audio samples
            known_animals = execute_query(
                """SELECT a.id, a.animal_name, a.breed, a.tag_id, a.audio_path
                   FROM animals a
                   INNER JOIN farms f ON a.farm_id = f.id
                   WHERE f.user_id = %s AND a.audio_path IS NOT NULL""",
                (request.user_id,),
                fetch=True
            ) or []

            if identify_cow_by_voice is None:
                model_result = {
                    'model_configured': False,
                    'match_found': False,
                    'similarity': 0.0,
                    'animal': None,
                    'message': 'ML module not available. Install: pip install torch torchaudio',
                }
            else:
                model_result = identify_cow_by_voice(audio_path, known_animals)

            return jsonify({
                'success': True,
                'audio_path': audio_path,
                'model_configured': model_result.get('model_configured'),
                'match_found': model_result.get('match_found'),
                'similarity': model_result.get('similarity'),
                'animal': model_result.get('animal'),
                'message': model_result.get('message'),
            })

        return jsonify({
            'success': False,
            'error': 'Invalid or unsupported audio file'
        }), 400
        
    except Exception as e:
        print(f"Voice identification error: {e}")
        return jsonify({
            'success': False,
            'error': 'Server error'
        }), 500

# ============================================
# STATIC FILES
# ============================================

@app.route('/uploads/<path:filename>')
def uploaded_file(filename):
    """Serve uploaded files"""
    return send_from_directory(app.config['UPLOAD_FOLDER'], filename)


@app.route('/api/predictions/identify-cow-image', methods=['POST'])
@token_required
def identify_cow_image():
    """Identify a cow by face image using a PyTorch model."""
    try:
        if 'image' not in request.files:
            return jsonify({
                'success': False,
                'error': 'Image file is required'
            }), 400

        image = request.files['image']
        if not (image and allowed_file(image.filename)):
            return jsonify({
                'success': False,
                'error': 'Invalid or unsupported image file'
            }), 400

        filename = secure_filename(f"{datetime.now().timestamp()}_{image.filename}")
        image_path = os.path.join(app.config['UPLOAD_FOLDER'], filename)
        image.save(image_path)

        # Collect reference animals for this user that have images
        known_animals = execute_query(
            """SELECT a.id, a.animal_name, a.breed, a.tag_id, a.image_path
               FROM animals a
               INNER JOIN farms f ON a.farm_id = f.id
               WHERE f.user_id = %s AND a.image_path IS NOT NULL""",
            (request.user_id,),
            fetch=True
        ) or []

        if identify_cow_by_face is None:
            model_result = {
                'model_configured': False,
                'match_found': False,
                'similarity': 0.0,
                'animal': None,
                'message': 'ML module not available. Install: pip install torch torchvision Pillow',
            }
        else:
            model_result = identify_cow_by_face(image_path, known_animals)

        return jsonify({
            'success': True,
            'image_path': image_path,
            'model_configured': model_result.get('model_configured'),
            'match_found': model_result.get('match_found'),
            'similarity': model_result.get('similarity'),
            'animal': model_result.get('animal'),
            'message': model_result.get('message'),
        })

    except Exception as e:
        print(f"Image cow identification error: {e}")
        return jsonify({
            'success': False,
            'error': 'Server error'
        }), 500

# ============================================
# APPLICATION STARTUP
# ============================================

if __name__ == '__main__':
    # Initialize database pool
    if init_db_pool():
        print("\n" + "="*60)
        print("🐮 GoPashu Backend Server")
        print("="*60)
        print(f"✅ Server running on http://0.0.0.0:{os.getenv('PORT', 5000)}")
        print(f"✅ Database: {os.getenv('DB_NAME', 'gopashu_db')}")
        print("="*60)
        print("\n📡 Available endpoints:")
        print("   GET  /health")
        print("   POST /api/auth/signup")
        print("   POST /api/auth/login")
        print("   GET  /api/farms")
        print("   GET  /api/animals")
        print("   POST /api/predictions/predict")
        print("\n💡 Use Ctrl+C to stop the server")
        print("="*60 + "\n")
        
        try:
            app.run(
                host='0.0.0.0',
                port=int(os.getenv('PORT', 5000)),
                debug=(os.getenv('FLASK_ENV') == 'development')
            )
        finally:
            close_db_pool()
    else:
        print("❌ Failed to initialize database connection")
        print("Please check your database configuration in .env file")


