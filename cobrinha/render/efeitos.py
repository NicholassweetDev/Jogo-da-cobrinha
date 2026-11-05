"""Curvas de animação, partículas, ondas de choque, textos flutuantes e tremor de tela."""
from __future__ import annotations

import math
import random

import pygame

from cobrinha.render import desenho, tema
from cobrinha.render.tema import Cor

NIVEIS_FADE = 8
LIMITE_PARTICULAS = 600


def suave(t: float) -> float:
    """Curva em S."""
    t = max(0.0, min(1.0, t))
    return t * t * (3 - 2 * t)


def saida_cubica(t: float) -> float:
    """Desacelera até parar."""
    t = max(0.0, min(1.0, t))
    return 1 - (1 - t) ** 3


def saida_elastica(t: float) -> float:
    """Passa do ponto e volta: bom para coisas que surgem na tela."""
    t = max(0.0, min(1.0, t))
    forca = 1.70158
    return 1 + (forca + 1) * (t - 1) ** 3 + forca * (t - 1) ** 2


class Particula:
    """Ponto luminoso com física simples."""

    __slots__ = ("x", "y", "vx", "vy", "vida", "total", "raio", "cor", "gravidade", "atrito")

    def __init__(self, x, y, vx, vy, vida, raio, cor, gravidade, atrito):
        self.x, self.y, self.vx, self.vy = x, y, vx, vy
        self.vida = self.total = vida
        self.raio, self.cor = raio, cor
        self.gravidade, self.atrito = gravidade, atrito


