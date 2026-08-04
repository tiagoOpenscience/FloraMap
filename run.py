"""Ponto de entrada do FloraMap.

Executar com: python run.py
Para manter o modo debug do Flask (recarregamento automático,
depurador no navegador), rode com FLASK_DEBUG=1 — nunca em produção,
já que o depurador exposto é uma falha de segurança grave.
"""

import os

from backend.app import criar_app

app = criar_app()

if __name__ == "__main__":
    app.run(debug=os.environ.get("FLASK_DEBUG") == "1", port=5000)
