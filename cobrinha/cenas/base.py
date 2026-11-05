"""Base das cenas e a lista de opções usada em todos os menus."""
from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass
from typing import TYPE_CHECKING

import pygame

from cobrinha.entrada import Acao
from cobrinha.render import desenho, tema

if TYPE_CHECKING:
    from cobrinha.app import App


class Cena:
    """Uma tela do jogo."""

    def __init__(self, app: "App") -> None:
        self.app = app

    def acao(self, acao: Acao) -> None:
        """Recebe uma ação do jogador."""

    def mouse(self, evento: pygame.event.Event) -> None:
        """Recebe um evento de mouse."""

    def atualizar(self, dt: float) -> None:
        """Avança a cena."""

    def desenhar(self, tela: pygame.Surface) -> None:
        """Desenha a cena."""

    def perdeu_foco(self) -> None:
        """Avisa que a janela perdeu o foco."""


@dataclass
class Item:
    """Uma linha de menu: botão ou seletor de valor."""

    rotulo: str
    confirmar: Callable[[], None] | None = None
    mudar: Callable[[int], None] | None = None
    valor: Callable[[], str] | None = None


class ListaMenu:
    """Lista navegável por teclado, gamepad e mouse."""

    def __init__(
        self,
        app: "App",
        itens: list[Item],
        centro_x: int,
        y: int,
        largura: int = 460,
        passo: int = 52,
        tamanho: int = 25,
    ) -> None:
        self.app = app
        self.itens = itens
        self.centro_x = centro_x
        self.y = y
        self.largura = largura
        self.passo = passo
        self.tamanho = tamanho
        self.selecionado = 0
        self.y_barra = float(y)
        self.tempo = 0.0

    def _retangulo(self, indice: int) -> pygame.Rect:
        return pygame.Rect(
            self.centro_x - self.largura // 2,
            self.y + indice * self.passo,
            self.largura,
            self.passo - 6,
        )

    def acao(self, acao: Acao) -> None:
        """Navega ou aciona o item selecionado."""
        item = self.itens[self.selecionado]
        if acao in (Acao.CIMA, Acao.BAIXO):
            passo = -1 if acao is Acao.CIMA else 1
            self.selecionado = (self.selecionado + passo) % len(self.itens)
            self.app.audio.tocar("menu_mover")
        elif acao in (Acao.ESQUERDA, Acao.DIREITA) and item.mudar:
            item.mudar(-1 if acao is Acao.ESQUERDA else 1)
            self.app.audio.tocar("menu_mudar")
        elif acao is Acao.CONFIRMAR:
            self._confirmar(item, 1)

    def _confirmar(self, item: Item, sentido: int) -> None:
        if item.confirmar:
            self.app.audio.tocar("menu_ok")
            item.confirmar()
        elif item.mudar:
            item.mudar(sentido)
            self.app.audio.tocar("menu_mudar")

    def mouse(self, evento: pygame.event.Event) -> None:
        """Seleciona ao passar e aciona ao clicar."""
        if evento.type not in (pygame.MOUSEMOTION, pygame.MOUSEBUTTONDOWN):
            return
        for indice, item in enumerate(self.itens):
            retangulo = self._retangulo(indice)
            if not retangulo.collidepoint(evento.pos):
                continue
            if indice != self.selecionado:
                self.selecionado = indice
                self.app.audio.tocar("menu_mover")
            if evento.type == pygame.MOUSEBUTTONDOWN and evento.button == 1:
                self._confirmar(item, -1 if evento.pos[0] < retangulo.centerx else 1)
            return

    def atualizar(self, dt: float) -> None:
        """Desliza a barra de seleção."""
        self.tempo += dt
        alvo = self._retangulo(self.selecionado).y
        self.y_barra += (alvo - self.y_barra) * min(1.0, dt * 20)

    def desenhar(self, tela: pygame.Surface) -> None:
        """Desenha a barra e os itens."""
        barra = desenho.painel(self.largura, self.passo - 6, (30, 36, 72), 235, 12, tema.CIANO)
        x = self.centro_x - self.largura // 2
        tela.blit(barra, (x, int(self.y_barra)))
        for indice, item in enumerate(self.itens):
            retangulo = self._retangulo(indice)
            ativo = indice == self.selecionado
            cor = tema.TEXTO if ativo else tema.TEXTO_SUAVE
            if item.valor is None:
                desenho.escrever(tela, item.rotulo, self.tamanho, retangulo.center, cor, "forte")
                continue
            desenho.escrever(
                tela, item.rotulo, self.tamanho, (retangulo.x + 22, retangulo.centery), cor,
                "forte", "midleft",
            )
            valor = item.valor()
            direita = retangulo.right - 22
            cor_valor = tema.CIANO if ativo else tema.TEXTO_SUAVE
            caixa = desenho.escrever(
                tela, valor, self.tamanho - 2, (direita - (20 if ativo else 0), retangulo.centery),
                cor_valor, "ui", "midright",
            )
            if ativo and item.mudar:
                self._setas(tela, caixa, retangulo, cor_valor)

    @staticmethod
    def _setas(tela, caixa: pygame.Rect, retangulo: pygame.Rect, cor) -> None:
        y = retangulo.centery
        for x, sentido in ((caixa.left - 14, -1), (caixa.right + 14, 1)):
            pygame.draw.polygon(
                tela, cor, [(x + 5 * sentido, y), (x - 4 * sentido, y - 7), (x - 4 * sentido, y + 7)]
            )


def formatar_tempo(segundos: float) -> str:
    """Converte segundos em m:ss."""
    minutos, resto = divmod(int(segundos), 60)
    return f"{minutos}:{resto:02d}"


def formatar_pontos(pontos: int) -> str:
    """Separa os milhares com ponto."""
    return f"{pontos:,}".replace(",", ".")
