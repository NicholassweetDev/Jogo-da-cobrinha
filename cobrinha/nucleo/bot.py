"""Piloto automático simples, usado na demonstração do menu e nos testes."""
from __future__ import annotations

from collections import deque

from cobrinha.nucleo.partida import Partida
from cobrinha.nucleo.tipos import Celula, Direcao


_PASSOS = tuple((direcao, direcao.dx, direcao.dy) for direcao in Direcao)


def _vizinhas(partida: Partida, celula: tuple[int, int]):
    """Lista (direção, célula vizinha) dentro da arena."""
    largura, altura = partida.regras.largura, partida.regras.altura
    atravessa = partida.atravessa
    saida = []
    for direcao, dx, dy in _PASSOS:
        x, y = celula[0] + dx, celula[1] + dy
        if atravessa:
            saida.append((direcao, (x % largura, y % altura)))
        elif 0 <= x < largura and 0 <= y < altura:
            saida.append((direcao, (x, y)))
    return saida


def _bloqueadas(partida: Partida) -> set[Celula]:
    bloqueadas = set(partida.cobra.segmentos) | partida.obstaculos
    if partida.cobra.crescimento_pendente == 0:
        bloqueadas.discard(partida.cobra.segmentos[-1])
    return bloqueadas


def _area_livre(partida: Partida, inicio: tuple, bloqueadas: set[Celula], limite: int) -> int:
    vistas = {inicio}
    pilha = [inicio]
    while pilha and len(vistas) < limite:
        atual = pilha.pop()
        for _, vizinha in _vizinhas(partida, atual):
            if vizinha not in bloqueadas and vizinha not in vistas:
                vistas.add(vizinha)
                pilha.append(vizinha)
    return len(vistas)


def _primeiro_passo_ate_comida(partida: Partida, bloqueadas: set[Celula]) -> Direcao | None:
    alvos = {c.celula for c in partida.comidas}
    fila: deque[tuple[Celula, Direcao | None]] = deque([(partida.cobra.cabeca, None)])
    vistas = {partida.cobra.cabeca}
    while fila:
        atual, primeiro = fila.popleft()
        if atual in alvos and primeiro is not None:
            return primeiro
        for direcao, vizinha in _vizinhas(partida, atual):
            if vizinha in bloqueadas or vizinha in vistas:
                continue
            vistas.add(vizinha)
            fila.append((vizinha, primeiro or direcao))
    return None


def escolher_direcao(partida: Partida) -> Direcao:
    """Vai pelo menor caminho até a comida, sem entrar em becos menores que a cobra."""
    bloqueadas = _bloqueadas(partida)
    cabeca = partida.cobra.cabeca
    atual = partida.cobra.direcao
    necessario = partida.cobra.comprimento + 2

    areas: dict[Direcao, int] = {}
    for direcao, vizinha in _vizinhas(partida, cabeca):
        if direcao is not atual.oposta() and vizinha not in bloqueadas:
            areas[direcao] = _area_livre(partida, vizinha, bloqueadas, necessario)
    if not areas:
        return atual

    desejada = _primeiro_passo_ate_comida(partida, bloqueadas)
    if desejada in areas and areas[desejada] >= necessario:
        return desejada
    return max(areas, key=lambda d: (areas[d], d is atual))
