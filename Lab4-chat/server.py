import socket
import select
import sys
import threading

HOST = ''                   #interface padrao de comunicacao da maquina
PORT = 5000                 #identifica o port do processo na maquina
MAXPENDINGCONNECTIONS = 10  #indica quantidade de conexoes pendentes permitidas

#Dict contendo os usuarios conectados (key: clientSocket, value: username):
connectedUsers = {}     #usuarios conectados mas nao logados sao identificados pelo username ''
lock = threading.Lock() #lock para acesso concorrente ao dicionario

class RequestValidation:

    def addNewConnection(self, newSocket):
        lock.acquire()
        connectedUsers[newSocket] = ''
        lock.release()
        return True

    def disconnect(self, clientSocket):
        lock.acquire()
        if clientSocket in connectedUsers:
            connectedUsers.pop(clientSocket)
            lock.release()
            return True
        else:
            lock.release()
            return False

    def login(self, clientSocket, newUsername):
        lock.acquire()
        if connectedUsers[clientSocket] != '':
            lock.release()
            return "Voce ja esta logado!"
        elif newUsername in connectedUsers.values():
            lock.release()
            return "Este nome ja esta em uso por outro usuario no momento. Tente novamente com outro nome."
        else:
            connectedUsers[clientSocket] = newUsername
            lock.release()
            return "Login realizado com sucesso! Voce esta pronto para utilizar o chat."

    def logout(self, clientSocket):
        lock.acquire()
        if clientSocket in connectedUsers:
            connectedUsers[clientSocket] = ''
            lock.release()
            return "Voce foi deslogado com sucesso."
        lock.release()
        return "Voce nao esta logado."

    def isUsernameAvailable(self, username):
        if username == '': return False
        lock.acquire()
        outBool = username in connectedUsers.values()
        lock.release()
        return outBool

    def isSocketAvailable(self, socket):
        lock.acquire()
        if socket in connectedUsers and connectedUsers[socket] != '':
            lock.release()
            return True
        lock.release()
        return False

    def getSocket(self, username):
        if username == '': return False
        lock.acquire()
        for socket in connectedUsers:
            if connectedUsers[socket] == username:
                lock.release()
                return socket
        lock.release()
        return False

    def getSocketList(self):
        out = []
        lock.acquire()
        for socket in connectedUsers:
            out.append(socket)
        lock.release()
        return out

    def getUsername(self, socket):
        lock.acquire()
        if socket in connectedUsers:
            out = connectedUsers[socket]
            lock.release()
            return out
        lock.release()
        return False

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


class ServerCommunication:

    def __init__(self, hostIP, hostPort):
        #Cria o descritor de socket:
        self.serverSocket = socket.socket(socket.AF_INET, socket.SOCK_STREAM) #argumento indica comunicacao via internet e TCP
        #Vincula o endereco e porta:
        self.serverSocket.bind((hostIP, hostPort))
        #Se posiciona em modo de espera:
        self.serverSocket.listen(MAXPENDINGCONNECTIONS)
        self.serverSocket.setblocking(False) #torna o socket nao bloqueante, deixando o bloqueio a cargo da funcao select() na main

    def acceptConnection(self):
        clientSocket, addr = self.serverSocket.accept()
        RequestValidation().addNewConnection(clientSocket)
        return clientSocket, addr


    def handleRequests(self, clientSocket, addr):
        self.sendTo("\nBem vindo ao Servidor de Chat! Digite 'help' para ver a lista de comandos disponiveis.\n", clientSocket)
        while True:
            request = self.receiveFrom(clientSocket)
            if not request:
                print("Cliente " + str(addr) + " desconectado.\n")
                RequestValidation().disconnect(clientSocket) #remove o cliente do dicionario global de clientes ativos
                clientSocket.close() #fecha descritor de socket da conexao e sai do loop pelo return
                return
            self.processRequest(clientSocket, request)


    def processRequest(self, clientSocket, request):
        loginCommands = {'login', 'Login', '!login', '!Login'}
        logoutCommands = {'logout', 'Logout', '!logout', '!Logout'}
        listUsersCommands = {'list', 'List', 'users', 'Users', 'lista', '!Lista', '!list', '!List', '!users', '!Users', '!lista', '!Lista', 'listusers', 'Listusers', '!listusers', '!Listusers'}
        helpCommands = {'help', 'Help', '!help', '!Help'}

        validate = RequestValidation()

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
            RequestValidationMessage = validate.login(clientSocket, request.split(' ')[1])
            self.sendTo(RequestValidationMessage, clientSocket)

        #Requisicao de Logout:
        elif(splitRequest[0] in logoutCommands):
            RequestValidationMessage = validate.logout(clientSocket)
            self.sendTo(RequestValidationMessage, clientSocket)

        #Requisicao de Mensagem a Usuario:
        elif(splitRequest[0][0] == '@'):
            if not validate.isSocketAvailable(clientSocket):
                self.sendTo("ERRO - Voce deve estar logado para enviar mensagens.", clientSocket)
                return
            targetSocket = validate.getSocket(splitRequest[0][1:])
            targetUsername = splitRequest[0][1:]
            thisUsername = validate.getUsername(clientSocket)
            try:
                message = splitRequest[1].strip()
                if thisUsername == targetUsername:
                    self.sendTo("ERRO - Voce nao pode se enviar mensagens.", clientSocket)
                elif len(message) == 0:
                    self.sendTo("ERRO - Mensagem a ser enviada nao pode conter somente espacos em branco.", clientSocket)
                elif not validate.isUsernameAvailable(targetUsername):
                    self.sendTo("ERRO - Nao ha usuarios conectados com esse nome no momento.", clientSocket)
                else:
                    self.sendTo(thisUsername + ": " + message, targetSocket)
                    print("[" + thisUsername + " to " + targetUsername + "]: " + message) #log da mensagem para visualizacao do administrador
            except IndexError:
                self.sendTo("ERRO - Mensagem a ser enviada deve estar no formato: @user message", clientSocket)

        #Requisicao para Mostrar Lista de Usuarios Disponiveis:
        elif(splitRequest[0] in listUsersCommands):
            userList = validate.displayAvailableUsers()
            self.sendTo(userList, clientSocket)
        
        #Requisicao Invalida:
        else:
            self.sendTo("ERRO - Comando invalido. Digite 'help' para uma lista de comandos.", clientSocket)

    def broadcast(self, message):
        socketList = RequestValidation().getSocketList()
        for s in socketList:
            self.sendTo(message, s)

    def receiveFrom(self, clientSocket):
        return str(clientSocket.recv(2048), encoding = 'utf-8')

    def sendTo(self, message, clientSocket):
        clientSocket.send(str.encode(message))


