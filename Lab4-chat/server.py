import socket
import select
import sys
import threading

HOST = ''                   #interface padrao de comunicacao da maquina
PORT = 5000                 #identifica o port do processo na maquina
MAXPENDINGCONNECTIONS = 10  #indica quantidade de conexoes pendentes permitidas

#Dicionario contendo os usuarios conectados (key: clientSocket, value: username):
connectedUsers = {}     #usuarios conectados mas nao logados sao identificados pelo username ''
lock = threading.Lock() #lock para acesso compartilhado ao dicionario

#---CAMADA DE VALIDACAO---:
class RequestValidation:

    #Adiciona o usuario no dicionario, indicando que ele esta deslogado:
    def addNewConnection(self, newSocket):
        lock.acquire()
        connectedUsers[newSocket] = ''
        lock.release()
        return True

    #Remove o usuario do dicionario:
    def removeConnection(self, clientSocket):
        lock.acquire()
        if clientSocket in connectedUsers:
            connectedUsers.pop(clientSocket)
            lock.release()
            return True
        else:
            lock.release()
            return False

    #Loga o usuario associado ao descritor de socket clientSocket com nome de usuario newUsername, modificando o dicionario de acordo:
    def login(self, clientSocket, newUsername):
        lock.acquire()
        if connectedUsers[clientSocket] != '':
            lock.release()
            return "ERRO - Voce ja esta logado!"
        elif newUsername in connectedUsers.values():
            lock.release()
            return "ERRO - Este nome ja esta em uso por outro usuario no momento. Tente novamente com outro nome."
        else:
            connectedUsers[clientSocket] = newUsername
            lock.release()
            return "Login realizado com sucesso! Voce esta pronto para utilizar o chat.\n"

    #Desloga o usuario associado ao descritor de socket passado como parametro, modificando o dicionario de acordo:
    def logout(self, clientSocket):
        lock.acquire()
        if clientSocket in connectedUsers:
            connectedUsers[clientSocket] = ''
            lock.release()
            return "Voce foi deslogado com sucesso."
        lock.release()
        return "ERRO - Voce nao esta logado."

    #Retorna True caso o usuario associado ao username passado como parametro esteja logado (disponivel para mensagens):
    def isUsernameAvailable(self, username):
        if username == '': return False
        lock.acquire()
        outBool = username in connectedUsers.values()
        lock.release()
        return outBool

    #Retorna True caso o usuario associado ao descritor de socket passado como parametro esteja logado (disponivel para mensagens):
    def isSocketAvailable(self, socket):
        lock.acquire()
        if socket in connectedUsers and connectedUsers[socket] != '':
            lock.release()
            return True
        lock.release()
        return False

    #Retorna o descritor de socket de um cliente logado dado seu username (ou False caso nao tenha nenhum usuario logado com esse nome):
    def getSocket(self, username):
        if username == '': return False
        lock.acquire()
        for socket in connectedUsers:
            if connectedUsers[socket] == username:
                lock.release()
                return socket
        lock.release()
        return False

    #Retorna o username de um cliente dado seu descritor de socket (ou False caso o descritor de socket nao esteja presente no dicionario):
    def getUsername(self, socket):
        lock.acquire()
        if socket in connectedUsers:
            out = connectedUsers[socket]
            lock.release()
            return out
        lock.release()
        return False

    #Retorna a lista pronta para impressao de usuarios logados (disponiveis para troca de mensagens):
    def displayAvailableUsers(self):
        out = "\nUsuarios Disponiveis:\n"
        lock.acquire()
        for username in connectedUsers.values():
            if len(username) > 0:
                out = out + '>' + username + '\n'
        lock.release()
        if out == "\nUsuarios Disponiveis:\n":
            out = "\nNenhum Usuario Disponivel.\n"
        return out

    #Retorna a lista pronta para impressao de usuarios conectados, incluindo aqueles que nao estiverem logados (indisponiveis para troca de mensagens):
    def displayConnectedUsers(self):
        out = "\nUsuarios Conectados:\n"
        lock.acquire()
        for socket in connectedUsers:
            username = connectedUsers[socket]
            if username != '':
                username = " -> " + username
            out = out + str(socket.getpeername()) + username + '\n'
        lock.release()
        if out == "\nUsuarios Conectados:\n":
            out = "\nNenhum Usuario Conectado.\n"
        return out



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
        for s in connectedUsers:
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



