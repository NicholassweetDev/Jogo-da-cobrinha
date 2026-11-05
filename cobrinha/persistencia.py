"""Recordes e configurações salvos em JSON, tolerando arquivo ausente ou corrompido."""
from __future__ import annotations

import json
import os
from dataclasses import asdict, dataclass, fields
from pathlib import Path

from cobrinha.nucleo.tipos import Dificuldade, Modo

VERSAO = 1
MAXIMO_RECORDES = 5


@dataclass
class Configuracoes:
    """Preferências do jogador."""

    volume_musica: float = 0.5
    volume_efeitos: float = 0.8
    mudo: bool = False
    tremor: bool = True
    flash: bool = True
    tela_cheia: bool = False
    modo: str = Modo.CLASSICO.name
    dificuldade: str = Dificuldade.NORMAL.name
    skin: str = "Esmeralda"


@dataclass
class Recorde:
    """Uma pontuação guardada na tabela."""

    pontos: int
    data: str
    comidas: int = 0
    tempo_s: float = 0.0
    nivel: int = 1
    combo: int = 1


def caminho_padrao() -> Path:
    """Usa COBRINHA_DADOS se definido; senão, a pasta de configuração do usuário."""
    definido = os.environ.get("COBRINHA_DADOS")
    if definido:
        return Path(definido)
    return Path.home() / ".config" / "cobrinha" / "dados.json"


def _chave(modo: Modo, dificuldade: Dificuldade) -> str:
    return f"{modo.name}/{dificuldade.name}"


def _preencher(classe, dados: dict):
    """Cria a dataclass só com os campos conhecidos e de tipo compatível."""
    padrao = classe() if classe is Configuracoes else None
    valores = {}
    for campo in fields(classe):
        if campo.name not in dados:
            continue
        valor = dados[campo.name]
        if padrao is not None:
            esperado = type(getattr(padrao, campo.name))
            if esperado is float and isinstance(valor, int) and not isinstance(valor, bool):
                valor = float(valor)
            if type(valor) is not esperado:
                continue
        valores[campo.name] = valor
    return classe(**valores)


class Armazenamento:
    """Guarda configurações, recordes e totais; falhas de disco nunca derrubam o jogo."""

    def __init__(self, caminho: Path | None = None) -> None:
        self.caminho = caminho or caminho_padrao()
        self.config = Configuracoes()
        self._recordes: dict[str, list[Recorde]] = {}
        self.partidas = 0
        self.comidas_totais = 0
        self.tempo_total_s = 0.0
        self.carregar()

    def carregar(self) -> None:
        """Lê o arquivo; qualquer problema mantém os valores padrão."""
        try:
            dados = json.loads(self.caminho.read_text(encoding="utf-8"))
            if not isinstance(dados, dict):
                return
        except (OSError, ValueError):
            return
        try:
            self.config = _preencher(Configuracoes, dados.get("config", {}))
        except (TypeError, AttributeError):
            self.config = Configuracoes()
        recordes = dados.get("recordes", {})
        if isinstance(recordes, dict):
            for chave, lista in recordes.items():
                self._recordes[chave] = self._ler_lista(lista)
        totais = dados.get("totais", {})
        if isinstance(totais, dict):
            self.partidas = self._numero(totais.get("partidas"), int)
            self.comidas_totais = self._numero(totais.get("comidas"), int)
            self.tempo_total_s = self._numero(totais.get("tempo_s"), float)

    @staticmethod
    def _numero(valor, tipo):
        try:
            return tipo(valor)
        except (TypeError, ValueError):
            return tipo(0)

    @staticmethod
    def _ler_lista(lista) -> list[Recorde]:
        saida = []
        if not isinstance(lista, list):
            return saida
        for item in lista:
            try:
                recorde = _preencher(Recorde, item)
                if isinstance(recorde.pontos, int):
                    saida.append(recorde)
            except (TypeError, AttributeError):
                continue
        saida.sort(key=lambda r: r.pontos, reverse=True)
        return saida[:MAXIMO_RECORDES]

    def salvar(self) -> None:
        """Grava de forma atômica; erros de disco são ignorados."""
        dados = {
            "versao": VERSAO,
            "config": asdict(self.config),
            "recordes": {
                chave: [asdict(r) for r in lista] for chave, lista in self._recordes.items()
            },
            "totais": {
                "partidas": self.partidas,
                "comidas": self.comidas_totais,
                "tempo_s": self.tempo_total_s,
            },
        }
        try:
            self.caminho.parent.mkdir(parents=True, exist_ok=True)
            temporario = self.caminho.with_suffix(".tmp")
            temporario.write_text(json.dumps(dados, ensure_ascii=False, indent=2), encoding="utf-8")
            os.replace(temporario, self.caminho)
        except OSError:
            pass

    def recordes(self, modo: Modo, dificuldade: Dificuldade) -> list[Recorde]:
        """Devolve a tabela do modo e dificuldade, do maior para o menor."""
        return list(self._recordes.get(_chave(modo, dificuldade), []))

    def melhor(self, modo: Modo, dificuldade: Dificuldade) -> int:
        """Devolve a maior pontuação registrada, ou zero."""
        tabela = self.recordes(modo, dificuldade)
        return tabela[0].pontos if tabela else 0

    def registrar(self, modo: Modo, dificuldade: Dificuldade, recorde: Recorde) -> int | None:
        """Soma a partida aos totais e devolve a posição (1 a 5) se entrou na tabela."""
        self.partidas += 1
        self.comidas_totais += recorde.comidas
        self.tempo_total_s += recorde.tempo_s
        posicao = None
        if recorde.pontos > 0:
            tabela = self._recordes.setdefault(_chave(modo, dificuldade), [])
            tabela.append(recorde)
            tabela.sort(key=lambda r: r.pontos, reverse=True)
            del tabela[MAXIMO_RECORDES:]
            if any(r is recorde for r in tabela):
                posicao = next(i for i, r in enumerate(tabela, 1) if r is recorde)
        self.salvar()
        return posicao
