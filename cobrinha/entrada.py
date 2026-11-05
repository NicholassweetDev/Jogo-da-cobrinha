"""Traduz teclado e gamepad em ações do jogo."""
from __future__ import annotations

from enum import Enum, auto

import pygame

from cobrinha.nucleo.tipos import Direcao


class Acao(Enum):
    """Ações que as cenas entendem."""

    CIMA = auto()
    BAIXO = auto()
    ESQUERDA = auto()
    DIREITA = auto()
    CONFIRMAR = auto()
    VOLTAR = auto()
    PAUSAR = auto()
    REINICIAR = auto()
    TELA_CHEIA = auto()
    MUDO = auto()
    FPS = auto()


DIRECOES = {
    Acao.CIMA: Direcao.CIMA,
    Acao.BAIXO: Direcao.BAIXO,
    Acao.ESQUERDA: Direcao.ESQUERDA,
    Acao.DIREITA: Direcao.DIREITA,
}

_TECLAS = {
    pygame.K_UP: Acao.CIMA,
    pygame.K_w: Acao.CIMA,
    pygame.K_DOWN: Acao.BAIXO,
    pygame.K_s: Acao.BAIXO,
    pygame.K_LEFT: Acao.ESQUERDA,
    pygame.K_a: Acao.ESQUERDA,
    pygame.K_RIGHT: Acao.DIREITA,
    pygame.K_d: Acao.DIREITA,
    pygame.K_RETURN: Acao.CONFIRMAR,
    pygame.K_KP_ENTER: Acao.CONFIRMAR,
    pygame.K_SPACE: Acao.CONFIRMAR,
    pygame.K_ESCAPE: Acao.VOLTAR,
    pygame.K_p: Acao.PAUSAR,
    pygame.K_r: Acao.REINICIAR,
    pygame.K_F11: Acao.TELA_CHEIA,
    pygame.K_m: Acao.MUDO,
    pygame.K_F3: Acao.FPS,
}

_BOTOES = {0: Acao.CONFIRMAR, 1: Acao.VOLTAR, 6: Acao.REINICIAR, 7: Acao.PAUSAR}
ZONA_MORTA = 0.5


def mapear_tecla(tecla: int) -> Acao | None:
    """Devolve a ação da tecla, se houver."""
    return _TECLAS.get(tecla)


def mapear_botao(botao: int) -> Acao | None:
    """Devolve a ação de um botão de gamepad, se houver."""
    return _BOTOES.get(botao)


def mapear_hat(valor: tuple[int, int]) -> Acao | None:
    """Devolve a direção do direcional digital do gamepad."""
    x, y = valor
    if x:
        return Acao.DIREITA if x > 0 else Acao.ESQUERDA
    if y:
        return Acao.CIMA if y > 0 else Acao.BAIXO
    return None


class LeitorEixo:
    """Transforma o analógico em ações, disparando uma vez por inclinação."""

    def __init__(self) -> None:
        self._ultimo: dict[int, int] = {}

    def ler(self, eixo: int, valor: float) -> Acao | None:
        """Devolve a ação quando o eixo cruza a zona morta."""
        if eixo not in (0, 1):
            return None
        sinal = 0 if abs(valor) < ZONA_MORTA else (1 if valor > 0 else -1)
        if sinal == self._ultimo.get(eixo, 0):
            return None
        self._ultimo[eixo] = sinal
        if sinal == 0:
            return None
        if eixo == 0:
            return Acao.DIREITA if sinal > 0 else Acao.ESQUERDA
        return Acao.BAIXO if sinal > 0 else Acao.CIMA
