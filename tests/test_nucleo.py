"""Regras do jogo, sem pygame."""
import pytest

from cobrinha import config
from cobrinha.nucleo.bot import escolher_direcao
from cobrinha.nucleo.partida import (
    Cobra,
    Comida,
    Partida,
    Regras,
    arena_conectada,
    sortear_celula_livre,
)
from cobrinha.nucleo.tipos import (
    Celula,
    ComboPerdido,
    Comeu,
    ComidaExpirou,
    Dificuldade,
    Direcao,
    Encolheu,
    Modo,
    Morreu,
    PowerUp,
    PowerUpExpirou,
    SubiuNivel,
    TempoEsgotou,
    TipoComida,
    Venceu,
    Virou,
)


def nova(modo=Modo.CLASSICO, dificuldade=Dificuldade.NORMAL, **extras):
    return Partida(Regras(modo, dificuldade, semente=1, **extras))


def por_comida(partida, celula, tipo=TipoComida.MACA, expira_s=None):
    partida.comidas[:] = [Comida(celula, tipo, expira_s)]


def frente(partida, passos=1):
    cabeca = partida.cobra.cabeca
    direcao = partida.cobra.direcao
    return Celula(cabeca.x + direcao.dx * passos, cabeca.y + direcao.dy * passos)


def comer_em_frente(partida, tipo=TipoComida.MACA):
    por_comida(partida, frente(partida), tipo)
    return partida.tick()


def sem_especiais(monkeypatch):
    monkeypatch.setattr(config, "CHANCE_ESPECIAL_POR_TICK", 0.0)


