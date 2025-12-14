"""
test_week3_pipeline.py - Comprehensive test for Week 3 after-hours pipeline
Verifies: After-hours filtering, threat classification, clip extraction
"""

import os
from pathlib import Path
from datetime import datetime, timedelta
from dotenv import load_dotenv

from threat_detector import ThreatDetector


def test_after_hours_logic():
    """Test 1: Verify after-hours detection logic"""
    print("="*60)
    print("TEST 1: After-Hours Detection Logic")
    print("="*60)
    
    detector = ThreatDetector(after_hours_start=22, after_hours_end=6)
    
    test_cases = [
        (datetime(2025, 1, 15, 22, 0, 0), True, "10:00 PM - Start of after-hours"),
        (datetime(2025, 1, 15, 23, 30, 0), True, "11:30 PM - Middle of night"),
        (datetime(2025, 1, 16, 2, 15, 0), True, "2:15 AM - Early morning"),
        (datetime(2025, 1, 16, 5, 59, 0), True, "5:59 AM - End of after-hours"),
        (datetime(2025, 1, 16, 6, 0, 0), False, "6:00 AM - Business hours start"),
        (datetime(2025, 1, 16, 14, 0, 0), False, "2:00 PM - Middle of day"),
        (datetime(2025, 1, 16, 21, 59, 0), False, "9:59 PM - Before after-hours"),
    ]
    
    all_passed = True
    for dt, expected, description in test_cases:
        result = detector.is_after_hours(dt)
        status = "✅ PASS" if result == expected else "❌ FAIL"
        
        if result != expected:
            all_passed = False
        
        print(f"{status} | {description}")
        print(f"       Time: {dt.strftime('%I:%M %p')} | Expected: {expected} | Got: {result}")
    
    print(f"\n{'✅ All tests passed!' if all_passed else '❌ Some tests failed!'}\n")
    return all_passed


def test_threat_classification():
    """Test 2: Verify threat classification logic"""
    print("="*60)
    print("TEST 2: Threat Classification")
    print("="*60)
    
    detector = ThreatDetector()
    
    test_cases = [
        ('person', 'HIGH', True, 'Person should be HIGH threat with alert'),
        ('car', 'MEDIUM', True, 'Car should be MEDIUM threat with alert'),
        ('truck', 'MEDIUM', True, 'Truck should be MEDIUM threat with alert'),
        ('backpack', 'MEDIUM', True, 'Backpack should be MEDIUM threat with alert'),
        ('dog', 'LOW', False, 'Dog should be LOW threat, no alert'),
        ('cat', 'LOW', False, 'Cat should be LOW threat, no alert'),
    ]
    
    all_passed = True
    for obj_class, expected_level, expected_alert, description in test_cases:
        result = detector.classify_threat(obj_class)
        
        level_ok = result['level'] == expected_level
        alert_ok = result['alert'] == expected_alert
        passed = level_ok and alert_ok
        
        status = "✅ PASS" if passed else "❌ FAIL"
        
        if not passed:
            all_passed = False
        
        print(f"{status} | {description}")
        print(f"       Object: {obj_class} | Level: {result['level']} (expected {expected_level})")
        print(f"       Alert: {result['alert']} (expected {expected_alert})")
    
    print(f"\n{'✅ All tests passed!' if all_passed else '❌ Some tests failed!'}\n")
    return all_passed


