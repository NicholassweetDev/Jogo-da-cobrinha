"""Mundo do jogo: reage aos eventos da partida e desenha a arena inteira."""
from __future__ import annotations

import math
import random

import pygame

from cobrinha import config
from cobrinha.nucleo.partida import Partida
from cobrinha.nucleo.tipos import (
    Celula,
    Comeu,
    ComidaExpirou,
    ComidaNasceu,
    Encolheu,
    Evento,
    Morreu,
    ObstaculosNasceram,
    PowerUp,
    PowerUpAtivado,
    PowerUpExpirou,
    SubiuNivel,
    TipoComida,
    Virou,
)
from cobrinha.render import cenario, desenho, tema
from cobrinha.render.cobra import CobraVisual
from cobrinha.render.efeitos import Efeitos, saida_elastica
from cobrinha.render.tema import ARENA_A, ARENA_L, ARENA_X, ARENA_Y, CELULA, Cor

TAMANHO_COMIDA = 34
DURACAO_FADE_TEMA = 0.7
DURACAO_NASCER = 0.32
QUADROS_POR_FUNDO = 4  # o fundo muda devagar: recompor sempre seria desperdício
CORES_POWER_UP: dict[PowerUp, Cor] = {
    PowerUp.VELOZ: tema.LARANJA,
    PowerUp.LENTA: tema.AZUL,
    PowerUp.FANTASMA: tema.VIOLETA,
    PowerUp.MULTIPLICADOR: tema.ROSA,
}


def centro(celula: Celula) -> tuple[float, float]:
    """Centro da célula em pixels, relativo à arena."""
    return (celula.x + 0.5) * CELULA, (celula.y + 0.5) * CELULA


