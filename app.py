from heritrace.app import app
import os

def get_ssl_context():
    if os.path.exists('cert.pem') and os.path.exists('key.pem'):
        return ('cert.pem', 'key.pem')
    return None

if __name__ == '__main__':
    env = os.getenv('FLASK_ENV', 'development')
    
    if env == 'development':
        app.run(
            host='0.0.0.0',
            port=5000,
            ssl_context=get_ssl_context(),
            debug=True
        )
    else:
        app.run(
            host='0.0.0.0',
            port=5000
        )