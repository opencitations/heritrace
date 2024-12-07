import os

from config import Config
from heritrace import create_app


def get_ssl_context():
    """Get SSL context if certificates exist."""
    if os.path.exists('cert.pem') and os.path.exists('key.pem'):
        return ('cert.pem', 'key.pem')
    return None

app = create_app(Config)

if __name__ == '__main__':
    env = os.getenv('FLASK_ENV', 'development')
    
    run_args = {
        'host': '0.0.0.0',
        'port': 5000
    }
    
    if env == 'development':
        run_args.update({
            'ssl_context': get_ssl_context(),
            'debug': True
        })
        
    app.run(**run_args)