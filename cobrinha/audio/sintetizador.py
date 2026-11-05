"""Síntese de som em Python puro: nenhum arquivo de áudio acompanha o jogo."""
from __future__ import annotations

import math
import random
from array import array
from collections.abc import Iterator

DOIS_PI = 2.0 * math.pi
_ruido = random.Random(7)


def _amostra(onda: str, fase: float) -> float:
    fase %= 1.0
    if onda == "seno":
        return math.sin(DOIS_PI * fase)
    if onda == "quadrada":
        return 0.6 if fase < 0.5 else -0.6
    if onda == "pulso":
        return 0.6 if fase < 0.25 else -0.6
    if onda == "triangulo":
        return 4.0 * abs(fase - 0.5) - 1.0
    if onda == "serra":
        return (2.0 * fase - 1.0) * 0.7
    return _ruido.uniform(-1.0, 1.0)


def tom(
    taxa: int,
    inicio_hz: float,
    fim_hz: float | None = None,
    duracao_ms: float = 100.0,
    onda: str = "seno",
    volume: float = 0.5,
    ataque_ms: float = 3.0,
    soltura: float = 0.7,
) -> list[float]:
    """Gera um tom com deslize de frequência e envelope; ``soltura`` é a fração final."""
    fim_hz = inicio_hz if fim_hz is None else fim_hz
    total = max(1, int(taxa * duracao_ms / 1000.0))
    ataque = max(1, int(taxa * ataque_ms / 1000.0))
    inicio_soltura = total * (1.0 - soltura)
    resto = max(1.0, total - inicio_soltura)
    razao = (fim_hz / inicio_hz) ** (1.0 / total)
    frequencia = inicio_hz
    fase = 0.0
    saida = [0.0] * total
    for i in range(total):
        envelope = 1.0 if i >= ataque else i / ataque
        if i > inicio_soltura:
            queda = 1.0 - (i - inicio_soltura) / resto
            envelope *= queda * queda
        saida[i] = _amostra(onda, fase) * envelope * volume
        fase += frequencia / taxa
        frequencia *= razao
    return saida


def misturar(taxa: int, partes: list[tuple[float, list[float]]]) -> list[float]:
    """Soma trechos, cada um começando em seu instante em ms."""
    tamanho = max(int(taxa * ms / 1000.0) + len(p) for ms, p in partes)
    saida = [0.0] * tamanho
    for ms, parte in partes:
        posicao = int(taxa * ms / 1000.0)
        for i, valor in enumerate(parte):
            saida[posicao + i] += valor
    return saida


def para_pcm(amostras: list[float], canais: int, pico: float = 0.9) -> bytes:
    """Normaliza só se passar do pico e converte para PCM de 16 bits."""
    maior = max((abs(v) for v in amostras), default=0.0)
    ganho = 32767.0 * (pico / maior if maior > pico else 1.0)
    return _intercalar(array("h", [int(v * ganho) for v in amostras]), canais)


def _intercalar(mono: array, canais: int) -> bytes:
    """Repete o sinal mono em todos os canais."""
    if canais == 1:
        return mono.tobytes()
    intercalado = array("h", bytes(2 * canais * len(mono)))
    for canal in range(canais):
        intercalado[canal::canais] = mono
    return intercalado.tobytes()


ESCALA_COMER = (523.25, 587.33, 659.25, 783.99, 880.0, 1046.5, 1174.66, 1318.51)


