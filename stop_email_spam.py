#!/usr/bin/env python3
"""
Emergency script to stop email spam
"""

import os
import sys

def stop_spam():
    """Stop any running processes that might be sending emails"""
    
    print("🚨 Emergency Email Spam Stopper")
    print("=" * 40)
    
    # Check for running Python processes
    import subprocess
    try:
        result = subprocess.run(['ps', 'aux'], capture_output=True, text=True)
        python_processes = [line for line in result.stdout.split('\n') 
                           if 'python' in line and 'outbound' in line]
        
        if python_processes:
            print("⚠️  Found running outbound.py processes:")
            for proc in python_processes:
                print(f"   {proc}")
            
            # Kill the processes
            for proc in python_processes:
                pid = proc.split()[1]
                try:
                    subprocess.run(['kill', '-9', pid])
                    print(f"✅ Killed process {pid}")
                except:
                    print(f"❌ Failed to kill process {pid}")
        else:
            print("✅ No outbound.py processes found running")
            
    except Exception as e:
        print(f"❌ Error checking processes: {e}")
    
    # Check for scheduler processes
    try:
        result = subprocess.run(['ps', 'aux'], capture_output=True, text=True)
        scheduler_processes = [line for line in result.stdout.split('\n') 
                             if 'python' in line and 'scheduler' in line]
        
        if scheduler_processes:
            print("⚠️  Found running scheduler processes:")
            for proc in scheduler_processes:
                print(f"   {proc}")
            
            # Kill the processes
            for proc in scheduler_processes:
                pid = proc.split()[1]
                try:
                    subprocess.run(['kill', '-9', pid])
                    print(f"✅ Killed scheduler process {pid}")
                except:
                    print(f"❌ Failed to kill scheduler process {pid}")
        else:
            print("✅ No scheduler processes found running")
            
    except Exception as e:
        print(f"❌ Error checking scheduler processes: {e}")
    
    print("\n📧 Email spam should now be stopped!")
    print("🔧 The email logic has been fixed to prevent duplicates")

if __name__ == "__main__":
    stop_spam()