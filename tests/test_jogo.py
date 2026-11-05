"""O jogo inteiro rodando sem janela, com eventos de verdade."""
import pygame
import pytest

from cobrinha.app import App
from cobrinha.cenas.jogo import CenaJogo
from cobrinha.cenas.menu import CenaMenu
from cobrinha.nucleo.bot import escolher_direcao
from cobrinha.nucleo.partida import Comida
from cobrinha.nucleo.tipos import Celula, Dificuldade, Modo, PowerUp, TipoComida
from cobrinha.persistencia import Armazenamento
from cobrinha.render import tema

DT = 1 / 60


@pytest.fixture(scope="module")
def app_base(tmp_path_factory):
    return App(tmp_path_factory.mktemp("dados") / "dados.json")


@pytest.fixture
def app(app_base, tmp_path):
    app_base.dados = Armazenamento(tmp_path / "dados.json")
    app_base.config = app_base.dados.config
    app_base.audio.config = app_base.config
    app_base.cena = CenaMenu(app_base)
    app_base._troca = None
    app_base._tempo_transicao = 99.0
    app_base.rodando = True
    pygame.event.clear()
    return app_base


def rodar(app, quadros):
    for _ in range(quadros):
        app.passo(DT)


def tecla(app, codigo):
    pygame.event.post(pygame.event.Event(pygame.KEYDOWN, key=codigo, mod=0, unicode="", scancode=0))
    app.passo(DT)


def iniciar(app, modo=Modo.CLASSICO, dificuldade=Dificuldade.NORMAL):
    app.cena = CenaJogo(app, modo, dificuldade)
    cena = app.cena
    while cena.estado == "contagem":
        app.passo(DT)
    assert cena.estado == "jogando"
    return cena


def cores_distintas(tela):
    pequena = pygame.transform.scale(tela, (160, 90))
    return len({tuple(pequena.get_at((x, y)))[:3] for x in range(160) for y in range(90)})


def test_menu_desenha_algo_rico(app):
    rodar(app, 30)
    assert cores_distintas(app.tela) > 300


def test_enter_no_menu_abre_a_partida(app):
    rodar(app, 5)
    tecla(app, pygame.K_RETURN)
    rodar(app, 40)
    assert isinstance(app.cena, CenaJogo)
    assert app.cena.estado == "contagem"


def test_navegacao_do_menu_pelo_teclado(app):
    menu = app.cena
    tecla(app, pygame.K_DOWN)
    assert menu.lista_principal.selecionado == 1
    tecla(app, pygame.K_RIGHT)
    assert app.config.modo == Modo.ATRAVESSAR.name
    tecla(app, pygame.K_DOWN)
    tecla(app, pygame.K_LEFT)
    assert app.config.dificuldade == Dificuldade.FACIL.name
    tecla(app, pygame.K_DOWN)
    tecla(app, pygame.K_RIGHT)
    assert app.config.skin == "Neon"


@pytest.mark.parametrize("pagina", ["recordes", "opcoes", "ajuda"])
def test_paginas_do_menu_abrem_e_voltam(app, pagina):
    app.cena._abrir(pagina)
    rodar(app, 3)
    tecla(app, pygame.K_ESCAPE)
    assert app.cena.pagina == "principal"


def test_opcoes_mudam_volume_e_alternam(app):
    menu = app.cena
    menu._abrir("opcoes")
    tecla(app, pygame.K_LEFT)
    assert app.config.volume_musica == 0.4
    for _ in range(12):
        tecla(app, pygame.K_LEFT)
    assert app.config.volume_musica == 0.0
    tecla(app, pygame.K_DOWN)
    tecla(app, pygame.K_DOWN)
    tecla(app, pygame.K_RETURN)
    assert app.config.tremor is False


def test_mouse_seleciona_e_clica(app):
    menu = app.cena
    lista = menu.lista_principal
    alvo = lista._retangulo(5).center
    pygame.event.post(pygame.event.Event(pygame.MOUSEMOTION, pos=alvo, rel=(0, 0), buttons=(0, 0, 0)))
    app.passo(DT)
    assert lista.selecionado == 5
    pygame.event.post(pygame.event.Event(pygame.MOUSEBUTTONDOWN, pos=alvo, button=1))
    app.passo(DT)
    assert menu.pagina == "opcoes"