def receitas(taxa: int) -> dict[str, list[float]]:
    """Monta todos os efeitos sonoros do jogo."""
    sons: dict[str, list[float]] = {}

    for indice, nota in enumerate(ESCALA_COMER):
        sons[f"comer{indice}"] = misturar(
            taxa,
            [
                (0, tom(taxa, nota, nota * 1.35, 95, "seno", 0.42)),
                (0, tom(taxa, nota * 2, nota * 2.7, 70, "quadrada", 0.1)),
            ],
        )

    def arpejo(notas, passo_ms, duracao_ms, onda="triangulo", volume=0.34):
        return misturar(
            taxa,
            [(i * passo_ms, tom(taxa, n, None, duracao_ms, onda, volume)) for i, n in enumerate(notas)],
        )

    sons["dourada"] = arpejo((659.25, 830.61, 987.77, 1318.51), 55, 170)
    sons["powerup"] = misturar(
        taxa,
        [
            (0, tom(taxa, 300, 1100, 240, "pulso", 0.2)),
            (70, tom(taxa, 600, 1800, 190, "seno", 0.24)),
        ],
    )
    sons["expirar"] = tom(taxa, 700, 260, 200, "triangulo", 0.3)
    sons["sumiu"] = tom(taxa, 900, 420, 120, "seno", 0.2)
    sons["encolher"] = misturar(
        taxa,
        [
            (0, tom(taxa, 1000, 300, 150, "quadrada", 0.18)),
            (40, tom(taxa, 2000, 500, 130, "ruido", 0.08)),
        ],
    )
    sons["combo_perdido"] = tom(taxa, 420, 260, 130, "triangulo", 0.16)
    sons["nivel"] = arpejo((523.25, 659.25, 783.99, 1046.5), 80, 230, "pulso", 0.24)
    sons["morrer"] = misturar(
        taxa,
        [
            (0, tom(taxa, 340, 45, 520, "serra", 0.5, soltura=0.5)),
            (0, tom(taxa, 900, 200, 300, "ruido", 0.32)),
            (0, tom(taxa, 110, 40, 420, "seno", 0.5)),
        ],
    )
    sons["fim"] = arpejo((440.0, 392.0, 329.63, 261.63), 170, 360, "triangulo", 0.34)
    sons["recorde"] = arpejo(
        (523.25, 659.25, 783.99, 1046.5, 1318.51, 1567.98), 85, 300, "pulso", 0.22
    )
    sons["vitoria"] = arpejo(
        (523.25, 783.99, 1046.5, 783.99, 1046.5, 1567.98, 2093.0), 95, 340, "triangulo", 0.3
    )
    sons["conta"] = tom(taxa, 523.25, None, 110, "pulso", 0.24)
    sons["vai"] = misturar(
        taxa,
        [
            (0, tom(taxa, 1046.5, None, 260, "pulso", 0.24)),
            (0, tom(taxa, 523.25, None, 260, "triangulo", 0.3)),
        ],
    )
    sons["pausa"] = arpejo((659.25, 523.25), 70, 110, "seno", 0.3)
    sons["retomar"] = arpejo((523.25, 659.25), 70, 110, "seno", 0.3)
    sons["menu_mover"] = tom(taxa, 880, 1040, 38, "seno", 0.22)
    sons["menu_mudar"] = tom(taxa, 660, 780, 55, "triangulo", 0.26)
    sons["menu_ok"] = arpejo((659.25, 987.77), 55, 120, "pulso", 0.22)
    sons["menu_voltar"] = arpejo((659.25, 440.0), 55, 110, "triangulo", 0.26)
    sons["virar"] = tom(taxa, 240, 200, 18, "seno", 0.09)
    return sons


# Sequência da música: acorde por compasso, em Hz
_ACORDES = (
    (110.0, (220.0, 261.63, 329.63, 440.0)),  # Lá menor
    (87.31, (174.61, 220.0, 261.63, 349.23)),  # Fá maior
    (130.81, (196.0, 261.63, 329.63, 392.0)),  # Dó maior
    (98.0, (196.0, 246.94, 293.66, 392.0)),  # Sol maior
)
_PADRAO_ARPEJO = (0, 2, 1, 3, 2, 1, 3, 2)
BPM = 104


def gerar_musica(taxa: int, canais: int) -> Iterator[bytes | None]:
    """Compõe o loop aos poucos: rende None a cada passo e o áudio pronto no fim.

    Assim o trabalho se espalha pelos quadros e a imagem não engasga.
    """
    batida = 60.0 / BPM
    colcheia = batida / 2.0
    compassos = 8
    total = int(taxa * compassos * 4 * batida)
    faixa = [0.0] * total
    cache: dict[tuple, list[float]] = {}

    def somar(instante: float, chave: tuple, volume: float) -> None:
        if chave not in cache:
            frequencia, duracao_ms, onda = chave
            cache[chave] = tom(taxa, frequencia, None, duracao_ms, onda, 1.0, 6.0, 0.8)
        inicio = int(instante * taxa) % total
        nota = cache[chave]
        # o resto da nota dá a volta para o começo, e o loop não estala
        fim = min(len(nota), total - inicio)
        for i in range(fim):
            faixa[inicio + i] += nota[i] * volume
        for i in range(fim, len(nota)):
            faixa[inicio + i - total] += nota[i] * volume

    for compasso in range(compassos):
        grave, notas = _ACORDES[compasso % len(_ACORDES)]
        inicio = compasso * 4 * batida
        for tempo in (0.0, 1.5, 2.0, 3.5):
            somar(inicio + tempo * batida, (grave, 300.0, "triangulo"), 0.34)
            yield None
        for passo, indice in enumerate(_PADRAO_ARPEJO):
            nota = notas[indice] * (2.0 if compasso >= 4 and passo % 4 == 3 else 1.0)
            instante = inicio + passo * colcheia
            somar(instante, (nota * 2.0, 260.0, "pulso"), 0.1)
            somar(instante + colcheia * 1.5, (nota * 2.0, 260.0, "pulso"), 0.035)  # eco
            yield None
        for tempo in range(8):
            somar(inicio + tempo * colcheia, (6000.0, 30.0, "ruido"), 0.03 if tempo % 2 else 0.05)
        yield None

    maior = max(max(faixa), -min(faixa)) or 1.0
    ganho = 32767.0 * min(1.0, 0.75 / maior)
    mono = array("h")
    for inicio in range(0, total, 16384):
        mono.extend(int(v * ganho) for v in faixa[inicio : inicio + 16384])
        yield None
    yield _intercalar(mono, canais)
