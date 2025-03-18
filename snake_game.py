import pygame
import random
import sys

# Inicialização do Pygame
pygame.init()

# Cores
PRETO = (0, 0, 0)
BRANCO = (255, 255, 255)
VERMELHO = (255, 0, 0)
VERDE = (0, 255, 0)

# Configurações da tela
LARGURA = 800
ALTURA = 600
TAMANHO_BLOCO = 20
VELOCIDADE = 15

# Criação da tela
tela = pygame.display.set_mode((LARGURA, ALTURA))
pygame.display.set_caption('Jogo da Cobra')
relogio = pygame.time.Clock()

class Cobra:
    def __init__(self):
        self.reiniciar()

    def reiniciar(self):
        self.posicao = [100, 50]
        self.corpo = [[100, 50], [90, 50], [80, 50]]
        self.direcao = "DIREITA"
        self.mudar_direcao = self.direcao

    def mudar_direcao_cobra(self, nova_direcao):
        if nova_direcao == "DIREITA" and not self.direcao == "ESQUERDA":
            self.direcao = "DIREITA"
        if nova_direcao == "ESQUERDA" and not self.direcao == "DIREITA":
            self.direcao = "ESQUERDA"
        if nova_direcao == "CIMA" and not self.direcao == "BAIXO":
            self.direcao = "CIMA"
        if nova_direcao == "BAIXO" and not self.direcao == "CIMA":
            self.direcao = "BAIXO"

    def mover(self, comida_pos):
        if self.direcao == "DIREITA":
            self.posicao[0] += TAMANHO_BLOCO
        if self.direcao == "ESQUERDA":
            self.posicao[0] -= TAMANHO_BLOCO
        if self.direcao == "CIMA":
            self.posicao[1] -= TAMANHO_BLOCO
        if self.direcao == "BAIXO":
            self.posicao[1] += TAMANHO_BLOCO

        self.corpo.insert(0, list(self.posicao))
        
        # Verificar se a cobra comeu a comida
        if (abs(self.posicao[0] - comida_pos[0]) < TAMANHO_BLOCO and 
            abs(self.posicao[1] - comida_pos[1]) < TAMANHO_BLOCO):
            return True
        else:
            self.corpo.pop()
            return False

    def verificar_colisao(self):
        if self.posicao[0] >= LARGURA or self.posicao[0] < 0:
            return True
        if self.posicao[1] >= ALTURA or self.posicao[1] < 0:
            return True
        for segmento in self.corpo[1:]:
            if self.posicao == segmento:
                return True
        return False

    def desenhar(self):
        for pos in self.corpo:
            pygame.draw.rect(tela, VERDE, pygame.Rect(pos[0], pos[1], TAMANHO_BLOCO, TAMANHO_BLOCO))

class Comida:
    def __init__(self):
        self.posicao = self.gerar_posicao()

    def gerar_posicao(self):
        x = random.randrange(0, LARGURA - TAMANHO_BLOCO, TAMANHO_BLOCO)
        y = random.randrange(0, ALTURA - TAMANHO_BLOCO, TAMANHO_BLOCO)
        return [x, y]

    def desenhar(self):
        pygame.draw.rect(tela, VERMELHO, pygame.Rect(self.posicao[0], self.posicao[1], TAMANHO_BLOCO, TAMANHO_BLOCO))

def mostrar_game_over(pontuacao):
    fonte = pygame.font.Font(None, 74)
    texto_game_over = fonte.render('GAME OVER!', True, BRANCO)
    texto_pontuacao = fonte.render(f'Pontuação: {pontuacao}', True, BRANCO)
    texto_reiniciar = fonte.render('Pressione ESPAÇO para jogar novamente', True, BRANCO)
    
    tela.blit(texto_game_over, (LARGURA//2 - texto_game_over.get_width()//2, ALTURA//2 - 100))
    tela.blit(texto_pontuacao, (LARGURA//2 - texto_pontuacao.get_width()//2, ALTURA//2))
    tela.blit(texto_reiniciar, (LARGURA//2 - texto_reiniciar.get_width()//2, ALTURA//2 + 100))
    pygame.display.flip()

def main():
    cobra = Cobra()
    comida = Comida()
    pontuacao = 0
    fonte = pygame.font.Font(None, 36)
    game_over = False

    while True:
        for evento in pygame.event.get():
            if evento.type == pygame.QUIT:
                pygame.quit()
                sys.exit()
            elif evento.type == pygame.KEYDOWN:
                if game_over and evento.key == pygame.K_SPACE:
                    cobra.reiniciar()
                    comida.posicao = comida.gerar_posicao()
                    pontuacao = 0
                    game_over = False
                elif not game_over:
                    if evento.key == pygame.K_RIGHT:
                        cobra.mudar_direcao_cobra("DIREITA")
                    elif evento.key == pygame.K_LEFT:
                        cobra.mudar_direcao_cobra("ESQUERDA")
                    elif evento.key == pygame.K_UP:
                        cobra.mudar_direcao_cobra("CIMA")
                    elif evento.key == pygame.K_DOWN:
                        cobra.mudar_direcao_cobra("BAIXO")

        if not game_over:
            # Movimento da cobra
            if cobra.mover(comida.posicao):
                pontuacao += 1
                comida.posicao = comida.gerar_posicao()

            # Verificar colisão
            if cobra.verificar_colisao():
                game_over = True
                mostrar_game_over(pontuacao)
            else:
                # Desenhar
                tela.fill(PRETO)
                cobra.desenhar()
                comida.desenhar()
                
                # Mostrar pontuação
                texto_pontuacao = fonte.render(f'Pontuação: {pontuacao}', True, BRANCO)
                tela.blit(texto_pontuacao, (10, 10))

                pygame.display.flip()
                relogio.tick(VELOCIDADE)

if __name__ == "__main__":
    main() 