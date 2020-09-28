import socket
import select
import sys
import threading

HOST = ''   #interface padrao de comunicacao da maquina
PORT = 5000 #identifica o port do processo na maquina

#TODO:
#>TERMINAR DE IMPLEMENTAR O PROCESSAMNETO DE REQUERIMENTOS DOS CLIENTES
#>IMPLEMENTAR O RESTO DA INTERFACE DE ADMIN

activeUsers = {}        #dict contendo os usuarios logados (key: username, value: clientSocket)
lock = threading.Lock() #lock para acesso ao dicionario

class Validation:

    def login(newSocket, newUsername):
        lock.acquire()
        for s in activeUsers.values():
            if s == newSocket:
                lock.release()
                return "Voce ja esta logado!"
        if not newUsername in activeUsers:
                activeUsers[newUsername] = newSocket
                lock.release()
                return "Login realizado com sucesso! Voce esta pronto para utilizar o chat."
        else:
            lock.release()
            return "Este nome ja esta em uso por outro usuario no momento. Tente novamente com outro nome."

    def logout(clientSocket):
        lock.acquire()
        for username in activeUsers:
            if activeUsers[username] == clientSocket:
                activeUsers.pop(username)
                lock.release()
                return "Voce foi deslogado com sucesso."
        lock.release()
        return "Voce nao esta logado."

    def isUsernameConnected(username):
        lock.acquire()
        out = username in activeUsers
        lock.release()
        return out

    def isSocketConnected(socket):
        lock.acquire()
        for s in activeUsers.values():
            if s == socket:
                lock.release()
                return True
        lock.release()
        return False

    def getSocket(username):
        lock.acquire()
        if username in activeUsers:
            socket = activeUsers[username]
            lock.release()
            return socket
        else:
            lock.release()
            return False

    def getUsername(socket):
        lock.acquire()
        for username in activeUsers:
            if activeUsers[username] == socket:
                lock.release()
                return username
        lock.release()
        return False


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
        return clientSocket, addr


    def handleRequests(self, clientSocket, addr):
        while True:
            request = self.receiveFrom(clientSocket)
            if not request:
                print("Cliente " + str(addr) + " desconectado.\n")
                Validation.logout(clientSocket) #remove o cliente do dicionario global de clientes ativos
                clientSocket.close() #fecha descritor de socket da conexao e sai do loop pelo return
                return
            print("Requisicao do cliente " + str(addr) + " recebida.")
            self.processRequest(clientSocket, addr, request)


    def processRequest(self, clientSocket, addr, request):
        loginCommands = {'login', 'Login'}
        logoutCommands = {'logout', 'Logout'}

        splitRequest = request.split(' ', 1)

        #Requisicao de Login:
        if(splitRequest[0] in loginCommands):
            validationMessage = Validation.login(clientSocket, request.split(' ')[1])
            self.sendTo(validationMessage, clientSocket)
            print(activeUsers)

        #Requisicao de Logout:
        elif(splitRequest[0] in logoutCommands):
            validationMessage = Validation.logout(clientSocket)
            self.sendTo(validationMessage, clientSocket)
            print(activeUsers)

        #Requisicao de mensagem a outro usuário:
        elif(splitRequest[0][0] == '@'):
            if not Validation.isSocketConnected(clientSocket):
                self.sendTo("ERRO - Voce deve estar logado para enviar mensagens.", clientSocket)
                return
            targetSocket = Validation.getSocket(splitRequest[0][1:])
            if targetSocket:
                try:
                    message = splitRequest[1].strip()
                    if len(message) > 0:
                        self.sendTo("[" + Validation.getUsername(clientSocket) + "]: " + message, targetSocket)
                    else:
                        self.sendTo("ERRO - Mensagem a ser enviada nao pode conter somente espacos em branco.", clientSocket)
                except IndexError:
                    self.sendTo("ERRO - Mensagem a ser enviada deve estar no formato: @user message", clientSocket)
            else:
                self.sendTo("ERRO - Nao ha usuarios conectados com esse nome no momento.", clientSocket)
        




    def receiveFrom(self, clientSocket):
        return str(clientSocket.recv(2048), encoding = 'utf-8')

    def sendTo(self, message, clientSocket):
        clientSocket.send(str.encode(message))


class ServerInterface:
    def __init__(self, hostIP, hostPort):
        self.main(hostIP, hostPort)

    def main(self, hostIP, hostPort):
        comm = ServerCommunication(hostIP, hostPort)
        serverSocket = comm.serverSocket
        inputs = [sys.stdin, serverSocket]

        while True:
        #Aceita conexao, bloqueia se nao houver pedidos de conexao, comandos no buffer sys.stdin ou requisicoes de clientes ja conectados:
            r, w, e = select.select(inputs, [], [])
            for inputToBeRead in r:
                if inputToBeRead == serverSocket:
                    self.initiateClientThread(comm)
                elif inputToBeRead == sys.stdin:
                    cmd = input()
                    if cmd == 'exit':
                        #Fecha o descritor de socket principal da aplicacao servidor e termina a aplicacao:
                        print("Desligando o servidor.")
                        serverSocket.close()
                        sys.exit()
                    if cmd == 'printa':
                        print(activeUsers)
            

    def initiateClientThread(self, comm):
        clientSocket, address = comm.acceptConnection()
        print("Nova conexao com " + str(address) + " estabelecida.\n")
        #Inicia uma nova thread para responder requisicoes do novo cliente com a funcao handleRequests, recebendo como argumentos clientSocket e address:
        clientThread = threading.Thread(target = comm.handleRequests, args = (clientSocket, address))
        clientThread.start()

    
ServerInterface(HOST, PORT)