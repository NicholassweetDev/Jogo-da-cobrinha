"""Desenho da cobra: corpo contínuo com curvas suaves, olhos, língua e engolida."""
from __future__ import annotations

import math

import pygame

from cobrinha.nucleo.partida import Cobra
from cobrinha.render import desenho, tema
from cobrinha.render.efeitos import suave
from cobrinha.render.tema import CELULA, PASSOS_LUT, Cor, misturar

RAIO_CORPO = 13.0
RAIO_CABECA = 16.0
AMPLITUDE_ENGOLIDA = 5.5
LARGURA_ENGOLIDA = 34.0
VELOCIDADE_ENGOLIDA = 300.0
PERIODO_LISTRA = 46.0
TONS_LISTRA = tema.BANDAS

# Perfil do corpo: quase constante e afinando na última parte
_PERFIL = tuple(
    1.0 if t < 0.55 else 1.0 - 0.62 * ((t - 0.55) / 0.45) ** 1.7
    for t in (i / 63 for i in range(64))
)


def centros(cobra: Cobra) -> list[tuple[float, float]]:
    """Centros dos segmentos em pixels, desfazendo os saltos da travessia."""
    celulas = list(cobra.segmentos)
    if cobra.cauda_anterior is not None:
        celulas.append(cobra.cauda_anterior)
    primeira = celulas[0]
    x, y = primeira.x, primeira.y
    pontos = [((x + 0.5) * CELULA, (y + 0.5) * CELULA)]
    ax, ay = x, y
    for celula in celulas[1:]:
        dx, dy = celula.x - ax, celula.y - ay
        if abs(dx) > 1:
            dx = -1 if dx > 0 else 1
        if abs(dy) > 1:
            dy = -1 if dy > 0 else 1
        ax, ay = celula.x, celula.y
        x += dx
        y += dy
        pontos.append(((x + 0.5) * CELULA, (y + 0.5) * CELULA))
    return pontos


def tracar(
    pontos: list[tuple[float, float]], curva_inicial: float
) -> tuple[list[float], list[float], list[float], list[float]]:
    """Liga os centros com curvas nas dobras e mede o comprimento acumulado.

    A primeira dobra arredonda aos poucos (``curva_inicial`` de 0 a 1), para a
    cabeça não saltar quando a virada acontece.
    Devolve x, y, comprimento acumulado e o comprimento em cada célula.
    """
    xs = [pontos[0][0]]
    ys = [pontos[0][1]]
    acumulado = [0.0]
    marcos = [0.0]

    def anexar(x: float, y: float) -> None:
        distancia = math.hypot(x - xs[-1], y - ys[-1])
        if distancia > 1e-6:
            xs.append(x)
            ys.append(y)
            acumulado.append(acumulado[-1] + distancia)

    for i in range(1, len(pontos) - 1):
        ax, ay = pontos[i - 1]
        bx, by = pontos[i]
        cx, cy = pontos[i + 1]
        if (ax == bx == cx) or (ay == by == cy):
            anexar(bx, by)
            marcos.append(acumulado[-1])
            continue
        k = 0.5 * (curva_inicial if i == 1 else 1.0)
        m1x, m1y = bx + (ax - bx) * k, by + (ay - by) * k
        m2x, m2y = bx + (cx - bx) * k, by + (cy - by) * k
        anexar(m1x, m1y)
        for t in (0.25, 0.5, 0.75):
            u = 1 - t
            anexar(
                u * u * m1x + 2 * u * t * bx + t * t * m2x,
                u * u * m1y + 2 * u * t * by + t * t * m2y,
            )
            if t == 0.5:
                marcos.append(acumulado[-1])
        anexar(m2x, m2y)
    anexar(*pontos[-1])
    marcos.append(acumulado[-1])
    return xs, ys, acumulado, marcos


