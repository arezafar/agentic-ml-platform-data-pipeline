#!/usr/bin/env python3
"""
H2O MOJO Artifact Validator

Validates H2O MOJO (Model Object, Optimized) artifacts including:
- File structure and format validation
- Metadata completeness
- Model configuration
- H2O version compatibility
- Required files presence

Usage:
    python validate_mojo.py <mojo_path>
    python validate_mojo.py <mojo_path> --check-genmodel
"""

import argparse
import json
import os
import re
import sys
import zipfile
from pathlib import Path
from typing import Any


class MojoValidationError(Exception):
    """Custom exception for MOJO validation errors."""
    pass


class MojoValidator:
    """Validates H2O MOJO artifact files."""
    
    # Required files inside MOJO zip
    REQUIRED_FILES = [
        'model.ini',
        'domains/',
    ]
    
    # Common MOJO model files
    EXPECTED_FILES = [
        'model.ini',
        'experimental/modelDetails.json',
    ]
    
    # Supported model types
    SUPPORTED_MODEL_TYPES = {
        'gbm': 'Gradient Boosting Machine',
        'glm': 'Generalized Linear Model',
        'deeplearning': 'Deep Learning',
        'drf': 'Distributed Random Forest',
        'xgboost': 'XGBoost',
        'stackedensemble': 'Stacked Ensemble',
        'naivebayes': 'Naive Bayes',
        'isolationforest': 'Isolation Forest',
        'extendedisolationforest': 'Extended Isolation Forest',
    }
    
    # Minimum supported H2O version
    MIN_H2O_VERSION = (3, 30, 0)  # 3.30.0
    
    def __init__(self, mojo_path: Path):
        self.mojo_path = mojo_path
        self.errors: list[str] = []
        self.warnings: list[str] = []
        self.metadata: dict[str, Any] = {}
        self.model_ini: dict[str, Any] = {}
        self.is_zip = False
        
    def validate(self) -> bool:
        """Run all validation checks. Returns True if valid."""
        try:
            self._validate_file_exists()
            self._validate_file_format()
            self._validate_structure()
            self._validate_model_ini()
            self._validate_model_type()
            self._validate_h2o_version()
            self._validate_metadata()
            
            return len(self.errors) == 0
        except Exception as e:
            self.errors.append(f"Unexpected validation error: {e}")
            return False
    
    def _validate_file_exists(self) -> None:
        """Check that the MOJO file exists."""
        if not self.mojo_path.exists():
            raise MojoValidationError(f"MOJO file not found: {self.mojo_path}")
        
        if self.mojo_path.is_dir():
            # Check for extracted MOJO directory
            model_ini = self.mojo_path / 'model.ini'
            if not model_ini.exists():
                raise MojoValidationError(
                    f"MOJO directory missing model.ini: {self.mojo_path}"
                )
            self.is_zip = False
        else:
            self.is_zip = True
    
    def _validate_file_format(self) -> None:
        """Validate MOJO file format."""
        if self.is_zip:
            # Check it's a valid zip file
            if not zipfile.is_zipfile(self.mojo_path):
                self.errors.append(
                    "MOJO file is not a valid ZIP archive"
                )
                return
            
            # Check file extension
            suffix = self.mojo_path.suffix.lower()
            if suffix not in ('.zip', '.mojo'):
                self.warnings.append(
                    f"Unusual file extension '{suffix}' - expected .zip or .mojo"
                )
    
    def _validate_structure(self) -> None:
        """Validate MOJO archive structure."""
        if self.is_zip:
            try:
                with zipfile.ZipFile(self.mojo_path, 'r') as zf:
                    file_list = zf.namelist()
                    
                    # Check for required files
                    has_model_ini = any(
                        f.endswith('model.ini') for f in file_list
                    )
                    if not has_model_ini:
                        self.errors.append("MOJO missing required file: model.ini")
                    
                    # Check for domains directory
                    has_domains = any(
                        'domains/' in f for f in file_list
                    )
                    if not has_domains:
                        self.warnings.append(
                            "MOJO missing domains directory - may have no categorical features"
                        )
                    
                    # Store file count
                    self.metadata['file_count'] = len(file_list)
                    self.metadata['files'] = file_list[:20]  # First 20 for reference
                    
            except zipfile.BadZipFile as e:
                self.errors.append(f"Corrupt ZIP file: {e}")
        else:
            # Directory structure
            has_model_ini = (self.mojo_path / 'model.ini').exists()
            if not has_model_ini:
                self.errors.append("MOJO missing required file: model.ini")
    
    def _validate_model_ini(self) -> None:
        """Parse and validate model.ini configuration."""
        try:
            if self.is_zip:
                with zipfile.ZipFile(self.mojo_path, 'r') as zf:
                    # Find model.ini (may be in subdirectory)
                    model_ini_files = [
                        f for f in zf.namelist() if f.endswith('model.ini')
                    ]
                    if not model_ini_files:
                        return
                    
                    with zf.open(model_ini_files[0]) as f:
                        content = f.read().decode('utf-8')
            else:
                with open(self.mojo_path / 'model.ini', 'r') as f:
                    content = f.read()
            
            # Parse INI-style content
            self.model_ini = self._parse_ini(content)
            
            # Validate required fields
            required_fields = ['algo', 'n_features']
            for field in required_fields:
                if field not in self.model_ini:
                    self.warnings.append(
                        f"model.ini missing expected field: {field}"
                    )
            
        except Exception as e:
            self.errors.append(f"Failed to read model.ini: {e}")
    
    def _parse_ini(self, content: str) -> dict[str, Any]:
        """Parse INI-style configuration."""
        result = {}
        current_section = '__default__'
        
        for line in content.split('\n'):
            line = line.strip()
            
            # Skip empty lines and comments
            if not line or line.startswith('#') or line.startswith(';'):
                continue
            
            # Section header
            if line.startswith('[') and line.endswith(']'):
                current_section = line[1:-1]
                continue
            
            # Key-value pair
            if '=' in line:
                key, value = line.split('=', 1)
                key = key.strip()
                value = value.strip()
                
                # Type conversion
                if value.lower() == 'true':
                    value = True
                elif value.lower() == 'false':
                    value = False
                elif value.isdigit():
                    value = int(value)
                elif re.match(r'^-?\d+\.?\d*$', value):
                    value = float(value)
                
                if current_section == '__default__':
                    result[key] = value
                else:
                    if current_section not in result:
                        result[current_section] = {}
                    result[current_section][key] = value
        
        return result
    
    def _validate_model_type(self) -> None:
        """Validate model type is supported."""
        algo = self.model_ini.get('algo', '').lower()
        
        if not algo:
            self.warnings.append("Could not determine model algorithm")
            return
        
        if algo not in self.SUPPORTED_MODEL_TYPES:
            self.warnings.append(
                f"Model type '{algo}' may not be fully supported. "
                f"Known types: {list(self.SUPPORTED_MODEL_TYPES.keys())}"
            )
        else:
            self.metadata['model_type'] = self.SUPPORTED_MODEL_TYPES[algo]
            self.metadata['algorithm'] = algo
    
    def _validate_h2o_version(self) -> None:
        """Validate H2O version compatibility."""
        # Try to extract H2O version from metadata
        h2o_version = self.model_ini.get('h2o_version', '')
        
        if not h2o_version:
            # Try experimental metadata
            self._load_experimental_metadata()
            h2o_version = self.metadata.get('h2o_version', '')
        
        if not h2o_version:
            self.warnings.append(
                "Could not determine H2O version from MOJO"
            )
            return
        
        self.metadata['h2o_version'] = h2o_version
        
        # Parse version
        version_match = re.match(r'(\d+)\.(\d+)\.(\d+)', h2o_version)
        if version_match:
            version_tuple = tuple(int(v) for v in version_match.groups())
            
            if version_tuple < self.MIN_H2O_VERSION:
                self.warnings.append(
                    f"H2O version {h2o_version} is older than minimum "
                    f"recommended {'.'.join(map(str, self.MIN_H2O_VERSION))}"
                )
    
    def _load_experimental_metadata(self) -> None:
        """Load experimental modelDetails.json if present."""
        try:
            if self.is_zip:
                with zipfile.ZipFile(self.mojo_path, 'r') as zf:
                    metadata_files = [
                        f for f in zf.namelist() 
                        if 'modelDetails.json' in f
                    ]
                    if metadata_files:
                        with zf.open(metadata_files[0]) as f:
                            details = json.load(f)
                            self.metadata.update(details)
            else:
                metadata_path = self.mojo_path / 'experimental' / 'modelDetails.json'
                if metadata_path.exists():
                    with open(metadata_path, 'r') as f:
                        details = json.load(f)
                        self.metadata.update(details)
        except Exception:
            pass  # Optional metadata
    
    def _validate_metadata(self) -> None:
        """Validate model metadata completeness."""
        # Check feature count
        n_features = self.model_ini.get('n_features')
        if n_features is not None:
            self.metadata['n_features'] = n_features
            if n_features < 1:
                self.errors.append("Model has no features (n_features < 1)")
        
        # Check for target/response column
        response_column = self.model_ini.get('response_column_name', '')
        if response_column:
            self.metadata['response_column'] = response_column
        
        # Check model category
        model_category = self.model_ini.get('category', '')
        if model_category:
            self.metadata['category'] = model_category
            if model_category.lower() not in ['binomial', 'multinomial', 'regression', 
                                               'clustering', 'autoencoder', 'anomalydetection']:
                self.warnings.append(f"Unusual model category: {model_category}")
    
    def get_report(self) -> str:
        """Generate a validation report."""
        lines = [
            "=" * 60,
            "H2O MOJO VALIDATION REPORT",
            "=" * 60,
            f"Path: {self.mojo_path}",
            f"Format: {'ZIP archive' if self.is_zip else 'Directory'}",
        ]
        
        if self.metadata:
            lines.append("")
            lines.append("METADATA:")
            for key, value in self.metadata.items():
                if key != 'files':  # Skip file list
                    lines.append(f"  {key}: {value}")
        
        lines.append("")
        
        if self.errors:
            lines.append(f"ERRORS ({len(self.errors)}):")
            for err in self.errors:
                lines.append(f"  ❌ {err}")
            lines.append("")
            
        if self.warnings:
            lines.append(f"WARNINGS ({len(self.warnings)}):")
            for warn in self.warnings:
                lines.append(f"  ⚠️  {warn}")
            lines.append("")
            
        if not self.errors and not self.warnings:
            lines.append("✅ MOJO validation passed with no issues!")
        elif not self.errors:
            lines.append("✅ MOJO is valid (with warnings)")
        else:
            lines.append("❌ MOJO validation FAILED")
            
        lines.append("=" * 60)
        return '\n'.join(lines)


