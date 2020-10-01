import socket
import sys
import select

HOST = 'localhost'          #configuracao de ip da aplicacao servidor
PORT = 5000                 #identifica o port do processo na maquina
FIXEDMESSAGESIZE = 1024     #indica o tamanho em bytes fixo das mensagens trocadas entre cliente e servidor

#---CAMADA DE COMUNICACAO DO CLIENTE---
class ClientCommunication:

    #Instancia o descritor de socket:
    def __init__(self):
        self.clientSocket = socket.socket()

    #Estabelece a conexao com o servidor:
    def connectToServer(self, hostIP, hostPort):
        try:
            self.clientSocket.connect((hostIP, hostPort))
        except:
            self.disconnect()
            return False
        return True

    #Fecha o descritor de socket:
    def disconnect(self):
        self.clientSocket.close()


    #Envia a mensagem (passada por parametro como string) apos adequa-la ao protocolo estabelecido:
    def send(self, messageString):
        messageLength = len(messageString)
        if messageLength > 9999:
            messageString = messageString[:9999] #caso a mensagem ultrapasse o limite de 9999 caracteres, remove os caracteres extras
            messageLength = 9999
        #Header no formato "XXXX:", com os 4 Xs sendo digitos representando o tamanho da mensagem que segue os dois pontos:
        header = '0' * (4 - len(str(messageLength))) + str(messageLength) + ':'
        messageString = header + messageString #concatena o header com a mensagem a ser enviada
        message = messageString.encode('utf-8')
        return self.clientSocket.sendall(message)


    #Recebe uma mensagem, a retornando no formato de string:
    def receive(self):
        #Recebe o Header contendo o tamanho da Mensagem a ser lida:
        numberBytesRead = 0
        dataChunks = []
        while numberBytesRead < 5:
            data = self.clientSocket.recv(5 - numberBytesRead)
            if not data: return False
            dataChunks.append(data)
            numberBytesRead = numberBytesRead + len(data)
        header = str(b''.join(dataChunks), encoding = 'utf-8')
        if(header[-1] != ':'): return False

        messageLength = int(header[:4]) #tamanho da mensagem, obtido apartir do header

        #Recebe a Mensagem:
        numberBytesRead = 0
        dataChunks = []
        while numberBytesRead < messageLength:
            data = self.clientSocket.recv(min(messageLength - numberBytesRead, 1024))
            if not data: return False
            dataChunks.append(data)
            numberBytesRead = numberBytesRead + len(data)
        message = str(b''.join(dataChunks), encoding = 'utf-8')

        return message


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
            print("Sessao encerrada remotamente pelo administrador. Fechando o programa.")
            sys.exit()
        else:
            print(message) #caso contrario, mostra ao usuario a mensagem enviada pelo servidor


ClientInterface(HOST, PORT)