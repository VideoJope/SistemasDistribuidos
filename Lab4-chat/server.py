import socket
import select
import sys
import threading

HOST = ''   #interface padrao de comunicacao da maquina
PORT = 5000 #identifica o port do processo na maquina

#TODO:
#>IMPLEMENTAR O REQUERIMENTO DE !HELP DOS CLIENTES/ADMIN
#>IMPLEMENTAR A MENSAGEM INICIAL PARA OS CLIENTES/ADMIN

activeUsers = {}        #dict contendo os usuarios logados (key: clientSocket, value: username)
lock = threading.Lock() #lock para acesso ao dicionario

class RequestValidation:


    def newConnection(self, newSocket):
        lock.acquire()
        activeUsers[newSocket] = ''
        lock.release()
        return True

    def disconnect(self, clientSocket):
        lock.acquire()
        if clientSocket in activeUsers:
            activeUsers.pop(clientSocket)
            lock.release()
            return True
        else:
            lock.release()
            return False

    def login(self, clientSocket, newUsername):
        lock.acquire()
        if activeUsers[clientSocket] != '':
            lock.release()
            return "Voce ja esta logado!"
        elif newUsername in activeUsers.values():
            lock.release()
            return "Este nome ja esta em uso por outro usuario no momento. Tente novamente com outro nome."
        else:
            activeUsers[clientSocket] = newUsername
            lock.release()
            return "Login realizado com sucesso! Voce esta pronto para utilizar o chat."

    def logout(self, clientSocket):
        lock.acquire()
        if clientSocket in activeUsers:
            activeUsers[clientSocket] = ''
            lock.release()
            return "Voce foi deslogado com sucesso."
        lock.release()
        return "Voce nao esta logado."

    def isUsernameAvailable(self, username):
        if username == '': return False
        lock.acquire()
        outBool = username in activeUsers.values()
        lock.release()
        return outBool

    def isSocketAvailable(self, socket):
        lock.acquire()
        if socket in activeUsers and activeUsers[socket] != '':
            lock.release()
            return True
        lock.release()
        return False

    def getSocket(self, username):
        if username == '': return False
        lock.acquire()
        for socket in activeUsers:
            if activeUsers[socket] == username:
                lock.release()
                return socket
        lock.release()
        return False

    def getSocketList(self):
        out = []
        lock.acquire()
        for socket in activeUsers:
            out.append(socket)
        lock.release()
        return out

    def getUsername(self, socket):
        lock.acquire()
        if socket in activeUsers:
            out = activeUsers[socket]
            lock.release()
            return out
        lock.release()
        return False

    def displayAvailableUsers(self):
        out = "\nUsuarios Disponiveis:\n"
        lock.acquire()
        for username in activeUsers.values():
            if len(username) > 0:
                out = out + '>' + username + '\n'
        lock.release()
        if out == "\nUsuarios Disponiveis:\n":
            out = "\nNenhum Usuario Disponivel.\n"
        return out

    def displayConnectedUsers(self):
        out = "\nUsuarios Conectados:\n"
        lock.acquire()
        for socket in activeUsers:
            username = activeUsers[socket]
            if username != '':
                username = " -> " + username
            out = out + str(socket.getpeername()) + username + '\n'
        lock.release()
        return out


class ServerCommunication:

    def __init__(self, hostIP, hostPort):
        #Cria o descritor de socket:
        self.serverSocket = socket.socket(socket.AF_INET, socket.SOCK_STREAM) #argumento indica comunicacao via internet e TCP
        #Vincula o endereco e porta:
        self.serverSocket.bind((hostIP, hostPort))
        #Se posiciona em modo de espera:
        self.serverSocket.listen(10)         #argumento indica quantidade de conexoes pendentes permitidas
        self.serverSocket.setblocking(False) #torna o socket nao bloqueante, deixando o bloqueio a cargo da funcao select() na main

    def acceptConnection(self):
        clientSocket, addr = self.serverSocket.accept()
        RequestValidation().newConnection(clientSocket)
        return clientSocket, addr


    def handleRequests(self, clientSocket, addr):
        while True:
            request = self.receiveFrom(clientSocket)
            if not request:
                print("Cliente " + str(addr) + " desconectado.\n")
                RequestValidation().disconnect(clientSocket) #remove o cliente do dicionario global de clientes ativos
                clientSocket.close() #fecha descritor de socket da conexao e sai do loop pelo return
                return
            #print("Requisicao do cliente " + str(addr) + " recebida.")
            self.processRequest(clientSocket, request)


    def processRequest(self, clientSocket, request):
        loginCommands = {'login', 'Login', '!login', '!Login'}
        logoutCommands = {'logout', 'Logout', '!logout', '!Logout'}
        listUsersCommands = {'list', 'List', 'users', 'Users', 'lista', '!Lista', '!list', '!List', '!users', '!Users', '!lista', '!Lista', 'listusers', 'Listusers', '!listusers', '!Listusers'}
        helpCommands = {'help', 'Help', '!help', '!Help'}

        validate = RequestValidation()

        splitRequest = request.split(' ', 1)

        #Requisicao de Help:
        #TODO

        #Requisicao de Login:
        if(splitRequest[0] in loginCommands):
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
        #TODO

        #Requisicao de Saida:
        if splitRequest[0] in exitCommands:
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