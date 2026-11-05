"""Reprodução dos sons gerados; sem placa de som o jogo segue mudo, sem erro."""
from __future__ import annotations

import pygame

from cobrinha.audio import sintetizador
from cobrinha.persistencia import Configuracoes

TAXA_PEDIDA = 22050
INTERVALO_MINIMO_MS = 45
VOLUME_MUSICA_ABAFADA = 0.35


def preparar_mixer() -> None:
    """Deve ser chamada antes de ``pygame.init``."""
    pygame.mixer.pre_init(TAXA_PEDIDA, -16, 2, 256, allowedchanges=0)


class Audio:
    """Toca efeitos e música respeitando volumes e o modo mudo."""

    def __init__(self, config: Configuracoes) -> None:
        self.config = config
        self.sons: dict[str, pygame.mixer.Sound] = {}
        self._ultimo_toque: dict[str, int] = {}
        self._composicao = None
        self._musica: pygame.mixer.Sound | None = None
        self._canal_musica: pygame.mixer.Channel | None = None
        self._abafada = False
        self.canais = 0
        self.taxa = 0
        formato = pygame.mixer.get_init()
        if not formato:
            return
        self.taxa, _, self.canais = formato
        pygame.mixer.set_num_channels(16)
        pygame.mixer.set_reserved(1)
        self._canal_musica = pygame.mixer.Channel(0)
        for nome, amostras in sintetizador.receitas(self.taxa).items():
            self.sons[nome] = pygame.mixer.Sound(
                buffer=sintetizador.para_pcm(amostras, self.canais)
            )
        self._composicao = sintetizador.gerar_musica(self.taxa, self.canais)

    @property
    def ativo(self) -> bool:
        return bool(self.sons)

    def tocar(self, nome: str, volume: float = 1.0) -> None:
        """Toca um efeito, evitando repeti-lo no mesmo instante."""
        som = self.sons.get(nome)
        if som is None or self.config.mudo:
            return
        agora = pygame.time.get_ticks()
        if agora - self._ultimo_toque.get(nome, -1000) < INTERVALO_MINIMO_MS:
            return
        self._ultimo_toque[nome] = agora
        som.set_volume(self.config.volume_efeitos * volume)
        som.play()

    def comer(self, combo: int) -> None:
        """Toca a mordida, mais aguda conforme o combo sobe."""
        self.tocar(f"comer{min(combo, 8) - 1}")

    def passo(self) -> None:
        """Avança a composição da música um pouco por quadro."""
        if self._composicao is None:
            return
        resultado = next(self._composicao, None)
        if resultado is None:
            return
        self._composicao = None
        self._musica = pygame.mixer.Sound(buffer=resultado)
        self._canal_musica.play(self._musica, loops=-1, fade_ms=1500)
        self.aplicar_volumes()

    def abafar(self, abafada: bool) -> None:
        """Baixa a música durante a pausa e as telas finais."""
        self._abafada = abafada
        self.aplicar_volumes()

    def aplicar_volumes(self) -> None:
        """Reaplica volume e mudo na música."""
        if self._canal_musica is None:
            return
        volume = 0.0 if self.config.mudo else self.config.volume_musica
        if self._abafada:
            volume *= VOLUME_MUSICA_ABAFADA
        self._canal_musica.set_volume(volume)
