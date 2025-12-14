#!/usr/bin/env python3
"""
Model Registry Manager

CLI for managing H2O model registry in PostgreSQL.
Supports model registration, activation, querying, and capability search.

Usage:
    python model_registry_manager.py register --model-id churn_gbm_v1 --algorithm GBM ...
    python model_registry_manager.py list --active
    python model_registry_manager.py activate --model-id churn_gbm_v1
    python model_registry_manager.py search --capability "churn prediction"
"""

import argparse
import json
import sys
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import Any, Optional


@dataclass
class ModelInfo:
    """Model registry entry."""
    model_id: str
    model_name: str
    algorithm: str
    problem_type: str
    capabilities_description: str
    required_features: list[str]
    is_active: bool
    version: str
    mojo_path: Optional[str] = None
    validation_auc: Optional[float] = None
    validation_rmse: Optional[float] = None
    
    def to_dict(self) -> dict:
        return {
            'model_id': self.model_id,
            'model_name': self.model_name,
            'algorithm': self.algorithm,
            'problem_type': self.problem_type,
            'capabilities_description': self.capabilities_description,
            'required_features': self.required_features,
            'is_active': self.is_active,
            'version': self.version,
            'mojo_path': self.mojo_path,
            'metrics': {
                'auc': self.validation_auc,
                'rmse': self.validation_rmse,
            }
        }


