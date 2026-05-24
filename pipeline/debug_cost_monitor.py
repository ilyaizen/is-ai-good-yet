#!/usr/bin/env python3
"""
Debug script for CostMonitor issue.
"""

import sys
import os

# Add pipeline/src to path for imports
sys.path.append(os.path.join(os.path.dirname(__file__), 'src'))

from src.prefilter import CostMonitor

def test_cost_monitor_debug():
    """Debug the CostMonitor class."""
    print("Debugging CostMonitor...")

    # Create cost monitor
    cost_monitor = CostMonitor()

    print(f"Initial tokens: {cost_monitor.total_tokens}")
    print(f"Initial successful calls: {cost_monitor.successful_calls}")
    print(f"Initial failed calls: {cost_monitor.failed_calls}")

    # Test adding calls
    cost_monitor.add_call(100, 50, True)
    print(f"After first call - tokens: {cost_monitor.total_tokens}")

    cost_monitor.add_call(120, 60, False)
    print(f"After second call - tokens: {cost_monitor.total_tokens}")

    cost_monitor.add_call(110, 55, True)
    print(f"After third call - tokens: {cost_monitor.total_tokens}")

    print(f"Final tokens: {cost_monitor.total_tokens}")
    print(f"Expected: 345")
    print(f"Match: {cost_monitor.total_tokens == 345}")

if __name__ == "__main__":
    test_cost_monitor_debug()