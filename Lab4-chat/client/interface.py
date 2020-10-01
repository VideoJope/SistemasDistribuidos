import sys
import select

from communication import ClientCommunication

#---CAMADA DE INTERFACE DO CLIENTE---
class ClientInterface:

    def __init__(self, hostIP, hostPort):
        #Instancia a Camada de Comunicacao:
        self.comm = ClientCommunication()
        #Chama a Main:
        self.main(hostIP, hostPort)


    def main(self, hostIP, hostPort):

        inputs = [sys.stdin, self.comm.clientSocket] #lista de inputs para a funcao select

        self.establishConnection(hostIP, hostPort)

        #Loop principal:
        while True:
            #Bloqueia se nao houver mensagens do servidor ou comandos no buffer sys.stdin:
            r, w, e = select.select(inputs, [], [])
            for inputToBeRead in r:
                if inputToBeRead == sys.stdin:
                    request = input()
                    self.handleOutgoing(request)
                if inputToBeRead == self.comm.clientSocket:
                    self.handleIncoming()


    #Estabelece conexao com o servidor:
    def establishConnection(self, hostIP, hostPort):
        print("Estabelecendo conexao com servidor...")
        if not self.comm.connectToServer(hostIP, hostPort):
            print("Servidor indisponivel! Fechando o programa.")
            self.comm.disconnect()
            sys.exit(1)
        else: print("Conexao estabelecida!")


    #Trata mensagem a ser enviada ao servidor:
    def handleOutgoing(self, request):

        exitCommands = {'exit', 'Exit', 'quit', 'Quit', 'disconnect', 'Disconnect', '!exit', '!Exit', '!quit', '!Quit', '!disconnect', '!Disconnect'}

        if (request in exitCommands): #se a mensagem estiver contida em exitCommands, nao envia nada ao servidor e fecha a aplicacao
            self.comm.disconnect()
            print("Sessao encerrada. Fechando o programa.")
            sys.exit()
        else:
            self.comm.send(request) #se nao, envia a mensagem ao servidor para ser processada


    #Trata mensagem recebida do servidor: 
    def handleIncoming(self):
        message = self.comm.receive()
        if not message or message == '$QUIT': #fecha aplicacao caso o servidor pare de responder ou a mensagem especial $QUIT seja enviada por ele
            self.comm.disconnect()
            print("Conexao encerrada! Fechando o programa.")
            sys.exit()
        else:
            print(message) #caso contrario, mostra ao usuario a mensagem enviada pelo servidor