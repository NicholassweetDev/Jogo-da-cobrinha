"""Cenário pré-renderizado: céu, tabuleiro, moldura neon e blocos de obstáculo."""
from __future__ import annotations

import math
import random
from functools import lru_cache

import pygame

from cobrinha.render import desenho, tema
from cobrinha.render.tema import ARENA_A, ARENA_L, CELULA, Cor, misturar

MARGEM_MOLDURA = 36


def _gradiente_vertical(largura: int, altura: int, topo: Cor, base: Cor) -> pygame.Surface:
    coluna = pygame.Surface((1, altura))
    for y in range(altura):
        coluna.set_at((0, y), misturar(topo, base, y / altura))
    return pygame.transform.scale(coluna, (largura, altura))


@lru_cache(maxsize=4)
def _vinheta(largura: int, altura: int, forca: int) -> pygame.Surface:
    """Escurece as bordas da imagem."""
    pequena = pygame.Surface((96, 54), pygame.SRCALPHA)
    for y in range(54):
        for x in range(96):
            dx = (x - 47.5) / 47.5
            dy = (y - 26.5) / 26.5
            distancia = min(1.0, math.hypot(dx, dy) / 1.414)
            pequena.set_at((x, y), (0, 0, 0, int(forca * distancia**2.2)))
    return pygame.transform.smoothscale(pequena, (largura, altura))


@lru_cache(maxsize=1)
def ceu() -> pygame.Surface:
    """Fundo da tela inteira, com estrelas."""
    superficie = _gradiente_vertical(tema.LARGURA, tema.ALTURA, tema.FUNDO_TOPO, tema.FUNDO_BASE)
    rng = random.Random(11)
    for _ in range(220):
        x, y = rng.randrange(tema.LARGURA), rng.randrange(tema.ALTURA)
        forca = rng.uniform(0.15, 0.75)
        cor = misturar(tema.FUNDO_TOPO, tema.TEXTO, forca)
        if rng.random() < 0.12:
            pygame.draw.circle(superficie, cor, (x, y), 1)
        else:
            superficie.set_at((x, y), cor)
    superficie.blit(_vinheta(tema.LARGURA, tema.ALTURA, 170), (0, 0))
    return superficie.convert()


@lru_cache(maxsize=8)
def tabuleiro(indice_tema: int) -> pygame.Surface:
    """Tabuleiro xadrez levemente tingido pela cor do nível."""
    cor = tema.TEMAS[indice_tema % len(tema.TEMAS)]
    clara = misturar(tema.CASA_CLARA, cor, 0.05)
    escura = misturar(tema.CASA_ESCURA, cor, 0.035)
    superficie = pygame.Surface((ARENA_L, ARENA_A))
    superficie.fill(escura)
    for y in range(ARENA_A // CELULA):
        for x in range(ARENA_L // CELULA):
            if (x + y) % 2 == 0:
                superficie.fill(clara, (x * CELULA, y * CELULA, CELULA, CELULA))
    superficie.blit(_vinheta(ARENA_L, ARENA_A, 150), (0, 0))
    return superficie.convert()


@lru_cache(maxsize=8)
def moldura_brilho(indice_tema: int) -> pygame.Surface:
    """Halo da moldura, para somar à imagem."""
    cor = tema.TEMAS[indice_tema % len(tema.TEMAS)]
    m = MARGEM_MOLDURA
    largura, altura = ARENA_L + m * 2, ARENA_A + m * 2
    superficie = pygame.Surface((largura // 4, altura // 4))
    pygame.draw.rect(
        superficie,
        misturar((0, 0, 0), cor, 0.75),
        (m // 4, m // 4, ARENA_L // 4, ARENA_A // 4),
        3,
        border_radius=4,
    )
    media = pygame.transform.smoothscale(superficie, (largura // 8, altura // 8))
    return pygame.transform.smoothscale(media, (largura, altura)).convert()


def preaquecer() -> None:
    """Gera os cenários de todos os temas, para o jogo não engasgar ao subir de nível."""
    for indice, cor in enumerate(tema.TEMAS):
        tabuleiro(indice)
        moldura_brilho(indice)
        bloco(indice)
        desenho.brilho(cor, 300, 10)
        desenho.brilho(cor, 5, 40)
    desenho.brilho(tema.VIOLETA, 260, 8)


@lru_cache(maxsize=8)
def bloco(indice_tema: int) -> pygame.Surface:
    """Bloco de obstáculo com relevo."""
    cor = tema.TEMAS[indice_tema % len(tema.TEMAS)]
    escala = 4
    lado = CELULA * escala
    s = pygame.Surface((lado, lado), pygame.SRCALPHA)
    corpo = misturar((46, 40, 86), cor, 0.18)
    s.fill((*corpo, 0))
    area = pygame.Rect(6, 6, lado - 12, lado - 12)
    pygame.draw.rect(s, (*misturar(corpo, (0, 0, 0), 0.45), 255), area, border_radius=22)
    pygame.draw.rect(
        s, (*corpo, 255), (area.x, area.y, area.w, area.h - 14), border_radius=22
    )
    pygame.draw.rect(
        s,
        (*misturar(corpo, tema.BRANCO, 0.14), 255),
        (area.x + 14, area.y + 12, area.w - 28, 14),
        border_radius=7,
    )
    pygame.draw.rect(s, (*misturar(corpo, cor, 0.7), 255), area, 5, border_radius=22)
    return pygame.transform.smoothscale(s, (CELULA, CELULA))
