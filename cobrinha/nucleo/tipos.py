"""Tipos básicos do jogo e eventos emitidos pela lógica."""
from __future__ import annotations

from dataclasses import dataclass
from enum import Enum
from typing import NamedTuple

from cobrinha import config


class Celula(NamedTuple):
    """Posição na grade."""

    x: int
    y: int


class Direcao(Enum):
    """Direções de movimento, com o deslocamento em células."""

    CIMA = (0, -1)
    BAIXO = (0, 1)
    ESQUERDA = (-1, 0)
    DIREITA = (1, 0)

    @property
    def dx(self) -> int:
        return self.value[0]

    @property
    def dy(self) -> int:
        return self.value[1]

    def oposta(self) -> "Direcao":
        """Devolve a direção contrária."""
        return _OPOSTAS[self]


_OPOSTAS = {
    Direcao.CIMA: Direcao.BAIXO,
    Direcao.BAIXO: Direcao.CIMA,
    Direcao.ESQUERDA: Direcao.DIREITA,
    Direcao.DIREITA: Direcao.ESQUERDA,
}


class Modo(Enum):
    """Modos de jogo."""

    CLASSICO = "Clássico"
    ATRAVESSAR = "Sem paredes"
    OBSTACULOS = "Obstáculos"
    TEMPO = "Contra o tempo"

    @property
    def rotulo(self) -> str:
        return self.value


class Dificuldade(Enum):
    """Níveis de dificuldade."""

    FACIL = "Fácil"
    NORMAL = "Normal"
    DIFICIL = "Difícil"
    INSANO = "Insano"

    @property
    def rotulo(self) -> str:
        return self.value


class PowerUp(Enum):
    """Efeitos temporários ativados por comidas especiais."""

    VELOZ = "Veloz"
    LENTA = "Câmera lenta"
    FANTASMA = "Fantasma"
    MULTIPLICADOR = "Pontos em dobro"

    @property
    def rotulo(self) -> str:
        return self.value

    @property
    def duracao_s(self) -> float:
        return config.DURACOES_POWER_UP_S[self.name]


class TipoComida(Enum):
    """Comidas que aparecem na arena."""

    MACA = "Maçã"
    DOURADA = "Maçã dourada"
    VELOZ = "Raio"
    LENTA = "Ampulheta"
    FANTASMA = "Fantasma"
    ENCOLHER = "Encolher"
    MULTIPLICADOR = "Dobro"

    @property
    def rotulo(self) -> str:
        return self.value

    @property
    def pontos(self) -> int:
        if self is TipoComida.MACA:
            return config.PONTOS_MACA
        if self is TipoComida.DOURADA:
            return config.PONTOS_DOURADA
        return config.PONTOS_ESPECIAL

    @property
    def crescimento(self) -> int:
        if self is TipoComida.MACA:
            return 1
        if self is TipoComida.DOURADA:
            return config.CRESCIMENTO_DOURADA
        return 0

    @property
    def eh_especial(self) -> bool:
        return self is not TipoComida.MACA

    @property
    def power_up(self) -> PowerUp | None:
        return PowerUp[self.name] if self.name in PowerUp.__members__ else None


class Evento:
    """Base dos fatos emitidos por ``Partida.tick`` para render e áudio."""


@dataclass(frozen=True)
class Virou(Evento):
    direcao: Direcao


@dataclass(frozen=True)
class Comeu(Evento):
    celula: Celula
    tipo: TipoComida
    pontos: int
    combo: int


@dataclass(frozen=True)
class ComboPerdido(Evento):
    combo: int


@dataclass(frozen=True)
class ComidaNasceu(Evento):
    celula: Celula
    tipo: TipoComida


@dataclass(frozen=True)
class ComidaExpirou(Evento):
    celula: Celula
    tipo: TipoComida


@dataclass(frozen=True)
class PowerUpAtivado(Evento):
    power_up: PowerUp


@dataclass(frozen=True)
class PowerUpExpirou(Evento):
    power_up: PowerUp


@dataclass(frozen=True)
class Encolheu(Evento):
    removidas: tuple[Celula, ...]


@dataclass(frozen=True)
class SubiuNivel(Evento):
    nivel: int


@dataclass(frozen=True)
class ObstaculosNasceram(Evento):
    celulas: tuple[Celula, ...]


@dataclass(frozen=True)
class Morreu(Evento):
    causa: str  # "parede", "corpo" ou "obstaculo"
    celula: Celula


@dataclass(frozen=True)
class TempoEsgotou(Evento):
    pontos: int


@dataclass(frozen=True)
class Venceu(Evento):
    pontos: int
