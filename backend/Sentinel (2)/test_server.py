#!/usr/bin/env python
"""
Test Django server directly
"""
import os
import sys
import subprocess


def main() -> None:
    project_dir = os.path.dirname(os.path.abspath(__file__))

    # Start Django server in background
    print("🚀 Starting Django server...")
    server_process = subprocess.Popen([
        sys.executable, 'manage.py', 'runserver', '--noreload'
    ], cwd=project_dir)

    print("✅ Server started on http://localhost:8000")
    print("📝 Open another terminal and run:")
    print("   python -c \"import requests; print(requests.post('http://localhost:8000/api/auth/register/', json={'full_name': 'Test User', 'email': 'test@example.com', 'password': 'testpass123', 'password_confirm': 'testpass123', 'contact_no': '9876543210'}).json())\"")

    try:
        input("Press Enter to stop server...")
    except KeyboardInterrupt:
        pass
    finally:
        server_process.terminate()
        print("🛑 Server stopped")


if __name__ == '__main__':
    main()
