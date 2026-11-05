"""Regras do jogo: cobra, comidas, obstáculos e o avanço da partida tick a tick."""
from __future__ import annotations

import random
from collections import deque
from dataclasses import dataclass

from cobrinha import config
from cobrinha.nucleo.tipos import (
    Celula,
    Comeu,
    ComboPerdido,
    ComidaExpirou,
    ComidaNasceu,
    Dificuldade,
    Direcao,
    Encolheu,
    Evento,
    Modo,
    Morreu,
    ObstaculosNasceram,
    PowerUp,
    PowerUpAtivado,
    PowerUpExpirou,
    SubiuNivel,
    TempoEsgotou,
    TipoComida,
    Venceu,
    Virou,
)


class Cobra:
    """Corpo da cobra e sua fila de viradas."""

    def __init__(self, segmentos: list[Celula], direcao: Direcao) -> None:
        self.segmentos: deque[Celula] = deque(segmentos)
        self.direcao = direcao
        self.fila_viradas: deque[Direcao] = deque()
        self.crescimento_pendente = 0
        self.cauda_anterior: Celula | None = None  # célula liberada no último passo

    @property
    def cabeca(self) -> Celula:
        return self.segmentos[0]

    @property
    def comprimento(self) -> int:
        return len(self.segmentos)

    def virar(self, nova: Direcao) -> bool:
        """Enfileira uma virada; ignora repetição, inversão de 180° e fila cheia."""
        referencia = self.fila_viradas[-1] if self.fila_viradas else self.direcao
        if nova is referencia or nova is referencia.oposta():
            return False
        if len(self.fila_viradas) >= config.FILA_VIRADAS_MAX:
            return False
        self.fila_viradas.append(nova)
        return True

    def consumir_virada(self) -> Direcao | None:
        """Aplica a próxima virada da fila, se houver."""
        if not self.fila_viradas:
            return None
        self.direcao = self.fila_viradas.popleft()
        return self.direcao

    def proxima_cabeca(self, largura: int, altura: int, atravessar: bool) -> Celula | None:
        """Calcula a próxima célula da cabeça; None significa bater na parede."""
        x = self.cabeca.x + self.direcao.dx
        y = self.cabeca.y + self.direcao.dy
        if atravessar:
            return Celula(x % largura, y % altura)
        if 0 <= x < largura and 0 <= y < altura:
            return Celula(x, y)
        return None

    def avancar(self, nova_cabeca: Celula) -> None:
        """Move a cobra uma célula, crescendo se houver crescimento pendente."""
        self.segmentos.appendleft(nova_cabeca)
        if self.crescimento_pendente > 0:
            self.crescimento_pendente -= 1
            self.cauda_anterior = None
        else:
            self.cauda_anterior = self.segmentos.pop()

    def ocupa(self, celula: Celula, ignorar_cauda: bool = False) -> bool:
        """Diz se o corpo ocupa a célula; a cauda que vai sair pode ser ignorada."""
        if ignorar_cauda and celula == self.segmentos[-1]:
            return self.segmentos.count(celula) > 1
        return celula in self.segmentos

    def encolher(self, quantidade: int) -> tuple[Celula, ...]:
        """Remove segmentos da cauda, sem passar do comprimento mínimo."""
        removidas = []
        while quantidade > 0 and self.comprimento > config.COMPRIMENTO_MINIMO:
            removidas.append(self.segmentos.pop())
            quantidade -= 1
        self.crescimento_pendente = 0
        self.cauda_anterior = None
        return tuple(removidas)


@dataclass
class Comida:
    """Uma comida na arena; especiais têm hora para sumir."""

    celula: Celula
    tipo: TipoComida
    expira_s: float | None = None

    def vida_restante(self, tempo_s: float) -> float | None:
        """Segundos até sumir, ou None se não expira."""
        return None if self.expira_s is None else self.expira_s - tempo_s

    def piscando(self, tempo_s: float) -> bool:
        """Diz se a comida está nos últimos segundos de vida."""
        vida = self.vida_restante(tempo_s)
        return vida is not None and vida <= config.PISCAR_ESPECIAL_S


def sortear_celula_livre(
    rng: random.Random, largura: int, altura: int, ocupadas: set[Celula]
) -> Celula | None:
    """Escolhe uma célula livre ao acaso; None quando a arena está cheia."""
    livres = [
        Celula(x, y)
        for y in range(altura)
        for x in range(largura)
        if Celula(x, y) not in ocupadas
    ]
    return rng.choice(livres) if livres else None


