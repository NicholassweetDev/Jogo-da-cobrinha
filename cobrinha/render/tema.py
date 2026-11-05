"""Constantes visuais: medidas da tela, paleta, temas por nível e skins da cobra."""
from __future__ import annotations

from functools import lru_cache

from cobrinha import config

Cor = tuple[int, int, int]

# Tela lógica (a janela escala esta área mantendo a proporção)
LARGURA = 1280
ALTURA = 720
CELULA = 36
ARENA_X = 64
ARENA_Y = 62
ARENA_L = config.GRADE_LARGURA * CELULA
ARENA_A = config.GRADE_ALTURA * CELULA

# Paleta
FUNDO_TOPO: Cor = (13, 12, 32)
FUNDO_BASE: Cor = (6, 16, 28)
CASA_CLARA: Cor = (24, 28, 52)
CASA_ESCURA: Cor = (19, 22, 43)
TEXTO: Cor = (236, 242, 255)
TEXTO_SUAVE: Cor = (150, 165, 200)
TEXTO_APAGADO: Cor = (92, 104, 138)
PAINEL: Cor = (14, 16, 34)
CIANO: Cor = (64, 232, 208)
ROSA: Cor = (255, 77, 141)
OURO: Cor = (255, 200, 61)
VIOLETA: Cor = (167, 139, 250)
AZUL: Cor = (96, 165, 250)
VERDE: Cor = (74, 222, 128)
LARANJA: Cor = (251, 146, 60)
VERMELHO: Cor = (248, 63, 80)
BRANCO: Cor = (255, 255, 255)

# Cor da moldura e do clima da arena, trocada a cada nível
TEMAS: tuple[Cor, ...] = (CIANO, VIOLETA, ROSA, OURO, AZUL, VERDE)

FONTES = {
    "titulo": "Audiowide-Regular.ttf",
    "ui": "ChakraPetch-SemiBold.ttf",
    "forte": "ChakraPetch-Bold.ttf",
}

SKINS: dict[str, tuple[Cor, ...]] = {
    "Esmeralda": ((90, 235, 160), (34, 200, 130), (14, 150, 118), (6, 95, 90)),
    "Neon": ((80, 225, 255), (56, 149, 248), (139, 92, 246), (190, 60, 220)),
    "Coral": ((255, 170, 130), (251, 113, 133), (225, 29, 110), (130, 20, 90)),
    "Solar": ((255, 225, 80), (250, 180, 40), (240, 90, 30), (170, 30, 30)),
    "Arco-íris": (
        (248, 80, 90),
        (250, 170, 50),
        (240, 230, 80),
        (70, 220, 120),
        (60, 170, 250),
        (170, 100, 250),
    ),
}

PASSOS_LUT = 64
BANDAS = 4


def misturar(a: Cor, b: Cor, t: float) -> Cor:
    """Interpola duas cores."""
    t = max(0.0, min(1.0, t))
    return (
        int(a[0] + (b[0] - a[0]) * t),
        int(a[1] + (b[1] - a[1]) * t),
        int(a[2] + (b[2] - a[2]) * t),
    )


def _gradiente(paradas: tuple[Cor, ...], t: float) -> Cor:
    posicao = t * (len(paradas) - 1)
    indice = min(int(posicao), len(paradas) - 2)
    return misturar(paradas[indice], paradas[indice + 1], posicao - indice)


@lru_cache(maxsize=None)
def paleta_skin(skin: str) -> tuple[tuple[tuple[Cor, ...], ...], tuple[Cor, ...], Cor]:
    """Devolve as cores do corpo por banda, as cores de brilho e a cor do contorno."""
    paradas = SKINS.get(skin, SKINS["Esmeralda"])
    base = [_gradiente(paradas, i / (PASSOS_LUT - 1)) for i in range(PASSOS_LUT)]
    bandas = tuple(
        tuple(misturar(c, (0, 0, 0), 0.20 * (1 - b / (BANDAS - 1))) for c in base)
        for b in range(BANDAS)
    )
    brilhos = tuple(misturar(c, BRANCO, 0.38) for c in base)
    contorno = misturar(paradas[-1], (4, 6, 18), 0.72)
    return bandas, brilhos, contorno
