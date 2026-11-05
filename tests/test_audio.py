"""Síntese de som em Python puro."""
from array import array

from cobrinha.audio import sintetizador

TAXA = 22050


def test_todos_os_sons_tem_conteudo_e_nao_estouram():
    sons = sintetizador.receitas(TAXA)
    esperados = {f"comer{i}" for i in range(8)} | {
        "dourada", "powerup", "expirar", "sumiu", "encolher", "combo_perdido", "nivel",
        "morrer", "fim", "recorde", "vitoria", "conta", "vai", "pausa", "retomar",
        "menu_mover", "menu_mudar", "menu_ok", "menu_voltar", "virar",
    }
    assert esperados == set(sons)
    for nome, amostras in sons.items():
        pcm = array("h", sintetizador.para_pcm(amostras, 1))
        assert len(pcm) == len(amostras), nome
        assert max(abs(v) for v in pcm) > 500, nome
        assert max(abs(v) for v in pcm) <= 32767 * 0.91, nome


def test_tom_comeca_e_termina_sem_estalo():
    amostras = sintetizador.tom(TAXA, 440, None, 100, "quadrada", 0.5)
    assert abs(amostras[0]) < 0.05
    assert abs(amostras[-1]) < 0.05


def test_pcm_estereo_repete_o_sinal():
    pcm = array("h", sintetizador.para_pcm([0.1, -0.2], 2))
    assert len(pcm) == 4
    assert pcm[0] == pcm[1] and pcm[2] == pcm[3]


def test_musica_sai_em_pedacos_e_com_duracao_certa():
    passos = list(sintetizador.gerar_musica(TAXA, 2))
    assert all(p is None for p in passos[:-1])
    assert len(passos) > 100  # o trabalho se divide entre os quadros
    pcm = array("h", passos[-1])
    segundos = len(pcm) / 2 / TAXA
    assert abs(segundos - 8 * 4 * 60 / sintetizador.BPM) < 0.01
    assert 3000 < max(abs(v) for v in pcm) <= 32767
