#!/usr/bin/env python3
"""
Simple test script to verify imports and basic functionality.
"""

try:
    # Test progress tracker import
    from progress_tracker import ProgressTracker, ProgressSnapshot
    print("✓ progress_tracker imports successfully")
    
    # Test basic instantiation
    tracker = ProgressTracker()
    print("✓ ProgressTracker instantiates successfully")
    
    # Test basic functionality
    stats = tracker.get_statistics()
    print(f"✓ get_statistics() returns: {stats}")
    
    # Test snapshot creation
    snapshot = ProgressSnapshot(
        timestamp=1234567890.0,
        progress_percent=50.0,
        size_left=1000000,
        status="downloading",
        title="Test Movie"
    )
    print("✓ ProgressSnapshot creates successfully")
    
    print("\n🎉 All basic tests passed!")
    
except ImportError as e:
    print(f"❌ Import error: {e}")
except Exception as e:
    print(f"❌ Error: {e}")