class Mundo:
    """Liga a partida ao que aparece na tela."""

    def __init__(
        self,
        partida: Partida,
        skin: str,
        tremor: bool = True,
        flash: bool = True,
        efeitos_de_jogo: bool = True,
    ) -> None:
        self.partida = partida
        self.cobra = CobraVisual(skin, partida.atravessa)
        self.efeitos = Efeitos(tremor, flash)
        self.efeitos_de_jogo = efeitos_de_jogo
        self.tempo = 0.0
        self.tema = 0
        self.tema_anterior = 0
        self.fade_tema = 1.0
        self.nascimento_comida: dict[Celula, float] = {}
        self.nascimento_bloco: dict[Celula, float] = {c: -9.0 for c in partida.obstaculos}
        self.corte = 0.0
        self.dobra_rastro = 0.0
        self.camada_fantasma = pygame.Surface((ARENA_L, ARENA_A), pygame.SRCALPHA)
        self.fundo = pygame.Surface((tema.LARGURA, tema.ALTURA)).convert()
        self.quadros = 0
        rng = random.Random(5)
        self.poeira = [
            [rng.uniform(0, ARENA_L), rng.uniform(0, ARENA_A), rng.uniform(5, 16), rng.uniform(0, 6.28)]
            for _ in range(26)
        ]

    def reagir(self, eventos: list[Evento]) -> None:
        """Dispara os efeitos visuais dos eventos do último tick."""
        e = self.efeitos
        for evento in eventos:
            if isinstance(evento, Comeu):
                self._comeu(evento)
            elif isinstance(evento, ComidaNasceu):
                self.nascimento_comida[evento.celula] = self.tempo
                x, y = centro(evento.celula)
                e.onda(x, y, desenho.CORES_COMIDA[evento.tipo], 30, 0.3)
            elif isinstance(evento, ComidaExpirou):
                x, y = centro(evento.celula)
                e.explosao(x, y, (tema.TEXTO_SUAVE,), 10, 90, 0.4, 6)
            elif isinstance(evento, PowerUpAtivado):
                cor = CORES_POWER_UP[evento.power_up]
                x, y = self.cobra.posicao_cabeca
                e.onda(x, y, cor, 150, 0.55)
                e.flash(cor, 0.22)
                e.flutuar(x, y - 28, evento.power_up.rotulo, cor, 24)
            elif isinstance(evento, PowerUpExpirou):
                x, y = self.cobra.posicao_cabeca
                e.onda(x, y, CORES_POWER_UP[evento.power_up], 50, 0.3)
            elif isinstance(evento, Encolheu):
                for celula in evento.removidas:
                    x, y = centro(celula)
                    e.explosao(x, y, (tema.CIANO, tema.BRANCO), 12, 170, 0.5, 7)
            elif isinstance(evento, SubiuNivel):
                self._subiu_nivel(evento.nivel)
            elif isinstance(evento, ObstaculosNasceram):
                for celula in evento.celulas:
                    self.nascimento_bloco[celula] = self.tempo
                    x, y = centro(celula)
                    e.explosao(x, y, (self.cor_tema(),), 5, 90, 0.4, 6)
            elif isinstance(evento, Morreu):
                self.cobra.morta = True
            elif isinstance(evento, Virou):
                x, y = self.cobra.posicao_cabeca
                e.explosao(x, y, (self.cobra.bandas[-1][8],), 4, 70, 0.3, 5)

    def cor_tema(self) -> Cor:
        return tema.TEMAS[self.tema % len(tema.TEMAS)]

    def _comeu(self, evento: Comeu) -> None:
        e = self.efeitos
        x, y = centro(evento.celula)
        cor = desenho.CORES_COMIDA[evento.tipo]
        self.cobra.engolir()
        dourada = evento.tipo is TipoComida.DOURADA
        quantidade = 26 + evento.combo * 4 + (22 if dourada else 0)
        e.explosao(x, y, (cor, tema.misturar(cor, tema.BRANCO, 0.5), tema.BRANCO), quantidade, 300, 0.62)
        e.onda(x, y, cor, 74 + evento.combo * 7)
        e.tremer(2.5 + evento.combo * 0.45 + (3 if dourada else 0))
        tamanho = min(44, 24 + evento.combo * 2)
        e.flutuar(x, y - 12, f"+{evento.pontos}", tema.misturar(cor, tema.BRANCO, 0.35), tamanho)
        if evento.combo >= 2:
            e.flutuar(x, y + 22, f"COMBO x{evento.combo}", tema.OURO, 20)

    def _subiu_nivel(self, nivel: int) -> None:
        self.tema_anterior = self.tema
        self.tema = nivel - 1
        self.fade_tema = 0.0
        e = self.efeitos
        cor = self.cor_tema()
        e.flash(cor, 0.3)
        x, y = self.cobra.posicao_cabeca
        e.onda(x, y, cor, 220, 0.7)

    def desfazer_celula(self, celula: Celula) -> None:
        """Explode um pedaço do corpo durante a morte."""
        x, y = centro(celula)
        cores = self.cobra.bandas[-1]
        tons = (cores[4], cores[28], cores[56], tema.BRANCO)
        self.efeitos.explosao(x, y, tons, 12, 190, 0.7, 8, gravidade=240.0)

    def atualizar(self, dt: float) -> None:
        """Avança as animações do mundo."""
        self.tempo += dt
        self.fade_tema = min(1.0, self.fade_tema + dt / DURACAO_FADE_TEMA)
        self.cobra.atualizar(dt, self._comida_perto())
        self.efeitos.atualizar(dt)
        self._emitir_rastros(dt)

    def _comida_perto(self) -> bool:
        cabeca = self.partida.cobra.cabeca
        return any(
            abs(c.celula.x - cabeca.x) + abs(c.celula.y - cabeca.y) <= 2
            for c in self.partida.comidas
        )

    def _emitir_rastros(self, dt: float) -> None:
        ativos = self.partida.power_ups_ativos
        if not ativos or self.partida.acabou:
            return
        self.dobra_rastro += dt * 26
        if self.dobra_rastro < 1:
            return
        self.dobra_rastro -= 1
        x, y = self.cobra.posicao_cabeca
        for power_up in ativos:
            self.efeitos.rastro(x, y, CORES_POWER_UP[power_up])

    def alvo_olhar(self) -> tuple[float, float] | None:
        """Comida mais próxima, que os olhos da cobra acompanham."""
        comidas = self.partida.comidas
        if not comidas:
            return None
        hx, hy = self.cobra.posicao_cabeca
        return min(
            (centro(c.celula) for c in comidas),
            key=lambda p: (p[0] - hx) ** 2 + (p[1] - hy) ** 2,
        )

    def desenhar(self, tela: pygame.Surface, alpha: float) -> None:
        """Desenha céu, tabuleiro, comidas, cobra e efeitos."""
        if self.quadros % QUADROS_POR_FUNDO == 0 or self.fade_tema < 1.0:
            self._compor_fundo()
        self.quadros += 1
        ox, oy = self.efeitos.deslocamento
        ax, ay = ARENA_X + ox, ARENA_Y + oy
        if ox or oy:
            tela.blit(cenario.ceu(), (0, 0))
        tela.blit(self.fundo, (ox, oy))
        tela.set_clip(pygame.Rect(ax, ay, ARENA_L, ARENA_A))
        self._desenhar_blocos(tela, ax, ay)
        self._desenhar_comidas(tela, ax, ay)
        self._desenhar_cobra(tela, ax, ay, alpha)
        tela.set_clip(None)
        self._desenhar_moldura(tela, ax, ay)
        self.efeitos.desenhar(tela, ax, ay)

    def _compor_fundo(self) -> None:
        """Junta céu, tabuleiro, clima e halo da moldura numa imagem só."""
        fundo = self.fundo
        fundo.blit(cenario.ceu(), (0, 0))
        self._desenhar_tabuleiro(fundo, ARENA_X, ARENA_Y)
        self._desenhar_clima(fundo, ARENA_X, ARENA_Y)
        m = cenario.MARGEM_MOLDURA
        fundo.blit(
            cenario.moldura_brilho(self.tema),
            (ARENA_X - m, ARENA_Y - m),
            special_flags=desenho.ADITIVO,
        )

    def _desenhar_tabuleiro(self, tela: pygame.Surface, ax: int, ay: int) -> None:
        if self.fade_tema < 1.0:
            tela.blit(cenario.tabuleiro(self.tema_anterior), (ax, ay))
            novo = cenario.tabuleiro(self.tema)
            novo.set_alpha(int(255 * self.fade_tema))
            tela.blit(novo, (ax, ay))
            novo.set_alpha(None)
        else:
            tela.blit(cenario.tabuleiro(self.tema), (ax, ay))

    def _desenhar_clima(self, tela: pygame.Surface, ax: int, ay: int) -> None:
        cor = self.cor_tema()
        t = self.tempo
        x1 = ARENA_L * (0.5 + 0.42 * math.sin(t * 0.17))
        y1 = ARENA_A * (0.5 + 0.40 * math.cos(t * 0.23))
        x2 = ARENA_L * (0.5 + 0.42 * math.sin(t * 0.13 + 2.4))
        y2 = ARENA_A * (0.5 + 0.40 * math.cos(t * 0.19 + 1.1))
        desenho.somar_brilho(tela, ax + x1, ay + y1, cor, 300, 10)
        desenho.somar_brilho(tela, ax + x2, ay + y2, tema.VIOLETA, 260, 8)
        lote = []
        halo = desenho.brilho(cor, 5, 40)
        for x, y, velocidade, fase in self.poeira:
            px = (x + math.sin(t * 0.4 + fase) * 22) % ARENA_L
            py = (y - t * velocidade) % ARENA_A
            lote.append((halo, (int(px) + ax - 5, int(py) + ay - 5)))
        tela.fblits(lote, desenho.ADITIVO)

    def _desenhar_blocos(self, tela: pygame.Surface, ax: int, ay: int) -> None:
        obstaculos = self.partida.obstaculos
        if not obstaculos:
            return
        base = cenario.bloco(self.tema)
        for celula in obstaculos:
            idade = self.tempo - self.nascimento_bloco.get(celula, -9.0)
            x = ax + celula.x * CELULA
            y = ay + celula.y * CELULA
            if idade >= DURACAO_NASCER:
                tela.blit(base, (x, y))
                continue
            tamanho = max(2, int(CELULA * saida_elastica(idade / DURACAO_NASCER)))
            menor = pygame.transform.smoothscale(base, (tamanho, tamanho))
            tela.blit(menor, menor.get_rect(center=(x + CELULA // 2, y + CELULA // 2)))

    def _desenhar_comidas(self, tela: pygame.Surface, ax: int, ay: int) -> None:
        t = self.tempo
        partida = self.partida
        for comida in partida.comidas:
            cx, cy = centro(comida.celula)
            cx += ax
            cy += ay
            idade = t - self.nascimento_comida.get(comida.celula, -9.0)
            surgir = saida_elastica(idade / DURACAO_NASCER)
            pulso = 1 + 0.07 * math.sin(t * 5.2 + comida.celula.x)
            flutua = math.sin(t * 3.4 + comida.celula.y) * 2.2
            cor = desenho.CORES_COMIDA[comida.tipo]
            desenho.somar_brilho(tela, cx, cy, cor, 46, 42 if comida.tipo.eh_especial else 30)
            sombra = desenho.disco(int(20 * surgir) + 2, (6, 7, 16))
            sombra.set_alpha(110)
            tela.blit(sombra, sombra.get_rect(center=(int(cx), int(cy) + 13)))
            sombra.set_alpha(255)

            piscando = comida.piscando(partida.tempo_s)
            if piscando and int(t * 9) % 2 == 0:
                continue
            tamanho = max(2, int(TAMANHO_COMIDA * surgir * pulso))
            base = desenho.sprite_comida(comida.tipo, TAMANHO_COMIDA)
            sprite = pygame.transform.smoothscale(base, (tamanho, tamanho))
            tela.blit(sprite, sprite.get_rect(center=(int(cx), int(cy + flutua))))

            vida = comida.vida_restante(partida.tempo_s)
            if vida is not None:
                desenho.arco(tela, (cx, cy), 21, vida / config.VIDA_ESPECIAL_S, cor)
            if comida.tipo is TipoComida.DOURADA and int(t * 4) % 3 == 0:
                self.efeitos.rastro(cx - ax, cy - ay, tema.OURO, 5)

    def _desenhar_cobra(self, tela: pygame.Surface, ax: int, ay: int, alpha: float) -> None:
        cobra = self.partida.cobra
        alvo = self.alvo_olhar()
        fantasma = PowerUp.FANTASMA in self.partida.power_ups_ativos
        if fantasma:
            camada = self.camada_fantasma
            camada.fill((0, 0, 0, 0))
            self.cobra.desenhar(camada, (0, 0), cobra, alpha, alvo, False, self.corte)
            camada.set_alpha(int(150 + 40 * math.sin(self.tempo * 9)))
            tela.blit(camada, (ax, ay))
        else:
            self.cobra.desenhar(tela, (ax, ay), cobra, alpha, alvo, True, self.corte)

    def _desenhar_moldura(self, tela: pygame.Surface, ax: int, ay: int) -> None:
        cor = tema.misturar(self.cor_tema(), tema.BRANCO, 0.1 + 0.1 * math.sin(self.tempo * 2.2))
        pygame.draw.rect(tela, cor, (ax - 3, ay - 3, ARENA_L + 6, ARENA_A + 6), 3, border_radius=8)