class ServerInterface:
    def __init__(self, hostIP, hostPort):
        self.main(hostIP, hostPort)

    def main(self, hostIP, hostPort):
        comm = ServerCommunication(hostIP, hostPort)
        inputs = [sys.stdin, comm.serverSocket]

        print("\n----Servidor de Chat Online----\n Pronto para receber conexoes.\n")
        print("Digite 'help' para ver a lista de comandos disponiveis.\n")

        while True:
        #Aceita conexao, bloqueia se nao houver pedidos de conexao, comandos no buffer sys.stdin ou requisicoes de clientes ja conectados:
            r, w, e = select.select(inputs, [], [])
            for inputToBeRead in r:
                if inputToBeRead == comm.serverSocket:
                    self.initiateClientThread(comm)
                elif inputToBeRead == sys.stdin:
                    adminRequest = input()
                    self.handleAdminRequest(comm, adminRequest)
            

    def initiateClientThread(self, comm):
        clientSocket, address = comm.acceptConnection()
        print("Nova conexao com " + str(address) + " estabelecida.\n")
        #Inicia uma nova thread para responder requisicoes do novo cliente com a funcao handleRequests, recebendo como argumentos clientSocket e address:
        clientThread = threading.Thread(target = comm.handleRequests, args = (clientSocket, address))
        clientThread.start()

    def handleAdminRequest(self, comm, request):
        broadcastCommands = {'broadcast', 'Broadcast', '!broadcast', '!Broadcast'}
        kickCommands = {'kick', 'Kick', '!kick', '!Kick', '!ban', '!Ban'}
        listUsersCommands = {'list', 'List', 'users', 'Users', 'lista', '!Lista', '!list', '!List', '!users', '!Users', '!lista', '!Lista', 'listusers', 'Listusers', '!listusers', '!Listusers'}
        exitCommands = {'exit', 'Exit', 'quit', 'Quit', 'disconnect', 'Disconnect', '!exit', '!Exit', '!quit', '!Quit', '!disconnect', '!Disconnect'}
        helpCommands = {'help', 'Help', '!help', '!Help'}

        validate = RequestValidation()

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
            comm.serverSocket.close()
            comm.broadcast('$QUIT')
            sys.exit()

        #Requisicao para Mostrar Lista de Usuarios Conectados:
        elif splitRequest[0] in listUsersCommands:
            print(validate.displayConnectedUsers()) #incluira todos usuarios conectados, incluindo aqueles que nao estiverem disponiveis (logados) para troca de mensagens

        #Requisicao para Deslogar um Usuario:
        elif splitRequest[0] in kickCommands:
            try:
                targetUsername = splitRequest[1].strip()
                targetSocket = validate.getSocket(targetUsername)
                if targetSocket:
                    validate.logout(targetSocket)
                    comm.sendTo("Voce foi deslogado remotamente pelo servidor.\nUtilize o comando de 'login' para relogar ou 'exit' para sair da aplicacao.", targetSocket)
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
                    comm.broadcast(message)
                    print("Mensagem enviada para todos os clientes conectados.")
                else:
                    print("ERRO - Mensagem a ser enviada nao pode conter somente espacos em branco.")
            except IndexError:
                print("ERRO - Comando deve estar no formato: broadcast message")

        #Requisicao de Mensagem a Usuario:
        elif(splitRequest[0][0] == '@'):
            targetSocket = validate.getSocket(splitRequest[0][1:])
            targetUsername = splitRequest[0][1:]
            try:
                message = splitRequest[1].strip()
                if len(message) == 0:
                    print("ERRO - Mensagem a ser enviada nao pode conter somente espacos em branco.")
                elif not validate.isUsernameAvailable(targetUsername):
                    print("ERRO - Nao ha usuarios conectados com esse nome no momento.")
                else:
                    comm.sendTo("[ADMIN] " + message, targetSocket)
            except IndexError:
                print("ERRO - Mensagem a ser enviada deve estar no formato: @user message")

        #Requisicao Invalida:
        else:
            print("ERRO - Comando invalido. Digite 'help' para uma lista de comandos.")


ServerInterface(HOST, PORT)