class Efeitos:
    """Reúne todos os efeitos passageiros do mundo do jogo."""

    def __init__(self, tremor_ativo: bool = True, flash_ativo: bool = True) -> None:
        self.tremor_ativo = tremor_ativo
        self.flash_ativo = flash_ativo
        self.particulas: list[Particula] = []
        self.aneis: list[list] = []  # x, y, idade, duração, raio final, cor
        self.textos: list[list] = []  # x, y, idade, conteúdo, cor, tamanho
        self.flash_cor: Cor = tema.BRANCO
        self.flash_forca = 0.0
        self.tremor_forca = 0.0
        self.tempo = 0.0
        self.rng = random.Random()
        self._camada_flash: pygame.Surface | None = None

    def explosao(
        self,
        x: float,
        y: float,
        cores: tuple[Cor, ...],
        quantidade: int = 20,
        velocidade: float = 240.0,
        vida: float = 0.6,
        raio: int = 9,
        gravidade: float = 0.0,
        atrito: float = 2.4,
    ) -> None:
        """Lança partículas em todas as direções."""
        rng = self.rng
        for _ in range(quantidade):
            if len(self.particulas) >= LIMITE_PARTICULAS:
                return
            angulo = rng.uniform(0, math.tau)
            forca = velocidade * rng.uniform(0.25, 1.0)
            self.particulas.append(
                Particula(
                    x,
                    y,
                    math.cos(angulo) * forca,
                    math.sin(angulo) * forca,
                    vida * rng.uniform(0.6, 1.1),
                    max(3, int(raio * rng.uniform(0.6, 1.2))),
                    rng.choice(cores),
                    gravidade,
                    atrito,
                )
            )

    def rastro(self, x: float, y: float, cor: Cor, raio: int = 7) -> None:
        """Solta uma partícula quase parada."""
        if len(self.particulas) < LIMITE_PARTICULAS:
            rng = self.rng
            self.particulas.append(
                Particula(
                    x + rng.uniform(-6, 6),
                    y + rng.uniform(-6, 6),
                    rng.uniform(-14, 14),
                    rng.uniform(-14, 14),
                    0.45,
                    raio,
                    cor,
                    0.0,
                    1.0,
                )
            )

    def confete(self, cores: tuple[Cor, ...], quantidade: int = 90) -> None:
        """Faz chover brilhos de cima da tela."""
        rng = self.rng
        for _ in range(quantidade):
            if len(self.particulas) >= LIMITE_PARTICULAS:
                return
            self.particulas.append(
                Particula(
                    rng.uniform(0, tema.LARGURA),
                    rng.uniform(-260, -10),
                    rng.uniform(-40, 40),
                    rng.uniform(40, 200),
                    rng.uniform(1.8, 3.2),
                    rng.randint(5, 10),
                    rng.choice(cores),
                    170.0,
                    0.3,
                )
            )

    def onda(self, x: float, y: float, cor: Cor, raio: int = 70, duracao: float = 0.42) -> None:
        """Cria uma onda de choque circular."""
        self.aneis.append([x, y, 0.0, duracao, raio, cor])

    def flutuar(self, x: float, y: float, conteudo: str, cor: Cor, tamanho: int = 26) -> None:
        """Mostra um texto que sobe e some."""
        self.textos.append([x, y, 0.0, conteudo, cor, tamanho])

    def flash(self, cor: Cor, forca: float = 0.5) -> None:
        """Pisca a tela numa cor."""
        if self.flash_ativo:
            self.flash_cor = cor
            self.flash_forca = max(self.flash_forca, forca)

    def tremer(self, forca: float) -> None:
        """Sacode a arena; a força é a amplitude em pixels."""
        if self.tremor_ativo:
            self.tremor_forca = max(self.tremor_forca, forca)

    @property
    def deslocamento(self) -> tuple[int, int]:
        """Deslocamento atual da arena por causa do tremor."""
        if self.tremor_forca < 0.3:
            return 0, 0
        return (
            int(math.sin(self.tempo * 71.0) * self.tremor_forca),
            int(math.cos(self.tempo * 57.0) * self.tremor_forca),
        )

    def atualizar(self, dt: float) -> None:
        """Avança todos os efeitos."""
        self.tempo += dt
        vivas = []
        for p in self.particulas:
            p.vida -= dt
            if p.vida <= 0:
                continue
            freio = max(0.0, 1.0 - p.atrito * dt)
            p.vx *= freio
            p.vy = p.vy * freio + p.gravidade * dt
            p.x += p.vx * dt
            p.y += p.vy * dt
            vivas.append(p)
        self.particulas = vivas
        for item in self.aneis:
            item[2] += dt
        self.aneis = [a for a in self.aneis if a[2] < a[3]]
        for item in self.textos:
            item[2] += dt
        self.textos = [t for t in self.textos if t[2] < 0.95]
        self.flash_forca = max(0.0, self.flash_forca - dt * 2.6)
        self.tremor_forca *= max(0.0, 1.0 - dt * 7.5)

    def desenhar(self, tela: pygame.Surface, ox: int, oy: int) -> None:
        """Desenha partículas, ondas e textos, sem o flash."""
        lote = []
        for p in self.particulas:
            nivel = 1 + int((p.vida / p.total) * (NIVEIS_FADE - 1))
            halo = desenho.brilho(p.cor, p.raio, nivel * 100 // NIVEIS_FADE)
            lote.append((halo, (int(p.x) + ox - p.raio, int(p.y) + oy - p.raio)))
        if lote:
            tela.fblits(lote, desenho.ADITIVO)
        for x, y, idade, duracao, raio_final, cor in self.aneis:
            t = idade / duracao
            raio = max(4, int(raio_final * saida_cubica(t)) // 3 * 3)
            intensidade = max(1, int((1 - t) * 8)) * 12
            superficie = desenho.anel(raio, cor, intensidade)
            meio = superficie.get_width() // 2
            tela.blit(
                superficie,
                (int(x) + ox - meio, int(y) + oy - meio),
                special_flags=desenho.ADITIVO,
            )
        for x, y, idade, conteudo, cor, tamanho in self.textos:
            t = idade / 0.95
            subida = 52 * saida_cubica(t)
            alpha = 255 if t < 0.6 else int(255 * (1 - (t - 0.6) / 0.4))
            desenho.escrever(
                tela, conteudo, tamanho, (x + ox, y + oy - subida), cor, "forte", alpha=alpha
            )

    def desenhar_flash(self, tela: pygame.Surface) -> None:
        """Cobre a tela com o flash atual."""
        if self.flash_forca <= 0.01:
            return
        forca = min(self.flash_forca, 1.0) * 0.55
        if self._camada_flash is None:
            self._camada_flash = pygame.Surface(tela.get_size())
        camada = self._camada_flash
        camada.fill(self.flash_cor)
        camada.set_alpha(int(255 * forca))
        tela.blit(camada, (0, 0))
