"""A partida em si: contagem, jogo, pausa, morte e tela final."""
from __future__ import annotations

from datetime import date
from typing import TYPE_CHECKING

import pygame

from cobrinha.cenas.base import Cena, Item, ListaMenu, formatar_pontos, formatar_tempo
from cobrinha.entrada import DIRECOES, Acao
from cobrinha.nucleo.partida import Partida, Regras
from cobrinha.nucleo.tipos import (
    ComboPerdido,
    Comeu,
    ComidaExpirou,
    Dificuldade,
    Evento,
    Modo,
    Morreu,
    PowerUpAtivado,
    PowerUpExpirou,
    SubiuNivel,
    TempoEsgotou,
    TipoComida,
    Venceu,
    Virou,
)
from cobrinha.persistencia import Recorde
from cobrinha.render import cenario, desenho, tema
from cobrinha.render.efeitos import saida_cubica, saida_elastica
from cobrinha.render.hud import Hud
from cobrinha.render.mundo import Mundo

if TYPE_CHECKING:
    from cobrinha.app import App

CONTAGEM_S = 0.62
CONTAGEM_RETOMAR_S = 0.4
IMPACTO_S = 0.16
ESPERA_CORTINA_S = 0.3
DURACAO_BANNER = 1.25
DURACAO_VAI = 0.6
CENTRO_ARENA = (tema.ARENA_X + tema.ARENA_L // 2, tema.ARENA_Y + tema.ARENA_A // 2)
CARTAO_X, CARTAO_Y, CARTAO_L, CARTAO_A = 250, 110, 780, 510


class CenaJogo(Cena):
    """Controla uma partida do início ao fim."""

    def __init__(self, app: "App", modo: Modo, dificuldade: Dificuldade) -> None:
        super().__init__(app)
        self.modo = modo
        self.dificuldade = dificuldade
        self.tela_pausa: pygame.Surface | None = None
        self.veu = pygame.Surface((tema.LARGURA, tema.ALTURA))
        self.veu.fill((5, 6, 18))
        self.lista_pausa = ListaMenu(
            app,
            [
                Item("Continuar", confirmar=self._retomar),
                Item("Recomeçar", confirmar=self.recomecar),
                Item("Voltar ao menu", confirmar=self._sair),
            ],
            tema.LARGURA // 2,
            320,
            largura=380,
        )
        self.lista_fim = ListaMenu(
            app,
            [
                Item("Jogar de novo", confirmar=self.recomecar),
                Item("Voltar ao menu", confirmar=self._sair),
            ],
            CARTAO_X + 200,
            CARTAO_Y + CARTAO_A - 126,
            largura=320,
        )
        cenario.preaquecer()
        self.recomecar()
        self.tempo_estado = -ESPERA_CORTINA_S

    def recomecar(self) -> None:
        """Começa uma partida nova, sem trocar de cena."""
        config = self.app.config
        self.partida = Partida(Regras(self.modo, self.dificuldade))
        self.mundo = Mundo(self.partida, config.skin, config.tremor, config.flash)
        self.hud = Hud(self.app.dados.melhor(self.modo, self.dificuldade))
        self.acumulador = 0.0
        self.banner: tuple[str, tema.Cor] | None = None
        self.idade_banner = 0.0
        self.idade_vai = DURACAO_VAI
        self.posicao_recorde: int | None = None
        self.novo_recorde = False
        self.titulo_fim = "FIM DE JOGO"
        self.resumo = None
        self.tempo_fim = 0.0
        self.segmentos_mortos: list = []
        self.proximo_morto = 0
        self.duracao_morte = 1.0
        self.lista_fim.selecionado = 0
        self.app.audio.abafar(False)
        self._entrar("contagem", CONTAGEM_S)

    def _entrar(self, estado: str, passo_contagem: float = CONTAGEM_S) -> None:
        self.estado = estado
        self.tempo_estado = 0.0
        self.passo_contagem = passo_contagem
        self.numero_tocado = 0

    def _sair(self) -> None:
        from cobrinha.cenas.menu import CenaMenu

        self.app.audio.abafar(False)
        self.app.trocar(lambda: CenaMenu(self.app))

    def _pausar(self) -> None:
        tela = self.app.tela
        pequena = pygame.transform.smoothscale(tela, (tema.LARGURA // 6, tema.ALTURA // 6))
        self.tela_pausa = pygame.transform.smoothscale(pequena, (tema.LARGURA, tema.ALTURA))
        self.lista_pausa.selecionado = 0
        self.app.audio.abafar(True)
        self.app.audio.tocar("pausa")
        self._entrar("pausa")

    def _retomar(self) -> None:
        self.app.audio.abafar(False)
        self.app.audio.tocar("retomar")
        self._entrar("contagem", CONTAGEM_RETOMAR_S)

    def perdeu_foco(self) -> None:
        if self.estado in ("jogando", "contagem"):
            self._pausar()

    def acao(self, acao: Acao) -> None:
        if self.estado in ("jogando", "contagem"):
            if acao in DIRECOES:
                self.partida.virar(DIRECOES[acao])
            elif acao in (Acao.PAUSAR, Acao.VOLTAR):
                self._pausar()
        elif self.estado == "pausa":
            if acao in (Acao.PAUSAR, Acao.VOLTAR):
                self._retomar()
            elif acao is Acao.REINICIAR:
                self.recomecar()
            else:
                self.lista_pausa.acao(acao)
        elif self.estado == "fim":
            if acao is Acao.REINICIAR:
                self.recomecar()
            elif acao is Acao.VOLTAR:
                self._sair()
            else:
                self.lista_fim.acao(acao)

    def mouse(self, evento: pygame.event.Event) -> None:
        if self.estado == "pausa":
            self.lista_pausa.mouse(evento)
        elif self.estado == "fim":
            self.lista_fim.mouse(evento)

    def _alpha(self) -> float:
        if self.partida.acabou:
            return 1.0
        return min(1.0, self.acumulador * self.partida.ticks_por_segundo)

    def atualizar(self, dt: float) -> None:
        self.tempo_estado += dt
        if self.estado == "pausa":
            self.lista_pausa.atualizar(dt)
            return
        if self.estado == "contagem":
            self._atualizar_contagem()
        elif self.estado == "jogando":
            self._atualizar_jogo(dt)
        elif self.estado == "impacto":
            if self.tempo_estado >= IMPACTO_S:
                self._iniciar_morte()
            return  # o mundo congela por um instante: é o que dá peso à batida
        elif self.estado == "morrendo":
            self._atualizar_morte()
        elif self.estado == "fim":
            self.tempo_fim += dt
            self.lista_fim.atualizar(dt)
        self.mundo.atualizar(dt)
        self.hud.atualizar(dt, self.partida)
        self.idade_vai = min(DURACAO_VAI, self.idade_vai + dt)
        if self.banner:
            self.idade_banner += dt
            if self.idade_banner >= DURACAO_BANNER:
                self.banner = None

    def _atualizar_contagem(self) -> None:
        if self.tempo_estado < 0:
            return
        passo = int(self.tempo_estado / self.passo_contagem)
        if passo >= 3:
            self.app.audio.tocar("vai")
            self.idade_vai = 0.0
            self._entrar("jogando")
        elif passo >= self.numero_tocado:
            self.numero_tocado = passo + 1
            self.app.audio.tocar("conta")

    def _atualizar_jogo(self, dt: float) -> None:
        self.acumulador += dt
        periodo = 1.0 / self.partida.ticks_por_segundo
        while self.acumulador >= periodo and not self.partida.acabou:
            self.acumulador -= periodo
            eventos = self.partida.tick()
            self.mundo.reagir(eventos)
            self._reagir(eventos)
            periodo = 1.0 / self.partida.ticks_por_segundo

    def _reagir(self, eventos: list[Evento]) -> None:
        audio = self.app.audio
        for evento in eventos:
            if isinstance(evento, Comeu):
                if evento.tipo is TipoComida.MACA:
                    audio.comer(evento.combo)
                elif evento.tipo is TipoComida.DOURADA:
                    audio.tocar("dourada")
                elif evento.tipo is TipoComida.ENCOLHER:
                    audio.tocar("encolher")
            elif isinstance(evento, PowerUpAtivado):
                audio.tocar("powerup")
            elif isinstance(evento, PowerUpExpirou):
                audio.tocar("expirar")
            elif isinstance(evento, ComidaExpirou):
                audio.tocar("sumiu")
            elif isinstance(evento, ComboPerdido):
                audio.tocar("combo_perdido")
            elif isinstance(evento, Virou):
                audio.tocar("virar")
            elif isinstance(evento, SubiuNivel):
                audio.tocar("nivel")
                self.banner = (f"NÍVEL {evento.nivel}", self.mundo.cor_tema())
                self.idade_banner = 0.0
            elif isinstance(evento, Morreu):
                self._morreu()
            elif isinstance(evento, TempoEsgotou):
                self._terminar("TEMPO ESGOTADO")
            elif isinstance(evento, Venceu):
                self._terminar("VOCÊ VENCEU!")

    def _morreu(self) -> None:
        self.app.audio.tocar("morrer")
        self.mundo.efeitos.tremer(16)
        self.mundo.efeitos.flash(tema.VERMELHO, 0.8)
        self._entrar("impacto")

    def _terminar(self, titulo: str) -> None:
        self.titulo_fim = titulo
        self._abrir_cartao()

    def _iniciar_morte(self) -> None:
        self.segmentos_mortos = list(self.partida.cobra.segmentos)
        self.duracao_morte = min(1.5, 0.3 + len(self.segmentos_mortos) * 0.035)
        self.proximo_morto = len(self.segmentos_mortos) - 1
        self._entrar("morrendo")

    def _atualizar_morte(self) -> None:
        progresso = min(1.0, self.tempo_estado / self.duracao_morte)
        self.mundo.corte = progresso
        total = len(self.segmentos_mortos)
        limite = int((1.0 - progresso) * total)
        while self.proximo_morto >= limite and self.proximo_morto >= 0:
            self.mundo.desfazer_celula(self.segmentos_mortos[self.proximo_morto])
            self.proximo_morto -= 1
        if progresso >= 1.0:
            self.mundo.cobra.visivel = False
            self._abrir_cartao()

    def _abrir_cartao(self) -> None:
        resumo = self.partida.estatisticas()
        self.resumo = resumo
        anterior = self.app.dados.melhor(self.modo, self.dificuldade)
        self.posicao_recorde = self.app.dados.registrar(
            self.modo,
            self.dificuldade,
            Recorde(
                pontos=resumo.pontos,
                data=date.today().isoformat(),
                comidas=resumo.comidas,
                tempo_s=round(resumo.tempo_s, 1),
                nivel=resumo.nivel,
                combo=resumo.maior_combo,
            ),
        )
        self.novo_recorde = resumo.pontos > anterior
        audio = self.app.audio
        audio.abafar(True)
        cores = (tema.OURO, tema.CIANO, tema.ROSA, tema.VIOLETA, tema.VERDE)
        if self.partida.venceu:
            audio.tocar("vitoria")
            self.mundo.efeitos.confete(cores, 180)
        elif self.novo_recorde:
            audio.tocar("recorde")
            self.mundo.efeitos.confete(cores, 130)
        else:
            audio.tocar("fim")
        self.tempo_fim = 0.0
        self._entrar("fim")

    def desenhar(self, tela: pygame.Surface) -> None:
        if self.estado == "pausa":
            self._desenhar_pausa(tela)
            return
        self.mundo.desenhar(tela, self._alpha())
        self.hud.desenhar(tela, self.partida)
        if self.estado == "contagem":
            self._desenhar_contagem(tela)
        elif self.idade_vai < DURACAO_VAI:
            self._desenhar_numero(tela, "VAI!", self.idade_vai / DURACAO_VAI, tema.VERDE, 110)
        if self.banner:
            self._desenhar_banner(tela)
        if self.estado == "fim":
            self._desenhar_cartao(tela)
        self.mundo.efeitos.desenhar_flash(tela)

    def _desenhar_numero(
        self, tela: pygame.Surface, conteudo: str, t: float, cor: tema.Cor, tamanho: int = 150
    ) -> None:
        base = desenho.texto(conteudo, tamanho, cor, "titulo")
        escala = 1.7 - 0.7 * saida_cubica(min(1.0, t * 2.2))
        imagem = pygame.transform.smoothscale_by(base, escala)
        imagem.set_alpha(255 if t < 0.65 else int(255 * (1 - (t - 0.65) / 0.35)))
        tela.blit(imagem, imagem.get_rect(center=(CENTRO_ARENA[0], CENTRO_ARENA[1] - 150)))

    def _desenhar_contagem(self, tela: pygame.Surface) -> None:
        if self.tempo_estado < 0:
            return
        passo = min(2, int(self.tempo_estado / self.passo_contagem))
        t = (self.tempo_estado - passo * self.passo_contagem) / self.passo_contagem
        cor = (tema.ROSA, tema.OURO, tema.CIANO)[passo]
        self._desenhar_numero(tela, str(3 - passo), t, cor)

    def _desenhar_banner(self, tela: pygame.Surface) -> None:
        conteudo, cor = self.banner
        t = self.idade_banner / DURACAO_BANNER
        y = tema.ARENA_Y + 130 - 14 * saida_cubica(t)
        alpha = 255 if t < 0.7 else int(255 * (1 - (t - 0.7) / 0.3))
        base = desenho.texto(conteudo, 60, tema.misturar(cor, tema.BRANCO, 0.3), "titulo")
        escala = 0.6 + 0.4 * saida_elastica(min(1.0, t * 5))
        imagem = pygame.transform.smoothscale_by(base, escala)
        imagem.set_alpha(alpha)
        tela.blit(imagem, imagem.get_rect(center=(CENTRO_ARENA[0], int(y))))

    def _desenhar_pausa(self, tela: pygame.Surface) -> None:
        tela.blit(self.tela_pausa, (0, 0))
        self.veu.set_alpha(150)
        tela.blit(self.veu, (0, 0))
        halo = desenho.halo_texto("PAUSA", 72, tema.CIANO)
        tela.blit(halo, halo.get_rect(center=(tema.LARGURA // 2, 210)), special_flags=desenho.ADITIVO)
        desenho.escrever(tela, "PAUSA", 72, (tema.LARGURA / 2, 210), tema.TEXTO, "titulo")
        self.lista_pausa.desenhar(tela)
        desenho.escrever(
            tela,
            f"{self.modo.rotulo}, {self.dificuldade.rotulo}",
            20,
            (tema.LARGURA / 2, 510),
            tema.TEXTO_SUAVE,
        )

    def _desenhar_cartao(self, tela: pygame.Surface) -> None:
        entrada = saida_cubica(min(1.0, self.tempo_fim / 0.4))
        self.veu.set_alpha(int(165 * entrada))
        tela.blit(self.veu, (0, 0))
        y = CARTAO_Y + int((1 - entrada) * 44)
        borda = tema.OURO if self.novo_recorde or self.partida.venceu else tema.CIANO
        tela.blit(desenho.painel(CARTAO_L, CARTAO_A, tema.PAINEL, 240, 22, borda), (CARTAO_X, y))
        esquerda = CARTAO_X + 40
        centro_esquerda = CARTAO_X + 200
        desenho.escrever(tela, self.titulo_fim, 38, (CARTAO_X + CARTAO_L / 2, y + 48), tema.TEXTO, "titulo")

        contagem = saida_cubica(min(1.0, self.tempo_fim / 0.9))
        pontos = int(self.resumo.pontos * contagem)
        desenho.escrever(tela, "PONTOS", 16, (centro_esquerda, y + 104), tema.TEXTO_SUAVE, "forte")
        desenho.escrever(tela, formatar_pontos(pontos), 54, (centro_esquerda, y + 146), borda, "titulo")
        if self.novo_recorde:
            pulso = 1 + 0.06 * abs(((self.tempo_fim * 2.4) % 2) - 1)
            selo = pygame.transform.smoothscale_by(
                desenho.texto("NOVO RECORDE!", 24, tema.OURO, "forte"), pulso
            )
            tela.blit(selo, selo.get_rect(center=(centro_esquerda, y + 194)))

        linhas = (
            ("Comidas", str(self.resumo.comidas)),
            ("Maior combo", f"x{self.resumo.maior_combo}"),
            ("Tamanho", str(self.resumo.comprimento)),
            ("Tempo", formatar_tempo(self.resumo.tempo_s)),
        )
        for indice, (rotulo, valor) in enumerate(linhas):
            linha = y + 228 + indice * 30
            desenho.escrever(tela, rotulo, 19, (esquerda, linha), tema.TEXTO_SUAVE, "ui", "midleft")
            desenho.escrever(tela, valor, 20, (esquerda + 320, linha), tema.TEXTO, "forte", "midright")

        self.lista_fim.y = y + CARTAO_A - 126
        self.lista_fim.desenhar(tela)
        self._desenhar_top5(tela, y)

    def _desenhar_top5(self, tela: pygame.Surface, y: int) -> None:
        x = CARTAO_X + 420
        largura = 320
        topo = y + 100
        desenho.escrever(
            tela, "MELHORES PONTUAÇÕES", 16, (x + largura / 2, topo), tema.TEXTO_SUAVE, "forte"
        )
        desenho.escrever(
            tela,
            f"{self.modo.rotulo}, {self.dificuldade.rotulo}",
            16,
            (x + largura / 2, topo + 24),
            tema.TEXTO_APAGADO,
        )
        tabela = self.app.dados.recordes(self.modo, self.dificuldade)
        for indice, recorde in enumerate(tabela):
            linha = topo + 66 + indice * 46
            atual = self.posicao_recorde == indice + 1
            if atual:
                tela.blit(desenho.painel(largura, 40, (70, 56, 20), 200, 10), (x, linha - 20))
            cor = tema.OURO if atual else tema.TEXTO
            desenho.escrever(tela, f"{indice + 1}.", 20, (x + 16, linha), tema.TEXTO_SUAVE, "forte", "midleft")
            desenho.escrever(tela, formatar_pontos(recorde.pontos), 23, (x + 56, linha), cor, "titulo", "midleft")
            desenho.escrever(
                tela, formatar_tempo(recorde.tempo_s), 18, (x + largura - 16, linha),
                tema.TEXTO_SUAVE, "ui", "midright",
            )
        if not tabela:
            desenho.escrever(
                tela, "Sem pontos desta vez.", 20, (x + largura / 2, topo + 90), tema.TEXTO_SUAVE
            )
