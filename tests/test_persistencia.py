"""Recordes e configurações em disco."""
import json

from cobrinha.nucleo.tipos import Dificuldade, Modo
from cobrinha.persistencia import Armazenamento, Recorde, caminho_padrao

C, N = Modo.CLASSICO, Dificuldade.NORMAL


def recorde(pontos):
    return Recorde(pontos, "2026-11-05", comidas=3, tempo_s=10.0)


def test_arquivo_ausente_usa_padrao(tmp_path):
    dados = Armazenamento(tmp_path / "novo" / "dados.json")
    assert dados.melhor(C, N) == 0
    assert dados.config.skin == "Esmeralda"


def test_arquivo_corrompido_nao_derruba(tmp_path):
    caminho = tmp_path / "dados.json"
    for conteudo in ("{quebrado", "[1, 2]", '{"config": 5, "recordes": 7, "totais": []}'):
        caminho.write_text(conteudo, encoding="utf-8")
        dados = Armazenamento(caminho)
        assert dados.recordes(C, N) == []
        assert dados.config.volume_efeitos == 0.8


def test_campos_invalidos_sao_ignorados(tmp_path):
    caminho = tmp_path / "dados.json"
    caminho.write_text(
        json.dumps(
            {
                "config": {"volume_musica": "alto", "mudo": True, "desconhecido": 1},
                "recordes": {"CLASSICO/NORMAL": [{"pontos": 90, "data": "2026-01-01"}, "lixo", {"x": 1}]},
                "totais": {"partidas": "muitas"},
            }
        ),
        encoding="utf-8",
    )
    dados = Armazenamento(caminho)
    assert dados.config.volume_musica == 0.5
    assert dados.config.mudo is True
    assert [r.pontos for r in dados.recordes(C, N)] == [90]
    assert dados.partidas == 0


def test_top_5_ordenado_e_posicao(tmp_path):
    dados = Armazenamento(tmp_path / "dados.json")
    for pontos in (10, 50, 30, 20, 40):
        dados.registrar(C, N, recorde(pontos))
    assert [r.pontos for r in dados.recordes(C, N)] == [50, 40, 30, 20, 10]
    assert dados.registrar(C, N, recorde(35)) == 3
    assert dados.registrar(C, N, recorde(1)) is None
    assert len(dados.recordes(C, N)) == 5


def test_zero_ponto_nao_entra_na_tabela_mas_conta_a_partida(tmp_path):
    dados = Armazenamento(tmp_path / "dados.json")
    assert dados.registrar(C, N, recorde(0)) is None
    assert dados.recordes(C, N) == []
    assert dados.partidas == 1


def test_tabelas_separadas_por_modo_e_dificuldade(tmp_path):
    dados = Armazenamento(tmp_path / "dados.json")
    dados.registrar(C, N, recorde(100))
    assert dados.melhor(Modo.TEMPO, N) == 0
    assert dados.melhor(C, Dificuldade.INSANO) == 0


def test_salva_e_recarrega(tmp_path):
    caminho = tmp_path / "dados.json"
    dados = Armazenamento(caminho)
    dados.config.skin = "Neon"
    dados.registrar(C, N, recorde(77))
    novo = Armazenamento(caminho)
    assert novo.config.skin == "Neon"
    assert novo.melhor(C, N) == 77
    assert novo.partidas == 1
    assert novo.comidas_totais == 3
    assert not caminho.with_suffix(".tmp").exists()


def test_erro_de_disco_e_silencioso(tmp_path):
    arquivo = tmp_path / "arquivo"
    arquivo.write_text("x", encoding="utf-8")
    dados = Armazenamento(arquivo / "dados.json")  # o pai é um arquivo: não dá para criar
    dados.registrar(C, N, recorde(5))
    assert dados.melhor(C, N) == 5


def test_caminho_vem_da_variavel_de_ambiente(tmp_path, monkeypatch):
    monkeypatch.setenv("COBRINHA_DADOS", str(tmp_path / "x.json"))
    assert caminho_padrao() == tmp_path / "x.json"
