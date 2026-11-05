"""Barra superior da partida: pontos, recorde, combo, nível, tempo e power-ups."""
from __future__ import annotations

import pygame

from cobrinha.nucleo.partida import Partida
from cobrinha.nucleo.tipos import TipoComida
from cobrinha.render import desenho, tema
from cobrinha.render.efeitos import saida_cubica
from cobrinha.render.mundo import CORES_POWER_UP
from cobrinha.render.tema import ARENA_L, ARENA_X

Y_ROTULO = 16
Y_VALOR = 39


class Hud:
    """Mostra o estado da partida, com animação nos números."""

    def __init__(self, recorde: int) -> None:
        self.recorde = recorde
        self.pontos_vistos = 0.0
        self.pontos_antes = 0
        self.pop = 0.0
        self.pop_combo = 0.0
        self.combo_antes = 1
        self.tempo = 0.0

    def atualizar(self, dt: float, partida: Partida) -> None:
        """Faz o placar correr até o valor real."""
        self.tempo += dt
        if partida.pontos != self.pontos_antes:
            self.pontos_antes = partida.pontos
            self.pop = 1.0
        diferenca = partida.pontos - self.pontos_vistos
        self.pontos_vistos += diferenca * min(1.0, dt * 14)
        if abs(diferenca) < 1:
            self.pontos_vistos = partida.pontos
        self.pop = max(0.0, self.pop - dt * 4.5)
        if partida.combo > self.combo_antes:
            self.pop_combo = 1.0
        self.combo_antes = partida.combo
        self.pop_combo = max(0.0, self.pop_combo - dt * 4.0)

    def desenhar(self, tela: pygame.Surface, partida: Partida) -> None:
        """Desenha a barra."""
        self._pontos(tela, partida)
        self._nivel_e_tempo(tela, partida)
        self._combo(tela, partida)
        self._power_ups(tela, partida)

    def _rotulo(self, tela, conteudo: str, x: float, ancora: str = "midleft") -> None:
        desenho.escrever(tela, conteudo, 13, (x, Y_ROTULO), tema.TEXTO_SUAVE, "forte", ancora)

    def _pontos(self, tela: pygame.Surface, partida: Partida) -> None:
        self._rotulo(tela, "PONTOS", ARENA_X)
        valor = f"{int(self.pontos_vistos):,}".replace(",", ".")
        base = desenho.texto(valor, 26, tema.TEXTO, "titulo")
        if self.pop > 0:
            escala = 1 + 0.28 * saida_cubica(self.pop)
            base = pygame.transform.smoothscale_by(base, escala)
        tela.blit(base, base.get_rect(midleft=(ARENA_X, Y_VALOR)))

        batido = partida.pontos > self.recorde and self.recorde > 0
        cor = tema.OURO if batido else tema.TEXTO_SUAVE
        self._rotulo(tela, "RECORDE", ARENA_X + 190)
        melhor = f"{max(self.recorde, partida.pontos):,}".replace(",", ".")
        desenho.escrever(tela, melhor, 22, (ARENA_X + 190, Y_VALOR), cor, "titulo", "midleft")

    def _nivel_e_tempo(self, tela: pygame.Surface, partida: Partida) -> None:
        x = ARENA_X + 370
        self._rotulo(tela, "NÍVEL", x)
        desenho.escrever(tela, str(partida.nivel), 22, (x, Y_VALOR), tema.TEXTO, "titulo", "midleft")
        if partida.tempo_restante_s is None:
            return
        x += 90
        self._rotulo(tela, "TEMPO", x)
        restante = partida.tempo_restante_s
        alerta = restante <= 10 and int(self.tempo * 5) % 2 == 0
        cor = tema.VERMELHO if alerta else tema.TEXTO
        minutos, segundos = divmod(int(restante + 0.999), 60)
        desenho.escrever(
            tela, f"{minutos}:{segundos:02d}", 22, (x, Y_VALOR), cor, "titulo", "midleft"
        )

    def _combo(self, tela: pygame.Surface, partida: Partida) -> None:
        if partida.combo <= 1:
            return
        centro_x = ARENA_X + ARENA_L * 0.60
        tamanho = 28 + int(10 * self.pop_combo)
        desenho.escrever(
            tela, f"x{partida.combo}", tamanho, (centro_x - 64, 32), tema.OURO, "titulo"
        )
        largura = 150
        y = 28
        trilho = pygame.Rect(int(centro_x - 34), y, largura, 8)
        pygame.draw.rect(tela, (38, 42, 70), trilho, border_radius=4)
        cheio = int(largura * partida.fracao_combo)
        if cheio > 2:
            pygame.draw.rect(
                tela, tema.OURO, (trilho.x, trilho.y, cheio, 8), border_radius=4
            )
        desenho.escrever(
            tela, "COMBO", 13, (trilho.x, y - 11), tema.TEXTO_SUAVE, "forte", "midleft"
        )

    def _power_ups(self, tela: pygame.Surface, partida: Partida) -> None:
        x = ARENA_X + ARENA_L - 18
        for power_up, restante in partida.power_ups_ativos.items():
            fracao = restante / power_up.duracao_s
            if restante < 1.5 and int(self.tempo * 10) % 2 == 0:
                x -= 48
                continue
            sprite = desenho.sprite_comida(TipoComida[power_up.name], 34)
            tela.blit(sprite, sprite.get_rect(center=(x, 30)))
            desenho.arco(tela, (x, 30), 20, fracao, CORES_POWER_UP[power_up])
            x -= 48

