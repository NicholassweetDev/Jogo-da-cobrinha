"""Laço principal: janela, relógio, eventos e transição entre cenas."""
from __future__ import annotations

import asyncio
from collections.abc import Callable
from pathlib import Path

import pygame

from cobrinha import audio as modulo_audio
from cobrinha.audio import Audio
from cobrinha.cenas.base import Cena
from cobrinha.entrada import Acao, LeitorEixo, mapear_botao, mapear_hat, mapear_tecla
from cobrinha.nucleo.tipos import TipoComida
from cobrinha.persistencia import Armazenamento
from cobrinha.render import desenho, tema

FPS_MAXIMO = 120
DT_MAXIMO = 0.05
DURACAO_FECHAR = 0.3
DURACAO_ABRIR = 0.36
COR_CHAVE = (255, 0, 255)
COR_CORTINA = (7, 8, 22)


def _abrir_janela() -> pygame.Surface:
    """Abre a janela escalável; recua para o modo simples se o vídeo não suportar."""
    tamanho = (tema.LARGURA, tema.ALTURA)
    bandeiras = pygame.SCALED | pygame.RESIZABLE
    for tentativa in (
        lambda: pygame.display.set_mode(tamanho, bandeiras, vsync=1),
        lambda: pygame.display.set_mode(tamanho, bandeiras),
    ):
        try:
            return tentativa()
        except pygame.error:
            continue
    return pygame.display.set_mode(tamanho)


class App:
    """Dono da janela, dos dados salvos, do áudio e da cena atual."""

    def __init__(self, dados: Path | None = None) -> None:
        modulo_audio.preparar_mixer()
        pygame.init()
        pygame.display.set_caption("Jogo da Cobrinha")
        self.dados = Armazenamento(dados)
        self.config = self.dados.config
        self.tela = _abrir_janela()
        pygame.display.set_icon(desenho.sprite_comida(TipoComida.MACA, 64))
        self.audio = Audio(self.config)
        self.relogio = pygame.time.Clock()
        self.rodando = True
        self.mostrar_fps = False
        self.leitor_eixo = LeitorEixo()
        self.controles: dict[int, pygame.joystick.JoystickType] = {}
        self.cortina = pygame.Surface((tema.LARGURA, tema.ALTURA))
        self.cortina.set_colorkey(COR_CHAVE)
        self._troca: Callable[[], Cena] | None = None
        self._tamanho_janela: tuple[int, int] | None = None
        self._tempo_transicao = DURACAO_FECHAR + DURACAO_ABRIR
        if self.config.tela_cheia:
            self.config.tela_cheia = False
            self.alternar_tela_cheia()

        from cobrinha.cenas.menu import CenaMenu

        self.cena: Cena = CenaMenu(self)
        self._tempo_transicao = DURACAO_FECHAR  # o jogo abre já com a cortina subindo

    def sair(self) -> None:
        """Encerra o laço principal."""
        self.rodando = False

    def trocar(self, fabrica: Callable[[], Cena]) -> None:
        """Fecha a cortina, troca de cena e abre de novo."""
        if self._troca is None and not self._em_transicao:
            self._troca = fabrica
            self._tempo_transicao = 0.0

    @property
    def _em_transicao(self) -> bool:
        return self._tempo_transicao < DURACAO_FECHAR + DURACAO_ABRIR

    def alternar_tela_cheia(self) -> None:
        """Liga ou desliga a tela cheia, devolvendo a janela ao tamanho de antes."""
        try:
            if not self.config.tela_cheia:
                self._tamanho_janela = pygame.display.get_window_size()
            pygame.display.toggle_fullscreen()
            self.config.tela_cheia = not self.config.tela_cheia
            if not self.config.tela_cheia and self._tamanho_janela:
                pygame.Window.from_display_module().size = self._tamanho_janela
        except (pygame.error, AttributeError):
            pass

    def _acao(self, acao: Acao | None) -> None:
        if acao is None:
            return
        if acao is Acao.TELA_CHEIA:
            self.alternar_tela_cheia()
        elif acao is Acao.MUDO:
            self.config.mudo = not self.config.mudo
            self.audio.aplicar_volumes()
        elif acao is Acao.FPS:
            self.mostrar_fps = not self.mostrar_fps
        elif not self._em_transicao:
            self.cena.acao(acao)

    def _evento(self, evento: pygame.event.Event) -> None:
        tipo = evento.type
        if tipo == pygame.QUIT:
            self.sair()
        elif tipo == pygame.KEYDOWN:
            self._acao(mapear_tecla(evento.key))
        elif tipo in (pygame.MOUSEMOTION, pygame.MOUSEBUTTONDOWN):
            if not self._em_transicao:
                self.cena.mouse(evento)
        elif tipo == pygame.WINDOWFOCUSLOST:
            self.cena.perdeu_foco()
        elif tipo == pygame.JOYDEVICEADDED:
            controle = pygame.joystick.Joystick(evento.device_index)
            self.controles[controle.get_instance_id()] = controle
        elif tipo == pygame.JOYDEVICEREMOVED:
            self.controles.pop(evento.instance_id, None)
        elif tipo == pygame.JOYBUTTONDOWN:
            self._acao(mapear_botao(evento.button))
        elif tipo == pygame.JOYHATMOTION:
            self._acao(mapear_hat(evento.value))
        elif tipo == pygame.JOYAXISMOTION:
            self._acao(self.leitor_eixo.ler(evento.axis, evento.value))

    def _atualizar_transicao(self, dt: float) -> None:
        if not self._em_transicao:
            return
        antes = self._tempo_transicao
        self._tempo_transicao += dt
        if antes < DURACAO_FECHAR <= self._tempo_transicao and self._troca is not None:
            self.cena = self._troca()
            self._troca = None

    def _desenhar_transicao(self) -> None:
        if not self._em_transicao:
            return
        t = self._tempo_transicao
        if t < DURACAO_FECHAR:
            abertura = 1 - t / DURACAO_FECHAR
        else:
            abertura = (t - DURACAO_FECHAR) / DURACAO_ABRIR
        abertura = abertura * abertura * (3 - 2 * abertura)
        raio = int(abertura * 780)
        centro = (tema.LARGURA // 2, tema.ALTURA // 2)
        self.cortina.fill(COR_CORTINA)
        if raio > 0:
            pygame.draw.circle(self.cortina, COR_CHAVE, centro, raio)
        self.tela.blit(self.cortina, (0, 0))
        if raio > 2:
            pygame.draw.aacircle(self.tela, tema.CIANO, centro, raio, 3)

    def passo(self, dt: float) -> None:
        """Roda um quadro completo."""
        self.audio.passo()
        for evento in pygame.event.get():
            self._evento(evento)
        self._atualizar_transicao(dt)
        self.cena.atualizar(dt)
        self.cena.desenhar(self.tela)
        self._desenhar_transicao()
        if self.mostrar_fps:
            desenho.escrever(
                self.tela,
                f"{self.relogio.get_fps():.0f} FPS",
                16,
                (tema.LARGURA - 12, tema.ALTURA - 14),
                tema.TEXTO_SUAVE,
                "ui",
                "midright",
            )
        pygame.display.flip()

    async def rodar(self) -> None:
        """Laço assíncrono, compatível com a execução no navegador."""
        while self.rodando:
            dt = min(self.relogio.tick(FPS_MAXIMO) / 1000.0, DT_MAXIMO)
            self.passo(dt)
            await asyncio.sleep(0)
        self.dados.salvar()
        pygame.quit()


def executar() -> None:
    """Abre o jogo."""
    asyncio.run(App().rodar())
