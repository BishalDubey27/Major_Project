#!/usr/bin/env python3
"""
Auto-Synonym Discovery Tool
============================
Uses sentence-transformer embeddings to find semantically similar phrases
in the knowledge base and suggests new synonym mappings.

Usage:
    python auto_discover_synonyms.py                  # Print suggestions
    python auto_discover_synonyms.py --apply          # Apply suggestions to synonym_dict.json
    python auto_discover_synonyms.py --threshold 0.7  # Custom similarity threshold
"""

import json
import os
import argparse
import numpy as np
from sentence_transformers import SentenceTransformer

METADATA_PATH = 'knowledge_base/metadata.json'
SYNONYM_PATH = 'knowledge_base/synonym_dict.json'


def load_data():
    """Load metadata and existing synonyms."""
    with open(METADATA_PATH, 'r', encoding='utf-8') as f:
        metadata = json.load(f)

    phrases = [item['text'].lower() for item in metadata]

    existing_synonyms = {}
    if os.path.exists(SYNONYM_PATH):
        with open(SYNONYM_PATH, 'r', encoding='utf-8') as f:
            existing_synonyms = json.load(f)

    return phrases, existing_synonyms


def compute_similarity_matrix(phrases, model):
    """Encode all phrases and compute pairwise cosine similarities."""
    print(f"Encoding {len(phrases)} phrases...")
    embeddings = model.encode(phrases, convert_to_numpy=True, show_progress_bar=True)

    # Normalise for cosine similarity
    norms = np.linalg.norm(embeddings, axis=1, keepdims=True)
    norms[norms == 0] = 1  # avoid division by zero
    normed = embeddings / norms

    similarity_matrix = normed @ normed.T
    return similarity_matrix


def discover_synonyms(phrases, similarity_matrix, threshold=0.65, existing_synonyms=None):
    """
    Find phrase pairs whose cosine similarity exceeds *threshold*.
    Skips pairs that already exist in the synonym dict (either direction).
    """
    if existing_synonyms is None:
        existing_synonyms = {}

    existing_pairs = set()
    for k, v in existing_synonyms.items():
        existing_pairs.add((k.lower(), v.lower()))
        existing_pairs.add((v.lower(), k.lower()))

    suggestions = []
    n = len(phrases)
    for i in range(n):
        for j in range(i + 1, n):
            sim = similarity_matrix[i][j]
            if sim >= threshold and sim < 0.999:  # skip exact duplicates
                p1, p2 = phrases[i], phrases[j]
                if (p1, p2) in existing_pairs or (p2, p1) in existing_pairs:
                    continue
                # Suggest shorter phrase as synonym of longer (maps rare → common)
                if len(p1) <= len(p2):
                    syn_from, syn_to = p1, p2
                else:
                    syn_from, syn_to = p2, p1
                suggestions.append({
                    'from': syn_from,
                    'to': syn_to,
                    'similarity': round(float(sim), 4),
                })

    suggestions.sort(key=lambda s: s['similarity'], reverse=True)
    return suggestions


def main():
    parser = argparse.ArgumentParser(description='Auto-discover synonym pairs from the ISL knowledge base')
    parser.add_argument('--threshold', type=float, default=0.65,
                        help='Cosine similarity threshold (0-1). Default: 0.65')
    parser.add_argument('--apply', action='store_true',
                        help='Automatically append suggestions to synonym_dict.json')
    parser.add_argument('--top', type=int, default=50,
                        help='Maximum number of suggestions to show. Default: 50')
    args = parser.parse_args()

    phrases, existing_synonyms = load_data()

    print("Loading sentence-transformer model (all-MiniLM-L6-v2)...")
    model = SentenceTransformer('all-MiniLM-L6-v2')

    similarity_matrix = compute_similarity_matrix(phrases, model)
    suggestions = discover_synonyms(phrases, similarity_matrix,
                                     threshold=args.threshold,
                                     existing_synonyms=existing_synonyms)

    if not suggestions:
        print(f"\nNo new synonym pairs found above threshold {args.threshold}.")
        print("Try lowering --threshold (e.g. 0.55).")
        return

    print(f"\n{'='*60}")
    print(f" Found {len(suggestions)} potential synonym pairs (threshold={args.threshold})")
    print(f"{'='*60}\n")

    display = suggestions[:args.top]
    for i, s in enumerate(display, 1):
        print(f"  {i:3d}. \"{s['from']}\"  →  \"{s['to']}\"   (similarity: {s['similarity']})")

    if len(suggestions) > args.top:
        print(f"\n  ... and {len(suggestions) - args.top} more (use --top to see more)")

    if args.apply:
        new_count = 0
        for s in suggestions:
            if s['from'] not in existing_synonyms:
                existing_synonyms[s['from']] = s['to']
                new_count += 1

        with open(SYNONYM_PATH, 'w', encoding='utf-8') as f:
            json.dump(existing_synonyms, f, indent=2, ensure_ascii=False)

        print(f"\n✅ Applied {new_count} new synonyms to {SYNONYM_PATH}")
        print(f"   Total synonyms now: {len(existing_synonyms)}")
    else:
        print(f"\n💡 Run with --apply to add these to {SYNONYM_PATH}")


if __name__ == '__main__':
    main()
