#!/usr/bin/env python3
"""
MOJO Deployer CLI

Command-line tool for deploying H2O MOJO artifacts to serving infrastructure.
Supports:
- MOJO validation and verification
- Version management
- Serving container updates
- Rollback capabilities

Usage:
    python mojo_deployer.py deploy --mojo-path /models/model.mojo --target production
    python mojo_deployer.py rollback --version 20240115_120000
    python mojo_deployer.py list-versions
"""

import argparse
import json
import shutil
import sys
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional


class MojoDeployer:
    """Manage MOJO artifact deployments."""
    
    def __init__(self, model_dir: str = "/models"):
        """Initialize deployer with model directory."""
        self.model_dir = Path(model_dir)
        self.production_dir = self.model_dir / "production"
        self.versions_dir = self.model_dir / "versions"
        self.archive_dir = self.model_dir / "archive"
        
    def deploy(
        self,
        mojo_path: str,
        genmodel_path: Optional[str] = None,
        version: Optional[str] = None,
        metadata: Optional[Dict] = None,
    ) -> Dict[str, Any]:
        """
        Deploy a MOJO artifact to production.
        
        Args:
            mojo_path: Path to .mojo file
            genmodel_path: Path to h2o-genmodel.jar
            version: Version string (auto-generated if None)
            metadata: Additional deployment metadata
            
        Returns:
            Deployment result dictionary
        """
        mojo_file = Path(mojo_path)
        
        if not mojo_file.exists():
            return {'success': False, 'error': f"MOJO file not found: {mojo_path}"}
        
        # Validate MOJO
        validation = self.validate_mojo(mojo_path)
        if not validation['valid']:
            return {'success': False, 'error': f"MOJO validation failed: {validation['errors']}"}
        
        # Generate version
        version = version or datetime.now().strftime('%Y%m%d_%H%M%S')
        
        # Create directories
        self.production_dir.mkdir(parents=True, exist_ok=True)
        version_dir = self.versions_dir / version
        version_dir.mkdir(parents=True, exist_ok=True)
        
        # Copy MOJO to versioned directory
        version_mojo = version_dir / "model.mojo"
        shutil.copy2(mojo_file, version_mojo)
        print(f"✅ Copied MOJO to: {version_mojo}")
        
        # Copy genmodel jar if provided
        if genmodel_path and Path(genmodel_path).exists():
            version_genmodel = version_dir / "h2o-genmodel.jar"
            shutil.copy2(genmodel_path, version_genmodel)
            print(f"✅ Copied genmodel jar to: {version_genmodel}")
        
        # Archive current production (if exists)
        current_mojo = self.production_dir / "model.mojo"
        if current_mojo.exists():
            self._archive_current(current_mojo)
        
        # Update production symlinks
        prod_mojo_link = self.production_dir / "model.mojo"
        prod_genmodel_link = self.production_dir / "h2o-genmodel.jar"
        
        for link in [prod_mojo_link, prod_genmodel_link]:
            if link.is_symlink():
                link.unlink()
        
        prod_mojo_link.symlink_to(version_mojo.resolve())
        
        if (version_dir / "h2o-genmodel.jar").exists():
            prod_genmodel_link.symlink_to((version_dir / "h2o-genmodel.jar").resolve())
        
        # Save deployment metadata
        deploy_metadata = {
            'version': version,
            'deployed_at': datetime.now().isoformat(),
            'mojo_source': str(mojo_path),
            'validation': validation,
            **(metadata or {}),
        }
        
        metadata_file = version_dir / "deployment.json"
        with open(metadata_file, 'w') as f:
            json.dump(deploy_metadata, f, indent=2)
        
        # Write current version file
        current_version_file = self.production_dir / "CURRENT_VERSION"
        current_version_file.write_text(version)
        
        print(f"✅ Deployed version {version} to production")
        
        return {
            'success': True,
            'version': version,
            'production_path': str(self.production_dir),
            'metadata': deploy_metadata,
        }
    
    def rollback(self, target_version: str) -> Dict[str, Any]:
        """
        Rollback to a previous version.
        
        Args:
            target_version: Version string to rollback to
            
        Returns:
            Rollback result dictionary
        """
        version_dir = self.versions_dir / target_version
        
        if not version_dir.exists():
            return {'success': False, 'error': f"Version not found: {target_version}"}
        
        version_mojo = version_dir / "model.mojo"
        if not version_mojo.exists():
            return {'success': False, 'error': f"MOJO not found in version: {target_version}"}
        
        # Update production symlinks
        prod_mojo_link = self.production_dir / "model.mojo"
        prod_genmodel_link = self.production_dir / "h2o-genmodel.jar"
        
        for link in [prod_mojo_link, prod_genmodel_link]:
            if link.is_symlink():
                link.unlink()
        
        prod_mojo_link.symlink_to(version_mojo.resolve())
        
        version_genmodel = version_dir / "h2o-genmodel.jar"
        if version_genmodel.exists():
            prod_genmodel_link.symlink_to(version_genmodel.resolve())
        
        # Update current version file
        current_version_file = self.production_dir / "CURRENT_VERSION"
        current_version_file.write_text(target_version)
        
        print(f"✅ Rolled back to version: {target_version}")
        
        return {
            'success': True,
            'version': target_version,
            'rolled_back_at': datetime.now().isoformat(),
        }
    
    def list_versions(self) -> List[Dict[str, Any]]:
        """List all deployed versions."""
        versions = []
        
        if not self.versions_dir.exists():
            return versions
        
        current_version = None
        current_file = self.production_dir / "CURRENT_VERSION"
        if current_file.exists():
            current_version = current_file.read_text().strip()
        
        for version_dir in sorted(self.versions_dir.iterdir(), reverse=True):
            if version_dir.is_dir():
                metadata_file = version_dir / "deployment.json"
                metadata = {}
                if metadata_file.exists():
                    with open(metadata_file) as f:
                        metadata = json.load(f)
                
                versions.append({
                    'version': version_dir.name,
                    'is_current': version_dir.name == current_version,
                    'deployed_at': metadata.get('deployed_at'),
                    'path': str(version_dir),
                })
        
        return versions
    
    def validate_mojo(self, mojo_path: str) -> Dict[str, Any]:
        """
        Validate a MOJO artifact.
        
        Checks:
        - File exists and is readable
        - File is a valid ZIP archive
        - Contains expected MOJO structure
        """
        import zipfile
        
        mojo_file = Path(mojo_path)
        result = {'valid': True, 'errors': [], 'warnings': []}
        
        # Check file exists
        if not mojo_file.exists():
            result['valid'] = False
            result['errors'].append(f"File not found: {mojo_path}")
            return result
        
        # Check file size
        size_mb = mojo_file.stat().st_size / (1024 * 1024)
        if size_mb > 500:
            result['warnings'].append(f"Large MOJO file: {size_mb:.1f} MB")
        
        # Check ZIP structure
        try:
            with zipfile.ZipFile(mojo_file, 'r') as zf:
                namelist = zf.namelist()
                
                # Check for expected MOJO files
                required_patterns = ['model.ini']
                for pattern in required_patterns:
                    if not any(pattern in name for name in namelist):
                        result['warnings'].append(f"Missing expected file: {pattern}")
                
                result['file_count'] = len(namelist)
                
        except zipfile.BadZipFile:
            result['valid'] = False
            result['errors'].append("Invalid ZIP archive")
        except Exception as e:
            result['valid'] = False
            result['errors'].append(f"Validation error: {e}")
        
        return result
    
    def _archive_current(self, current_mojo: Path) -> None:
        """Archive the current production MOJO before replacement."""
        self.archive_dir.mkdir(parents=True, exist_ok=True)
        archive_name = f"archived_{datetime.now().strftime('%Y%m%d_%H%M%S')}.mojo"
        archive_path = self.archive_dir / archive_name
        
        if current_mojo.is_symlink():
            # Resolve symlink and copy the actual file
            shutil.copy2(current_mojo.resolve(), archive_path)
        else:
            shutil.copy2(current_mojo, archive_path)
        
        print(f"📦 Archived current model to: {archive_path}")


