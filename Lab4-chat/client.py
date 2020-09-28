import socket
import sys
import select

HOST = 'localhost' #configuracao de ip da aplicacao servidor
PORT = 5000        #identifica o port do processo na maquina


class ClientCommunication:
    def __init__(self):
        self.clientSocket = socket.socket()

    def connectToServer(self, hostIP, hostPort):
        try:
            self.clientSocket.connect((hostIP, hostPort))
        except:
            self.disconnect()
            return False
        return True

    def disconnect(self):
        self.clientSocket.close()

    def send(self, request):
        self.clientSocket.send(str.encode(request))

    def receive(self):
        return str(self.clientSocket.recv(2048), encoding = 'utf-8')


class ClientInterface:

    exitCommands = {"exit", "Exit", "logout", "Logout", "quit", "Quit"}

    def __init__(self, hostIP, hostPort):
        self.main(hostIP, hostPort)


    def main(self, hostIP, hostPort):
        comm = ClientCommunication()
        clientSocket = comm.clientSocket
        inputs = [sys.stdin, clientSocket]

        self.establishConnection(comm, hostIP, hostPort)

        while True:
            r, w, e = select.select(inputs, [], [])
            for inputToBeRead in r:
                if inputToBeRead == sys.stdin:
                    request = input()
                    self.handleOutgoing(comm, request)
                if inputToBeRead == clientSocket:
                    self.handleIncoming(comm)


    def establishConnection(self, comm, hostIP, hostPort):
        print("Estabelecendo conexao com servidor...")
        if not comm.connectToServer(hostIP, hostPort):
            print("Servidor indisponivel! Fechando o programa.")
            comm.disconnect()
            sys.exit(1)
        else: print("Conexao estabelecida!")


    def handleOutgoing(self, comm, request):
        if (request in self.exitCommands):
            comm.disconnect()
            print("Sessao encerrada. Fechando o programa.")
            sys.exit()
        else:
            comm.send(request)

    def handleIncoming(self, comm):
        message = comm.receive()
        if message == '$QUIT':
            comm.disconnect()
            print("Sessao encerrada remotamente pelo administrador. Fechando o programa.")
            sys.exit()
        else:
            print(message)


ClientInterface(HOST, PORT)