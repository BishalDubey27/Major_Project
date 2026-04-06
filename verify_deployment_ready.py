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
        print(f"✅ {description}: {path} ({size:,} bytes)")
        return True
    else:
        print(f"❌ {description} MISSING: {path}")
        return False

def check_directory(path, description, min_files=0, extension=None):
    """Check if a directory exists and has files"""
    if not os.path.exists(path):
        print(f"❌ {description} MISSING: {path}")
        return False
    
    if extension:
        files = [f for f in os.listdir(path) if f.endswith(extension)]
    else:
        files = os.listdir(path)
    
    if len(files) >= min_files:
        print(f"✅ {description}: {path} ({len(files)} files)")
        return True
    else:
        print(f"⚠️ {description}: {path} (only {len(files)} files, expected at least {min_files})")
        return len(files) > 0

def main():
    print("="*70)
    print("🔍 ISL TRANSLATOR - DEPLOYMENT VERIFICATION")
    print("="*70)
    print()
    
    all_checks_passed = True
    
    # Critical files
    print("📋 Checking critical files...")
    all_checks_passed &= check_file('unified_app.py', 'Main application')
    all_checks_passed &= check_file('requirements.txt', 'Requirements file')
    all_checks_passed &= check_file('Dockerfile.cloudrun', 'Dockerfile')
    all_checks_passed &= check_file('knowledge_base/metadata.json', 'Video metadata')
    print()
    
    # Model files
    print("🤖 Checking model files...")
    model_found = (
        check_file('augs_transformer.pth', 'Sign recognition model (root)') or
        check_file('INCLUDE/augs_transformer (1).pth', 'Sign recognition model (INCLUDE)') or
        check_file('INCLUDE/include_no_cnn_transformer_small.pth', 'Sign recognition model (alternative)')
    )
    if not model_found:
        print("❌ No sign recognition model found!")
        all_checks_passed = False
    
    all_checks_passed &= check_file('INCLUDE/label_maps/label_map_include50.json', 'Label map')
    all_checks_passed &= check_file('INCLUDE/hand_landmarker.task', 'Hand landmarker')
    all_checks_passed &= check_file('INCLUDE/pose_landmarker_lite.task', 'Pose landmarker')
    print()
    
    # Directories
    print("📁 Checking directories...")
    all_checks_passed &= check_directory('knowledge_base/videos', 'Video files', min_files=100, extension='.mp4')
    check_directory('knowledge_base/generated_audio', 'Audio files', min_files=0, extension='.mp3')
    all_checks_passed &= check_directory('templates', 'HTML templates', min_files=3, extension='.html')
    all_checks_passed &= check_directory('static', 'Static files', min_files=1)
    print()
    
    # Validate metadata.json
    print("🔍 Validating metadata.json...")
    try:
        with open('knowledge_base/metadata.json', 'r') as f:
            metadata = json.load(f)
        
        if not isinstance(metadata, list):
            print("❌ metadata.json is not a list")
            all_checks_passed = False
        elif len(metadata) == 0:
            print("❌ metadata.json is empty")
            all_checks_passed = False
        else:
            print(f"✅ metadata.json contains {len(metadata)} entries")
            
            # Check first entry structure
            if metadata:
                required_keys = ['file', 'text']
                first_entry = metadata[0]
                missing_keys = [k for k in required_keys if k not in first_entry]
                if missing_keys:
                    print(f"⚠️ metadata.json entries missing keys: {missing_keys}")
                else:
                    print(f"✅ metadata.json structure is valid")
    except Exception as e:
        print(f"❌ Failed to validate metadata.json: {e}")
        all_checks_passed = False
    print()
    
    # Check .dockerignore
    print("🐳 Checking .dockerignore...")
    if os.path.exists('.dockerignore'):
        with open('.dockerignore', 'r') as f:
            dockerignore = f.read()
        
        # Check that videos are NOT excluded (look for uncommented exclusion)
        lines = [line.strip() for line in dockerignore.split('\n') if line.strip() and not line.strip().startswith('#')]
        if 'knowledge_base/videos' in lines or 'knowledge_base/videos/' in lines:
            print("⚠️ WARNING: knowledge_base/videos is excluded in .dockerignore")
            all_checks_passed = False
        else:
            print("✅ .dockerignore looks good - videos will be included")
    print()
    
    # Summary
    print("="*70)
    if all_checks_passed:
        print("✅ ALL CHECKS PASSED - Ready for deployment!")
        print("="*70)
        print()
        print("Next steps:")
        print("1. Run: bash deploy-cloudrun.sh")
        print("2. Wait for deployment to complete")
        print("3. Test the deployed application")
        return 0
    else:
        print("❌ SOME CHECKS FAILED - Fix issues before deploying")
        print("="*70)
        print()
        print("Common fixes:")
        print("1. Run: python generate_metadata.py")
        print("2. Run: python generate_audio_for_new_videos.py")
        print("3. Ensure all video files are in knowledge_base/videos/")
        print("4. Check that .gitignore allows *.json files")
        return 1

if __name__ == '__main__':
    sys.exit(main())
