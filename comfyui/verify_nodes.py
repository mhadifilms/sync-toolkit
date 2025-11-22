#!/usr/bin/env python3
"""
Verification script to check if all nodes are properly registered.
Run this to verify nodes are available before restarting ComfyUI.
"""
import sys
from pathlib import Path

# Add current directory to path
current_dir = Path(__file__).parent.resolve()
sys.path.insert(0, str(current_dir))

try:
    from __init__ import NODE_CLASS_MAPPINGS, NODE_DISPLAY_NAME_MAPPINGS
    
    print("=" * 60)
    print("Sync Toolkit Node Verification")
    print("=" * 60)
    print(f"\nTotal nodes registered: {len(NODE_CLASS_MAPPINGS)}")
    print(f"\nAll registered nodes:")
    for node_name in sorted(NODE_CLASS_MAPPINGS.keys()):
        display_name = NODE_DISPLAY_NAME_MAPPINGS.get(node_name, node_name)
        node_class = NODE_CLASS_MAPPINGS[node_name]
        category = getattr(node_class, 'CATEGORY', 'unknown')
        print(f"  ✓ {node_name:20s} -> {display_name:30s} ({category})")
    
    print("\n" + "=" * 60)
    print("Checking OrganizeOutputs specifically:")
    print("=" * 60)
    
    if 'OrganizeOutputs' in NODE_CLASS_MAPPINGS:
        print("✓ OrganizeOutputs is registered")
        node_class = NODE_CLASS_MAPPINGS['OrganizeOutputs']
        print(f"✓ Display name: {NODE_DISPLAY_NAME_MAPPINGS.get('OrganizeOutputs', 'NOT FOUND')}")
        print(f"✓ Category: {node_class.CATEGORY}")
        print(f"✓ Function: {node_class.FUNCTION}")
        print(f"✓ Return types: {node_class.RETURN_TYPES}")
        
        # Test INPUT_TYPES
        try:
            input_types = node_class.INPUT_TYPES()
            print(f"✓ Required inputs: {list(input_types.get('required', {}).keys())}")
            print(f"✓ Optional inputs: {list(input_types.get('optional', {}).keys())}")
        except Exception as e:
            print(f"✗ Error getting INPUT_TYPES: {e}")
    else:
        print("✗ OrganizeOutputs is NOT registered!")
        print("Available nodes:", sorted(NODE_CLASS_MAPPINGS.keys()))
    
    print("\n" + "=" * 60)
    print("If all checks pass, restart ComfyUI to load the nodes.")
    print("=" * 60)
    
except Exception as e:
    print(f"✗ Error: {e}")
    import traceback
    traceback.print_exc()
    sys.exit(1)

