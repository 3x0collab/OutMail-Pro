import sys, os

# Add your app directory to the path
sys.path.insert(0, '/home/agfireed/outmail_pro')

# Activate your virtual environment
activate_this = '/home/agfireed/virtualenv/outmail_pro/3.9/bin/activate_this.py'
with open(activate_this) as file_:
    exec(file_.read(), dict(__file__=activate_this))

# Import the WSGI application
from ecommerce.wsgi import application  # change 'ecommerce' to your Django project name