def test_comeca_no_centro_indo_para_a_direita():
    partida = nova()
    assert partida.cobra.comprimento == config.TAMANHO_INICIAL
    assert partida.cobra.direcao is Direcao.DIREITA
    assert partida.cobra.cabeca == Celula(config.GRADE_LARGURA // 2, config.GRADE_ALTURA // 2)


def test_anda_uma_celula_sem_crescer():
    partida = nova()
    por_comida(partida, Celula(0, 0))
    destino = frente(partida)
    partida.tick()
    assert partida.cobra.cabeca == destino
    assert partida.cobra.comprimento == config.TAMANHO_INICIAL


def test_cresce_um_tick_depois_de_comer():
    partida = nova()
    comer_em_frente(partida)
    assert partida.cobra.comprimento == config.TAMANHO_INICIAL
    por_comida(partida, Celula(0, 0))
    partida.tick()
    assert partida.cobra.comprimento == config.TAMANHO_INICIAL + 1


def test_duas_viradas_rapidas_valem_em_ticks_seguidos():
    partida = nova()
    por_comida(partida, Celula(0, 0))
    assert partida.virar(Direcao.CIMA)
    assert partida.virar(Direcao.ESQUERDA)
    primeiro = partida.tick()
    assert Virou(Direcao.CIMA) in primeiro
    segundo = partida.tick()
    assert Virou(Direcao.ESQUERDA) in segundo
    assert not partida.acabou


def test_inversao_de_180_graus_e_ignorada():
    cobra = nova().cobra
    assert not cobra.virar(Direcao.ESQUERDA)
    assert cobra.virar(Direcao.CIMA)
    assert not cobra.virar(Direcao.BAIXO)  # seria 180° em relação à virada na fila


def test_fila_de_viradas_tem_limite():
    cobra = nova().cobra
    assert cobra.virar(Direcao.CIMA)
    assert cobra.virar(Direcao.ESQUERDA)
    assert not cobra.virar(Direcao.BAIXO)


def test_cabeca_entra_na_celula_que_a_cauda_libera():
    partida = nova()
    corpo = [Celula(1, 0), Celula(1, 1), Celula(0, 1), Celula(0, 0)]
    partida.cobra = Cobra(corpo, Direcao.ESQUERDA)
    por_comida(partida, Celula(9, 9))
    partida.tick()
    assert not partida.acabou
    assert partida.cobra.cabeca == Celula(0, 0)


def test_cauda_nao_libera_a_celula_se_a_cobra_esta_crescendo():
    partida = nova()
    corpo = [Celula(1, 0), Celula(1, 1), Celula(0, 1), Celula(0, 0)]
    partida.cobra = Cobra(corpo, Direcao.ESQUERDA)
    partida.cobra.crescimento_pendente = 1
    por_comida(partida, Celula(9, 9))
    eventos = partida.tick()
    assert Morreu("corpo", Celula(1, 0)) in eventos


def test_parede_mata_no_classico():
    partida = nova()
    por_comida(partida, Celula(0, 0))
    eventos = []
    while not partida.acabou:
        eventos = partida.tick()
    assert partida.causa_fim == "parede"
    assert any(isinstance(e, Morreu) for e in eventos)
    assert partida.tick() == []


def test_sem_paredes_a_cobra_da_a_volta():
    partida = nova(Modo.ATRAVESSAR)
    por_comida(partida, Celula(0, 0))
    for _ in range(config.GRADE_LARGURA):
        por_comida(partida, Celula(0, 0))
        partida.tick()
    assert not partida.acabou
    assert partida.cobra.cabeca.y == config.GRADE_ALTURA // 2


def test_corpo_mata_e_fantasma_atravessa():
    corpo = [Celula(5, 5), Celula(6, 5), Celula(6, 6), Celula(5, 6), Celula(4, 6), Celula(4, 5)]
    partida = nova()
    partida.cobra = Cobra(corpo, Direcao.BAIXO)
    por_comida(partida, Celula(0, 0))
    assert any(isinstance(e, Morreu) for e in partida.tick())

    partida = nova()
    partida.cobra = Cobra(corpo, Direcao.BAIXO)
    partida.power_ups_ativos[PowerUp.FANTASMA] = 5.0
    por_comida(partida, Celula(0, 0))
    partida.tick()
    assert not partida.acabou


def test_obstaculo_mata_mesmo_com_fantasma():
    partida = nova()
    partida.power_ups_ativos[PowerUp.FANTASMA] = 5.0
    partida.obstaculos.add(frente(partida))
    por_comida(partida, Celula(0, 0))
    assert any(isinstance(e, Morreu) and e.causa == "obstaculo" for e in partida.tick())


def test_combo_sobe_comendo_rapido_e_some_no_prazo(monkeypatch):
    sem_especiais(monkeypatch)
    partida = nova(Modo.ATRAVESSAR)
    assert comer_em_frente(partida)[0].combo == 1
    segundo = next(e for e in comer_em_frente(partida) if isinstance(e, Comeu))
    assert segundo.combo == 2
    assert segundo.pontos == config.PONTOS_MACA * 2
    assert 0 < partida.fracao_combo <= 1

    perdeu = []
    for _ in range(80):
        por_comida(partida, Celula(0, 0) if partida.cobra.cabeca.y else Celula(0, 1))
        perdeu += [e for e in partida.tick() if isinstance(e, ComboPerdido)]
        if perdeu:
            break
    assert perdeu == [ComboPerdido(2)]
    assert partida.combo == 1


def test_combo_tem_teto(monkeypatch):
    sem_especiais(monkeypatch)
    partida = nova(Modo.ATRAVESSAR)
    for _ in range(config.COMBO_MAXIMO + 5):
        comer_em_frente(partida)
    assert partida.combo == config.COMBO_MAXIMO
    assert partida.maior_combo == config.COMBO_MAXIMO


def test_nivel_sobe_e_acelera_ate_o_maximo(monkeypatch):
    sem_especiais(monkeypatch)
    partida = nova(Modo.ATRAVESSAR)
    inicial, maximo = config.DIFICULDADES["NORMAL"]
    assert partida.ticks_por_segundo == inicial
    eventos = []
    for _ in range(config.COMIDAS_POR_NIVEL):
        eventos += comer_em_frente(partida)
    assert SubiuNivel(2) in eventos
    assert partida.ticks_por_segundo == inicial + config.INCREMENTO_VELOCIDADE_POR_NIVEL
    partida.nivel = 500
    assert partida.ticks_por_segundo == maximo


@pytest.mark.parametrize("dificuldade", list(Dificuldade))
def test_cada_dificuldade_tem_velocidade_propria(dificuldade):
    partida = nova(dificuldade=dificuldade)
    assert partida.ticks_por_segundo == config.DIFICULDADES[dificuldade.name][0]


def test_dourada_vale_50_e_cresce_3():
    partida = nova()
    comer_em_frente(partida, TipoComida.DOURADA)
    assert partida.pontos == config.PONTOS_DOURADA
    assert partida.cobra.crescimento_pendente == config.CRESCIMENTO_DOURADA


def test_multiplicador_dobra_os_pontos():
    partida = nova(Modo.ATRAVESSAR)
    partida.power_ups_ativos[PowerUp.MULTIPLICADOR] = 5.0
    comer_em_frente(partida)
    assert partida.pontos == config.PONTOS_MACA * config.FATOR_MULTIPLICADOR


def test_veloz_e_lenta_mudam_a_velocidade_e_se_cancelam():
    partida = nova()
    base = partida.ticks_por_segundo
    comer_em_frente(partida, TipoComida.VELOZ)
    assert partida.ticks_por_segundo == pytest.approx(base * config.FATOR_VELOZ)
    eventos = comer_em_frente(partida, TipoComida.LENTA)
    assert PowerUpExpirou(PowerUp.VELOZ) in eventos
    assert partida.ticks_por_segundo == pytest.approx(base * config.FATOR_LENTA)


def test_power_up_expira_com_evento():
    partida = nova()
    partida.power_ups_ativos[PowerUp.FANTASMA] = 0.01
    por_comida(partida, Celula(0, 0))
    assert PowerUpExpirou(PowerUp.FANTASMA) in partida.tick()
    assert PowerUp.FANTASMA not in partida.power_ups_ativos


def test_encolher_respeita_o_minimo():
    partida = nova()
    partida.cobra = Cobra(
        [Celula(10 - i, 5) for i in range(5)], Direcao.DIREITA
    )
    eventos = comer_em_frente(partida, TipoComida.ENCOLHER)
    assert partida.cobra.comprimento == config.COMPRIMENTO_MINIMO
    removidas = next(e for e in eventos if isinstance(e, Encolheu)).removidas
    assert len(removidas) == 2


def test_especial_some_no_prazo(monkeypatch):
    sem_especiais(monkeypatch)
    partida = nova()
    partida.comidas.append(Comida(Celula(0, 0), TipoComida.DOURADA, partida.tempo_s + 0.01))
    eventos = partida.tick()
    assert ComidaExpirou(Celula(0, 0), TipoComida.DOURADA) in eventos
    assert all(not c.tipo.eh_especial for c in partida.comidas)


def test_comida_pisca_antes_de_sumir():
    comida = Comida(Celula(0, 0), TipoComida.VELOZ, 10.0)
    assert not comida.piscando(0.0)
    assert comida.piscando(10.0 - config.PISCAR_ESPECIAL_S)
    assert not Comida(Celula(0, 0), TipoComida.MACA).piscando(99.0)


def test_modo_tempo_esgota_e_comer_da_bonus(monkeypatch):
    sem_especiais(monkeypatch)
    partida = nova(Modo.TEMPO)
    assert partida.tempo_restante_s == config.TEMPO_INICIAL_S
    antes = partida.tempo_restante_s
    comer_em_frente(partida)
    assert partida.tempo_restante_s > antes
    partida.tempo_restante_s = 0.001
    por_comida(partida, Celula(0, 0))
    eventos = partida.tick()
    assert any(isinstance(e, TempoEsgotou) for e in eventos)
    assert partida.acabou and partida.causa_fim == "tempo"


def test_vitoria_quando_a_arena_enche():
    partida = nova(largura=4, altura=3)
    caminho = [Celula(x, 0) for x in range(4)]
    caminho += [Celula(x, 1) for x in range(3, -1, -1)]
    caminho += [Celula(x, 2) for x in range(3)]
    partida.cobra = Cobra(list(reversed(caminho)), Direcao.DIREITA)
    partida.cobra.crescimento_pendente = 1
    por_comida(partida, Celula(3, 2))
    eventos = partida.tick()
    assert any(isinstance(e, Venceu) for e in eventos)
    assert partida.venceu and partida.acabou


def test_sortear_celula_livre():
    import random

    rng = random.Random(1)
    assert sortear_celula_livre(rng, 2, 1, {Celula(0, 0)}) == Celula(1, 0)
    assert sortear_celula_livre(rng, 1, 1, {Celula(0, 0)}) is None


def test_arena_conectada_detecta_divisao():
    muro = {Celula(2, y) for y in range(5)}
    assert not arena_conectada(5, 5, muro)
    assert arena_conectada(5, 5, muro - {Celula(2, 2)})


def test_obstaculos_crescem_sem_dividir_a_arena(monkeypatch):
    sem_especiais(monkeypatch)
    partida = nova(Modo.OBSTACULOS)
    assert partida.obstaculos
    linha_inicial = config.GRADE_ALTURA // 2
    assert all(c.y != linha_inicial for c in partida.obstaculos)
    tamanhos = [len(partida.obstaculos)]
    for _ in range(8):
        partida._adicionar_obstaculos([])
        tamanhos.append(len(partida.obstaculos))
    assert tamanhos[-1] > tamanhos[0]
    assert arena_conectada(config.GRADE_LARGURA, config.GRADE_ALTURA, partida.obstaculos)
    celulas = config.GRADE_LARGURA * config.GRADE_ALTURA
    assert len(partida.obstaculos) <= celulas * (config.DENSIDADE_MAXIMA_OBSTACULOS + 0.05)


@pytest.mark.parametrize("modo", list(Modo))
@pytest.mark.parametrize("semente", range(6))
def test_invariantes_em_partidas_inteiras(modo, semente):
    partida = Partida(Regras(modo, Dificuldade.INSANO, semente=semente))
    for _ in range(1500):
        if partida.acabou:
            break
        partida.virar(escolher_direcao(partida))
        partida.tick()
        corpo = list(partida.cobra.segmentos)
        if PowerUp.FANTASMA not in partida.power_ups_ativos and not partida.acabou:
            assert len(set(corpo)) == len(corpo)
        ocupadas = set(corpo) | partida.obstaculos
        for comida in partida.comidas:
            if comida.celula != partida.cobra.cabeca:
                assert comida.celula not in ocupadas
        assert sum(not c.tipo.eh_especial for c in partida.comidas) == (0 if partida.venceu else 1)
        assert sum(c.tipo.eh_especial for c in partida.comidas) <= 1
    assert partida.total_comidas > 0


def test_mesma_semente_gera_a_mesma_partida():
    def jogar():
        partida = nova(Modo.OBSTACULOS)
        eventos = []
        for _ in range(300):
            partida.virar(escolher_direcao(partida))
            eventos += partida.tick()
        return eventos, partida.pontos

    assert jogar() == jogar()
