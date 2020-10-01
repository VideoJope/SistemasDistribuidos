import socket

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