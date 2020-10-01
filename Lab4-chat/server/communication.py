import socket

from validation import RequestValidation

MAXPENDINGCONNECTIONS = 10  #indica quantidade de conexoes pendentes permitidas

#---CAMADA DE COMUNICACAO DO SERVIDOR---
class ServerCommunication:

    def __init__(self, hostIP, hostPort):
        #Cria o descritor de socket:
        self.serverSocket = socket.socket(socket.AF_INET, socket.SOCK_STREAM) #argumento indica comunicacao via internet e TCP
        #Vincula o endereco e porta:
        self.serverSocket.bind((hostIP, hostPort))
        #Se posiciona em modo de espera:
        self.serverSocket.listen(MAXPENDINGCONNECTIONS)
        self.serverSocket.setblocking(False) #torna o socket nao bloqueante, deixando o bloqueio a cargo da funcao select() na main da camada de interface do admnistrador
        #Instancia a Camada de Validacao:
        self.validate = RequestValidation()


    #Aceita uma nova conexao, incluindo o descritor de socket no dicionario e o retornando junto com o endereco do cliente:
    def acceptConnection(self):
        clientSocket, addr = self.serverSocket.accept()
        self.validate.addNewConnection(clientSocket)
        return clientSocket, addr


    #Metodo que cada Thread associada a um cliente ira chamar para responder a requisicoes:
    def handleRequests(self, clientSocket, addr):
        self.sendTo("\nBem vindo ao Servidor de Chat! Digite 'help' para ver a lista de comandos disponiveis.\n", clientSocket)
        while True:
            request = self.receiveFrom(clientSocket)
            if not request:
                print("Cliente " + str(addr) + " desconectado.\n")
                self.validate.removeConnection(clientSocket) #remove o cliente do dicionario global de clientes ativos
                clientSocket.close() #fecha descritor de socket da conexao e sai do loop pelo return
                return
            self.processRequest(clientSocket, request) #processa a requisicao


    #Processamento de requisicoes de clientes:
    def processRequest(self, clientSocket, request):

        #Listas de Comandos:
        loginCommands = {'login', 'Login', '!login', '!Login'}
        logoutCommands = {'logout', 'Logout', '!logout', '!Logout'}
        listUsersCommands = {'list', 'List', 'users', 'Users', 'lista', '!Lista', '!list', '!List', '!users', '!Users', '!lista', '!Lista', 'listusers', 'Listusers', '!listusers', '!Listusers'}
        helpCommands = {'help', 'Help', '!help', '!Help'}

        #Separa o request em uma lista de 2 strings no primeiro espaco encontrado:
        splitRequest = request.split(' ', 1)

        #Requisicao de Help:
        if splitRequest[0] in helpCommands:
            out = "\nComandos Disponiveis:\n"
            out = out + "help\n  Mostra esta mensagem contendo os comandos disponiveis.\n"
            out = out + "list\n  Mostra a lista de usuarios logados disponiveis para chat.\n"
            out = out + "login username\n  Se torna disponivel para chat com outros usuarios. O nome de usuario 'username' escolhido deve ser unico.\n"
            out = out + "logout\n  Se torna indisponivel para chat com outros usuarios. Deve estar logado.\n"
            out = out + "@username message\n  Envia ao usuario de nome 'username' a mensagem 'message'. Deve estar logado.\n"
            out = out + "exit\n  Desconecta do servidor, fechando a aplicacao.\n"
            self.sendTo(out, clientSocket)

        #Requisicao de Login:
        elif(splitRequest[0] in loginCommands):
            try:
                outputValidationMessage = self.validate.login(clientSocket, request.split(' ')[1])
                self.sendTo(outputValidationMessage, clientSocket)
            except IndexError:
                self.sendTo("ERRO - Mensagem a ser enviada deve estar no formato: login username", clientSocket)

        #Requisicao de Logout:
        elif(splitRequest[0] in logoutCommands):
            outputValidationMessage = self.validate.logout(clientSocket)
            self.sendTo(outputValidationMessage, clientSocket)

        #Requisicao de Mensagem a Usuario:
        elif(len(splitRequest[0]) > 0 and splitRequest[0][0] == '@'):
            if not self.validate.isSocketAvailable(clientSocket):
                self.sendTo("ERRO - Voce deve estar logado para enviar e receber mensagens.", clientSocket)
                return
            targetSocket = self.validate.getSocket(splitRequest[0][1:])
            targetUsername = splitRequest[0][1:]
            thisUsername = self.validate.getUsername(clientSocket)
            try:
                message = splitRequest[1].strip()
                if thisUsername == targetUsername:
                    self.sendTo("ERRO - Voce nao pode se enviar mensagens.", clientSocket)
                elif len(message) == 0:
                    self.sendTo("ERRO - Mensagem a ser enviada nao pode conter somente espacos em branco.", clientSocket)
                elif not self.validate.isUsernameAvailable(targetUsername):
                    self.sendTo("ERRO - Nao ha usuarios conectados com esse nome no momento.", clientSocket)
                else:
                    self.sendTo(thisUsername + ": " + message, targetSocket)
                    print("[" + thisUsername + " to " + targetUsername + "]: " + message) #log da mensagem para visualizacao do administrador
            except IndexError:
                self.sendTo("ERRO - Mensagem a ser enviada deve estar no formato: @user message", clientSocket)

        #Requisicao para Mostrar Lista de Usuarios Disponiveis:
        elif(splitRequest[0] in listUsersCommands):
            userList = self.validate.displayAvailableUsers()
            self.sendTo(userList, clientSocket)       

        #Requisicao Invalida:
        else:
            self.sendTo("ERRO - Comando invalido. Digite 'help' para uma lista de comandos.", clientSocket)


    #Envia a mensagem passada como parametro para todos usuarios conectados no servidor:
    def broadcast(self, message):
        for s in self.validate.getSocketList():
            self.sendTo(message, s)


    #Envia a mensagem (passada por parametro como string) ao socket do cliente apos adequa-la ao protocolo estabelecido:
    def sendTo(self, messageString, clientSocket):
        messageLength = len(messageString)
        if messageLength > 9999:
            messageString = messageString[:9999] #caso a mensagem ultrapasse o limite de 9999 caracteres, remove os caracteres extras
            messageLength = 9999
        #Header no formato "XXXX:", com os 4 Xs sendo digitos representando o tamanho da mensagem que segue os dois pontos:
        header = '0' * (4 - len(str(messageLength))) + str(messageLength) + ':'
        messageString = header + messageString #concatena o header com a mensagem a ser enviada
        message = messageString.encode('utf-8')
        return clientSocket.sendall(message)


    #Recebe uma mensagem do socket passado como parametro, a retornando no formato de string:
    def receiveFrom(self, clientSocket):
        #Recebe o Header contendo o tamanho da Mensagem a ser lida:
        numberBytesRead = 0
        dataChunks = []
        while numberBytesRead < 5:
            data = clientSocket.recv(5 - numberBytesRead)
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
            data = clientSocket.recv(min(messageLength - numberBytesRead, 1024))
            if not data: return False
            dataChunks.append(data)
            numberBytesRead = numberBytesRead + len(data)
        message = str(b''.join(dataChunks), encoding = 'utf-8')

        return message