def arena_conectada(largura: int, altura: int, bloqueadas: set[Celula]) -> bool:
    """Confere por flood fill se todas as células livres se alcançam."""
    total_livre = largura * altura - len(bloqueadas)
    inicio = next(
        (
            Celula(x, y)
            for y in range(altura)
            for x in range(largura)
            if Celula(x, y) not in bloqueadas
        ),
        None,
    )
    if inicio is None:
        return True
    vistas = {inicio}
    pilha = [inicio]
    while pilha:
        atual = pilha.pop()
        for direcao in Direcao:
            vizinha = Celula(atual.x + direcao.dx, atual.y + direcao.dy)
            if (
                0 <= vizinha.x < largura
                and 0 <= vizinha.y < altura
                and vizinha not in bloqueadas
                and vizinha not in vistas
            ):
                vistas.add(vizinha)
                pilha.append(vizinha)
    return len(vistas) == total_livre


def sortear_muro(
    rng: random.Random,
    largura: int,
    altura: int,
    existentes: set[Celula],
    proibidas: set[Celula],
) -> set[Celula]:
    """Sorteia um muro curto espelhado nos 4 quadrantes; vazio se não couber."""
    if len(existentes) >= largura * altura * config.DENSIDADE_MAXIMA_OBSTACULOS:
        return set()
    for _ in range(40):
        tamanho = rng.randint(2, 4)
        horizontal = rng.random() < 0.5
        x0 = rng.randint(2, max(2, largura // 2 - 2))
        y0 = rng.randint(2, max(2, altura // 2 - 2))
        muro: set[Celula] = set()
        for i in range(tamanho):
            x = x0 + (i if horizontal else 0)
            y = y0 + (0 if horizontal else i)
            for mx in (x, largura - 1 - x):
                for my in (y, altura - 1 - y):
                    muro.add(Celula(mx, my))
        fora = any(not (0 <= c.x < largura and 0 <= c.y < altura) for c in muro)
        if fora or muro & proibidas or muro <= existentes:
            continue
        if arena_conectada(largura, altura, existentes | muro):
            return muro - existentes
    return set()


@dataclass
class Regras:
    """Parâmetros que definem uma partida."""

    modo: Modo = Modo.CLASSICO
    dificuldade: Dificuldade = Dificuldade.NORMAL
    largura: int = config.GRADE_LARGURA
    altura: int = config.GRADE_ALTURA
    semente: int | None = None


@dataclass
class Estatisticas:
    """Resumo de uma partida."""

    pontos: int
    comidas: int
    especiais: int
    maior_combo: int
    tempo_s: float
    nivel: int
    comprimento: int


class Partida:
    """Estado completo de uma partida; ``tick`` avança uma célula."""

    def __init__(self, regras: Regras | None = None, rng: random.Random | None = None) -> None:
        self.regras = regras or Regras()
        self.rng = rng or random.Random(self.regras.semente)
        largura, altura = self.regras.largura, self.regras.altura
        cx, cy = largura // 2, altura // 2
        corpo = [Celula(cx - i, cy) for i in range(config.TAMANHO_INICIAL)]
        self.cobra = Cobra(corpo, Direcao.DIREITA)
        self.comidas: list[Comida] = []
        self.obstaculos: set[Celula] = set()
        self.pontos = 0
        self.combo = 1
        self.maior_combo = 1
        self.prazo_combo_tick = 0
        self.duracao_combo_ticks = 1
        self.nivel = 1
        self.tick_atual = 0
        self.tempo_s = 0.0
        self.acabou = False
        self.venceu = False
        self.causa_fim: str | None = None
        self.power_ups_ativos: dict[PowerUp, float] = {}
        self.total_comidas = 0
        self.total_especiais = 0
        self._comidas_no_nivel = 0
        self.tempo_restante_s: float | None = (
            config.TEMPO_INICIAL_S if self.regras.modo is Modo.TEMPO else None
        )
        if self.regras.modo is Modo.OBSTACULOS:
            self._adicionar_obstaculos([])
        self._repor_maca([])

    @property
    def atravessa(self) -> bool:
        return self.regras.modo is Modo.ATRAVESSAR

    @property
    def ticks_por_segundo(self) -> float:
        """Velocidade atual, já com nível e power-ups."""
        inicial, maximo = config.DIFICULDADES[self.regras.dificuldade.name]
        base = min(inicial + (self.nivel - 1) * config.INCREMENTO_VELOCIDADE_POR_NIVEL, maximo)
        if PowerUp.VELOZ in self.power_ups_ativos:
            base *= config.FATOR_VELOZ
        if PowerUp.LENTA in self.power_ups_ativos:
            base *= config.FATOR_LENTA
        return base

    @property
    def fracao_combo(self) -> float:
        """Quanto resta do prazo do combo atual, de 0 a 1."""
        if self.combo <= 1:
            return 0.0
        restante = self.prazo_combo_tick - self.tick_atual
        return max(0.0, min(1.0, restante / self.duracao_combo_ticks))

    def virar(self, direcao: Direcao) -> bool:
        """Pede uma virada para os próximos ticks."""
        return self.cobra.virar(direcao)

    def estatisticas(self) -> Estatisticas:
        """Resume a partida até aqui."""
        return Estatisticas(
            pontos=self.pontos,
            comidas=self.total_comidas,
            especiais=self.total_especiais,
            maior_combo=self.maior_combo,
            tempo_s=self.tempo_s,
            nivel=self.nivel,
            comprimento=self.cobra.comprimento,
        )

    def tick(self) -> list[Evento]:
        """Avança a partida uma célula e devolve o que aconteceu."""
        if self.acabou:
            return []
        eventos: list[Evento] = []
        virada = self.cobra.consumir_virada()
        if virada is not None:
            eventos.append(Virou(virada))

        proxima = self.cobra.proxima_cabeca(
            self.regras.largura, self.regras.altura, self.atravessa
        )
        causa = self._causa_da_colisao(proxima)
        if causa is not None:
            self.acabou = True
            self.causa_fim = causa
            eventos.append(Morreu(causa, self.cobra.cabeca))
            return eventos

        duracao = 1.0 / self.ticks_por_segundo
        self.cobra.avancar(proxima)
        self.tick_atual += 1
        self.tempo_s += duracao

        comida = next((c for c in self.comidas if c.celula == proxima), None)
        if comida is not None:
            self._comer(comida, eventos)
        if self.acabou:
            return eventos

        self._atualizar_combo(eventos)
        self._atualizar_power_ups(duracao, eventos)
        self._atualizar_especial(eventos)
        self._atualizar_relogio(duracao, eventos)
        return eventos

    def _causa_da_colisao(self, proxima: Celula | None) -> str | None:
        if proxima is None:
            return "parede"
        if proxima in self.obstaculos:
            return "obstaculo"
        if PowerUp.FANTASMA in self.power_ups_ativos:
            return None
        cauda_vai_sair = self.cobra.crescimento_pendente == 0
        return "corpo" if self.cobra.ocupa(proxima, ignorar_cauda=cauda_vai_sair) else None

    def _comer(self, comida: Comida, eventos: list[Evento]) -> None:
        self.comidas.remove(comida)
        rapido = self.total_comidas > 0 and self.tick_atual <= self.prazo_combo_tick
        self.combo = min(self.combo + 1, config.COMBO_MAXIMO) if rapido else 1
        self.maior_combo = max(self.maior_combo, self.combo)

        multiplicador = (
            config.FATOR_MULTIPLICADOR if PowerUp.MULTIPLICADOR in self.power_ups_ativos else 1
        )
        ganho = comida.tipo.pontos * self.combo * multiplicador
        self.pontos += ganho
        self.total_comidas += 1
        self.total_especiais += comida.tipo.eh_especial
        self.cobra.crescimento_pendente += comida.tipo.crescimento
        eventos.append(Comeu(comida.celula, comida.tipo, ganho, self.combo))

        if comida.tipo is TipoComida.ENCOLHER:
            removidas = self.cobra.encolher(config.ENCOLHER_SEGMENTOS)
            if removidas:
                eventos.append(Encolheu(removidas))
        if comida.tipo.power_up is not None:
            self._ativar(comida.tipo.power_up, eventos)
        if self.tempo_restante_s is not None:
            self.tempo_restante_s += (
                config.BONUS_TEMPO_DOURADA_S
                if comida.tipo is TipoComida.DOURADA
                else config.BONUS_TEMPO_MACA_S
            )

        self._comidas_no_nivel += 1
        if self._comidas_no_nivel >= config.COMIDAS_POR_NIVEL:
            self._comidas_no_nivel = 0
            self.nivel += 1
            eventos.append(SubiuNivel(self.nivel))
            if self.regras.modo is Modo.OBSTACULOS:
                self._adicionar_obstaculos(eventos)

        if comida.tipo is TipoComida.MACA:
            self._repor_maca(eventos)
        self._renovar_prazo_combo()

    def _ativar(self, power_up: PowerUp, eventos: list[Evento]) -> None:
        contrario = {PowerUp.VELOZ: PowerUp.LENTA, PowerUp.LENTA: PowerUp.VELOZ}.get(power_up)
        if contrario in self.power_ups_ativos:
            del self.power_ups_ativos[contrario]
            eventos.append(PowerUpExpirou(contrario))
        self.power_ups_ativos[power_up] = power_up.duracao_s
        eventos.append(PowerUpAtivado(power_up))

    def _atualizar_combo(self, eventos: list[Evento]) -> None:
        if self.combo > 1 and self.tick_atual > self.prazo_combo_tick:
            eventos.append(ComboPerdido(self.combo))
            self.combo = 1

    def _atualizar_power_ups(self, duracao: float, eventos: list[Evento]) -> None:
        for power_up in list(self.power_ups_ativos):
            self.power_ups_ativos[power_up] -= duracao
            if self.power_ups_ativos[power_up] <= 0:
                del self.power_ups_ativos[power_up]
                eventos.append(PowerUpExpirou(power_up))

    def _atualizar_especial(self, eventos: list[Evento]) -> None:
        for comida in list(self.comidas):
            vida = comida.vida_restante(self.tempo_s)
            if vida is not None and vida <= 0:
                self.comidas.remove(comida)
                eventos.append(ComidaExpirou(comida.celula, comida.tipo))
        tem_especial = any(c.tipo.eh_especial for c in self.comidas)
        if not tem_especial and self.rng.random() < config.CHANCE_ESPECIAL_POR_TICK:
            nomes = list(config.PESOS_ESPECIAIS)
            pesos = [config.PESOS_ESPECIAIS[n] for n in nomes]
            tipo = TipoComida[self.rng.choices(nomes, pesos)[0]]
            celula = sortear_celula_livre(
                self.rng, self.regras.largura, self.regras.altura, self._ocupadas()
            )
            if celula is not None:
                self.comidas.append(Comida(celula, tipo, self.tempo_s + config.VIDA_ESPECIAL_S))
                eventos.append(ComidaNasceu(celula, tipo))

    def _atualizar_relogio(self, duracao: float, eventos: list[Evento]) -> None:
        if self.tempo_restante_s is None:
            return
        self.tempo_restante_s -= duracao
        if self.tempo_restante_s <= 0:
            self.tempo_restante_s = 0.0
            self.acabou = True
            self.causa_fim = "tempo"
            eventos.append(TempoEsgotou(self.pontos))

    def _ocupadas(self) -> set[Celula]:
        ocupadas = set(self.cobra.segmentos) | self.obstaculos
        ocupadas.update(c.celula for c in self.comidas)
        return ocupadas

    def _repor_maca(self, eventos: list[Evento]) -> None:
        celula = sortear_celula_livre(
            self.rng, self.regras.largura, self.regras.altura, self._ocupadas()
        )
        if celula is None:
            self.acabou = True
            self.venceu = True
            self.causa_fim = "vitoria"
            eventos.append(Venceu(self.pontos))
            return
        self.comidas.append(Comida(celula, TipoComida.MACA))
        eventos.append(ComidaNasceu(celula, TipoComida.MACA))

    def _distancia(self, a: Celula, b: Celula) -> int:
        dx, dy = abs(a.x - b.x), abs(a.y - b.y)
        if self.atravessa:
            dx = min(dx, self.regras.largura - dx)
            dy = min(dy, self.regras.altura - dy)
        return dx + dy

    def _renovar_prazo_combo(self) -> None:
        if not self.comidas:
            return
        distancia = min(self._distancia(self.cobra.cabeca, c.celula) for c in self.comidas)
        self.duracao_combo_ticks = distancia + config.FOLGA_COMBO_TICKS
        self.prazo_combo_tick = self.tick_atual + self.duracao_combo_ticks

    def _adicionar_obstaculos(self, eventos: list[Evento]) -> None:
        cabeca = self.cobra.cabeca
        proibidas = self._ocupadas()
        for dy in range(-3, 4):
            for dx in range(-3, 4):
                proibidas.add(Celula(cabeca.x + dx, cabeca.y + dy))
        for x in range(self.regras.largura):  # a linha inicial fica sempre livre
            proibidas.add(Celula(x, self.regras.altura // 2))
        novos = sortear_muro(
            self.rng, self.regras.largura, self.regras.altura, self.obstaculos, proibidas
        )
        if novos:
            self.obstaculos |= novos
            eventos.append(ObstaculosNasceram(tuple(sorted(novos))))
