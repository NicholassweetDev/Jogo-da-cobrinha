"""Menu principal com uma partida de demonstração rodando ao fundo."""
from __future__ import annotations

import math
from datetime import date
from typing import TYPE_CHECKING

import pygame

from cobrinha.cenas.base import Cena, Item, ListaMenu, formatar_pontos, formatar_tempo
from cobrinha.entrada import Acao
from cobrinha.nucleo.bot import escolher_direcao
from cobrinha.nucleo.partida import Partida, Regras
from cobrinha.nucleo.tipos import Dificuldade, Modo, TipoComida
from cobrinha.render import desenho, tema
from cobrinha.render.mundo import Mundo

if TYPE_CHECKING:
    from cobrinha.app import App

TITULO = "COBRINHA"
DESCRICAO_MODO = {
    Modo.CLASSICO: "Bater na parede ou no corpo encerra a partida.",
    Modo.ATRAVESSAR: "As paredes viram portais: saia de um lado e volte do outro.",
    Modo.OBSTACULOS: "Novos muros surgem na arena a cada nível.",
    Modo.TEMPO: "Comer rende segundos extras. Marque o máximo antes de zerar.",
}
AJUDA_COMIDAS = (
    (TipoComida.MACA, "+10 pontos, cresce 1"),
    (TipoComida.DOURADA, "+50 pontos, cresce 3"),
    (TipoComida.VELOZ, "Mais veloz por 6 s"),
    (TipoComida.LENTA, "Câmera lenta por 6 s"),
    (TipoComida.FANTASMA, "Atravessa o corpo por 7 s"),
    (TipoComida.ENCOLHER, "Perde 3 pedaços"),
    (TipoComida.MULTIPLICADOR, "Pontos em dobro por 10 s"),
)
AJUDA_CONTROLES = (
    ("Setas ou WASD", "Mover"),
    ("P ou Esc", "Pausar"),
    ("R", "Recomeçar"),
    ("M", "Som ligado ou mudo"),
    ("F11", "Tela cheia"),
    ("Gamepad", "Direcional, A e Start"),
)


def _ciclar(lista: list, atual, passo: int):
    return lista[(lista.index(atual) + passo) % len(lista)]


