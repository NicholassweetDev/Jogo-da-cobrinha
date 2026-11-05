"""Roda o jogo sem janela, com um piloto automático, e salva capturas e quadros.

Uso: python ferramentas/capturar.py PASTA [--gif]
"""
from __future__ import annotations

import os
import sys
import tempfile
import time
from pathlib import Path

os.environ.setdefault("SDL_VIDEODRIVER", "dummy")
os.environ.setdefault("SDL_AUDIODRIVER", "dummy")
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import pygame  # noqa: E402

from cobrinha.app import App  # noqa: E402
from cobrinha.cenas.jogo import CenaJogo  # noqa: E402
from cobrinha.entrada import Acao  # noqa: E402
from cobrinha.nucleo.bot import escolher_direcao  # noqa: E402
from cobrinha.nucleo.partida import Comida, Partida, Regras  # noqa: E402
from cobrinha.nucleo.tipos import Celula, Dificuldade, Modo, PowerUp, TipoComida  # noqa: E402
from cobrinha.persistencia import Recorde  # noqa: E402
from cobrinha.render.mundo import Mundo  # noqa: E402

DT = 1 / 60


class Roteiro:
    """Avança o jogo em passos fixos e salva imagens."""

    def __init__(self, pasta: Path) -> None:
        self.pasta = pasta
        pasta.mkdir(parents=True, exist_ok=True)
        self.app = App(Path(tempfile.mkdtemp()) / "dados.json")
        self.tempos: list[float] = []

    def rodar(self, quadros: int, piloto: bool = False) -> None:
        for _ in range(quadros):
            cena = self.app.cena
            if piloto and isinstance(cena, CenaJogo) and cena.estado == "jogando":
                cena.partida.virar(escolher_direcao(cena.partida))
            inicio = time.process_time()  # tempo de CPU: não sofre com outros programas
            self.app.passo(DT)
            self.tempos.append(time.process_time() - inicio)

    def foto(self, nome: str) -> None:
        pygame.image.save(self.app.tela, self.pasta / f"{nome}.png")


def partida_longa(cena: CenaJogo, comprimento: int) -> None:
    """Deixa a cobra comprida, para ver o corpo e medir o desempenho."""
    partida = cena.partida
    while partida.cobra.comprimento < comprimento and not partida.acabou:
        partida.virar(escolher_direcao(partida))
        partida.cobra.crescimento_pendente += 1
        partida.tick()
    cena.mundo.partida = partida


def main() -> None:
    pasta = Path(sys.argv[1] if len(sys.argv) > 1 else "capturas")
    gif = "--gif" in sys.argv
    r = Roteiro(pasta)
    app = r.app
    app.dados.registrar(Modo.CLASSICO, Dificuldade.NORMAL, Recorde(1240, "2026-11-02", 62, 134.0, 13, 5))
    app.dados.registrar(Modo.CLASSICO, Dificuldade.NORMAL, Recorde(860, "2026-11-01", 45, 101.0, 10, 4))
    app.dados.registrar(Modo.CLASSICO, Dificuldade.NORMAL, Recorde(420, "2026-10-30", 27, 66.0, 6, 3))

    r.rodar(120)
    r.foto("01-menu")
    menu = app.cena
    menu.pagina = "ajuda"
    r.rodar(10)
    r.foto("02-como-jogar")
    menu.pagina = "recordes"
    r.rodar(10)
    r.foto("03-recordes")
    menu.pagina = "opcoes"
    r.rodar(10)
    r.foto("04-opcoes")
    menu.pagina = "principal"

    app.cena = CenaJogo(app, Modo.CLASSICO, Dificuldade.NORMAL)
    r.rodar(20)
    r.foto("05-contagem")
    r.rodar(120, piloto=True)
    r.rodar(200, piloto=True)
    r.foto("06-jogo-inicio")

    cena = app.cena
    partida_longa(cena, 34)
    r.rodar(60, piloto=True)
    r.foto("07-jogo-cobra-longa")

    if gif:
        for indice in range(240):
            r.rodar(2, piloto=True)
            r.foto(f"gif-{indice:04d}")

    cena.partida.power_ups_ativos[PowerUp.FANTASMA] = 6.0
    r.rodar(30, piloto=True)
    r.foto("08-fantasma")
    cena.partida.power_ups_ativos.clear()

    app._acao(Acao.PAUSAR)
    r.rodar(6)
    r.foto("09-pausa")
    app._acao(Acao.CONFIRMAR)
    r.rodar(90)

    # Bate a cobra para mostrar a morte
    while not cena.partida.acabou:
        r.rodar(1)
    r.rodar(2)
    r.foto("10-batida")
    r.rodar(40)
    r.foto("11-morte")
    while cena.estado != "fim":
        r.rodar(1)
    r.rodar(70)
    r.foto("12-fim-de-jogo")

    tempos = sorted(r.tempos)
    print(f"quadros: {len(tempos)}")
    print(f"mediana: {tempos[len(tempos) // 2] * 1000:.2f} ms")
    print(f"p99: {tempos[int(len(tempos) * 0.99)] * 1000:.2f} ms")
    print(f"pior: {tempos[-1] * 1000:.2f} ms")

    # Comidas especiais na arena
    partida = Partida(Regras(Modo.CLASSICO, Dificuldade.NORMAL, semente=8))
    app.cena = CenaJogo(app, Modo.CLASSICO, Dificuldade.NORMAL)
    cena = app.cena
    cena.partida = partida
    cena.mundo = Mundo(partida, "Coral")
    cena.estado = "jogando"
    tipos = [t for t in TipoComida if t.eh_especial]
    for indice, tipo in enumerate(tipos):
        partida.comidas.append(Comida(Celula(6 + indice * 4, 4), tipo, 6.0 + indice * 0.4))
    r.rodar(40)
    r.foto("15-especiais")

    # Cobra cruzando a borda no modo sem paredes
    partida = Partida(Regras(Modo.ATRAVESSAR, Dificuldade.NORMAL, semente=2))
    app.cena = CenaJogo(app, Modo.ATRAVESSAR, Dificuldade.NORMAL)
    cena = app.cena
    cena.partida = partida
    cena.mundo = Mundo(partida, "Arco-íris")
    cena.estado = "jogando"
    partida.cobra.crescimento_pendente = 12
    while partida.cobra.cabeca.x != 3 or partida.tick_atual < 18:
        partida.comidas.clear()
        partida.comidas.append(Comida(Celula(16, 2), TipoComida.MACA))
        partida.tick()
    r.rodar(1)
    r.foto("16-cruzando-borda")

    for modo, nome in ((Modo.OBSTACULOS, "13-obstaculos"), (Modo.ATRAVESSAR, "14-sem-paredes")):
        partida = Partida(Regras(modo, Dificuldade.NORMAL, semente=3))
        app.cena = CenaJogo(app, modo, Dificuldade.NORMAL)
        cena = app.cena
        cena.partida = partida
        cena.mundo = Mundo(partida, "Neon" if modo is Modo.ATRAVESSAR else "Solar")
        cena.estado = "jogando"
        for _ in range(4):
            partida.nivel += 1
            partida._adicionar_obstaculos([]) if modo is Modo.OBSTACULOS else None
        partida_longa(cena, 18)
        r.rodar(45, piloto=True)
        r.foto(nome)


if __name__ == "__main__":
    main()
