#!/usr/bin/env python3
"""
Generate metadata.json from existing video files in knowledge_base/videos/
This script creates the required metadata structure for the ISL translator.
"""

import os
import json
from datetime import datetime

def generate_metadata():
    """Generate metadata.json from video files"""
    videos_dir = 'knowledge_base/videos'
    output_file = 'knowledge_base/metadata.json'
    
    if not os.path.exists(videos_dir):
        print(f"❌ Error: {videos_dir} directory not found")
        return False
    
    metadata = []
    video_files = [f for f in os.listdir(videos_dir) if f.endswith('.mp4')]
    
    print(f"📹 Found {len(video_files)} video files")
    
    for video_file in sorted(video_files):
        # Extract phrase from filename (remove .mp4 extension)
        phrase = os.path.splitext(video_file)[0].lower()
        
        metadata.append({
            'file': video_file,
            'text': phrase,
            'description': f'ISL sign for {phrase}',
            'category': 'general',
            'created_at': datetime.now().isoformat()
        })
    
    # Save metadata
    os.makedirs(os.path.dirname(output_file), exist_ok=True)
    with open(output_file, 'w', encoding='utf-8') as f:
        json.dump(metadata, f, indent=2, ensure_ascii=False)
    
    print(f"✅ Generated {output_file} with {len(metadata)} entries")
    return True

if __name__ == '__main__':
    generate_metadata()
