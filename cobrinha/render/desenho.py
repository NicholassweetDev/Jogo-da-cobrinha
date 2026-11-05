"""Superfícies geradas por código e guardadas em cache: textos, halos, comidas e ícones."""
from __future__ import annotations

import math
from functools import lru_cache
from pathlib import Path

import pygame

from cobrinha.nucleo.tipos import TipoComida
from cobrinha.render import tema
from cobrinha.render.tema import Cor, misturar

PASTA_FONTES = Path(__file__).resolve().parent.parent / "assets" / "fontes"
ADITIVO = pygame.BLEND_RGB_ADD
ESCALA = 4


@lru_cache(maxsize=None)
def fonte(nome: str, tamanho: int) -> pygame.font.Font:
    """Carrega uma fonte do jogo."""
    return pygame.font.Font(str(PASTA_FONTES / tema.FONTES[nome]), tamanho)


@lru_cache(maxsize=2048)
def texto(conteudo: str, tamanho: int, cor: Cor = tema.TEXTO, nome: str = "ui") -> pygame.Surface:
    """Renderiza um texto com antisserrilhado."""
    return fonte(nome, tamanho).render(conteudo, True, cor)


@lru_cache(maxsize=256)
def halo_texto(conteudo: str, tamanho: int, cor: Cor, nome: str = "titulo") -> pygame.Surface:
    """Cria um brilho desfocado para somar atrás de um texto."""
    base = fonte(nome, tamanho).render(conteudo, True, cor)
    margem = tamanho // 2
    largura, altura = base.get_width() + margem * 2, base.get_height() + margem * 2
    fundo = pygame.Surface((largura, altura))
    fundo.blit(base, (margem, margem))
    pequena = pygame.transform.smoothscale(fundo, (max(1, largura // 8), max(1, altura // 8)))
    return pygame.transform.smoothscale(pequena, (largura, altura)).convert()


def escrever(
    tela: pygame.Surface,
    conteudo: str,
    tamanho: int,
    posicao: tuple[float, float],
    cor: Cor = tema.TEXTO,
    nome: str = "ui",
    ancora: str = "center",
    alpha: int = 255,
) -> pygame.Rect:
    """Desenha um texto ancorado num ponto do retângulo."""
    superficie = texto(conteudo, tamanho, cor, nome)
    retangulo = superficie.get_rect(**{ancora: (int(posicao[0]), int(posicao[1]))})
    superficie.set_alpha(alpha)
    tela.blit(superficie, retangulo)
    superficie.set_alpha(255)
    return retangulo


@lru_cache(maxsize=16384)
def disco(raio2: int, cor: Cor) -> pygame.Surface:
    """Círculo suavizado; ``raio2`` é o raio em meios pixels."""
    raio = raio2 / 2
    lado = int(raio * 2) + 4
    grande = pygame.Surface((lado * ESCALA, lado * ESCALA), pygame.SRCALPHA)
    grande.fill((*cor, 0))
    pygame.draw.circle(
        grande, (*cor, 255), (lado * ESCALA / 2, lado * ESCALA / 2), raio * ESCALA
    )
    return pygame.transform.smoothscale(grande, (lado, lado))


def carimbar(tela: pygame.Surface, x: float, y: float, raio: float, cor: Cor) -> None:
    """Desenha um círculo suavizado centrado em (x, y)."""
    superficie = disco(max(1, int(raio * 2)), cor)
    meio = superficie.get_width() // 2
    tela.blit(superficie, (int(x) - meio, int(y) - meio))


@lru_cache(maxsize=1024)
def brilho(cor: Cor, raio: int, intensidade: int = 100) -> pygame.Surface:
    """Halo radial sobre preto, para somar à imagem com ``ADITIVO``."""
    pequeno = max(8, min(raio, 96))
    superficie = pygame.Surface((pequeno * 2, pequeno * 2))
    for r in range(pequeno, 0, -1):
        forca = (1 - r / pequeno) ** 2 * intensidade / 100
        pygame.draw.circle(
            superficie,
            (int(cor[0] * forca), int(cor[1] * forca), int(cor[2] * forca)),
            (pequeno, pequeno),
            r,
        )
    return pygame.transform.smoothscale(superficie, (raio * 2, raio * 2)).convert()


def somar_brilho(
    tela: pygame.Surface, x: float, y: float, cor: Cor, raio: int, intensidade: int = 100
) -> None:
    """Soma um halo centrado em (x, y)."""
    tela.blit(brilho(cor, raio, intensidade), (int(x) - raio, int(y) - raio), special_flags=ADITIVO)


@lru_cache(maxsize=1024)
def anel(raio: int, cor: Cor, intensidade: int) -> pygame.Surface:
    """Anel fino sobre preto, para ondas de choque."""
    lado = raio * 2 + 10
    superficie = pygame.Surface((lado, lado))
    forca = intensidade / 100
    pygame.draw.aacircle(
        superficie,
        (int(cor[0] * forca), int(cor[1] * forca), int(cor[2] * forca)),
        (lado // 2, lado // 2),
        raio,
        3,
    )
    return superficie.convert()


@lru_cache(maxsize=128)
def painel(
    largura: int, altura: int, cor: Cor, alpha: int, raio: int, borda: Cor | None = None
) -> pygame.Surface:
    """Retângulo arredondado translúcido, com borda opcional."""
    grande = pygame.Surface((largura * 2, altura * 2), pygame.SRCALPHA)
    grande.fill((*cor, 0))
    pygame.draw.rect(grande, (*cor, alpha), grande.get_rect(), border_radius=raio * 2)
    if borda:
        pygame.draw.rect(grande, (*borda, 255), grande.get_rect(), 3, border_radius=raio * 2)
    return pygame.transform.smoothscale(grande, (largura, altura))


# Comidas e ícones: desenhados em 128 px e reduzidos, para bordas suaves
_S = 128


def _reduzir(superficie: pygame.Surface, tamanho: int) -> pygame.Surface:
    return pygame.transform.smoothscale(superficie, (tamanho, tamanho))


def _maca(base: Cor, luz: Cor, sombra: Cor, folha: Cor, tamanho: int) -> pygame.Surface:
    s = pygame.Surface((_S, _S), pygame.SRCALPHA)
    s.fill((*base, 0))
    passos = 12
    for i in range(passos):
        k = i / (passos - 1)
        cor = misturar(sombra, base, k * 2) if k < 0.5 else misturar(base, luz, (k - 0.5) * 1.4)
        raio = 45 * (1 - 0.6 * k)
        desvio = -13 * k
        for cx in (50, 78):
            pygame.draw.circle(s, (*cor, 255), (cx + desvio, 76 + desvio), raio)
    pygame.draw.ellipse(s, (*sombra, 255), (54, 30, 20, 12))
    pygame.draw.line(s, (92, 58, 34, 255), (64, 38), (70, 12), 7)
    pygame.draw.polygon(
        s,
        (*folha, 255),
        [(68, 30), (78, 15), (96, 8), (116, 12), (104, 26), (86, 33)],
    )
    pygame.draw.line(s, (*misturar(folha, tema.BRANCO, 0.35), 255), (72, 29), (108, 13), 2)
    pygame.draw.ellipse(s, (*misturar(luz, tema.BRANCO, 0.7), 255), (32, 50, 14, 24))
    return _reduzir(s, tamanho)


def _icone_raio(s: pygame.Surface, cor: Cor) -> None:
    pygame.draw.polygon(
        s, (*cor, 255), [(74, 20), (40, 72), (62, 72), (52, 108), (90, 52), (67, 52)]
    )


def _icone_ampulheta(s: pygame.Surface, cor: Cor) -> None:
    pygame.draw.polygon(s, (*cor, 255), [(42, 34), (86, 34), (64, 64)])
    pygame.draw.polygon(s, (*cor, 255), [(64, 64), (42, 94), (86, 94)])
    pygame.draw.rect(s, (*cor, 255), (36, 26, 56, 8), border_radius=4)
    pygame.draw.rect(s, (*cor, 255), (36, 94, 56, 8), border_radius=4)


def _icone_fantasma(s: pygame.Surface, cor: Cor) -> None:
    pygame.draw.circle(s, (*cor, 255), (64, 56), 28)
    pygame.draw.rect(s, (*cor, 255), (36, 56, 56, 34))
    for x in (45, 64, 83):
        pygame.draw.circle(s, (*cor, 255), (x, 90), 10)
    fundo = (20, 16, 44, 255)
    pygame.draw.circle(s, fundo, (54, 54), 6)
    pygame.draw.circle(s, fundo, (74, 54), 6)


def _icone_texto(s: pygame.Surface, cor: Cor, conteudo: str) -> None:
    letras = fonte("titulo", 56).render(conteudo, True, cor)
    s.blit(letras, letras.get_rect(center=(64, 64)))


def _orbe(cor: Cor, icone, tamanho: int) -> pygame.Surface:
    s = pygame.Surface((_S, _S), pygame.SRCALPHA)
    s.fill((*cor, 0))
    pygame.draw.circle(s, (*misturar(cor, (8, 10, 24), 0.8), 255), (64, 64), 60)
    pygame.draw.circle(s, (*cor, 255), (64, 64), 60, 8)
    icone(s)
    return _reduzir(s, tamanho)


CORES_COMIDA: dict[TipoComida, Cor] = {
    TipoComida.MACA: tema.VERMELHO,
    TipoComida.DOURADA: tema.OURO,
    TipoComida.VELOZ: tema.LARANJA,
    TipoComida.LENTA: tema.AZUL,
    TipoComida.FANTASMA: tema.VIOLETA,
    TipoComida.ENCOLHER: tema.CIANO,
    TipoComida.MULTIPLICADOR: tema.ROSA,
}


@lru_cache(maxsize=64)
def sprite_comida(tipo: TipoComida, tamanho: int) -> pygame.Surface:
    """Devolve o desenho de uma comida."""
    if tipo is TipoComida.MACA:
        return _maca((226, 40, 62), (255, 120, 120), (120, 12, 44), (74, 222, 128), tamanho)
    if tipo is TipoComida.DOURADA:
        return _maca((245, 170, 30), (255, 238, 150), (150, 80, 10), (250, 225, 120), tamanho)
    cor = CORES_COMIDA[tipo]
    icones = {
        TipoComida.VELOZ: lambda s: _icone_raio(s, misturar(cor, tema.BRANCO, 0.35)),
        TipoComida.LENTA: lambda s: _icone_ampulheta(s, misturar(cor, tema.BRANCO, 0.45)),
        TipoComida.FANTASMA: lambda s: _icone_fantasma(s, misturar(cor, tema.BRANCO, 0.6)),
        TipoComida.ENCOLHER: lambda s: _icone_texto(s, misturar(cor, tema.BRANCO, 0.5), "-3"),
        TipoComida.MULTIPLICADOR: lambda s: _icone_texto(s, misturar(cor, tema.BRANCO, 0.5), "x2"),
    }
    return _orbe(cor, icones[tipo], tamanho)


def arco(
    tela: pygame.Surface,
    centro: tuple[float, float],
    raio: float,
    fracao: float,
    cor: Cor,
    espessura: int = 2,
) -> None:
    """Desenha um arco que começa no topo e gira no sentido horário."""
    if fracao <= 0:
        return
    passos = max(2, int(36 * fracao))
    pontos = []
    for i in range(passos + 1):
        angulo = -math.pi / 2 + 2 * math.pi * fracao * i / passos
        pontos.append((centro[0] + math.cos(angulo) * raio, centro[1] + math.sin(angulo) * raio))
    for deslocamento in range(espessura):
        anel_pontos = [
            (centro[0] + (x - centro[0]) * (1 + deslocamento / raio),
             centro[1] + (y - centro[1]) * (1 + deslocamento / raio))
            for x, y in pontos
        ]
        pygame.draw.aalines(tela, cor, False, anel_pontos)