class ModelRegistryManager:
    """Manage H2O model registry in PostgreSQL."""
    
    def __init__(self, connection_string: Optional[str] = None):
        """Initialize with database connection.
        
        Args:
            connection_string: PostgreSQL connection string
        """
        self.connection_string = connection_string
        self.conn = None
    
    def connect(self) -> bool:
        """Establish database connection."""
        if not self.connection_string:
            print("Warning: No database connection. Running in mock mode.")
            return False
        
        try:
            import psycopg2
            self.conn = psycopg2.connect(self.connection_string)
            return True
        except ImportError:
            print("Warning: psycopg2 not installed. Running in mock mode.")
            return False
        except Exception as e:
            print(f"Error connecting to database: {e}")
            return False
    
    def close(self) -> None:
        """Close database connection."""
        if self.conn:
            self.conn.close()
    
    def register_model(
        self,
        model_id: str,
        model_name: str,
        algorithm: str,
        problem_type: str,
        capabilities: str,
        required_features: list[str],
        mojo_path: Optional[str] = None,
        version: str = "1.0.0",
        validation_auc: Optional[float] = None,
        validation_rmse: Optional[float] = None,
    ) -> bool:
        """Register a new model in the registry."""
        if not self.conn:
            print(f"[MOCK] Registering model: {model_id}")
            print(f"  Algorithm: {algorithm}")
            print(f"  Capabilities: {capabilities}")
            return True
        
        try:
            with self.conn.cursor() as cur:
                cur.execute("""
                    INSERT INTO h2o_intelligence.model_registry (
                        model_id, model_name, algorithm, problem_type,
                        capabilities_description, required_features,
                        mojo_path, version, validation_auc, validation_rmse
                    ) VALUES (%s, %s, %s, %s, %s, %s::jsonb, %s, %s, %s, %s)
                    ON CONFLICT (model_id) DO UPDATE SET
                        model_name = EXCLUDED.model_name,
                        algorithm = EXCLUDED.algorithm,
                        capabilities_description = EXCLUDED.capabilities_description,
                        required_features = EXCLUDED.required_features,
                        mojo_path = EXCLUDED.mojo_path,
                        version = EXCLUDED.version,
                        validation_auc = EXCLUDED.validation_auc,
                        validation_rmse = EXCLUDED.validation_rmse
                    RETURNING model_id
                """, (
                    model_id, model_name, algorithm, problem_type,
                    capabilities, json.dumps(required_features),
                    mojo_path, version, validation_auc, validation_rmse
                ))
                self.conn.commit()
                print(f"✅ Model registered: {model_id}")
                return True
        except Exception as e:
            self.conn.rollback()
            print(f"❌ Error registering model: {e}")
            return False
    
    def activate_model(self, model_id: str) -> bool:
        """Activate a model for agent use."""
        if not self.conn:
            print(f"[MOCK] Activating model: {model_id}")
            return True
        
        try:
            with self.conn.cursor() as cur:
                cur.execute("""
                    UPDATE h2o_intelligence.model_registry
                    SET is_active = TRUE, deployed_at = NOW()
                    WHERE model_id = %s
                    RETURNING model_id
                """, (model_id,))
                
                if cur.fetchone():
                    self.conn.commit()
                    print(f"✅ Model activated: {model_id}")
                    return True
                else:
                    print(f"❌ Model not found: {model_id}")
                    return False
        except Exception as e:
            self.conn.rollback()
            print(f"❌ Error activating model: {e}")
            return False
    
    def deactivate_model(self, model_id: str) -> bool:
        """Deactivate a model."""
        if not self.conn:
            print(f"[MOCK] Deactivating model: {model_id}")
            return True
        
        try:
            with self.conn.cursor() as cur:
                cur.execute("""
                    UPDATE h2o_intelligence.model_registry
                    SET is_active = FALSE
                    WHERE model_id = %s
                """, (model_id,))
                self.conn.commit()
                print(f"✅ Model deactivated: {model_id}")
                return True
        except Exception as e:
            self.conn.rollback()
            print(f"❌ Error deactivating model: {e}")
            return False
    
    def list_models(
        self,
        active_only: bool = False,
        algorithm: Optional[str] = None,
        problem_type: Optional[str] = None,
    ) -> list[dict]:
        """List models in the registry."""
        if not self.conn:
            print("[MOCK] Listing models...")
            return [
                {
                    'model_id': 'mock_churn_gbm',
                    'algorithm': 'GBM',
                    'is_active': True,
                    'capabilities_description': 'Predicts customer churn probability'
                }
            ]
        
        try:
            with self.conn.cursor() as cur:
                query = """
                    SELECT model_id, model_name, algorithm, problem_type,
                           capabilities_description, is_active, version,
                           validation_auc, validation_rmse
                    FROM h2o_intelligence.model_registry
                    WHERE 1=1
                """
                params = []
                
                if active_only:
                    query += " AND is_active = TRUE"
                
                if algorithm:
                    query += " AND algorithm = %s"
                    params.append(algorithm)
                
                if problem_type:
                    query += " AND problem_type = %s"
                    params.append(problem_type)
                
                query += " ORDER BY created_at DESC"
                
                cur.execute(query, params)
                
                models = []
                for row in cur.fetchall():
                    models.append({
                        'model_id': row[0],
                        'model_name': row[1],
                        'algorithm': row[2],
                        'problem_type': row[3],
                        'capabilities_description': row[4],
                        'is_active': row[5],
                        'version': row[6],
                        'auc': row[7],
                        'rmse': row[8],
                    })
                
                return models
        except Exception as e:
            print(f"❌ Error listing models: {e}")
            return []
    
    def search_by_capability(self, query: str) -> list[dict]:
        """Search models by capability description."""
        if not self.conn:
            print(f"[MOCK] Searching for: {query}")
            return []
        
        try:
            with self.conn.cursor() as cur:
                cur.execute("""
                    SELECT model_id, model_name, capabilities_description, is_active
                    FROM h2o_intelligence.model_registry
                    WHERE capabilities_description ILIKE %s
                      AND is_active = TRUE
                    ORDER BY model_id
                """, (f"%{query}%",))
                
                return [
                    {
                        'model_id': row[0],
                        'model_name': row[1],
                        'capabilities': row[2],
                        'is_active': row[3],
                    }
                    for row in cur.fetchall()
                ]
        except Exception as e:
            print(f"❌ Error searching models: {e}")
            return []
    
    def get_model_for_agent(self, capability_query: str) -> Optional[dict]:
        """Get the best model for an agent based on capability query.
        
        This is the function an agent would call to find the right model.
        """
        models = self.search_by_capability(capability_query)
        if models:
            return models[0]  # Return first match
        return None