def check_genmodel_jar(mojo_path: Path) -> tuple[bool, str]:
    """Check if h2o-genmodel.jar is available for scoring."""
    # Common locations
    locations = [
        mojo_path.parent / 'h2o-genmodel.jar',
        Path.home() / '.h2o' / 'h2o-genmodel.jar',
        Path('/opt/h2o/h2o-genmodel.jar'),
    ]
    
    for loc in locations:
        if loc.exists():
            return True, str(loc)
    
    return False, "h2o-genmodel.jar not found in common locations"


def main():
    parser = argparse.ArgumentParser(
        description='Validate H2O MOJO artifact files'
    )
    parser.add_argument(
        'mojo_path',
        type=str,
        help='Path to MOJO file (.zip, .mojo) or extracted directory'
    )
    parser.add_argument(
        '--json',
        action='store_true',
        help='Output results as JSON'
    )
    parser.add_argument(
        '--strict',
        action='store_true',
        help='Treat warnings as errors'
    )
    parser.add_argument(
        '--check-genmodel',
        action='store_true',
        help='Check for h2o-genmodel.jar availability'
    )
    
    args = parser.parse_args()
    
    mojo_path = Path(args.mojo_path)
    
    validator = MojoValidator(mojo_path)
    is_valid = validator.validate()
    
    if args.strict and validator.warnings:
        is_valid = False
    
    # Check genmodel if requested
    genmodel_info = None
    if args.check_genmodel:
        found, location = check_genmodel_jar(mojo_path)
        genmodel_info = {'found': found, 'location': location}
        if not found:
            validator.warnings.append(location)
    
    if args.json:
        result = {
            'valid': is_valid,
            'path': str(mojo_path),
            'format': 'zip' if validator.is_zip else 'directory',
            'metadata': validator.metadata,
            'errors': validator.errors,
            'warnings': validator.warnings,
        }
        if genmodel_info:
            result['genmodel'] = genmodel_info
        print(json.dumps(result, indent=2))
    else:
        print(validator.get_report())
        if genmodel_info:
            status = "✅" if genmodel_info['found'] else "⚠️"
            print(f"\n{status} h2o-genmodel.jar: {genmodel_info['location']}")
    
    sys.exit(0 if is_valid else 1)


if __name__ == '__main__':
    main()