def test_full_analysis():
    """Test 3: Full detection-to-threat pipeline"""
    print("="*60)
    print("TEST 3: Full Analysis Pipeline")
    print("="*60)
    
    detector = ThreatDetector(after_hours_start=22, after_hours_end=6)
    
    # Simulated detection data
    sample_detections = [
        {
            'frame_number': 100,
            'timestamp': datetime(2025, 1, 15, 23, 30, 0),  # After hours
            'detections': [
                {'class': 'person', 'confidence': 0.85, 'bbox': [100, 100, 200, 300]}
            ]
        },
        {
            'frame_number': 150,
            'timestamp': datetime(2025, 1, 15, 14, 0, 0),  # Business hours (should skip)
            'detections': [
                {'class': 'person', 'confidence': 0.90, 'bbox': [150, 150, 250, 350]}
            ]
        },
        {
            'frame_number': 200,
            'timestamp': datetime(2025, 1, 16, 2, 15, 0),  # After hours
            'detections': [
                {'class': 'car', 'confidence': 0.78, 'bbox': [300, 150, 500, 350]},
                {'class': 'dog', 'confidence': 0.65, 'bbox': [50, 200, 150, 400]}
            ]
        },
        {
            'frame_number': 300,
            'timestamp': datetime(2025, 1, 16, 3, 45, 0),  # After hours
            'detections': [
                {'class': 'backpack', 'confidence': 0.72, 'bbox': [200, 100, 300, 250]}
            ]
        }
    ]
    
    print(f"Processing {len(sample_detections)} detection frames...")
    
    threats = detector.analyze_detections(sample_detections)
    summary = detector.generate_threat_summary(threats)
    
    print(f"\n📊 Results:")
    print(f"   Total threats: {summary['total_threats']}")
    print(f"   HIGH threats: {summary['high_threats']}")
    print(f"   MEDIUM threats: {summary['medium_threats']}")
    print(f"   LOW threats: {summary['low_threats']}")
    print(f"   Alerts to send: {summary['alerts_triggered']}")
    
    print(f"\n   Threat breakdown:")
    for obj_class, info in summary['threat_breakdown'].items():
        print(f"     - {obj_class}: {info['count']} ({info['level']} threat)")
    
    # Verify expectations
    expected = {
        'total_threats': 4,  # person (after-hours), car, dog, backpack
        'high_threats': 1,   # person
        'medium_threats': 2, # car, backpack
        'low_threats': 1,    # dog
        'alerts_triggered': 3 # person, car, backpack (not dog)
    }
    
    all_passed = True
    for key, expected_val in expected.items():
        actual_val = summary[key]
        if actual_val != expected_val:
            print(f"\n❌ MISMATCH: {key} - expected {expected_val}, got {actual_val}")
            all_passed = False
    
    if all_passed:
        print(f"\n✅ All metrics match expectations!")
    else:
        print(f"\n❌ Some metrics don't match!")
    
    print()
    return all_passed


def test_environment_config():
    """Test 4: Verify environment configuration"""
    print("="*60)
    print("TEST 4: Environment Configuration")
    print("="*60)
    
    load_dotenv()
    
    required_vars = {
        'AFTER_HOURS_START': '22',
        'AFTER_HOURS_END': '6',
        'PERSON_CONFIDENCE': '0.5',
    }
    
    optional_vars = {
        'FOOTAGE_BUCKET': None,
        'ANALYSIS_BUCKET': None,
    }
    
    print("Required variables:")
    all_present = True
    for var, default in required_vars.items():
        value = os.getenv(var, default)
        print(f"  {var} = {value}")
        if value == default:
            print(f"    ℹ️  Using default value")
    
    print("\nOptional variables (for S3):")
    for var, _ in optional_vars.items():
        value = os.getenv(var)
        status = "✅ Set" if value else "⚠️  Not set (OK for local testing)"
        print(f"  {var}: {status}")
        if value:
            print(f"    Value: {value}")
    
    print(f"\n✅ Configuration check complete!\n")
    return True


def run_all_tests():
    """Run all Week 3 tests"""
    print("\n" + "="*60)
    print("🧪 WEEK 3 PIPELINE VERIFICATION TESTS")
    print("="*60)
    print("Testing: After-hours filtering, threat classification, pipeline logic")
    print()
    
    results = {
        'after_hours_logic': test_after_hours_logic(),
        'threat_classification': test_threat_classification(),
        'full_analysis': test_full_analysis(),
        'environment_config': test_environment_config()
    }
    
    # Summary
    print("="*60)
    print("📊 TEST SUMMARY")
    print("="*60)
    
    for test_name, passed in results.items():
        status = "✅ PASS" if passed else "❌ FAIL"
        print(f"{status} | {test_name.replace('_', ' ').title()}")
    
    all_passed = all(results.values())
    
    print("\n" + "="*60)
    if all_passed:
        print("🎉 ALL TESTS PASSED!")
        print("✅ Week 3 pipeline is ready for Week 4 cloud deployment")
    else:
        print("⚠️  SOME TESTS FAILED")
        print("Please review the failures above before proceeding to Week 4")
    print("="*60 + "\n")
    
    return all_passed


if __name__ == '__main__':
    success = run_all_tests()
    
    if success:
        print("\n💡 Next Steps:")
        print("   1. Test with real video: python run_pipeline.py")
        print("   2. Proceed to Week 4: Cloud deployment (EC2, S3, SNS)")
        print("   3. Update .env with S3 bucket names if not already done")
    else:
        print("\n💡 Fix the failing tests before proceeding")