def main():
    parser = argparse.ArgumentParser(description='H2O Model Registry Manager')
    parser.add_argument('--db', help='PostgreSQL connection string')
    
    subparsers = parser.add_subparsers(dest='command')
    
    # Register command
    reg_parser = subparsers.add_parser('register', help='Register a new model')
    reg_parser.add_argument('--model-id', required=True)
    reg_parser.add_argument('--model-name', required=True)
    reg_parser.add_argument('--algorithm', required=True, 
                           choices=['GBM', 'DRF', 'XGBoost', 'DeepLearning', 'GLM'])
    reg_parser.add_argument('--problem-type', required=True,
                           choices=['classification', 'regression', 'clustering', 'anomaly'])
    reg_parser.add_argument('--capabilities', required=True,
                           help='Natural language description of capabilities')
    reg_parser.add_argument('--features', required=True, nargs='+',
                           help='Required feature column names')
    reg_parser.add_argument('--mojo-path', help='Path to MOJO file')
    reg_parser.add_argument('--version', default='1.0.0')
    reg_parser.add_argument('--auc', type=float)
    reg_parser.add_argument('--rmse', type=float)
    
    # Activate command
    act_parser = subparsers.add_parser('activate', help='Activate a model')
    act_parser.add_argument('--model-id', required=True)
    
    # Deactivate command
    deact_parser = subparsers.add_parser('deactivate', help='Deactivate a model')
    deact_parser.add_argument('--model-id', required=True)
    
    # List command
    list_parser = subparsers.add_parser('list', help='List models')
    list_parser.add_argument('--active', action='store_true')
    list_parser.add_argument('--algorithm')
    list_parser.add_argument('--problem-type')
    list_parser.add_argument('--json', action='store_true')
    
    # Search command
    search_parser = subparsers.add_parser('search', help='Search by capability')
    search_parser.add_argument('--capability', required=True)
    search_parser.add_argument('--json', action='store_true')
    
    args = parser.parse_args()
    
    if not args.command:
        parser.print_help()
        sys.exit(1)
    
    manager = ModelRegistryManager(args.db)
    manager.connect()
    
    try:
        if args.command == 'register':
            manager.register_model(
                model_id=args.model_id,
                model_name=args.model_name,
                algorithm=args.algorithm,
                problem_type=args.problem_type,
                capabilities=args.capabilities,
                required_features=args.features,
                mojo_path=args.mojo_path,
                version=args.version,
                validation_auc=args.auc,
                validation_rmse=args.rmse,
            )
        
        elif args.command == 'activate':
            manager.activate_model(args.model_id)
        
        elif args.command == 'deactivate':
            manager.deactivate_model(args.model_id)
        
        elif args.command == 'list':
            models = manager.list_models(
                active_only=args.active,
                algorithm=args.algorithm,
                problem_type=args.problem_type,
            )
            
            if args.json:
                print(json.dumps(models, indent=2))
            else:
                print("\nMODEL REGISTRY")
                print("=" * 60)
                for m in models:
                    status = "🟢 ACTIVE" if m.get('is_active') else "⚪ INACTIVE"
                    print(f"\n{m['model_id']} [{status}]")
                    print(f"  Algorithm: {m.get('algorithm')}")
                    print(f"  Type: {m.get('problem_type')}")
                    print(f"  Capabilities: {m.get('capabilities_description', '')[:80]}")
                print("=" * 60)
        
        elif args.command == 'search':
            models = manager.search_by_capability(args.capability)
            
            if args.json:
                print(json.dumps(models, indent=2))
            else:
                print(f"\nSearch results for: '{args.capability}'")
                print("-" * 40)
                for m in models:
                    print(f"  • {m['model_id']}: {m['capabilities'][:60]}")
    
    finally:
        manager.close()


if __name__ == '__main__':
    main()
