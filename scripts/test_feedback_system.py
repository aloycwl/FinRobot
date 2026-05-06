#!/usr/bin/env python3
"""
Test script to verify the comprehensive feedback system is working.

This script:
1. Tests the feedback loop initialization
2. Verifies trigger conditions are properly detected
3. Tests the Opencode integration (without actually calling it)
4. Validates all configuration files are in place
"""

import sys
import os
sys.path.insert(0, '/home/openclaw/FinRobot')

from finrobot.optimization.comprehensive_feedback import (
    ComprehensiveFeedbackLoop,
    get_feedback_loop,
    TriggerCondition,
    TRIGGER_CONFIGS
)
from finrobot.testing_scenarios import (
    generate_all_scenarios,
    GRID_TESTING_CONFIG,
    MARTINGALE_TESTING_CONFIG,
    HFT_TESTING_CONFIG
)

def test_feedback_loop_initialization():
    """Test that the feedback loop can be initialized."""
    print("Testing feedback loop initialization...")
    try:
        loop = ComprehensiveFeedbackLoop()
        print("✅ Feedback loop initialized successfully")
        print(f"   - Scenarios loaded: {len(loop.scenarios)}")
        print(f"   - Trigger configs: {len(TRIGGER_CONFIGS)}")
        return True
    except Exception as e:
        print(f"❌ Failed to initialize feedback loop: {e}")
        return False

def test_trigger_conditions():
    """Test that all trigger conditions are properly defined."""
    print("\nTesting trigger conditions...")
    all_conditions = list(TriggerCondition)
    print(f"   - Total trigger conditions: {len(all_conditions)}")
    
    missing_configs = []
    for condition in all_conditions:
        if condition not in TRIGGER_CONFIGS:
            missing_configs.append(condition.value)
    
    if missing_configs:
        print(f"❌ Missing configurations for: {missing_configs}")
        return False
    else:
        print("✅ All trigger conditions have configurations")
        return True

def test_scenario_generation():
    """Test that scenarios are properly generated."""
    print("\nTesting scenario generation...")
    try:
        scenarios = generate_all_scenarios()
        print(f"   - Total scenarios: {len(scenarios)}")
        
        # Check scenario types
        grid_scenarios = [s for s in scenarios if "Grid" in s.name]
        martingale_scenarios = [s for s in scenarios if "Martingale" in s.name]
        hft_scenarios = [s for s in scenarios if "HFT" in s.name]
        
        print(f"   - Grid scenarios: {len(grid_scenarios)}")
        print(f"   - Martingale scenarios: {len(martingale_scenarios)}")
        print(f"   - HFT scenarios: {len(hft_scenarios)}")
        
        if len(scenarios) > 0:
            print("✅ Scenarios generated successfully")
            return True
        else:
            print("❌ No scenarios generated")
            return False
            
    except Exception as e:
        print(f"❌ Failed to generate scenarios: {e}")
        import traceback
        traceback.print_exc()
        return False

def test_opencode_cli():
    """Test that Opencode CLI is accessible."""
    print("\nTesting Opencode CLI...")
    opencode_path = "/home/openclaw/.npm-global/bin/opencode"
    
    if not os.path.exists(opencode_path):
        print(f"❌ Opencode CLI not found at {opencode_path}")
        return False
    
    print(f"✅ Opencode CLI found at {opencode_path}")
    
    # Try to get version (don't fail if this doesn't work)
    import subprocess
    try:
        result = subprocess.run(
            [opencode_path, "--version"],
            capture_output=True,
            text=True,
            timeout=5
        )
        if result.returncode == 0:
            print(f"   Version: {result.stdout.strip()}")
        else:
            print(f"   Version check failed: {result.stderr}")
    except Exception as e:
        print(f"   Could not check version: {e}")
    
    return True

def test_config_files():
    """Test that all required configuration files exist."""
    print("\nTesting configuration files...")
    
    required_files = [
        "/home/openclaw/FinRobot/finrobot/grid.py",
        "/home/openclaw/FinRobot/finrobot/backtesting.py",
        "/home/openclaw/FinRobot/finrobot/hft.py",
        "/home/openclaw/FinRobot/finrobot/testing_scenarios.py",
        "/home/openclaw/FinRobot/finrobot/comprehensive_feedback.py",
    ]
    
    missing_files = []
    for filepath in required_files:
        if not os.path.exists(filepath):
            missing_files.append(filepath)
        else:
            print(f"✅ {os.path.basename(filepath)}")
    
    if missing_files:
        print(f"❌ Missing files:")
        for f in missing_files:
            print(f"   - {f}")
        return False
    else:
        print("✅ All required files present")
        return True

def run_all_tests():
    """Run all tests and report results."""
    print("=" * 60)
    print("COMPREHENSIVE FEEDBACK SYSTEM TEST SUITE")
    print("=" * 60)
    
    results = {
        "Feedback Loop Initialization": test_feedback_loop_initialization(),
        "Trigger Conditions": test_trigger_conditions(),
        "Scenario Generation": test_scenario_generation(),
        "Opencode CLI": test_opencode_cli(),
        "Configuration Files": test_config_files(),
    }
    
    print("\n" + "=" * 60)
    print("TEST RESULTS SUMMARY")
    print("=" * 60)
    
    passed = sum(1 for v in results.values() if v)
    total = len(results)
    
    for test_name, result in results.items():
        status = "✅ PASS" if result else "❌ FAIL"
        print(f"{status}: {test_name}")
    
    print("=" * 60)
    print(f"Total: {passed}/{total} tests passed ({passed/total*100:.1f}%)")
    print("=" * 60)
    
    if passed == total:
        print("\n🎉 All tests passed! The comprehensive feedback system is ready.")
        return 0
    else:
        print("\n⚠️  Some tests failed. Please review the output above.")
        return 1

if __name__ == "__main__":
    sys.exit(run_all_tests())