# launch.py
import os
import sys

# Ensure project root is in sys.path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

# Set Django settings
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'outmail_pro.settings')

# Run Django
from django.core.management import execute_from_command_line

# Pass command-line arguments
execute_from_command_line(sys.argv)
