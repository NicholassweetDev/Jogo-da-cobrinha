"""Constantes de jogabilidade (as constantes visuais ficam em render/tema.py)."""
from __future__ import annotations

# Arena (em células)
GRADE_LARGURA: int = 32
GRADE_ALTURA: int = 18
TAMANHO_INICIAL: int = 3

# Dificuldade: nome -> (ticks/s inicial, ticks/s máximo)
DIFICULDADES: dict[str, tuple[float, float]] = {
    "FACIL": (6.0, 12.0),
    "NORMAL": (8.0, 16.0),
    "DIFICIL": (11.0, 20.0),
    "INSANO": (15.0, 26.0),
}

# Progressão
COMIDAS_POR_NIVEL: int = 5
INCREMENTO_VELOCIDADE_POR_NIVEL: float = 1.0  # ticks/s por nível, até o máximo

# Combo: o prazo para manter o combo é a distância até a comida + esta folga,
# assim comer rápido depende de ir direto, e não da sorte de a comida nascer perto.
FOLGA_COMBO_TICKS: int = 6
COMBO_MAXIMO: int = 8

# Comidas
PONTOS_MACA: int = 10
PONTOS_DOURADA: int = 50
PONTOS_ESPECIAL: int = 20
CRESCIMENTO_DOURADA: int = 3
CHANCE_ESPECIAL_POR_TICK: float = 0.015
VIDA_ESPECIAL_S: float = 7.0
PISCAR_ESPECIAL_S: float = 2.0
PESOS_ESPECIAIS: dict[str, int] = {
    "DOURADA": 30,
    "VELOZ": 15,
    "LENTA": 15,
    "FANTASMA": 15,
    "ENCOLHER": 10,
    "MULTIPLICADOR": 15,
}

# Power-ups (duração em segundos e fator aplicado)
DURACAO_VELOZ_S: float = 6.0
FATOR_VELOZ: float = 1.4
DURACAO_LENTA_S: float = 6.0
FATOR_LENTA: float = 0.65
DURACAO_FANTASMA_S: float = 7.0
DURACAO_MULTIPLICADOR_S: float = 10.0
FATOR_MULTIPLICADOR: int = 2
ENCOLHER_SEGMENTOS: int = 3
COMPRIMENTO_MINIMO: int = 3

DURACOES_POWER_UP_S: dict[str, float] = {
    "VELOZ": DURACAO_VELOZ_S,
    "LENTA": DURACAO_LENTA_S,
    "FANTASMA": DURACAO_FANTASMA_S,
    "MULTIPLICADOR": DURACAO_MULTIPLICADOR_S,
}

# Modo TEMPO
TEMPO_INICIAL_S: float = 60.0
BONUS_TEMPO_MACA_S: float = 4.0
BONUS_TEMPO_DOURADA_S: float = 8.0

# Modo OBSTACULOS
DENSIDADE_MAXIMA_OBSTACULOS: float = 0.14

# Entrada
FILA_VIRADAS_MAX: int = 2