def test_sair_pelo_menu_e_pelo_fechar_janela(app):
    app.cena.lista_principal.selecionado = 7
    tecla(app, pygame.K_RETURN)
    assert app.rodando is False
    app.rodando = True
    pygame.event.post(pygame.event.Event(pygame.QUIT))
    app.passo(DT)
    assert app.rodando is False


def test_setas_viram_a_cobra_e_contagem_guarda_a_virada(app):
    app.cena = CenaJogo(app, Modo.CLASSICO, Dificuldade.NORMAL)
    tecla(app, pygame.K_UP)
    assert list(app.cena.partida.cobra.fila_viradas)


def test_pausa_congela_e_retoma_com_contagem(app):
    cena = iniciar(app)
    tecla(app, pygame.K_p)
    assert cena.estado == "pausa"
    tick = cena.partida.tick_atual
    rodar(app, 60)
    assert cena.partida.tick_atual == tick
    tecla(app, pygame.K_RETURN)
    assert cena.estado == "contagem"
    rodar(app, 90)
    assert cena.estado == "jogando"
    assert cena.partida.tick_atual >= tick


def test_perder_o_foco_pausa(app):
    cena = iniciar(app)
    pygame.event.post(pygame.event.Event(pygame.WINDOWFOCUSLOST))
    app.passo(DT)
    assert cena.estado == "pausa"


def test_tecla_r_nao_reinicia_durante_o_jogo_mas_reinicia_na_pausa(app):
    cena = iniciar(app)
    partida = cena.partida
    tecla(app, pygame.K_r)
    assert cena.partida is partida
    tecla(app, pygame.K_p)
    tecla(app, pygame.K_r)
    assert cena.partida is not partida
    assert cena.estado == "contagem"


def test_morte_completa_ate_o_cartao_e_salva_recorde(app):
    cena = iniciar(app)
    partida = cena.partida
    partida.comidas[:] = [Comida(Celula(partida.cobra.cabeca.x + 1, partida.cobra.cabeca.y), TipoComida.DOURADA)]
    estados = []
    for _ in range(900):
        app.passo(DT)
        if not estados or estados[-1] != cena.estado:
            estados.append(cena.estado)
        if cena.estado == "fim":
            break
    assert estados == ["jogando", "impacto", "morrendo", "fim"]
    assert partida.causa_fim == "parede"
    assert app.dados.melhor(Modo.CLASSICO, Dificuldade.NORMAL) == 50
    assert cena.novo_recorde and cena.posicao_recorde == 1
    rodar(app, 80)
    tecla(app, pygame.K_RETURN)
    assert cena.estado == "contagem"
    assert cena.partida is not partida


def test_voltar_ao_menu_depois_do_fim(app):
    cena = iniciar(app)
    while cena.estado != "fim":
        app.passo(DT)
    tecla(app, pygame.K_ESCAPE)
    rodar(app, 40)
    assert isinstance(app.cena, CenaMenu)


def test_modo_tempo_termina_no_cartao(app):
    cena = iniciar(app, Modo.TEMPO)
    cena.partida.tempo_restante_s = 0.01
    rodar(app, 30)
    assert cena.estado == "fim"
    assert cena.titulo_fim == "TEMPO ESGOTADO"


@pytest.mark.parametrize("modo", list(Modo))
@pytest.mark.parametrize("skin", list(tema.SKINS))
def test_todos_os_modos_e_skins_rodam(app, modo, skin):
    app.config.skin = skin
    cena = iniciar(app, modo, Dificuldade.INSANO)
    partida = cena.partida
    partida.cobra.crescimento_pendente = 20
    for power_up in PowerUp:
        partida.power_ups_ativos[power_up] = 0.8
    for _ in range(150):
        if cena.estado == "jogando":
            partida.virar(escolher_direcao(partida))
        app.passo(DT)
    assert cores_distintas(app.tela) > 300


def test_tela_cheia_e_mudo_nao_quebram(app):
    tecla(app, pygame.K_F11)
    tecla(app, pygame.K_F11)
    tecla(app, pygame.K_m)
    assert app.config.mudo is True
    tecla(app, pygame.K_m)
    assert app.config.mudo is False


def test_musica_fica_pronta_rodando_quadros(app_base):
    for _ in range(400):
        app_base.audio.passo()
    assert app_base.audio._composicao is None
    assert app_base.audio._musica.get_length() > 15