def amostrar(
    xs: list[float], ys: list[float], acumulado: list[float], inicio: float, fim: float, passo: float
) -> list[tuple[float, float, float]]:
    """Percorre o traçado devolvendo (x, y, distância) a cada passo."""
    amostras = []
    s = inicio
    i = 0
    ultimo = len(acumulado) - 2
    while s <= fim:
        while i < ultimo and acumulado[i + 1] < s:
            i += 1
        trecho = acumulado[i + 1] - acumulado[i]
        t = (s - acumulado[i]) / trecho if trecho > 0 else 0.0
        amostras.append((xs[i] + (xs[i + 1] - xs[i]) * t, ys[i] + (ys[i + 1] - ys[i]) * t, s))
        s += passo
    return amostras


class CobraVisual:
    """Guarda o estado de animação da cobra e a desenha."""

    def __init__(self, skin: str, atravessa: bool) -> None:
        self.bandas, self.brilhos, self.contorno = tema.paleta_skin(skin)
        self.atravessa = atravessa
        self.tempo = 0.0
        self.engolidas: list[float] = []
        self.susto = 0.0  # aperto da cabeça ao comer, de 1 até 0
        self.boca = 0.0
        self.piscar_em = 2.4
        self.piscada = 0.0
        self.lingua_em = 1.2
        self.lingua = 0.0
        self.morta = False
        self.visivel = True
        self.posicao_cabeca = (0.0, 0.0)
        self.comprimento_px = 0.0

    def engolir(self) -> None:
        """Começa uma ondulação que percorre o corpo."""
        self.engolidas.append(0.0)
        self.susto = 1.0

    def atualizar(self, dt: float, boca_aberta: bool) -> None:
        """Avança piscadas, língua, boca e ondulações."""
        self.tempo += dt
        self.susto = max(0.0, self.susto - dt * 5.0)
        alvo_boca = 1.0 if boca_aberta and not self.morta else 0.0
        self.boca += (alvo_boca - self.boca) * min(1.0, dt * 16)
        self.engolidas = [
            d + VELOCIDADE_ENGOLIDA * dt
            for d in self.engolidas
            if d < self.comprimento_px + LARGURA_ENGOLIDA
        ]
        self.piscada = max(0.0, self.piscada - dt)
        self.lingua = max(0.0, self.lingua - dt)
        if self.tempo >= self.piscar_em:
            self.piscada = 0.13
            self.piscar_em = self.tempo + 2.2 + (self.tempo * 7.3) % 2.4
        if self.tempo >= self.lingua_em:
            self.lingua = 0.34
            self.lingua_em = self.tempo + 1.8 + (self.tempo * 3.1) % 2.2

    def _replicas(self, x: float, y: float, raio: float):
        """Em arena sem paredes, repete o que encosta nas bordas do outro lado."""
        x %= tema.ARENA_L
        y %= tema.ARENA_A
        lista = [(x, y)]
        if x < raio:
            lista.append((x + tema.ARENA_L, y))
        elif x > tema.ARENA_L - raio:
            lista.append((x - tema.ARENA_L, y))
        for px, py in tuple(lista):
            if y < raio:
                lista.append((px, py + tema.ARENA_A))
            elif y > tema.ARENA_A - raio:
                lista.append((px, py - tema.ARENA_A))
        return lista

    def desenhar(
        self,
        tela: pygame.Surface,
        origem: tuple[int, int],
        cobra: Cobra,
        alpha: float,
        alvo: tuple[float, float] | None,
        com_brilho: bool = True,
        corte: float = 0.0,
    ) -> None:
        """Desenha a cobra; ``alpha`` é o avanço entre dois ticks e ``corte`` some com a cauda."""
        if not self.visivel:
            return
        ox, oy = origem
        xs, ys, acumulado, marcos = tracar(centros(cobra), suave(alpha))
        inicio = marcos[1] * (1.0 - alpha)
        if cobra.cauda_anterior is not None:
            fim = marcos[-1] - (marcos[-1] - marcos[-2]) * alpha
        else:
            fim = marcos[-1]
        corpo_px = max(1.0, fim - inicio)
        self.comprimento_px = corpo_px
        fim_visivel = inicio + corpo_px * (1.0 - corte)

        passo = 3.5 if cobra.comprimento < 60 else 5.5
        amostras = amostrar(xs, ys, acumulado, inicio, fim_visivel, passo)
        if not amostras:
            return
        cabeca_x, cabeca_y, _ = amostras[0]
        frente_s = min(inicio + 8.0, acumulado[-1])
        frente = amostrar(xs, ys, acumulado, frente_s, frente_s, 1.0)[0]
        fx, fy = cabeca_x - frente[0], cabeca_y - frente[1]
        tamanho = math.hypot(fx, fy) or 1.0
        fx, fy = fx / tamanho, fy / tamanho

        contorno, corpo, luzes, halos = [], [], [], []
        bandas, brilhos, cor_contorno = self.bandas, self.brilhos, self.contorno
        engolidas = self.engolidas
        fator_lut = (PASSOS_LUT - 1) / corpo_px
        escala_listra = math.tau / PERIODO_LISTRA
        for indice in range(len(amostras) - 1, -1, -1):
            x, y, s = amostras[indice]
            relativo = s - inicio
            lut = min(PASSOS_LUT - 1, int(relativo * fator_lut))
            raio = RAIO_CORPO * _PERFIL[lut]
            for distancia in engolidas:
                delta = abs(relativo - distancia)
                if delta < LARGURA_ENGOLIDA:
                    onda = 1 - (delta / LARGURA_ENGOLIDA) ** 2
                    raio += AMPLITUDE_ENGOLIDA * onda * onda
            listra = (math.sin((fim - s) * escala_listra) + 1) * 0.5
            cor = bandas[min(TONS_LISTRA - 1, int(listra * TONS_LISTRA))][lut]
            raio2 = int(raio * 2)
            pele = desenho.disco(raio2 + 5, cor_contorno)
            miolo = desenho.disco(raio2, cor)
            reflexo = desenho.disco(max(2, int(raio * 0.56)), brilhos[lut])
            meio_pele = pele.get_width() >> 1
            meio_miolo = miolo.get_width() >> 1
            meio_reflexo = reflexo.get_width() >> 1
            lx, ly = raio * 0.32, raio * 0.36
            com_reflexo = raio >= 9.0  # na ponta da cauda o reflexo viraria pontinhos
            posicoes = (
                self._replicas(x, y, raio + 3) if self.atravessa else ((x, y),)
            )
            for px, py in posicoes:
                px = int(px) + ox
                py = int(py) + oy
                contorno.append((pele, (px - meio_pele, py - meio_pele)))
                corpo.append((miolo, (px - meio_miolo, py - meio_miolo)))
                if com_reflexo:
                    luzes.append(
                        (reflexo, (int(px - lx) - meio_reflexo, int(py - ly) - meio_reflexo))
                    )
                if com_brilho and indice % 6 == 0:
                    halo = desenho.brilho(cor, 30, 26)
                    halos.append((halo, (px - 30, py - 30)))

        if halos:
            tela.fblits(halos, desenho.ADITIVO)
        tela.fblits(contorno)
        tela.fblits(corpo)
        tela.fblits(luzes)

        self.posicao_cabeca = (cabeca_x % tema.ARENA_L, cabeca_y % tema.ARENA_A)
        hx, hy = self.posicao_cabeca
        cabecas = self._replicas(hx, hy, RAIO_CABECA + 12) if self.atravessa else ((hx, hy),)
        for px, py in cabecas:
            self._cabeca(tela, px + ox, py + oy, fx, fy, alvo, ox, oy)

    def _cabeca(
        self,
        tela: pygame.Surface,
        x: float,
        y: float,
        fx: float,
        fy: float,
        alvo: tuple[float, float] | None,
        ox: int,
        oy: int,
    ) -> None:
        cor = self.bandas[-1][0]
        escuro = misturar(cor, (0, 0, 0), 0.32)
        lx, ly = -fy, fx
        aperto = self.susto
        raio = RAIO_CABECA * (1 + 0.16 * aperto)
        focinho_x = x + fx * 8 * (1 - 0.3 * aperto)
        focinho_y = y + fy * 8 * (1 - 0.3 * aperto)
        raio_focinho = raio * 0.78

        if self.lingua > 0 and not self.morta:
            self._lingua(tela, focinho_x, focinho_y, fx, fy, lx, ly, raio_focinho)

        desenho.carimbar(tela, x, y, raio + 2.5, self.contorno)
        desenho.carimbar(tela, focinho_x, focinho_y, raio_focinho + 2.5, self.contorno)
        desenho.carimbar(tela, x, y, raio, cor)
        desenho.carimbar(tela, focinho_x, focinho_y, raio_focinho, cor)
        desenho.carimbar(tela, x - 3, y - 5, raio * 0.42, self.brilhos[0])

        if self.boca > 0.05:
            ponta = raio_focinho + 3
            abertura = 8.5 * self.boca
            pygame.draw.polygon(
                tela,
                (66, 12, 42),
                [
                    (focinho_x + fx * 1.5, focinho_y + fy * 1.5),
                    (focinho_x + fx * ponta + lx * abertura, focinho_y + fy * ponta + ly * abertura),
                    (focinho_x + fx * ponta - lx * abertura, focinho_y + fy * ponta - ly * abertura),
                ],
            )
        else:
            for lado in (-1, 1):
                desenho.carimbar(
                    tela,
                    focinho_x + fx * 7 + lx * 4 * lado,
                    focinho_y + fy * 7 + ly * 4 * lado,
                    1.3,
                    escuro,
                )

        for lado in (-1, 1):
            olho_x = x + fx * 3 + lx * 9 * lado
            olho_y = y + fy * 3 + ly * 9 * lado
            self._olho(tela, olho_x, olho_y, fx, fy, lx, ly, alvo, ox, oy, escuro)

    def _olho(self, tela, x, y, fx, fy, lx, ly, alvo, ox, oy, escuro) -> None:
        if self.morta:
            desenho.carimbar(tela, x, y, 6.5, tema.BRANCO)
            for sinal in (-1, 1):
                pygame.draw.line(
                    tela,
                    (40, 10, 30),
                    (x - 3.5, y - 3.5 * sinal),
                    (x + 3.5, y + 3.5 * sinal),
                    2,
                )
            return
        if self.piscada > 0:
            pygame.draw.line(
                tela, escuro, (x - fx * 5, y - fy * 5), (x + fx * 5, y + fy * 5), 3
            )
            return
        desenho.carimbar(tela, x, y, 7.0, self.contorno)
        desenho.carimbar(tela, x, y, 6.0, tema.BRANCO)
        olhar_x, olhar_y = fx, fy
        if alvo is not None:
            dx, dy = alvo[0] + ox - x, alvo[1] + oy - y
            distancia = math.hypot(dx, dy)
            if distancia > 1:
                olhar_x, olhar_y = dx / distancia, dy / distancia
        desenho.carimbar(tela, x + olhar_x * 2.4, y + olhar_y * 2.4, 3.4, (14, 16, 34))
        desenho.carimbar(tela, x + olhar_x * 2.4 - 1, y + olhar_y * 2.4 - 1, 1.1, tema.BRANCO)

    def _lingua(self, tela, x, y, fx, fy, lx, ly, raio) -> None:
        t = 1 - self.lingua / 0.34
        extensao = math.sin(t * math.pi) * 15
        balanco = math.sin(self.tempo * 40) * 1.6
        base_x, base_y = x + fx * raio, y + fy * raio
        ponta_x = base_x + fx * extensao + lx * balanco
        ponta_y = base_y + fy * extensao + ly * balanco
        cor: Cor = (255, 70, 110)
        pygame.draw.line(tela, cor, (base_x, base_y), (ponta_x, ponta_y), 2)
        for lado in (-1, 1):
            pygame.draw.line(
                tela,
                cor,
                (ponta_x, ponta_y),
                (ponta_x + fx * 5 + lx * 3.5 * lado, ponta_y + fy * 5 + ly * 3.5 * lado),
                2,
            )

