from heritrace.app import app

if __name__ == '__main__':
    app.run(host='127.0.0.1', port=5001, ssl_context=('cert.pem', 'key.pem'), debug=True)