class CenaMenu(Cena):
    """Tela inicial e suas páginas: recordes, opções e ajuda."""

    def __init__(self, app: "App") -> None:
        super().__init__(app)
        self.tempo = 0.0
        self.pagina = "principal"
        self.acumulador = 0.0
        self.espera_demo = 0.0
        self.veu = pygame.Surface((tema.LARGURA, tema.ALTURA))
        self.veu.fill((6, 7, 20))
        self.veu.set_alpha(158)
        self._nova_demo()
        cx = tema.LARGURA // 2
        self.lista_principal = ListaMenu(
            app,
            [
                Item("JOGAR", confirmar=self._jogar),
                Item("Modo", mudar=self._mudar_modo, valor=lambda: self._modo().rotulo),
                Item(
                    "Dificuldade",
                    mudar=self._mudar_dificuldade,
                    valor=lambda: self._dificuldade().rotulo,
                ),
                Item("Cobra", mudar=self._mudar_skin, valor=lambda: self.app.config.skin),
                Item("Recordes", confirmar=lambda: self._abrir("recordes")),
                Item("Opções", confirmar=lambda: self._abrir("opcoes")),
                Item("Como jogar", confirmar=lambda: self._abrir("ajuda")),
                Item("Sair", confirmar=self.app.sair),
            ],
            cx,
            232,
        )
        self.lista_opcoes = ListaMenu(
            app,
            [
                Item(
                    "Música",
                    mudar=lambda p: self._volume("volume_musica", p),
                    valor=lambda: f"{round(self.app.config.volume_musica * 100)}%",
                ),
                Item(
                    "Efeitos",
                    mudar=lambda p: self._volume("volume_efeitos", p),
                    valor=lambda: f"{round(self.app.config.volume_efeitos * 100)}%",
                ),
                Item(
                    "Tremor da tela",
                    mudar=lambda _: self._alternar("tremor"),
                    valor=lambda: "Ligado" if self.app.config.tremor else "Desligado",
                ),
                Item(
                    "Clarões",
                    mudar=lambda _: self._alternar("flash"),
                    valor=lambda: "Ligados" if self.app.config.flash else "Desligados",
                ),
                Item(
                    "Tela cheia",
                    mudar=lambda _: self.app.alternar_tela_cheia(),
                    valor=lambda: "Ligada" if self.app.config.tela_cheia else "Desligada",
                ),
                Item("Voltar", confirmar=lambda: self._abrir("principal")),
            ],
            cx,
            240,
            largura=520,
        )
        self.lista_recordes = ListaMenu(
            app,
            [
                Item("Modo", mudar=self._mudar_modo, valor=lambda: self._modo().rotulo),
                Item(
                    "Dificuldade",
                    mudar=self._mudar_dificuldade,
                    valor=lambda: self._dificuldade().rotulo,
                ),
                Item("Voltar", confirmar=lambda: self._abrir("principal")),
            ],
            cx,
            186,
            largura=520,
            passo=48,
        )

    def _modo(self) -> Modo:
        return Modo[self.app.config.modo]

    def _dificuldade(self) -> Dificuldade:
        return Dificuldade[self.app.config.dificuldade]

    def _nova_demo(self) -> None:
        self.demo = Partida(Regras(Modo.CLASSICO, Dificuldade.NORMAL))
        self.mundo = Mundo(self.demo, self.app.config.skin, tremor=False, flash=False)

    def _abrir(self, pagina: str) -> None:
        self.pagina = pagina
        self.app.dados.salvar()

    def _jogar(self) -> None:
        from cobrinha.cenas.jogo import CenaJogo

        self.app.dados.salvar()
        modo, dificuldade = self._modo(), self._dificuldade()
        self.app.trocar(lambda: CenaJogo(self.app, modo, dificuldade))

    def _mudar_modo(self, passo: int) -> None:
        self.app.config.modo = _ciclar(list(Modo), self._modo(), passo).name

    def _mudar_dificuldade(self, passo: int) -> None:
        self.app.config.dificuldade = _ciclar(list(Dificuldade), self._dificuldade(), passo).name

    def _mudar_skin(self, passo: int) -> None:
        self.app.config.skin = _ciclar(list(tema.SKINS), self.app.config.skin, passo)
        self._nova_demo()

    def _volume(self, campo: str, passo: int) -> None:
        atual = getattr(self.app.config, campo)
        setattr(self.app.config, campo, round(max(0.0, min(1.0, atual + passo * 0.1)), 1))
        self.app.audio.aplicar_volumes()

    def _alternar(self, campo: str) -> None:
        setattr(self.app.config, campo, not getattr(self.app.config, campo))

    def _lista_atual(self) -> ListaMenu | None:
        return {
            "principal": self.lista_principal,
            "opcoes": self.lista_opcoes,
            "recordes": self.lista_recordes,
        }.get(self.pagina)

    def acao(self, acao: Acao) -> None:
        if acao in (Acao.VOLTAR, Acao.PAUSAR) and self.pagina != "principal":
            self.app.audio.tocar("menu_voltar")
            self._abrir("principal")
            return
        lista = self._lista_atual()
        if lista is not None:
            lista.acao(acao)
        elif acao is Acao.CONFIRMAR:
            self.app.audio.tocar("menu_voltar")
            self._abrir("principal")

    def mouse(self, evento: pygame.event.Event) -> None:
        lista = self._lista_atual()
        if lista is not None:
            lista.mouse(evento)
        elif evento.type == pygame.MOUSEBUTTONDOWN:
            self._abrir("principal")

    def atualizar(self, dt: float) -> None:
        self.tempo += dt
        lista = self._lista_atual()
        if lista is not None:
            lista.atualizar(dt)
        if self.demo.acabou:
            self.espera_demo += dt
            if self.espera_demo > 1.4:
                self.espera_demo = 0.0
                self._nova_demo()
        else:
            self.acumulador += dt
            periodo = 1.0 / self.demo.ticks_por_segundo
            while self.acumulador >= periodo and not self.demo.acabou:
                self.acumulador -= periodo
                self.demo.virar(escolher_direcao(self.demo))
                self.mundo.reagir(self.demo.tick())
        self.mundo.atualizar(dt)

    def desenhar(self, tela: pygame.Surface) -> None:
        periodo = 1.0 / self.demo.ticks_por_segundo
        alpha = 1.0 if self.demo.acabou else min(1.0, self.acumulador / periodo)
        self.mundo.desenhar(tela, alpha)
        tela.blit(self.veu, (0, 0))
        if self.pagina == "principal":
            self._titulo(tela, 118, 96)
            self.lista_principal.desenhar(tela)
            desenho.escrever(
                tela, DESCRICAO_MODO[self._modo()], 20, (tema.LARGURA / 2, 660), tema.TEXTO_SUAVE
            )
            desenho.escrever(
                tela,
                "Setas para navegar, Enter para escolher",
                16,
                (tema.LARGURA / 2, 692),
                tema.TEXTO_APAGADO,
            )
        elif self.pagina == "opcoes":
            self._titulo_pagina(tela, "OPÇÕES")
            self.lista_opcoes.desenhar(tela)
        elif self.pagina == "recordes":
            self._titulo_pagina(tela, "RECORDES")
            self.lista_recordes.desenhar(tela)
            self._tabela_recordes(tela)
        else:
            self._titulo_pagina(tela, "COMO JOGAR")
            self._ajuda(tela)

    def _titulo(self, tela: pygame.Surface, y: int, tamanho: int) -> None:
        fonte = desenho.fonte("titulo", tamanho)
        largura = fonte.size(TITULO)[0]
        x = (tema.LARGURA - largura) / 2
        halo = desenho.halo_texto(TITULO, tamanho, tema.CIANO)
        tela.blit(halo, halo.get_rect(center=(tema.LARGURA // 2, y)), special_flags=desenho.ADITIVO)
        paradas = tema.paleta_skin(self.app.config.skin)[0][-1]
        for indice, letra in enumerate(TITULO):
            onda = math.sin(self.tempo * 2.6 - indice * 0.55)
            cor = paradas[int(indice / len(TITULO) * 40)]
            superficie = desenho.texto(letra, tamanho, tema.misturar(cor, tema.BRANCO, 0.25), "titulo")
            tela.blit(superficie, superficie.get_rect(midleft=(int(x), int(y + onda * 7))))
            x += fonte.size(letra)[0]

    def _titulo_pagina(self, tela: pygame.Surface, conteudo: str) -> None:
        halo = desenho.halo_texto(conteudo, 56, tema.CIANO)
        tela.blit(halo, halo.get_rect(center=(tema.LARGURA // 2, 110)), special_flags=desenho.ADITIVO)
        desenho.escrever(tela, conteudo, 56, (tema.LARGURA / 2, 110), tema.TEXTO, "titulo")

    def _tabela_recordes(self, tela: pygame.Surface) -> None:
        x, y, largura = 320, 346, 640
        tela.blit(desenho.painel(largura, 300, tema.PAINEL, 220, 16), (x, y))
        tabela = self.app.dados.recordes(self._modo(), self._dificuldade())
        if not tabela:
            desenho.escrever(
                tela, "Nenhuma partida ainda.", 24, (x + largura / 2, y + 120), tema.TEXTO_SUAVE
            )
        for indice, recorde in enumerate(tabela):
            linha = y + 38 + indice * 44
            cor = tema.OURO if indice == 0 else tema.TEXTO
            desenho.escrever(tela, f"{indice + 1}.", 22, (x + 34, linha), tema.TEXTO_SUAVE, "forte", "midleft")
            desenho.escrever(tela, formatar_pontos(recorde.pontos), 26, (x + 84, linha), cor, "titulo", "midleft")
            detalhe = f"{recorde.comidas} comidas, {formatar_tempo(recorde.tempo_s)}"
            desenho.escrever(tela, detalhe, 18, (x + 340, linha), tema.TEXTO_SUAVE, "ui", "midright")
            desenho.escrever(tela, _data_curta(recorde.data), 18, (x + largura - 30, linha), tema.TEXTO_APAGADO, "ui", "midright")
        dados = self.app.dados
        resumo = (
            f"{dados.partidas} partidas, {dados.comidas_totais} comidas, "
            f"{formatar_tempo(dados.tempo_total_s)} de jogo"
        )
        desenho.escrever(tela, resumo, 18, (x + largura / 2, y + 274), tema.TEXTO_APAGADO)

    def _ajuda(self, tela: pygame.Surface) -> None:
        tela.blit(desenho.painel(1000, 470, tema.PAINEL, 225, 18), (140, 170))
        desenho.escrever(tela, "COMIDAS", 20, (190, 206), tema.CIANO, "forte", "midleft")
        for indice, (tipo, descricao) in enumerate(AJUDA_COMIDAS):
            y = 250 + indice * 50
            sprite = desenho.sprite_comida(tipo, 38)
            tela.blit(sprite, sprite.get_rect(center=(210, y)))
            desenho.escrever(tela, tipo.rotulo, 22, (246, y - 11), tema.TEXTO, "forte", "midleft")
            desenho.escrever(tela, descricao, 18, (246, y + 12), tema.TEXTO_SUAVE, "ui", "midleft")
        desenho.escrever(tela, "CONTROLES", 20, (660, 206), tema.CIANO, "forte", "midleft")
        for indice, (tecla, efeito) in enumerate(AJUDA_CONTROLES):
            y = 250 + indice * 44
            desenho.escrever(tela, tecla, 22, (660, y), tema.TEXTO, "forte", "midleft")
            desenho.escrever(tela, efeito, 20, (840, y), tema.TEXTO_SUAVE, "ui", "midleft")
        desenho.escrever(
            tela,
            "Comer rápido sobe o combo, e cada comida vale mais.",
            20,
            (660, 530),
            tema.OURO,
            "ui",
            "midleft",
        )
        desenho.escrever(
            tela, "Enter ou Esc para voltar", 18, (tema.LARGURA / 2, 672), tema.TEXTO_APAGADO
        )


def _data_curta(data_iso: str) -> str:
    """Mostra a data no formato brasileiro."""
    try:
        return date.fromisoformat(data_iso).strftime("%d/%m/%Y")
    except (TypeError, ValueError):
        return ""
