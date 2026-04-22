#!/usr/bin/env python3
"""
Pre-deployment verification script
Checks that all required files and directories are present before deploying
"""

import os
import sys
import json

def check_file(path, description):
    """Check if a file exists"""
    if os.path.exists(path):
        size = os.path.getsize(path)
        print(f"[OK] {description}: {path} ({size:,} bytes)")
        return True
    else:
        print(f"[FAIL] {description} MISSING: {path}")
        return False

def check_directory(path, description, min_files=0, extension=None):
    """Check if a directory exists and has files"""
    if not os.path.exists(path):
        print(f"[FAIL] {description} MISSING: {path}")
        return False
    
    if extension:
        files = [f for f in os.listdir(path) if f.endswith(extension)]
    else:
        files = os.listdir(path)
    
    if len(files) >= min_files:
        print(f"[OK] {description}: {path} ({len(files)} files)")
        return True
    else:
        print(f"[WARN] {description}: {path} (only {len(files)} files, expected at least {min_files})")
        return len(files) > 0

def main():
    print("="*70)
    print("ISL TRANSLATOR - DEPLOYMENT VERIFICATION")
    print("="*70)
    print()
    
    all_checks_passed = True
    
    # Critical files
    print("Checking critical files...")
    all_checks_passed &= check_file('unified_app.py', 'Main application')
    all_checks_passed &= check_file('requirements.txt', 'Requirements file')
    all_checks_passed &= check_file('Dockerfile.cloudrun', 'Dockerfile')
    all_checks_passed &= check_file('knowledge_base/isl_database.db', 'SQLite database')
    print()
    
    # Model files
    print("Checking model files...")
    model_found = (
        check_file('augs_transformer.pth', 'Sign recognition model (root)') or
        check_file('INCLUDE/augs_transformer (1).pth', 'Sign recognition model (INCLUDE)') or
        check_file('INCLUDE/include_no_cnn_transformer_small.pth', 'Sign recognition model (alternative)')
    )
    if not model_found:
        print("[FAIL] No sign recognition model found!")
        all_checks_passed = False
    
    all_checks_passed &= check_file('INCLUDE/label_maps/label_map_include50.json', 'Label map')
    all_checks_passed &= check_file('INCLUDE/hand_landmarker.task', 'Hand landmarker')
    all_checks_passed &= check_file('INCLUDE/pose_landmarker_lite.task', 'Pose landmarker')
    print()
    
    # Directories
    print("Checking directories...")
    all_checks_passed &= check_directory('knowledge_base/videos', 'Video files', min_files=100, extension='.mp4')
    check_directory('knowledge_base/generated_audio', 'Audio files', min_files=0, extension='.mp3')
    all_checks_passed &= check_directory('templates', 'HTML templates', min_files=3, extension='.html')
    all_checks_passed &= check_directory('static', 'Static files', min_files=1)
    print()
    
    # Validate SQLite database
    print("Validating SQLite database...")
    try:
        import sqlite3
        conn = sqlite3.connect('knowledge_base/isl_database.db')
        cursor = conn.cursor()
        cursor.execute('SELECT COUNT(*) FROM video_metadata')
        count = cursor.fetchone()[0]
        conn.close()
        
        if count == 0:
            print("[FAIL] SQLite database is empty")
            all_checks_passed = False
        else:
            print(f"[OK] SQLite database contains {count} entries")
    except Exception as e:
        print(f"[FAIL] Failed to validate SQLite database: {e}")
        all_checks_passed = False
    print()
    
    # Check .dockerignore
    print("Checking .dockerignore...")
    if os.path.exists('.dockerignore'):
        with open('.dockerignore', 'r') as f:
            dockerignore = f.read()
        
        # Check that videos are NOT excluded (look for uncommented exclusion)
        lines = [line.strip() for line in dockerignore.split('\n') if line.strip() and not line.strip().startswith('#')]
        if 'knowledge_base/videos' in lines or 'knowledge_base/videos/' in lines:
            print("[WARN] WARNING: knowledge_base/videos is excluded in .dockerignore")
            all_checks_passed = False
        else:
            print("[OK] .dockerignore looks good - videos will be included")
    print()
    
    # Summary
    print("="*70)
    if all_checks_passed:
        print("SUCCESS: ALL CHECKS PASSED - Ready for deployment!")
        print("="*70)
        print()
        print("Next steps:")
        print("1. Run: bash FINAL_DEPLOY.sh")
        print("2. Wait for deployment to complete")
        print("3. Test the deployed application")
        return 0
    else:
        print("ERROR: SOME CHECKS FAILED - Fix issues before deploying")
        print("="*70)
        print()
        return 1

if __name__ == '__main__':
    sys.exit(main())
