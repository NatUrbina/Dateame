# Created by Miguel Pazo (https://miguelpazo.com)
from providers.curacao.Curacao import Curacao


def run(params):
    Curacao().run()
    return {"result": "ok"}
