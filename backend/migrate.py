#!/usr/bin/env python3
"""
Database Migration Script for GoPashu
Creates all necessary tables, indexes, and triggers
"""

import os
import sys
import psycopg2
from dotenv import load_dotenv

load_dotenv()

def create_database_schema():
    """Create complete database schema"""
    
    # Connect to PostgreSQL
    try:
        connection = psycopg2.connect(
            host=os.getenv('DB_HOST', 'localhost'),
            port=os.getenv('DB_PORT', '5432'),
            database=os.getenv('DB_NAME', 'gopashu_db'),
            user=os.getenv('DB_USER', 'postgres'),
            password=os.getenv('DB_PASSWORD')
        )
        cursor = connection.cursor()
        
        print("🔄 Starting database migration...")
        print("-" * 60)
        
        # Create UUID extension
        cursor.execute('CREATE EXTENSION IF NOT EXISTS "uuid-ossp";')
        print("✅ UUID extension created")
        
        # Create users table
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS users (
                id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
                name VARCHAR(255) NOT NULL,
                email VARCHAR(255) UNIQUE NOT NULL,
                password VARCHAR(255) NOT NULL,
                phone VARCHAR(20),
                location VARCHAR(255),
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            );
        """)
        print("✅ Users table created")
        
        # Create farms table
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS farms (
                id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
                user_id UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,
                farm_name VARCHAR(255) NOT NULL,
                location VARCHAR(255),
                total_animals INTEGER DEFAULT 0,
                health_score DECIMAL(5,2) DEFAULT 100.00,
                risk_level VARCHAR(20) DEFAULT 'Low',
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            );
        """)
        print("✅ Farms table created")
        
        # Create animals table
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS animals (
                id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
                farm_id UUID NOT NULL REFERENCES farms(id) ON DELETE CASCADE,
                animal_name VARCHAR(255) NOT NULL,
                breed VARCHAR(100),
                tag_id VARCHAR(50),
                vaccination_status VARCHAR(50) DEFAULT 'Up to date',
                medication_history TEXT,
                feed_quality VARCHAR(50) DEFAULT 'Good',
                symptoms TEXT[] DEFAULT '{}',
                risk_percentage DECIMAL(5,2) DEFAULT 0.00,
                risk_level VARCHAR(20) DEFAULT 'Low',
                health_score DECIMAL(5,2) DEFAULT 100.00,
                image_path VARCHAR(500),
                audio_path VARCHAR(500),
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            );
        """)
        print("✅ Animals table created")
        
        # Create predictions table
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS predictions (
                id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
                animal_id UUID NOT NULL REFERENCES animals(id) ON DELETE CASCADE,
                disease_probability DECIMAL(5,2) NOT NULL,
                risk_level VARCHAR(20) NOT NULL,
                health_score DECIMAL(5,2) NOT NULL,
                explanation TEXT NOT NULL,
                recommended_action TEXT NOT NULL,
                confidence DECIMAL(5,2) DEFAULT 0.00,
                input_factors JSONB,
                predicted_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            );
        """)
        print("✅ Predictions table created")
        
        # Create indexes
        cursor.execute("""
            CREATE INDEX IF NOT EXISTS idx_farms_user_id ON farms(user_id);
            CREATE INDEX IF NOT EXISTS idx_animals_farm_id ON animals(farm_id);
            CREATE INDEX IF NOT EXISTS idx_predictions_animal_id ON predictions(animal_id);
            CREATE INDEX IF NOT EXISTS idx_users_email ON users(email);
        """)
        print("✅ Indexes created")
        
        # Create update trigger function
        cursor.execute("""
            CREATE OR REPLACE FUNCTION update_updated_at_column()
            RETURNS TRIGGER AS $$
            BEGIN
                NEW.updated_at = CURRENT_TIMESTAMP;
                RETURN NEW;
            END;
            $$ language 'plpgsql';
        """)
        print("✅ Trigger function created")
        
        # Create triggers
        cursor.execute("""
            DROP TRIGGER IF EXISTS update_users_updated_at ON users;
            CREATE TRIGGER update_users_updated_at 
                BEFORE UPDATE ON users
                FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();
                
            DROP TRIGGER IF EXISTS update_farms_updated_at ON farms;
            CREATE TRIGGER update_farms_updated_at 
                BEFORE UPDATE ON farms
                FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();
                
            DROP TRIGGER IF EXISTS update_animals_updated_at ON animals;
            CREATE TRIGGER update_animals_updated_at 
                BEFORE UPDATE ON animals
                FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();
        """)
        print("✅ Triggers created")
        
        # Commit changes
        connection.commit()
        print("-" * 60)
        print("✅ Database migration completed successfully!")
        print("-" * 60)
        
        # Show table info
        cursor.execute("""
            SELECT table_name 
            FROM information_schema.tables 
            WHERE table_schema = 'public' 
            ORDER BY table_name;
        """)
        tables = cursor.fetchall()
        print("\n📊 Database Tables:")
        for table in tables:
            print(f"   - {table[0]}")
        
        cursor.close()
        connection.close()
        return True
        
    except Exception as e:
        print(f"\n❌ Migration failed: {e}")
        return False

if __name__ == "__main__":
    success = create_database_schema()
    sys.exit(0 if success else 1)
