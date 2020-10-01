import socket
import threading

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

    #Retorna uma lista contendo todos os descritores de socket conectados no servidor:
    def getSocketList(self):
        socketList = []
        lock.acquire()
        for socket in connectedUsers:
            socketList.append(socket)
        lock.release()
        return socketList

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