#---CAMADA DE INTERFACE DO ADMINISTRADOR---
class ServerInterface:

    def __init__(self, hostIP, hostPort):
        #Instancia a Camada de Comunicacao:
        self.comm = ServerCommunication(hostIP, hostPort)
        #Chama a Main:
        self.main(hostIP, hostPort)

    def main(self, hostIP, hostPort):

        print("\n----Servidor de Chat Online----\n Pronto para receber conexoes.\n")
        print("Digite 'help' para ver a lista de comandos disponiveis.\n")

        inputs = [sys.stdin, self.comm.serverSocket] #lista de inputs para a funcao select

        while True:
            #Bloqueia se nao houver pedidos de conexoes novas ou comandos no buffer sys.stdin:
            r, w, e = select.select(inputs, [], [])
            for inputToBeRead in r:
                if inputToBeRead == self.comm.serverSocket:
                    self.initiateClientThread()
                elif inputToBeRead == sys.stdin:
                    adminRequest = input()
                    self.processAdminRequest(adminRequest)
            
    #Aceita conexao e delega o processamento de requisicoes deste cliente a uma nova Thread:
    def initiateClientThread(self):
        clientSocket, address = self.comm.acceptConnection()
        print("Nova conexao com " + str(address) + " estabelecida.\n")
        #Inicia uma nova thread para responder requisicoes do novo cliente com o metodo handleRequests da Camada de Comunicacao:
        clientThread = threading.Thread(target = self.comm.handleRequests, args = (clientSocket, address))
        clientThread.start()

    #Processamento de Requisicoes de Administrador:
    def processAdminRequest(self, request):
        broadcastCommands = {'broadcast', 'Broadcast', '!broadcast', '!Broadcast'}
        kickCommands = {'kick', 'Kick', '!kick', '!Kick', '!ban', '!Ban'}
        listUsersCommands = {'list', 'List', 'users', 'Users', 'lista', '!Lista', '!list', '!List', '!users', '!Users', '!lista', '!Lista', 'listusers', 'Listusers', '!listusers', '!Listusers'}
        exitCommands = {'exit', 'Exit', 'quit', 'Quit', 'disconnect', 'Disconnect', '!exit', '!Exit', '!quit', '!Quit', '!disconnect', '!Disconnect'}
        helpCommands = {'help', 'Help', '!help', '!Help'}

        validate = self.comm.validate #atribuicao realizada para melhorar legibilidade

        #Separa o request em uma lista de 2 strings no primeiro espaco encontrado:
        splitRequest = request.split(' ', 1)

        #Requisicao de Help:
        if splitRequest[0] in helpCommands:
            print("\nComandos Disponiveis ao Administrador:")
            print("help\n  Mostra esta mensagem contendo os comandos disponiveis.")
            print("list\n  Mostra a lista de todos clientes conectados no servidor e seus nomes de usuario caso estejam logados.")
            print("broadcast message\n  Envia a todos clientes conectados a mensagem 'message'.")
            print("@username message\n  Envia ao usuario de nome 'username' a mensagem 'message'. O usuario nao pode responder a mensagens de administrador.")
            print("kick username\n  Desloga o usuario de nome 'username' do servico de chat. Isso nao desconecta o usuario do servidor.")
            print("exit\n  Desconecta todos os clientes e finaliza a aplicacao servidor.\n")

        #Requisicao de Saida:
        elif splitRequest[0] in exitCommands:
            print("Desligando o servidor.")
            self.comm.serverSocket.close()
            self.comm.broadcast('$QUIT') #mensagem especial do protocolo da camada de aplicacao para desconectar usuarios
            sys.exit()

        #Requisicao para Mostrar Lista de Usuarios Conectados:
        elif splitRequest[0] in listUsersCommands:
            print(validate.displayConnectedUsers()) #incluira todos usuarios conectados na lista, incluindo aqueles que nao estiverem disponiveis (logados) para troca de mensagens

        #Requisicao para Deslogar um Usuario:
        elif splitRequest[0] in kickCommands:
            try:
                targetUsername = splitRequest[1].strip()
                targetSocket = validate.getSocket(targetUsername)
                if targetSocket:
                    validate.logout(targetSocket)
                    self.comm.sendTo("Voce foi deslogado remotamente pelo servidor.\nUtilize o comando de 'login' para relogar ou 'exit' para sair da aplicacao.", targetSocket)
                    print("Usuario deslogado com sucesso.")
                else:
                    print("ERRO - Usuario invalido.")
            except IndexError:
                print("ERRO - Comando deve estar no formato: kick username")

        #Requisicao de Broadcast:
        elif splitRequest[0] in broadcastCommands:
            try:
                message = splitRequest[1].strip()
                if len(message) > 0:
                    message = "[BROADCAST] " + message
                    self.comm.broadcast(message)
                    print("Mensagem enviada para todos os clientes conectados.")
                else:
                    print("ERRO - Mensagem a ser enviada nao pode conter somente espacos em branco.")
            except IndexError:
                print("ERRO - Comando deve estar no formato: broadcast message")

        #Requisicao de Mensagem a Usuario:
        elif(len(splitRequest[0]) > 0 and splitRequest[0][0] == '@'):
            targetSocket = validate.getSocket(splitRequest[0][1:])
            targetUsername = splitRequest[0][1:]
            try:
                message = splitRequest[1].strip()
                if len(message) == 0:
                    print("ERRO - Mensagem a ser enviada nao pode conter somente espacos em branco.")
                elif not validate.isUsernameAvailable(targetUsername):
                    print("ERRO - Nao ha usuarios conectados com esse nome no momento.")
                else:
                    self.comm.sendTo("[ADMIN] " + message, targetSocket)
            except IndexError:
                print("ERRO - Mensagem a ser enviada deve estar no formato: @user message")

        #Requisicao Invalida:
        else:
            print("ERRO - Comando invalido. Digite 'help' para uma lista de comandos.")


ServerInterface(HOST, PORT)