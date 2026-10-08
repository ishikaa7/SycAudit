#!/usr/bin/env python3
"""Simple diagnostic test for GTE model loading and tokenization."""

import sys
from sentence_transformers import SentenceTransformer
import traceback

print("Python version:", sys.version)

# Test the specific model loading issue
try:
    print("Loading model Alibaba-NLP/gte-base-en-v1.5 with trust_remote_code=True")
    model = SentenceTransformer(
        "Alibaba-NLP/gte-base-en-v1.5",
        trust_remote_code=True
    )
    print("Model loaded successfully!")
    
    # Test tokenization on a simple string
    test_text = "Hello world"
    print(f"Testing with text: {test_text}")
    
    # Get the tokenizer
    tokenizer = model.tokenizer
    encoded = tokenizer(test_text, return_tensors="pt")
    print(f"Encoded tokens shape: {encoded['input_ids'].shape}")
    print(f"Position IDs tensor shape: {encoded.get('position_ids', 'Not found').shape if 'position_ids' in encoded else 'Not found'}")
    
    # Try encoding
    embeddings = model.encode([test_text], show_progress_bar=True)
    print("Encoding successful!")
    print(f"Embedding shape: {embeddings.shape}")
    
except Exception as e:
    print(f"Error occurred: {e}")
    traceback.print_exc()