def main():
    parser = argparse.ArgumentParser(description='MOJO Artifact Deployer')
    parser.add_argument('--model-dir', default='/models', help='Base model directory')
    
    subparsers = parser.add_subparsers(dest='command')
    
    # Deploy command
    deploy_parser = subparsers.add_parser('deploy', help='Deploy a MOJO artifact')
    deploy_parser.add_argument('--mojo-path', required=True, help='Path to .mojo file')
    deploy_parser.add_argument('--genmodel-path', help='Path to h2o-genmodel.jar')
    deploy_parser.add_argument('--version', help='Version string (auto-generated if omitted)')
    
    # Rollback command
    rollback_parser = subparsers.add_parser('rollback', help='Rollback to a previous version')
    rollback_parser.add_argument('--version', required=True, help='Version to rollback to')
    
    # List versions command
    subparsers.add_parser('list-versions', help='List all deployed versions')
    
    # Validate command
    validate_parser = subparsers.add_parser('validate', help='Validate a MOJO file')
    validate_parser.add_argument('--mojo-path', required=True, help='Path to .mojo file')
    
    args = parser.parse_args()
    
    if not args.command:
        parser.print_help()
        sys.exit(1)
    
    deployer = MojoDeployer(args.model_dir)
    
    if args.command == 'deploy':
        result = deployer.deploy(
            mojo_path=args.mojo_path,
            genmodel_path=args.genmodel_path,
            version=args.version,
        )
        print(json.dumps(result, indent=2))
        
    elif args.command == 'rollback':
        result = deployer.rollback(args.version)
        print(json.dumps(result, indent=2))
        
    elif args.command == 'list-versions':
        versions = deployer.list_versions()
        print("\nDEPLOYED VERSIONS")
        print("=" * 60)
        for v in versions:
            marker = "🟢" if v['is_current'] else "  "
            print(f"{marker} {v['version']} - {v.get('deployed_at', 'N/A')}")
        print("=" * 60)
        
    elif args.command == 'validate':
        result = deployer.validate_mojo(args.mojo_path)
        print(json.dumps(result, indent=2))


if __name__ == '__main__':
    main()
