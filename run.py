"""Ponto de entrada do FloraMap.

Executar com: python run.py
"""

from backend.app import criar_app

app = criar_app()

if __name__ == "__main__":
    app.run(debug=True, port=5000)
